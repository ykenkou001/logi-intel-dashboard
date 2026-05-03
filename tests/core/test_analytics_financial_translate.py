"""core/analytics/financial_translate.py の単体テスト。

実 e-Stat API を叩かないため、SimulationResult を合成 fixture で組み立てる。
"""
from __future__ import annotations

from core.analytics.financial_translate import (
    _calculate_npv,
    build_financial_translate_summary,
    translate_to_pnl_impact,
)
from core.analytics.simulator import MeasureSimulation, SimulationResult
from core.export.citation import co2_factors_citation
from core.static.financial_factors import CARBON_PRICE, NPV_PARAMS
from core.static.sample_company import get_sample


def _make_simulation(
    cost_saving: float = 100_000_000,    # 1 億円/年
    co2_reduction_kg: float = 1_000_000,  # 1,000t-CO2/年
    investment: float = 5_000_000,        # 500 万円
) -> SimulationResult:
    """テスト用の最小 SimulationResult を作る。"""
    return SimulationResult(
        jsic_code="3159", jsic_name="その他の電子部品",
        prefecture="愛知県", revenue_jpy=85_000_000_000,
        annual_freight_tons=120_000.0, is_estimate=False,
        avg_distance_km=500.0, long_distance_share_pct=30.0,
        measures=[MeasureSimulation(
            name="モーダルシフト",
            description="500km超を鉄道シフト",
            co2_reduction_kg_per_year=co2_reduction_kg,
            cost_saving_jpy_per_year=cost_saving,
            driver_hours_saving_per_year=None,
            investment_jpy=investment,
            payback_years=investment / cost_saving if cost_saving > 0 else None,
            rationale="r",
            citation=co2_factors_citation(),
        )],
    )


# ---- _calculate_npv ----


def test_npv_zero_saving_returns_negative_investment() -> None:
    npv = _calculate_npv(annual_saving=0, investment=1_000_000, years=5, discount_rate_pct=3.0)
    assert npv == -1_000_000


def test_npv_positive_saving_offsets_investment() -> None:
    """年 100 万円削減 × 5年・割引率 3%・投資 100 万円 → NPV プラス。"""
    npv = _calculate_npv(
        annual_saving=1_000_000, investment=1_000_000,
        years=5, discount_rate_pct=3.0,
    )
    assert npv > 3_500_000


def test_npv_higher_discount_rate_reduces_value() -> None:
    npv_low_rate = _calculate_npv(1_000_000, 0, 5, 3.0)
    npv_high_rate = _calculate_npv(1_000_000, 0, 5, 10.0)
    assert npv_low_rate > npv_high_rate


# ---- translate_to_pnl_impact ----


def test_translate_basic_structure() -> None:
    """基本構造: measures が 1 件、合算が正しく算出される。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    sim = _make_simulation()
    result = translate_to_pnl_impact(profile, sim)

    assert result.company_id == "sample_mfg_01"
    assert result.base_operating_profit_jpy == 5_950_000_000
    assert abs(result.base_operating_profit_margin_pct - 7.0) < 0.01

    assert len(result.measures) == 1
    impact = result.measures[0]
    assert impact.measure_name == "モーダルシフト"
    assert impact.operating_profit_increase_jpy_per_year == 100_000_000
    # 売上 850 億円 × 1 億円増 → +0.118 pp
    assert impact.operating_profit_margin_lift_pp is not None
    assert abs(impact.operating_profit_margin_lift_pp - 0.118) < 0.01


def test_translate_carbon_range_uses_min_max_factors() -> None:
    """炭素価格は J-クレジット〜GX-ETS の min/max レンジで提示される。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    sim = _make_simulation(co2_reduction_kg=1_000_000)  # 1,000 t-CO2
    result = translate_to_pnl_impact(profile, sim)

    impact = result.measures[0]
    # 1,000t × 3,000円 = 300万円
    assert impact.carbon_avoidance_jpy_low == 1000.0 * CARBON_PRICE.low
    # 1,000t × 5,000円 = 500万円
    assert impact.carbon_avoidance_jpy_high == 1000.0 * CARBON_PRICE.high
    assert impact.carbon_avoidance_jpy_high > impact.carbon_avoidance_jpy_low


def test_translate_no_co2_means_no_carbon_avoidance() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    sim = _make_simulation(co2_reduction_kg=0)
    result = translate_to_pnl_impact(profile, sim)
    assert result.measures[0].carbon_avoidance_jpy_low is None
    assert result.measures[0].carbon_avoidance_jpy_high is None


def test_translate_npv_uses_5_year_horizon() -> None:
    """5 年累積 NPV が NPV_PARAMS.horizon_years に従う。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    sim = _make_simulation(cost_saving=100_000_000, investment=5_000_000)
    result = translate_to_pnl_impact(profile, sim)
    impact = result.measures[0]
    assert impact.five_year_npv_jpy is not None
    # 1 億円 × 5 年（割引前）= 5 億円。割引後 + 投資差し引き → 概ね 4.4 億円超
    # 厳密: sum(1/1.03^t for t=1..5) ≒ 4.5797 × 1e8 - 5e6 ≒ 4.53e8
    assert impact.five_year_npv_jpy > 440_000_000
    assert impact.five_year_npv_jpy < 460_000_000
    assert NPV_PARAMS.horizon_years == 5


def test_translate_includes_qualitative_notes() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = translate_to_pnl_impact(profile, _make_simulation())
    assert "不作為コスト" in result.inaction_risk_note
    assert "ESG" in result.esg_qualitative_note
    assert "定性" in result.esg_qualitative_note


def test_translate_aggregates_across_measures() -> None:
    """複数施策の合算が正しい。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    sim = SimulationResult(
        jsic_code="3159", jsic_name="x",
        prefecture="愛知県", revenue_jpy=85_000_000_000,
        annual_freight_tons=120_000.0, is_estimate=False,
        avg_distance_km=500.0, long_distance_share_pct=30.0,
        measures=[
            MeasureSimulation(
                name="施策A", description="d",
                co2_reduction_kg_per_year=1_000_000,
                cost_saving_jpy_per_year=50_000_000,
                driver_hours_saving_per_year=None,
                investment_jpy=2_000_000,
                payback_years=0.04,
                rationale="r", citation=co2_factors_citation(),
            ),
            MeasureSimulation(
                name="施策B", description="d",
                co2_reduction_kg_per_year=2_000_000,
                cost_saving_jpy_per_year=80_000_000,
                driver_hours_saving_per_year=None,
                investment_jpy=3_000_000,
                payback_years=0.04,
                rationale="r", citation=co2_factors_citation(),
            ),
        ],
    )
    result = translate_to_pnl_impact(profile, sim)

    # 営業利益増合計 = 50M + 80M = 130M
    assert result.total_operating_profit_increase_jpy == 130_000_000
    # 投資合計 = 2M + 3M = 5M
    assert result.total_investment_jpy == 5_000_000
    # 炭素回避 low: (1,000t + 2,000t) × 3,000円 = 9,000,000
    assert result.total_carbon_avoidance_jpy_low == 9_000_000


def test_translate_citations_include_efficiency_law() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = translate_to_pnl_impact(profile, _make_simulation())
    labels = [c.label for c in result.citations]
    assert any("物流効率化法" in label for label in labels)
    assert any("Ver.3.2" in label for label in labels)


# ---- build_financial_translate_summary ----


def test_summary_includes_company_and_aggregates() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = translate_to_pnl_impact(profile, _make_simulation())
    text = build_financial_translate_summary(result)
    assert "テクノパーツ製造" in text
    assert "営業利益" in text
    assert "炭素価格回避レンジ" in text
    assert "5年累積 NPV" in text
    assert "ESG" in text
    assert "不作為コスト" in text


def test_summary_handles_no_cost_saving_measure() -> None:
    """コスト削減 None の施策が混在してもサマリーが壊れない。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    sim = SimulationResult(
        jsic_code="3159", jsic_name="x",
        prefecture="愛知県", revenue_jpy=85_000_000_000,
        annual_freight_tons=120_000.0, is_estimate=False,
        avg_distance_km=500.0, long_distance_share_pct=30.0,
        measures=[MeasureSimulation(
            name="ドライバー時間のみ施策", description="d",
            co2_reduction_kg_per_year=None,
            cost_saving_jpy_per_year=None,
            driver_hours_saving_per_year=1000,
            investment_jpy=2_000_000,
            payback_years=None,
            rationale="r", citation=co2_factors_citation(),
        )],
    )
    result = translate_to_pnl_impact(profile, sim)
    text = build_financial_translate_summary(result)
    assert "営業利益効果: 試算対象外" in text
    assert "炭素回避: なし" in text
    assert "5年NPV: 試算対象外" in text
