"""CompanyPackageOverride の JSON 永続化（outputs/profiles/<id>_override.json）。

CompanyProfile（事実）と CompanyPackageOverride（判断）を意図的に分離し、
個社差分のみを別ファイルで管理する。company_store.py と同じ読み書きパターン
（環境変数 LOGI_OUTPUTS_DIR を実行時に解決し、S3 backend にも追従）。

設計方針:
    - Pydantic v2 model_dump_json で書き出し、未知フィールドは既定で無視
      → 旧 JSON も読める（前方互換）
    - LOGI_STORAGE_BACKEND=s3 のときは S3 にも複製、読出時は S3 を優先
      → Lambda 上では /tmp はリクエスト間共有されないため

plan: plans/b-c-flickering-pixel.md §段階 c.5
"""
from __future__ import annotations

import os
from pathlib import Path

from core.playbook.industry_packages import CompanyPackageOverride

DEFAULT_PROFILES_DIR = Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs")) / "profiles"


def _resolve_base_dir(base_dir: Path | None) -> Path:
    """base_dir が None なら**実行時に** LOGI_OUTPUTS_DIR を再評価する。

    Python のデフォルト引数は関数定義時にバインドされるため、テストや実行時に
    LOGI_OUTPUTS_DIR を差し替えても既存挙動が反映されない。これを避けるため
    None を sentinel として明示的に実行時解決する（company_store.py と同じ）。
    """
    if base_dir is not None:
        return base_dir
    return Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs")) / "profiles"


def _override_path(company_id: str, base_dir: Path) -> Path:
    return base_dir / f"{company_id}_override.json"


def save_override(
    override: CompanyPackageOverride,
    base_dir: Path | None = None,
) -> Path:
    """CompanyPackageOverride を JSON ファイルに保存する。

    Args:
        override: 保存対象の CompanyPackageOverride
        base_dir: 出力ディレクトリ（None なら LOGI_OUTPUTS_DIR/profiles を実行時解決）

    Returns:
        書き出しファイルのパス
    """
    resolved = _resolve_base_dir(base_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    path = _override_path(override.company_id, resolved)
    path.write_text(override.model_dump_json(indent=2), encoding="utf-8")
    _maybe_publish_to_s3(path)
    return path


def load_override(
    company_id: str, base_dir: Path | None = None,
) -> CompanyPackageOverride | None:
    """ID から保存済み CompanyPackageOverride JSON を読み込む。

    LOGI_STORAGE_BACKEND=s3 のときは S3 から先にフェッチし、無ければローカル探索。
    存在しなければ None を返す（個社が override を持たない通常状態）。
    """
    s3_data = _maybe_fetch_from_s3(company_id)
    if s3_data is not None:
        return CompanyPackageOverride.model_validate_json(s3_data)

    resolved = _resolve_base_dir(base_dir)
    path = _override_path(company_id, resolved)
    if not path.is_file():
        return None
    return CompanyPackageOverride.model_validate_json(
        path.read_text(encoding="utf-8"),
    )


def _maybe_publish_to_s3(path: Path) -> None:
    """S3 backend 利用時はローカル書出後に複製。それ以外は no-op。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    import contextlib

    from core.storage import get_storage

    with contextlib.suppress(Exception):
        get_storage().publish(path)


def _maybe_fetch_from_s3(company_id: str) -> str | None:
    """S3 backend 利用時は profiles/<id>_override.json を S3 から取得。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return None
    from core.storage import get_storage

    storage = get_storage()
    data = storage.read_bytes(f"profiles/{company_id}_override.json")
    return data.decode("utf-8") if data is not None else None
