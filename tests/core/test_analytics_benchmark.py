"""core/analytics/benchmark.py の単体テスト。

実 e-Stat API を踏まないため、信頼性分類の純粋関数 `_classify_revenue_ratio_reliability`
と build_benchmark_summary の表示分岐に絞ってテストする。
"""
from __future__ import annotations

from core.analytics.benchmark import (
    REVENUE_VS_AVG_LARGE_SCALE_THRESHOLD_PCT,
    REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT,
    BenchmarkResult,
    _classify_revenue_ratio_reliability,
    build_benchmark_summary,
)


def _make_benchmark(
    revenue_vs_avg_pct: float | None,
    reliability: str = "normal",
    warning: str | None = None,
) -> BenchmarkResult:
    return BenchmarkResult(
        jsic_code="5411",
        jsic_name="食料・飲料卸売業",
        category="wholesale",
        prefecture="東京都",
        revenue_jpy=5_000_000_000,
        logistics_cost_jpy=None,
        estat_minor_code="541",
        national_peer_count=10000,
        regional_peer_count=1500,
        industry_avg_revenue_jpy=8e8,
        revenue_vs_avg_pct=revenue_vs_avg_pct,
        revenue_ratio_reliability=reliability,  # type: ignore[arg-type]
        revenue_ratio_warning=warning,
        logistics_cost_ratio=None,
        industry_avg_logistics_ratio=0.048,
        logistics_cost_gap_pct=None,
        co2_intensity_target_pct=23.4,
    )


# ---- _classify_revenue_ratio_reliability ----


def test_classify_none_returns_normal_no_warning() -> None:
    level, warning = _classify_revenue_ratio_reliability(None)
    assert level == "normal"
    assert warning is None


def test_classify_below_large_scale_threshold_is_normal() -> None:
    level, warning = _classify_revenue_ratio_reliability(150.0)
    assert level == "normal"
    assert warning is None


def test_classify_at_large_scale_boundary_is_normal() -> None:
    """境界値（200% 丁度）は normal（厳密に超えた場合のみ large_scale）。"""
    level, warning = _classify_revenue_ratio_reliability(
        REVENUE_VS_AVG_LARGE_SCALE_THRESHOLD_PCT,
    )
    assert level == "normal"
    assert warning is None


def test_classify_large_scale_range_no_warning() -> None:
    """200% 超 1000% 以下は large_scale で warning なし。"""
    level, warning = _classify_revenue_ratio_reliability(500.0)
    assert level == "large_scale"
    assert warning is None


def test_classify_above_reliability_threshold_yields_warning() -> None:
    """1000% を超えると low_reliability + 警告メッセージ。"""
    level, warning = _classify_revenue_ratio_reliability(
        REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT + 1.0,
    )
    assert level == "low_reliability"
    assert warning is not None
    assert "1001%" in warning or "1,001%" in warning
    assert "1000%" in warning  # しきい値の言及


def test_classify_at_reliability_boundary_is_large_scale() -> None:
    """境界値（1000% 丁度）は large_scale（厳密に超えた場合のみ low_reliability）。"""
    level, warning = _classify_revenue_ratio_reliability(
        REVENUE_VS_AVG_RELIABILITY_THRESHOLD_PCT,
    )
    assert level == "large_scale"
    assert warning is None


def test_classify_extreme_value_smartmart_case() -> None:
    """memory に記載されたスマートマート再現ケース（売上3200億 / 業界平均5億 = 64,000%）。"""
    level, warning = _classify_revenue_ratio_reliability(64_000.0)
    assert level == "low_reliability"
    assert warning is not None
    assert "64000%" in warning or "64,000%" in warning


# ---- build_benchmark_summary（警告メッセージ表示） ----


def test_summary_shows_warning_when_low_reliability() -> None:
    benchmark = _make_benchmark(
        revenue_vs_avg_pct=64_000.0,
        reliability="low_reliability",
        warning="業界平均売上比 64000% は信頼性しきい値 1000% を超過。",
    )
    text = build_benchmark_summary(benchmark)
    assert "⚠️" in text
    assert "64000%" in text or "信頼性しきい値" in text


def test_summary_omits_warning_when_normal() -> None:
    benchmark = _make_benchmark(revenue_vs_avg_pct=120.0, reliability="normal")
    text = build_benchmark_summary(benchmark)
    assert "⚠️" not in text


def test_summary_omits_warning_when_large_scale() -> None:
    """large_scale は規模優位企業として正常扱い、warning なし。"""
    benchmark = _make_benchmark(revenue_vs_avg_pct=500.0, reliability="large_scale")
    text = build_benchmark_summary(benchmark)
    assert "⚠️" not in text
