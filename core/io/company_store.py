"""CompanyProfile の JSON 永続化（outputs/profiles/<company_id>.json）。

設計方針:
    - 実データ Excel/CSV 取込 → CompanyProfile 構築 → JSON 保存 → サンプル3社と同じ
      ID 解決ルート（get_sample）で参照される。
    - outputs/ は gitignore 対象なので機密情報の混入リスクを切り離す。
    - スキーマ進化への備えとして Pydantic v2 の model_dump_json を使い、
      未知フィールドは Pydantic 既定で無視（旧 JSON も読める）。
    - LOGI_STORAGE_BACKEND=s3 のときは保存後に S3 にも複製、読出時は S3 から優先
      フェッチする（Lambda 上では /tmp はリクエスト間で共有されないため）。
"""
from __future__ import annotations

import os
from pathlib import Path

from core.static.sample_company import CompanyProfile

DEFAULT_PROFILES_DIR = Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs")) / "profiles"


def _resolve_base_dir(base_dir: Path | None) -> Path:
    """base_dir が None なら**実行時に**モジュール変数 DEFAULT_PROFILES_DIR を参照する。

    Python のデフォルト引数は関数定義時にバインドされるため、テストや実行時に
    DEFAULT_PROFILES_DIR を差し替えても既存挙動が反映されない。これを避けるため
    None を sentinel として明示的に実行時解決する。
    """
    return DEFAULT_PROFILES_DIR if base_dir is None else base_dir


def _profile_path(company_id: str, base_dir: Path) -> Path:
    return base_dir / f"{company_id}.json"


def save_company_profile(
    profile: CompanyProfile,
    base_dir: Path | None = None,
) -> Path:
    """CompanyProfile を JSON ファイルに保存する。

    Args:
        profile: 保存対象の CompanyProfile
        base_dir: 出力ディレクトリ（None なら DEFAULT_PROFILES_DIR を実行時解決）

    Returns:
        書き出しファイルのパス
    """
    resolved = _resolve_base_dir(base_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    path = _profile_path(profile.company_id, resolved)
    path.write_text(
        profile.model_dump_json(indent=2),
        encoding="utf-8",
    )
    _maybe_publish_to_s3(path)
    return path


def load_company_profile_from_json(
    company_id: str,
    base_dir: Path | None = None,
) -> CompanyProfile | None:
    """ID から保存済み CompanyProfile JSON を読み込む。

    LOGI_STORAGE_BACKEND=s3 のときは S3 から先にフェッチし、無ければローカル探索。
    """
    s3_data = _maybe_fetch_from_s3(company_id)
    if s3_data is not None:
        return CompanyProfile.model_validate_json(s3_data)

    resolved = _resolve_base_dir(base_dir)
    path = _profile_path(company_id, resolved)
    if not path.is_file():
        return None
    return CompanyProfile.model_validate_json(path.read_text(encoding="utf-8"))


def _maybe_publish_to_s3(path: Path) -> None:
    """S3 backend 利用時はローカル書出後に複製。それ以外は no-op。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    import contextlib

    from core.storage import get_storage

    # 失敗してもローカル保存は成功している。Lambda の場合は呼出元が
    # CloudWatch Logs で気付ける。ここでは握りつぶして UI を壊さない。
    with contextlib.suppress(Exception):
        get_storage().publish(path)


def _maybe_fetch_from_s3(company_id: str) -> str | None:
    """S3 backend 利用時は profiles/<id>.json を S3 から取得。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return None
    from core.storage import get_storage

    storage = get_storage()
    data = storage.read_bytes(f"profiles/{company_id}.json")
    return data.decode("utf-8") if data is not None else None
