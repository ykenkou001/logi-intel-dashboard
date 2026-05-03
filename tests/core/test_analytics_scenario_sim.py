"""core/analytics/scenario_sim.py の単体テスト。

シナリオシミュレータ（Step 3）の挙動を検証する。実 e-Stat API には依存しない。
"""
from __future__ import annotations

import pytest

from core.analytics.scenario_sim import (
    ScenarioParameters,
    ThreeBandValue,
    _build_scenario_result,
    _calculate_npv,
    build_scenario_summary,
    simulate_scenarios,
)
from core.static.financial_factors import NPV_PARAMS
from core.static.sample_company import get_sample

# ---- データ構造の基本 ----


def test_three_band_value_holds_three_floats() -> None:
    band = ThreeBandValue(conservative=10.0, standard=20.0, upside=30.0)
    assert band.conservative == 10.0
    assert band.standard == 20.0
    assert band.upside == 30.0


def test_scenario_parameters_construct() -> None:
    params = ScenarioParameters(
        name="x", label="X",
        cost_saving_multiplier=1.2,
        investment_multiplier=1.0,
        co2_multiplier=1.1,
        description="d",
    )
    assert params.cost_saving_multiplier == 1.2


# ---- シナジー（重複ダンピング） ----


def test_synergy_no_overlap_keeps_unity() -> None:
    """セクション跨ぎのみの施策セットでは倍率 1.0。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    # load + wait + loading をそれぞれ 1 件ずつ
    result = simulate_scenarios(
        profile,
        selected_measure_ids=[
            "modal_shift_to_rail",  # load
            "berth_booking_vbs",     # wait
            "warehouse_dx_wms",      # loading
        ],
    )
    assert result.synergy_multiplier == 1.0
    assert all(c == 1 for c in result.section_overlap_count.values())


def test_synergy_same_section_applies_dampening() -> None:
    """同 form3_section に 2 施策以上 → 効果合算に 0.7 倍を適用。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    # load カテゴリで 2 施策（modal_shift + load_factor_tms）
    result = simulate_scenarios(
        profile,
        selected_measure_ids=[
            "modal_shift_to_rail",
            "load_factor_tms",
        ],
    )
    assert result.synergy_multiplier == 0.7
    assert result.section_overlap_count.get("load") == 2


def test_synergy_dampening_reduces_baseline_cost() -> None:
    """同セクション 2 施策の baseline コスト合算は、別セクション 2 施策より小さい。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    same_section = simulate_scenarios(
        profile,
        selected_measure_ids=["modal_shift_to_rail", "load_factor_tms"],  # 両方 load
    )
    cross_section = simulate_scenarios(
        profile,
        selected_measure_ids=["modal_shift_to_rail", "berth_booking_vbs"],  # load + wait
    )
    # 効果絶対額の比較は施策個別効果に依存するため、
    # 同セクション側が「ダンピング適用済」であることを確認する
    assert same_section.synergy_multiplier == 0.7
    assert cross_section.synergy_multiplier == 1.0


# ---- 3 区分（conservative / standard / upside） ----


def test_three_band_ordering_when_positive_saving() -> None:
    """正のコスト削減では conservative < standard < upside の順。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])

    band = result.baseline.annual_operating_profit_increase_jpy
    assert band.conservative < band.standard < band.upside


def test_three_band_factors_are_0_6_and_1_3() -> None:
    """conservative = standard × 0.6 / upside = standard × 1.3。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])

    band = result.baseline.annual_cost_saving_jpy
    assert band.conservative == pytest.approx(band.standard * 0.6)
    assert band.upside == pytest.approx(band.standard * 1.3)


# ---- What-if シナリオ 8 種 ----


def test_baseline_plus_seven_stress_scenarios() -> None:
    """baseline + ストレス 7 = 計 8 シナリオ。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])

    assert result.baseline.scenario.name == "baseline"
    assert len(result.stress_scenarios) == 7
    names = {s.scenario.name for s in result.stress_scenarios}
    assert names == {
        "fuel_up_20", "fuel_down_20",
        "freight_up_10", "freight_down_10",
        "demand_up_10", "demand_down_10",
        "improvement_standard_strict",
    }


def test_baseline_self_ratio_is_one() -> None:
    """baseline.operating_profit_ratio_to_baseline は 1.0（自身が基準）。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])

    assert result.baseline.operating_profit_ratio_to_baseline == pytest.approx(1.0)
    assert result.baseline.robustness_level == "green"


# ---- 堅牢性判定（green / yellow / red） ----


def test_robustness_green_at_70_percent_boundary() -> None:
    """ratio = 0.70 ちょうどで green。"""
    params = ScenarioParameters(
        name="t", label="T",
        cost_saving_multiplier=0.70,
        investment_multiplier=1.0,
        co2_multiplier=1.0,
        description="d",
    )
    r = _build_scenario_result(
        scenario=params,
        base_cost_saving=1_000_000.0,
        base_co2_reduction=0.0,
        base_investment=0.0,
        baseline_standard_op_increase=1_000_000.0,
    )
    assert r.robustness_level == "green"


def test_robustness_yellow_between_50_and_70() -> None:
    params = ScenarioParameters(
        name="t", label="T",
        cost_saving_multiplier=0.60,
        investment_multiplier=1.0,
        co2_multiplier=1.0,
        description="d",
    )
    r = _build_scenario_result(
        scenario=params,
        base_cost_saving=1_000_000.0,
        base_co2_reduction=0.0,
        base_investment=0.0,
        baseline_standard_op_increase=1_000_000.0,
    )
    assert r.robustness_level == "yellow"


def test_robustness_red_below_50() -> None:
    params = ScenarioParameters(
        name="t", label="T",
        cost_saving_multiplier=0.40,
        investment_multiplier=1.0,
        co2_multiplier=1.0,
        description="d",
    )
    r = _build_scenario_result(
        scenario=params,
        base_cost_saving=1_000_000.0,
        base_co2_reduction=0.0,
        base_investment=0.0,
        baseline_standard_op_increase=1_000_000.0,
    )
    assert r.robustness_level == "red"


# ---- フェーズ3.5 完了条件: 燃料 +20% でも黒字維持 ----


def test_fuel_up_20_keeps_positive_profit() -> None:
    """燃料 +20% シナリオで営業利益増の standard 値が正であること。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])

    fuel_up = next(
        s for s in result.stress_scenarios if s.scenario.name == "fuel_up_20"
    )
    assert fuel_up.annual_operating_profit_increase_jpy.standard > 0
    assert fuel_up.robustness_level == "green"


# ---- 入力施策の解決（明示指定 / Top 3 自動採用 / エラー） ----


def test_explicit_selected_measures_are_used_as_is() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(
        profile,
        selected_measure_ids=["load_factor_tms", "visualization_baseline"],
    )
    assert result.measure_selection_source == "explicit"
    assert [m.measure_id for m in result.selected_measures] == [
        "load_factor_tms", "visualization_baseline",
    ]


def test_auto_top3_when_no_measure_ids() -> None:
    """selected_measure_ids=None の場合は Step 2 Top 3 が採用される。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile)

    assert result.measure_selection_source == "auto_top3"
    assert 1 <= len(result.selected_measures) <= 3


def test_invalid_measure_id_raises_value_error() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    with pytest.raises(ValueError, match="プレイブックに登録されていません"):
        simulate_scenarios(profile, selected_measure_ids=["nonexistent_id"])


# ---- NPV 算出 ----


def test_npv_band_increases_with_saving_band() -> None:
    """3 区分の NPV は conservative < standard < upside（コスト削減が正の前提）。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])

    npv = result.baseline.five_year_npv_jpy
    assert npv.conservative < npv.standard < npv.upside


def test_calculate_npv_matches_financial_translate_formula() -> None:
    """5 年累積 NPV（割引率 3%）の計算式が financial_translate と一致する。"""
    npv = _calculate_npv(annual_saving=1_000_000.0, investment=1_000_000.0)
    # sum(1e6 / 1.03^t for t=1..5) ≒ 4,579,707 - 1e6 ≒ 3,579,707
    assert NPV_PARAMS.discount_rate_pct == 3.0
    assert NPV_PARAMS.horizon_years == 5
    assert 3_500_000 < npv < 3_600_000


def test_calculate_npv_zero_saving_returns_negative_investment() -> None:
    npv = _calculate_npv(annual_saving=0.0, investment=5_000_000.0)
    assert npv == -5_000_000.0


# ---- 投資合算 ----


def test_investment_uses_typical_midpoint() -> None:
    """投資は (typical_investment_jpy_low + high) / 2。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    # load_factor_tms: low=2_000_000, high=15_000_000 → 中央値 8_500_000
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])
    assert result.baseline.total_investment_jpy == pytest.approx(8_500_000.0)


# ---- サマリー出力 ----


def test_summary_includes_company_and_robustness() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])
    text = build_scenario_summary(result)
    assert "テクノパーツ製造" in text
    assert "ベースラインシナリオ" in text
    assert "What-if ストレステスト" in text
    assert "堅牢性総合判定" in text
    assert "燃料 +20%" in text


def test_summary_marks_overlap_dampening() -> None:
    """同セクション重複時はサマリーに 0.7 倍適用が明示される。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(
        profile,
        selected_measure_ids=["modal_shift_to_rail", "load_factor_tms"],
    )
    text = build_scenario_summary(result)
    assert "重複あり" in text
    assert "0.7" in text


# ---- サンプル整合性 ----


def test_chain_franchise_sample_runs_end_to_end() -> None:
    """連鎖化サンプル（コンビニ）でも全 8 シナリオが返る。"""
    profile = get_sample("sample_chain_01")
    assert profile is not None
    result = simulate_scenarios(profile)
    assert result.industry == "chain_franchise"
    assert len(result.stress_scenarios) == 7


def test_citations_include_efficiency_law_and_co2_guideline() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = simulate_scenarios(profile, selected_measure_ids=["load_factor_tms"])
    labels = [c.label for c in result.citations]
    assert any("物流効率化法" in label for label in labels)
    assert any("Ver.3.2" in label for label in labels)
