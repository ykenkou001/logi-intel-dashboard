"""core/static/industry_benchmarks.py の単体テスト。

業界感覚レンジのデータ層が reference_industry_sense_ranges.md と整合しているかを確認する。
"""
from __future__ import annotations

from core.static.industry_benchmarks import (
    KPI_REACHABILITY,
    LOAD_FACTOR_ANNUAL_IMPROVEMENT_PP,
    LOAD_FACTOR_INDUSTRY_AVG_PCT,
    LOAD_FACTOR_TARGET_PCT,
    LOGISTICS_COST_RATIO,
    NATIONAL_CO2_INTENSITY_REDUCTION_PCT,
    NATIONAL_DRIVER_WORKERS_RANGE,
    OPERATING_PROFIT_MARGIN_PCT,
    REVENUE_VS_AVG_LARGE_SCALE_THRESHOLD_PCT,
    REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT,
    SANITY,
    Range,
    is_operating_profit_margin_in_range,
)

# ---- Range ----


def test_range_contains_value_within() -> None:
    r = Range(low=1.0, median=2.0, high=3.0)
    assert r.contains(2.0)
    assert r.contains(1.0)
    assert r.contains(3.0)


def test_range_contains_value_outside() -> None:
    r = Range(low=1.0, median=2.0, high=3.0)
    assert not r.contains(0.5)
    assert not r.contains(3.5)


# ---- 営業利益率レンジ ----


def test_operating_profit_margin_manufacturing_median_is_7pct() -> None:
    """製造業の中央値 7.0% が reference と整合。"""
    assert OPERATING_PROFIT_MARGIN_PCT["manufacturing"].median == 7.0


def test_operating_profit_margin_wholesale_is_low() -> None:
    """卸売業は薄利多売（中央値 2.0%）。"""
    assert OPERATING_PROFIT_MARGIN_PCT["wholesale"].median == 2.0


def test_is_operating_profit_margin_in_range_within() -> None:
    """製造業 7% は manufacturing レンジ内。"""
    within, range_def = is_operating_profit_margin_in_range("manufacturing", 7.0)
    assert within
    assert range_def is not None
    assert range_def.median == 7.0


def test_is_operating_profit_margin_in_range_outside() -> None:
    """製造業 15% は manufacturing レンジ外（高位 10%）。"""
    within, range_def = is_operating_profit_margin_in_range("manufacturing", 15.0)
    assert not within
    assert range_def is not None


def test_is_operating_profit_margin_unknown_category_returns_true() -> None:
    """未登録業種は判定不可として True を返す（誤検知防止）。"""
    within, range_def = is_operating_profit_margin_in_range("unknown_industry", 999.0)
    assert within
    assert range_def is None


# ---- 物流コスト比率（既存定数との整合）----


def test_logistics_cost_ratio_manufacturing_is_1_8pct() -> None:
    """JILS 2021: 製造業 1.8%。"""
    assert LOGISTICS_COST_RATIO["manufacturing"] == 0.018


def test_logistics_cost_ratio_transport_is_none() -> None:
    """運輸業は荷主ではないため None。"""
    assert LOGISTICS_COST_RATIO["transport"] is None


# ---- 積載率 ----


def test_load_factor_industry_avg_is_38pct() -> None:
    """自動車輸送統計年報: 営業用普通貨物車の業界平均積載率。"""
    assert LOAD_FACTOR_INDUSTRY_AVG_PCT == 38.0


def test_load_factor_target_is_50pct() -> None:
    """国交省「目指すべき水準」。"""
    assert LOAD_FACTOR_TARGET_PCT == 50.0


def test_load_factor_annual_improvement_is_1_5pp() -> None:
    """業界実績の年間改善ペース（標準）。"""
    assert LOAD_FACTOR_ANNUAL_IMPROVEMENT_PP == 1.5


# ---- ドライバー需給 ----


def test_driver_workers_range_includes_170man() -> None:
    """全国 170 万人（物流2024年問題資料）はレンジに収まる。"""
    assert NATIONAL_DRIVER_WORKERS_RANGE.contains(1_700_000)


def test_driver_workers_range_excludes_extreme_values() -> None:
    """50 万人や 500 万人はレンジ外（異常値検出用）。"""
    assert not NATIONAL_DRIVER_WORKERS_RANGE.contains(500_000)
    assert not NATIONAL_DRIVER_WORKERS_RANGE.contains(5_000_000)


# ---- 国家目標 ----


def test_co2_intensity_reduction_target_is_23_4pct() -> None:
    """物流分野 CO2 原単位削減目標。"""
    assert NATIONAL_CO2_INTENSITY_REDUCTION_PCT == 23.4


# ---- 信頼性しきい値（短期1 で benchmark.py から移行） ----


def test_revenue_vs_avg_thresholds() -> None:
    assert REVENUE_VS_AVG_LARGE_SCALE_THRESHOLD_PCT == 200.0
    assert REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT == 1000.0


# ---- 数値妥当性しきい値 ----


def test_sanity_thresholds_default_values() -> None:
    """reference_industry_sense_ranges.md の判定ガイドラインと整合。"""
    assert SANITY.operating_profit_increase_max_ratio == 0.30
    assert SANITY.npv_to_investment_max_multiple == 100.0
    assert SANITY.npv_to_investment_min_multiple == 0.5
    assert SANITY.profit_margin_lift_max_pp == 3.0


def test_kpi_reachability_thresholds() -> None:
    assert KPI_REACHABILITY.annual_improvement_pp_green == 1.5
    assert KPI_REACHABILITY.annual_improvement_pp_yellow == 3.0
