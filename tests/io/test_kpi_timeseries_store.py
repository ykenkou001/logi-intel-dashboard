"""月次 KPI 時系列ストア（core/io/kpi_timeseries_store.py）のテスト。

Tier S2（フェーズ 5.5）。カバレッジ:
    T1  append_monthly_snapshot で jsonl が 1 行ずつ追記される
    T2  load_monthly_snapshots は year_month 昇順で返す
    T3  同一 year_month に複数行ある場合 recorded_at 最大が採用される
    T4  from_year_month / to_year_month の範囲フィルタが両端含む
    T5  limit_months で末尾 N ヶ月のみ返す
    T6  jsonl の壊れた行はスキップ、他は読める（前方互換）
    T7  ファイル未生成時は空リスト
    T8  year_month が不正フォーマットなら ValueError
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core.io.kpi_timeseries_store import (
    MonthlyKpiSnapshot,
    append_monthly_snapshot,
    load_monthly_snapshots,
)


def _snap(
    *,
    company_id: str = "sample_wholesale_01",
    year_month: str = "2026-01",
    load_factor_pct: float | None = 80.0,
    recorded_at: datetime | None = None,
    standardization_score: float | None = None,
) -> MonthlyKpiSnapshot:
    return MonthlyKpiSnapshot(
        company_id=company_id,
        year_month=year_month,
        load_factor_pct=load_factor_pct,
        standardization_score=standardization_score,
        recorded_at=recorded_at or datetime(2026, 1, 31, 12, 0, 0),
    )


def test_append_and_load_returns_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    append_monthly_snapshot(_snap())
    snaps = load_monthly_snapshots("sample_wholesale_01")
    assert len(snaps) == 1
    assert snaps[0].year_month == "2026-01"
    assert snaps[0].load_factor_pct == 80.0


def test_load_returns_year_month_ascending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    append_monthly_snapshot(_snap(year_month="2026-03", load_factor_pct=82.0))
    append_monthly_snapshot(_snap(year_month="2026-01", load_factor_pct=80.0))
    append_monthly_snapshot(_snap(year_month="2026-02", load_factor_pct=81.0))

    snaps = load_monthly_snapshots("sample_wholesale_01")
    assert [s.year_month for s in snaps] == ["2026-01", "2026-02", "2026-03"]


def test_duplicate_year_month_keeps_latest_recorded_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    older = _snap(
        year_month="2026-01",
        load_factor_pct=75.0,
        recorded_at=datetime(2026, 1, 31, 12, 0, 0),
    )
    newer = _snap(
        year_month="2026-01",
        load_factor_pct=88.0,
        recorded_at=datetime(2026, 1, 31, 18, 0, 0),
    )
    append_monthly_snapshot(older)
    append_monthly_snapshot(newer)

    snaps = load_monthly_snapshots("sample_wholesale_01")
    assert len(snaps) == 1
    assert snaps[0].load_factor_pct == 88.0


def test_range_filter_inclusive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    for ym in ("2025-11", "2025-12", "2026-01", "2026-02", "2026-03"):
        append_monthly_snapshot(_snap(year_month=ym))

    snaps = load_monthly_snapshots(
        "sample_wholesale_01",
        from_year_month="2025-12",
        to_year_month="2026-02",
    )
    assert [s.year_month for s in snaps] == ["2025-12", "2026-01", "2026-02"]


def test_limit_months_returns_tail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    for ym in ("2025-10", "2025-11", "2025-12", "2026-01", "2026-02"):
        append_monthly_snapshot(_snap(year_month=ym))

    snaps = load_monthly_snapshots("sample_wholesale_01", limit_months=3)
    assert [s.year_month for s in snaps] == ["2025-12", "2026-01", "2026-02"]


def test_corrupt_line_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    append_monthly_snapshot(_snap(year_month="2026-01"))
    # 壊れた行を強制 append
    path = tmp_path / "kpi_timeseries" / "sample_wholesale_01.jsonl"
    with path.open("a", encoding="utf-8") as fp:
        fp.write("this is not json\n")
    append_monthly_snapshot(_snap(year_month="2026-02"))

    snaps = load_monthly_snapshots("sample_wholesale_01")
    assert [s.year_month for s in snaps] == ["2026-01", "2026-02"]


def test_missing_file_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    assert load_monthly_snapshots("never_recorded") == []


def test_invalid_year_month_raises() -> None:
    with pytest.raises(ValueError, match="year_month"):
        MonthlyKpiSnapshot(
            company_id="sample_wholesale_01",
            year_month="2026/01",  # 不正フォーマット
            recorded_at=datetime.now(),
        )


def test_zero_padded_month_required() -> None:
    with pytest.raises(ValueError, match="year_month"):
        MonthlyKpiSnapshot(
            company_id="sample_wholesale_01",
            year_month="2026-1",  # ゼロ詰めなし
            recorded_at=datetime.now(),
        )


def test_recorded_at_tie_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """recorded_at が完全に同じなら strict > 演算で最初に append したものが残る。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    ts = datetime(2026, 1, 31, 12, 0, 0)
    first = _snap(year_month="2026-01", load_factor_pct=77.0, recorded_at=ts)
    second = _snap(year_month="2026-01", load_factor_pct=99.0, recorded_at=ts)
    append_monthly_snapshot(first)
    append_monthly_snapshot(second)

    snaps = load_monthly_snapshots("sample_wholesale_01")
    assert len(snaps) == 1
    # 厳密 > なので最初の append (load=77) が残る
    assert snaps[0].load_factor_pct == 77.0


def test_recorded_at_microsecond_tiebreak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """microsecond の差異でも最新判定が機能する。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    earlier = _snap(year_month="2026-01", load_factor_pct=70.0)
    later = _snap(
        year_month="2026-01",
        load_factor_pct=95.0,
        recorded_at=earlier.recorded_at + timedelta(microseconds=1),
    )
    append_monthly_snapshot(earlier)
    append_monthly_snapshot(later)

    snaps = load_monthly_snapshots("sample_wholesale_01")
    assert len(snaps) == 1
    assert snaps[0].load_factor_pct == 95.0
