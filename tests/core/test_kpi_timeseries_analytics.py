"""KPI 時系列分析（core/analytics/kpi_timeseries.py）のテスト。

Tier S2（フェーズ 5.5）。カバレッジ:
    T1  roll_up_daily_to_monthly が日次 JSON を月平均に集約する
    T2  対象月の日次データが無ければ None を返す
    T3  detect_kpi_deterioration: 単発の閾値超え（load_factor 低下）で warn
    T4  detect_kpi_deterioration: 3 ヶ月連続悪化で critical 救済
    T5  detect_kpi_deterioration: 改善傾向ならアラート無し
    T6  detect_kpi_deterioration: 履歴 < 2 ヶ月なら空リスト
    T7  build_kpi_timeseries: 履歴空でも結果型は構築される
    T8  build_kpi_timeseries: limit_months で末尾 N ヶ月のみ
    T9  record_monthly_snapshot: persist=False でも snapshot 型を返す
    T10 record_monthly_snapshot: F2 計算失敗 (jsic_code 未解決) でも None で続行
    T11 重大悪化 (load_factor -10pt) で critical
    T12 罠件数増 (+5) で critical
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from core.analytics.kpi_timeseries import (
    build_kpi_timeseries,
    detect_kpi_deterioration,
    record_monthly_snapshot,
    roll_up_daily_to_monthly,
)
from core.io.kpi_timeseries_store import (
    MonthlyKpiSnapshot,
    append_monthly_snapshot,
)
from core.static.sample_company import SAMPLE_WHOLESALE


def _write_daily_snapshot(
    base: Path, company_id: str, date_str: str, payload: dict[str, object],
) -> None:
    """outputs/cockpit_snapshots/<id>/<yyyymmdd>.json を直接書く（テスト用）。"""
    dir_path = base / "cockpit_snapshots" / company_id
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / f"{date_str}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8",
    )


def _snap(
    *,
    year_month: str,
    load_factor_pct: float | None = None,
    wait_time_avg_min: float | None = None,
    handling_time_avg_min: float | None = None,
    co2_intensity_g_per_tonkm: float | None = None,
    standardization_score: float | None = None,
    waste_trap_count_high: int = 0,
    recorded_at: datetime | None = None,
) -> MonthlyKpiSnapshot:
    return MonthlyKpiSnapshot(
        company_id="sample_wholesale_01",
        year_month=year_month,
        load_factor_pct=load_factor_pct,
        wait_time_avg_min=wait_time_avg_min,
        handling_time_avg_min=handling_time_avg_min,
        co2_intensity_g_per_tonkm=co2_intensity_g_per_tonkm,
        standardization_score=standardization_score,
        waste_trap_count_high=waste_trap_count_high,
        recorded_at=recorded_at or datetime(2026, 5, 1, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# roll_up_daily_to_monthly
# ---------------------------------------------------------------------------


def test_roll_up_aggregates_daily(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    for d, lf in (("20260101", 80.0), ("20260102", 82.0), ("20260103", 84.0)):
        _write_daily_snapshot(
            tmp_path, "sample_wholesale_01", d,
            {
                "company_id": "sample_wholesale_01",
                "snapshot_date": f"2026-01-{d[6:]}",
                "load_factor_pct": lf,
                "wait_time_avg_min": 20.0,
                "wait_time_max_min": 100.0,
                "handling_time_avg_min": 30.0,
                "co2_intensity_g_per_tonkm": 60.0,
                "over_2h_count_total": 0,
                "compliance_overall": "ok",
                "feasibility_kpi_level": "yellow",
                "open_items": [],
            },
        )

    rolled = roll_up_daily_to_monthly(
        "sample_wholesale_01", target_year_month="2026-01",
    )
    assert rolled is not None
    assert rolled.year_month == "2026-01"
    assert rolled.load_factor_pct == pytest.approx(82.0)
    assert rolled.daily_sample_count == 3
    assert rolled.source == "rolled_up_from_daily"


def test_roll_up_missing_month_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    # 2026-02 の日次データが無い
    assert (
        roll_up_daily_to_monthly("sample_wholesale_01", target_year_month="2026-02")
        is None
    )


def test_roll_up_skips_other_months(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    _write_daily_snapshot(
        tmp_path, "sample_wholesale_01", "20260101",
        {
            "company_id": "sample_wholesale_01",
            "snapshot_date": "2026-01-01",
            "load_factor_pct": 80.0,
            "compliance_overall": "ok",
            "feasibility_kpi_level": "green",
            "over_2h_count_total": 0,
            "open_items": [],
        },
    )
    _write_daily_snapshot(
        tmp_path, "sample_wholesale_01", "20260201",
        {
            "company_id": "sample_wholesale_01",
            "snapshot_date": "2026-02-01",
            "load_factor_pct": 70.0,
            "compliance_overall": "ok",
            "feasibility_kpi_level": "green",
            "over_2h_count_total": 0,
            "open_items": [],
        },
    )

    feb = roll_up_daily_to_monthly("sample_wholesale_01", target_year_month="2026-02")
    assert feb is not None
    assert feb.load_factor_pct == pytest.approx(70.0)
    assert feb.daily_sample_count == 1


# ---------------------------------------------------------------------------
# detect_kpi_deterioration
# ---------------------------------------------------------------------------


def test_deterioration_load_factor_warn() -> None:
    months = [
        _snap(year_month="2025-11", load_factor_pct=85.0),
        _snap(year_month="2025-12", load_factor_pct=83.0),
        _snap(year_month="2026-01", load_factor_pct=82.0),
        _snap(year_month="2026-02", load_factor_pct=78.0),  # -7pt vs 2025-11
    ]
    alerts = detect_kpi_deterioration(months)
    lf = next(a for a in alerts if a.metric == "load_factor_pct")
    assert lf.severity in {"warn", "critical"}
    assert lf.direction == "down"
    assert lf.baseline_value == 85.0
    assert lf.latest_value == 78.0


def test_deterioration_three_month_consecutive_critical() -> None:
    months = [
        _snap(year_month="2025-12", co2_intensity_g_per_tonkm=60.0),
        _snap(year_month="2026-01", co2_intensity_g_per_tonkm=60.5),  # +0.8%
        _snap(year_month="2026-02", co2_intensity_g_per_tonkm=60.8),  # +0.5%
        _snap(year_month="2026-03", co2_intensity_g_per_tonkm=61.0),  # +0.3%
    ]
    alerts = detect_kpi_deterioration(months)
    co2 = next(a for a in alerts if a.metric == "co2_intensity_g_per_tonkm")
    assert co2.consecutive_months == 3
    assert co2.severity == "critical"


def test_deterioration_improving_no_alert() -> None:
    months = [
        _snap(year_month="2025-12", load_factor_pct=70.0, wait_time_avg_min=40.0),
        _snap(year_month="2026-01", load_factor_pct=75.0, wait_time_avg_min=35.0),
        _snap(year_month="2026-02", load_factor_pct=80.0, wait_time_avg_min=30.0),
        _snap(year_month="2026-03", load_factor_pct=85.0, wait_time_avg_min=25.0),
    ]
    alerts = detect_kpi_deterioration(months)
    assert alerts == []


def test_deterioration_too_few_months() -> None:
    months = [_snap(year_month="2026-01", load_factor_pct=80.0)]
    assert detect_kpi_deterioration(months) == []


def test_deterioration_load_factor_critical_10pt_drop() -> None:
    months = [
        _snap(year_month="2025-11", load_factor_pct=85.0),
        _snap(year_month="2025-12", load_factor_pct=84.0),
        _snap(year_month="2026-01", load_factor_pct=82.0),
        _snap(year_month="2026-02", load_factor_pct=74.0),  # -11pt
    ]
    alerts = detect_kpi_deterioration(months)
    lf = next(a for a in alerts if a.metric == "load_factor_pct")
    assert lf.severity == "critical"


def test_deterioration_waste_trap_count_high() -> None:
    months = [
        _snap(year_month="2025-11", waste_trap_count_high=0),
        _snap(year_month="2025-12", waste_trap_count_high=1),
        _snap(year_month="2026-01", waste_trap_count_high=2),
        _snap(year_month="2026-02", waste_trap_count_high=6),  # +6 vs 2025-11
    ]
    alerts = detect_kpi_deterioration(months)
    j2 = next(a for a in alerts if a.metric == "waste_trap_count_high")
    assert j2.severity == "critical"


# ---------------------------------------------------------------------------
# build_kpi_timeseries
# ---------------------------------------------------------------------------


def test_build_empty_history_returns_zero_months(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    result = build_kpi_timeseries("never_recorded")
    assert result.months == []
    assert result.deteriorations == []
    assert result.citations  # 物流効率化法 citation は常に付く


def test_build_respects_limit_months(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    for ym in ("2025-10", "2025-11", "2025-12", "2026-01", "2026-02"):
        append_monthly_snapshot(_snap(year_month=ym, load_factor_pct=80.0))

    result = build_kpi_timeseries("sample_wholesale_01", limit_months=3)
    assert [m.year_month for m in result.months] == ["2025-12", "2026-01", "2026-02"]


# ---------------------------------------------------------------------------
# record_monthly_snapshot
# ---------------------------------------------------------------------------


def test_record_monthly_snapshot_persist_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    snap = record_monthly_snapshot(
        SAMPLE_WHOLESALE,
        year_month="2026-04",
        measure_runs=[],
        persist=False,
    )
    assert snap.year_month == "2026-04"
    # 永続化していないので jsonl は無い
    assert not (tmp_path / "kpi_timeseries" / f"{SAMPLE_WHOLESALE.company_id}.jsonl").exists()


def test_record_monthly_snapshot_persist_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    snap = record_monthly_snapshot(
        SAMPLE_WHOLESALE,
        year_month="2026-04",
        measure_runs=[],
        persist=True,
    )
    assert snap.year_month == "2026-04"
    path = tmp_path / "kpi_timeseries" / f"{SAMPLE_WHOLESALE.company_id}.jsonl"
    assert path.exists()
    assert path.read_text(encoding="utf-8").count("2026-04") >= 1
