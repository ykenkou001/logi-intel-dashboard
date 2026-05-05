"""core/io/override_store.py のテスト（フェーズ5.0 段階 c.5）。

CompanyPackageOverride の JSON 永続化（save / load）と、LOGI_OUTPUTS_DIR の
実行時解決を確認する。company_store.py のテストと同じパターン。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core.io.override_store import (
    DEFAULT_PROFILES_DIR,
    load_override,
    save_override,
)
from core.playbook.industry_packages import (
    CompanyPackageOverride,
    OverrideEntry,
)


def _make_override(company_id: str = "test_co") -> CompanyPackageOverride:
    return CompanyPackageOverride(
        company_id=company_id,
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="load_factor_pct",
                category="approved_better_practice",
                rationale="自社実証で 50% を達成済",
                approved_by="山田CLO",
                diff={"target_value": 50.0},
            ),
        ],
        last_reviewed=date(2026, 5, 6),
    )


def test_save_writes_json_file(tmp_path: Path) -> None:
    override = _make_override()
    path = save_override(override, base_dir=tmp_path)
    assert path == tmp_path / "test_co_override.json"
    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    assert "test_co" in content
    assert "approved_better_practice" in content


def test_load_returns_none_when_absent(tmp_path: Path) -> None:
    assert load_override("never_saved", base_dir=tmp_path) is None


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    original = _make_override("rt_co")
    save_override(original, base_dir=tmp_path)
    loaded = load_override("rt_co", base_dir=tmp_path)
    assert loaded is not None
    assert loaded.company_id == "rt_co"
    assert loaded.base_industry == "manufacturing"
    assert len(loaded.entries) == 1
    entry = loaded.entries[0]
    assert entry.category == "approved_better_practice"
    assert entry.diff == {"target_value": 50.0}
    assert loaded.last_reviewed == date(2026, 5, 6)


def test_save_creates_parent_dir(tmp_path: Path) -> None:
    """base_dir が存在しなくても save_override が自動作成する。"""
    nested = tmp_path / "deep" / "dir"
    assert not nested.exists()
    save_override(_make_override("create_dir_co"), base_dir=nested)
    assert nested.is_dir()


def test_default_dir_uses_logi_outputs_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LOGI_OUTPUTS_DIR を実行時に再評価する（_resolve_base_dir の sentinel 対応）。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    override = _make_override("env_co")
    path = save_override(override)  # base_dir 未指定
    assert path.parent == tmp_path / "profiles"
    loaded = load_override("env_co")
    assert loaded is not None


def test_default_dir_constant_uses_module_load_time_env() -> None:
    """DEFAULT_PROFILES_DIR は import 時の env 値で凍結している（参照用）。

    実行時にユーザーが env を切替えた場合は _resolve_base_dir 経由でなければ
    反映されない。これは company_store.py と同じ設計トレードオフ。
    """
    assert DEFAULT_PROFILES_DIR.name == "profiles"


def test_load_override_handles_missing_company_id_gracefully(
    tmp_path: Path,
) -> None:
    """別 company の override しか存在しないとき、対象 ID 未保存なら None。"""
    save_override(_make_override("co_a"), base_dir=tmp_path)
    assert load_override("co_b", base_dir=tmp_path) is None
