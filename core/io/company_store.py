"""CompanyProfile の JSON 永続化（outputs/profiles/<company_id>.json）。

設計方針:
    - 実データ Excel/CSV 取込 → CompanyProfile 構築 → JSON 保存 → サンプル3社と同じ
      ID 解決ルート（get_sample）で参照される。
    - outputs/ は gitignore 対象なので機密情報の混入リスクを切り離す。
    - スキーマ進化への備えとして Pydantic v2 の model_dump_json を使い、
      未知フィールドは Pydantic 既定で無視（旧 JSON も読める）。
"""
from __future__ import annotations

from pathlib import Path

from core.static.sample_company import CompanyProfile

DEFAULT_PROFILES_DIR = Path("outputs/profiles")


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
    return path


def load_company_profile_from_json(
    company_id: str,
    base_dir: Path | None = None,
) -> CompanyProfile | None:
    """ID から保存済み CompanyProfile JSON を読み込む。

    Args:
        company_id: 企業 ID
        base_dir: 検索ディレクトリ（None なら DEFAULT_PROFILES_DIR を実行時解決）

    Returns:
        CompanyProfile（存在しない場合は None・file not found を黙ってフォールバック）
    """
    resolved = _resolve_base_dir(base_dir)
    path = _profile_path(company_id, resolved)
    if not path.is_file():
        return None
    return CompanyProfile.model_validate_json(path.read_text(encoding="utf-8"))
