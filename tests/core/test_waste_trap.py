"""J2 罠スコア (core/analytics/waste_trap.py) のテスト。

検証カバレッジ (plans/b-c-flickering-pixel.md §段階 c.6 J2):
    - 6 軸セーフガードがすべて発火条件で trap_severity="low" 固定
        ① ramp_up_period (months_since_start < 6 / None)
        ② data_incomplete (data_completeness < 0.5)
        ③ insufficient_samples (measured_count < 30)
        ④ seasonal_factor
        ⑤ external_event
        ⑥ before_payback
        + actual_not_measured (actual=None)
    - severity ロジック:
        actual/invested <= 0.3 かつ expected/invested >= 2.0 → high
        0.3 < ratio < 0.7 → medium
        それ以外 → low
    - investment_freeze_recommended:
        high かつ root_cause in {scale_misfit, wrong_kpi, implementation_quality}
    - 4 サンプル企業で smoke test
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.analytics.waste_trap import (
    HIGH_EXPECTATION_RATIO,
    LOW_RATIO_HIGH_SEVERITY,
    MID_RATIO_MEDIUM_SEVERITY,
    MIN_DATA_COMPLETENESS,
    MIN_MEASURED_COUNT,
    MIN_MONTHS_SINCE_START_FOR_JUDGMENT,
    MeasureExecutionRecord,
    RootCause,
    build_waste_trap_summary,
    detect_waste_traps,
)
from core.static.sample_company import (
    SAMPLE_CHAIN,
    SAMPLE_MANUFACTURING,
    SAMPLE_RETAIL,
    SAMPLE_WHOLESALE,
    CompanyProfile,
)

_TODAY = date(2026, 5, 6)


def _high_severity_run(
    measure_id: str = "load_factor_tms",
    root_cause: RootCause = "scale_misfit",
    *,
    started_on: date | None = None,
    expected: int = 30_000_000,
    actual: int = 1_000_000,
    invested: int = 10_000_000,
) -> MeasureExecutionRecord:
    """セーフガード回避 + high severity を狙う標準的な run record。

    - months_since_start = 12 (≥6) → ramp_up_period 発火しない
    - measured_count = 100 (≥30)
    - data_completeness = 0.9 (≥0.5)
    - actual_effect_jpy = 1M, invested_jpy = 10M → ratio 0.1 (≤0.3)
    - expected/invested = 3.0 (≥2.0)
    """
    return MeasureExecutionRecord(
        measure_id=measure_id,
        started_on=started_on or _TODAY - timedelta(days=365),
        invested_jpy=invested,
        expected_effect_jpy=expected,
        actual_effect_jpy=actual,
        measured_count=100,
        data_completeness=0.9,
        seasonal_factor_active=False,
        external_event_active=False,
        payback_months_estimated=6,
        suspected_root_cause=root_cause,
    )


# ---------------------------------------------------------------------------
# 1. 6 軸セーフガード（low 固定）
# ---------------------------------------------------------------------------


def test_safeguard_ramp_up_period() -> None:
    """months_since_start < 6 → low 固定。"""
    run = _high_severity_run(
        started_on=_TODAY - timedelta(days=30),  # 1 ヶ月
    )
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert "ramp_up_period" in result.items[0].safeguard_triggered


def test_safeguard_zero_months_locked_to_low() -> None:
    """months_since_start=0 でも low 固定 (HANDOFF 境界条件)。"""
    run = _high_severity_run(started_on=_TODAY)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert result.items[0].months_since_start == 0


def test_safeguard_started_on_none() -> None:
    """started_on=None でも low 固定 (情報不足は判定保留)。"""
    run = _high_severity_run(started_on=None)
    run = run.model_copy(update={"started_on": None})
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert result.items[0].months_since_start is None


def test_safeguard_data_incomplete() -> None:
    """data_completeness < 0.5 → low 固定。"""
    base = _high_severity_run()
    run = base.model_copy(update={"data_completeness": 0.3})
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert "data_incomplete" in result.items[0].safeguard_triggered


def test_safeguard_insufficient_samples() -> None:
    """measured_count < 30 → low 固定。"""
    base = _high_severity_run()
    run = base.model_copy(update={"measured_count": 10})
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert "insufficient_samples" in result.items[0].safeguard_triggered


def test_safeguard_seasonal_factor() -> None:
    base = _high_severity_run()
    run = base.model_copy(update={"seasonal_factor_active": True})
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert "seasonal_factor" in result.items[0].safeguard_triggered


def test_safeguard_external_event() -> None:
    base = _high_severity_run()
    run = base.model_copy(update={"external_event_active": True})
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert "external_event" in result.items[0].safeguard_triggered


def test_safeguard_before_payback() -> None:
    """months_since_start < payback_months_estimated → low 固定。"""
    base = _high_severity_run()
    run = base.model_copy(update={
        "started_on": _TODAY - timedelta(days=270),  # 9 ヶ月
        "payback_months_estimated": 24,              # 24 ヶ月想定
    })
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert "before_payback" in result.items[0].safeguard_triggered


def test_safeguard_actual_not_measured() -> None:
    """actual_effect_jpy=None → low 固定 (Claude 単独判断: 初版は判定保留)。"""
    base = _high_severity_run()
    run = base.model_copy(update={"actual_effect_jpy": None})
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert "actual_not_measured" in result.items[0].safeguard_triggered
    # remediation に「実績計測」が含まれる
    assert "実績計測" in result.items[0].suggested_remediation


# ---------------------------------------------------------------------------
# 2. severity 計算（セーフガード回避後）
# ---------------------------------------------------------------------------


def test_high_severity_when_low_actual_high_expected() -> None:
    """actual/invested ≤ 0.3 かつ expected/invested ≥ 2.0 → high。"""
    run = _high_severity_run(invested=10_000_000, actual=1_000_000, expected=30_000_000)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "high"
    assert result.high_count == 1


def test_medium_severity_in_mid_range() -> None:
    """0.3 < actual/invested < 0.7 → medium。"""
    run = _high_severity_run(invested=10_000_000, actual=5_000_000, expected=30_000_000)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "medium"
    assert result.medium_count == 1


def test_low_severity_when_actual_meets_expected() -> None:
    """actual/invested >= 0.7 → low (期待通り)。"""
    run = _high_severity_run(invested=10_000_000, actual=8_000_000, expected=30_000_000)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"
    assert result.low_count == 1


def test_low_severity_when_expected_below_threshold() -> None:
    """actual/invested ≤ 0.3 でも expected/invested < 2.0 → low。"""
    run = _high_severity_run(invested=10_000_000, actual=1_000_000, expected=15_000_000)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    # 期待効果も控えめなので high にはならない
    assert result.items[0].trap_severity == "low"


def test_low_severity_when_invested_zero() -> None:
    """invested = 0 (例: 横断系 visualization_baseline) → low。"""
    run = _high_severity_run(invested=0, actual=0, expected=0)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "low"


# ---------------------------------------------------------------------------
# 3. investment_freeze_recommended
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "root_cause", ["scale_misfit", "wrong_kpi", "implementation_quality"],
)
def test_investment_freeze_for_internal_root_causes(
    root_cause: RootCause,
) -> None:
    """high + 内部要因型 root_cause → freeze 推奨。"""
    run = _high_severity_run(root_cause=root_cause)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "high"
    assert result.items[0].investment_freeze_recommended is True
    assert result.investment_freeze_count == 1


@pytest.mark.parametrize(
    "root_cause",
    [
        "external_factor", "resource_missing", "governance_gap",
        "data_quality", "adoption_resistance", "unknown",
    ],
)
def test_investment_freeze_not_for_other_root_causes(
    root_cause: RootCause,
) -> None:
    """high でも外部・リソース・ガバナンス系は freeze 推奨しない。"""
    run = _high_severity_run(root_cause=root_cause)
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "high"
    assert result.items[0].investment_freeze_recommended is False
    assert result.investment_freeze_count == 0


def test_investment_freeze_not_for_medium() -> None:
    """medium severity では freeze 推奨しない。"""
    run = _high_severity_run(
        invested=10_000_000, actual=5_000_000, expected=30_000_000,
        root_cause="scale_misfit",
    )
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].trap_severity == "medium"
    assert result.items[0].investment_freeze_recommended is False


# ---------------------------------------------------------------------------
# 4. RootCause 全 9 値の Codex 勧告⑤対応
# ---------------------------------------------------------------------------


def test_codex_added_root_causes_accepted() -> None:
    """Codex 勧告⑤で追加した 3 種が型として受け取れる。"""
    for rc in ("data_quality", "adoption_resistance", "implementation_quality"):
        run = _high_severity_run(root_cause=rc)  # type: ignore[arg-type]
        result = detect_waste_traps(
            SAMPLE_MANUFACTURING, [run], today=_TODAY,
        )
        assert result.items[0].suspected_root_cause == rc


# ---------------------------------------------------------------------------
# 5. 集計 + 4 サンプル smoke test
# ---------------------------------------------------------------------------


def test_aggregate_counts() -> None:
    """high/medium/low 件数が正しく集計される。"""
    runs = [
        _high_severity_run(measure_id="load_factor_tms"),
        _high_severity_run(
            measure_id="warehouse_dx_wms",
            invested=10_000_000, actual=5_000_000, expected=30_000_000,
        ),  # medium
        _high_severity_run(
            measure_id="berth_booking_vbs",
            invested=10_000_000, actual=8_000_000, expected=30_000_000,
        ),  # low
    ]
    result = detect_waste_traps(SAMPLE_MANUFACTURING, runs, today=_TODAY)
    assert result.high_count == 1
    assert result.medium_count == 1
    assert result.low_count == 1


def test_empty_runs_returns_empty_result() -> None:
    """measure_runs=[] でも crash しない。"""
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [], today=_TODAY)
    assert result.items == []
    assert result.high_count == 0
    assert "罠候補なし" in build_waste_trap_summary(result)


@pytest.mark.parametrize(
    "profile",
    [SAMPLE_MANUFACTURING, SAMPLE_WHOLESALE, SAMPLE_RETAIL, SAMPLE_CHAIN],
    ids=["manufacturing", "wholesale", "retail", "chain"],
)
def test_runs_for_all_sample_companies(profile: CompanyProfile) -> None:
    """4 業種サンプル全てで動作する (smoke)。"""
    runs = [_high_severity_run()]
    result = detect_waste_traps(profile, runs, today=_TODAY)
    assert result.company_id == profile.company_id
    assert len(result.items) == 1
    assert result.citations
    assert result.items[0].measure_name  # ALL_MEASURES から取得した日本語名


# ---------------------------------------------------------------------------
# 6. measure_id が ALL_MEASURES に無いケース
# ---------------------------------------------------------------------------


def test_unknown_measure_id_uses_id_as_name() -> None:
    """ALL_MEASURES に無い measure_id でも crash せず、id をそのまま name に使う。"""
    run = _high_severity_run(measure_id="custom_pilot_xyz")
    result = detect_waste_traps(SAMPLE_MANUFACTURING, [run], today=_TODAY)
    assert result.items[0].measure_name == "custom_pilot_xyz"


# ---------------------------------------------------------------------------
# 7. 閾値定数の妥当性 (constants 公開の整合性チェック)
# ---------------------------------------------------------------------------


def test_thresholds_are_sane() -> None:
    """境界値定数が想定範囲。"""
    assert MIN_MONTHS_SINCE_START_FOR_JUDGMENT == 6
    assert MIN_DATA_COMPLETENESS == 0.5
    assert MIN_MEASURED_COUNT == 30
    assert LOW_RATIO_HIGH_SEVERITY == 0.3
    assert MID_RATIO_MEDIUM_SEVERITY == 0.7
    assert HIGH_EXPECTATION_RATIO == 2.0


def test_summary_includes_high_examples() -> None:
    runs = [_high_severity_run()]
    result = detect_waste_traps(SAMPLE_MANUFACTURING, runs, today=_TODAY)
    summary = build_waste_trap_summary(result)
    assert "high 例" in summary
    assert "load_factor_tms" in summary
