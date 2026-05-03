"""CompanyProfile の JSON 永続化と ID 解決優先順位のテスト。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.io.company_store import (
    load_company_profile_from_json,
    save_company_profile,
)
from core.static.sample_company import (
    SAMPLE_MANUFACTURING,
    CompanyProfile,
    CompanySite,
    WaitTimeRow,
)


def _make_actual_profile(company_id: str) -> CompanyProfile:
    return CompanyProfile(
        company_id=company_id,
        name="テスト実データ会社",
        jsic_code="3159",
        main_business="電子部品製造業",
        annual_revenue_jpy=10_000_000_000,
        annual_freight_tons_total=100_000.0,
        operating_profit_jpy=500_000_000,
        cost_of_goods_sold_jpy=8_000_000_000,
        clo_name="CLO 山田",
        plan_period_start_fy=2026,
        plan_period_end_fy=2030,
        data_source="actual",
        load_factor_actual_pct=42.0,
        annual_fuel_liters=1_000_000.0,
        annual_co2_emissions_kg=2_800_000.0,
        sites=[
            CompanySite(
                name="本社",
                site_type="factory",
                prefecture="東京都",
                annual_freight_tons=60_000,
            ),
        ],
        wait_time_rows=[
            WaitTimeRow(
                bucket_label="全体",
                measured_count=1000,
                average_minutes=20,
                max_minutes=60,
                over_2h_count=0,
            ),
        ],
    )


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """JSON 保存 → 読込で同一の CompanyProfile が復元できる。"""
    original = _make_actual_profile("test_actual_01")
    saved = save_company_profile(original, base_dir=tmp_path)
    assert saved.is_file()
    assert saved.name == "test_actual_01.json"

    loaded = load_company_profile_from_json("test_actual_01", base_dir=tmp_path)
    assert loaded is not None
    assert loaded.company_id == "test_actual_01"
    assert loaded.data_source == "actual"
    assert loaded.load_factor_actual_pct == 42.0
    assert len(loaded.sites) == 1
    assert len(loaded.wait_time_rows) == 1


def test_load_missing_returns_none(tmp_path: Path) -> None:
    """存在しない ID は None を返す（例外を投げない）。"""
    result = load_company_profile_from_json("nope", base_dir=tmp_path)
    assert result is None


def test_save_creates_directory(tmp_path: Path) -> None:
    """親ディレクトリが存在しなくても自動作成される。"""
    deep = tmp_path / "deep" / "nested" / "profiles"
    profile = _make_actual_profile("deep_01")
    saved = save_company_profile(profile, base_dir=deep)
    assert saved.is_file()
    assert deep.is_dir()


def test_get_sample_prefers_actual_over_built_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """実データ JSON が存在する場合、サンプル定数より優先される。"""
    # company_store の DEFAULT_PROFILES_DIR を tmp_path に差し替え
    from core.io import company_store

    monkeypatch.setattr(company_store, "DEFAULT_PROFILES_DIR", tmp_path)

    # サンプル ID と同じ ID で実データを上書き保存
    overridden = _make_actual_profile(SAMPLE_MANUFACTURING.company_id)
    save_company_profile(overridden, base_dir=tmp_path)

    # get_sample は実データ JSON を優先する
    from core.static.sample_company import get_sample

    resolved = get_sample(SAMPLE_MANUFACTURING.company_id)
    assert resolved is not None
    # 実データの値（テスト用）になっていること
    assert resolved.data_source == "actual"
    assert resolved.name == "テスト実データ会社"
    # サンプル本来の値（テクノパーツ製造）にはなっていない
    assert resolved.name != SAMPLE_MANUFACTURING.name


def test_get_sample_falls_back_to_built_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """実データ JSON が無い場合、サンプル定数にフォールバックする。"""
    from core.io import company_store

    monkeypatch.setattr(company_store, "DEFAULT_PROFILES_DIR", tmp_path)

    from core.static.sample_company import get_sample

    resolved = get_sample(SAMPLE_MANUFACTURING.company_id)
    assert resolved is not None
    # サンプル本来の値が返る
    assert resolved.name == SAMPLE_MANUFACTURING.name
    assert resolved.data_source == "estimated"
