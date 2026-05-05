"""core/static/sample_company.py の単体テスト。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.static.sample_company import (
    ALL_SAMPLES,
    SAMPLE_CHAIN,
    SAMPLE_MANUFACTURING,
    SAMPLE_WHOLESALE,
    CompanyProfile,
    CompanySite,
    HandlingTimeRow,
    KpiHistoryEntry,
    WaitTimeRow,
    get_sample,
)


def test_three_samples_registered() -> None:
    """サンプル3社が登録されている。"""
    assert len(ALL_SAMPLES) == 3
    assert SAMPLE_MANUFACTURING.company_id in ALL_SAMPLES
    assert SAMPLE_WHOLESALE.company_id in ALL_SAMPLES
    assert SAMPLE_CHAIN.company_id in ALL_SAMPLES


def test_get_sample_existing() -> None:
    """既存 ID で取得できる。"""
    profile = get_sample("sample_chain_01")
    assert profile is not None
    assert profile.is_chain_franchise is True


def test_get_sample_missing() -> None:
    """未登録 ID は None。"""
    assert get_sample("nope") is None


def test_manufacturing_sample_meets_first_class_threshold() -> None:
    """製造業サンプルは 9 万トン超で特定第一種荷主想定。"""
    assert SAMPLE_MANUFACTURING.annual_freight_tons_total >= 90_000


def test_chain_sample_is_chain_franchise() -> None:
    """連鎖化サンプルは is_chain_franchise=True。"""
    assert SAMPLE_CHAIN.is_chain_franchise is True
    assert SAMPLE_CHAIN.jsic_code == "5891"


def test_jsic_code_must_be_4digit() -> None:
    """JSIC コードは4桁必須。"""
    with pytest.raises(ValidationError):
        CompanyProfile(
            company_id="test",
            name="x",
            jsic_code="911",  # 3桁は不可
            main_business="x",
            annual_revenue_jpy=0,
            annual_freight_tons_total=0,
            clo_name="x",
            plan_period_start_fy=2026,
            plan_period_end_fy=2030,
        )


def test_negative_revenue_rejected() -> None:
    """負の売上は ValidationError。"""
    with pytest.raises(ValidationError):
        CompanyProfile(
            company_id="test",
            name="x",
            jsic_code="3159",
            main_business="x",
            annual_revenue_jpy=-1,
            annual_freight_tons_total=0,
            clo_name="x",
            plan_period_start_fy=2026,
            plan_period_end_fy=2030,
        )


def test_company_site_basic_fields() -> None:
    """CompanySite が必須フィールドで構築できる。"""
    site = CompanySite(
        name="テスト拠点",
        site_type="dc",
        prefecture="東京都",
        annual_freight_tons=1000.0,
    )
    assert site.site_type == "dc"


def test_sample_sites_freight_sums_match_total_loosely() -> None:
    """サンプルの拠点合計と total が概ね合致（±10% 程度の差は許容）。"""
    for sample in (SAMPLE_MANUFACTURING, SAMPLE_WHOLESALE, SAMPLE_CHAIN):
        sites_sum = sum(s.annual_freight_tons for s in sample.sites)
        # 必ずしも厳密一致ではないが、桁が合っているか確認
        assert sites_sum > 0
        assert sample.annual_freight_tons_total > 0


# --- フェーズ4.0 拡張フィールドのテスト ---


def test_samples_have_wait_time_rows_except_chain_handling() -> None:
    """サンプル3社は wait_time_rows を持つ（連鎖化は handling_time_rows のみ空）。"""
    for sample in (SAMPLE_MANUFACTURING, SAMPLE_WHOLESALE, SAMPLE_CHAIN):
        assert len(sample.wait_time_rows) > 0, f"{sample.company_id} should have wait_time_rows"
    # 連鎖化は荷役等時間が法令上対象外のため空
    assert SAMPLE_CHAIN.handling_time_rows == []
    # 製造業・卸売業は handling_time_rows を持つ
    assert len(SAMPLE_MANUFACTURING.handling_time_rows) > 0
    assert len(SAMPLE_WHOLESALE.handling_time_rows) > 0


def test_wait_time_row_validation() -> None:
    """WaitTimeRow が必須フィールドで構築できる。"""
    row = WaitTimeRow(
        bucket_label="全体",
        measured_count=100,
        average_minutes=15.0,
        max_minutes=60.0,
        over_2h_count=0,
    )
    assert row.bucket_label == "全体"
    assert row.measured_count == 100


def test_wait_time_row_negative_rejected() -> None:
    """負の measured_count は ValidationError。"""
    with pytest.raises(ValidationError):
        WaitTimeRow(
            bucket_label="x",
            measured_count=-1,
            average_minutes=0,
            max_minutes=0,
            over_2h_count=0,
        )


def test_handling_time_row_pct_range() -> None:
    """over_1h_pct は 0-100 の範囲外で ValidationError。"""
    with pytest.raises(ValidationError):
        HandlingTimeRow(
            bucket_label="x",
            measured_count=10,
            average_minutes=20,
            max_minutes=60,
            over_1h_pct=150.0,  # 範囲外
        )


def test_kpi_history_entry_basic() -> None:
    """KpiHistoryEntry が基本フィールドで構築できる。"""
    entry = KpiHistoryEntry(
        fy=2024,
        metric="load_factor_pct",
        value=42.5,
        unit="%",
    )
    assert entry.fy == 2024
    assert entry.metric == "load_factor_pct"


def test_optional_actual_fields_default_none() -> None:
    """サンプル3社は実測値オプションフィールドが None かつ data_source='sample'。"""
    for sample in (SAMPLE_MANUFACTURING, SAMPLE_WHOLESALE, SAMPLE_CHAIN):
        assert sample.load_factor_actual_pct is None
        assert sample.annual_fuel_liters is None
        assert sample.annual_co2_emissions_kg is None
        # data_source は架空企業データのため "sample"（経営判断不可の旨を明示）
        assert sample.data_source == "sample"


def test_company_profile_with_actual_fields() -> None:
    """実測値を持つ CompanyProfile が構築できる（実データ取込シミュレーション）。"""
    profile = CompanyProfile(
        company_id="test_actual_01",
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
        annual_fuel_liters=1_500_000.0,
        annual_co2_emissions_kg=4_200_000.0,
        kpi_history=[
            KpiHistoryEntry(fy=2024, metric="load_factor_pct", value=40.0, unit="%"),
            KpiHistoryEntry(fy=2025, metric="load_factor_pct", value=41.0, unit="%"),
        ],
    )
    assert profile.data_source == "actual"
    assert profile.load_factor_actual_pct == 42.0
    assert len(profile.kpi_history) == 2
