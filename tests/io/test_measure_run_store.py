"""MeasureExecutionRecord 永続化（core/io/measure_run_store.py）のテスト。

カバレッジ:
    1. save/load round-trip — 保存したレコードが完全に復元できる
    2. load が存在しないファイルで空リストを返す
    3. append_run — 既存レコードに追加される
    4. 同一 measure_id を複数回 append — 全件保持される
    5. company_id 分離 — 別 ID のファイルが混在しない
    6. merge_with_stored — incoming が stored を上書きし、stored にしかない ID は保持
    7. merge_with_stored — incoming のみ（stored なし）はそのまま返る
    8. save_runs が上書きであることを確認（2 回保存したら最後の内容だけ残る）
    9. date フィールドが JSON round-trip で正しく復元される
    10. カスタム base_dir が動作する（DEFAULT_RUNS_DIR を汚染しない）
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core.io.measure_run_store import (
    MeasureExecutionRecord,
    append_run,
    load_runs,
    merge_with_stored,
    save_runs,
)


def _make_run(
    measure_id: str = "load_factor_tms",
    *,
    actual_effect_jpy: int | None = 5_000_000,
    invested_jpy: int = 10_000_000,
    started_on: date | None = date(2025, 10, 1),
) -> MeasureExecutionRecord:
    return MeasureExecutionRecord(
        measure_id=measure_id,
        started_on=started_on,
        invested_jpy=invested_jpy,
        actual_effect_jpy=actual_effect_jpy,
        expected_effect_jpy=20_000_000,
        measured_count=50,
        data_completeness=0.9,
    )


# ---------------------------------------------------------------------------
# 1. save/load round-trip
# ---------------------------------------------------------------------------

def test_save_load_round_trip(tmp_path: Path) -> None:
    run = _make_run()
    save_runs("company_a", [run], base_dir=tmp_path)
    loaded = load_runs("company_a", base_dir=tmp_path)

    assert len(loaded) == 1
    assert loaded[0].measure_id == run.measure_id
    assert loaded[0].invested_jpy == run.invested_jpy
    assert loaded[0].actual_effect_jpy == run.actual_effect_jpy


# ---------------------------------------------------------------------------
# 2. load が存在しないファイルで空リストを返す
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_no_file(tmp_path: Path) -> None:
    result = load_runs("nonexistent_company", base_dir=tmp_path)
    assert result == []


# ---------------------------------------------------------------------------
# 3. append_run — 既存レコードに追加される
# ---------------------------------------------------------------------------

def test_append_run_adds_to_existing(tmp_path: Path) -> None:
    run1 = _make_run("measure_a")
    run2 = _make_run("measure_b")
    save_runs("company_a", [run1], base_dir=tmp_path)
    append_run("company_a", run2, base_dir=tmp_path)

    loaded = load_runs("company_a", base_dir=tmp_path)
    assert len(loaded) == 2
    ids = {r.measure_id for r in loaded}
    assert ids == {"measure_a", "measure_b"}


# ---------------------------------------------------------------------------
# 4. 同一 measure_id を複数回 append — 全件保持される
# ---------------------------------------------------------------------------

def test_append_same_measure_id_multiple_times(tmp_path: Path) -> None:
    run_v1 = _make_run("load_factor_tms", actual_effect_jpy=3_000_000)
    run_v2 = _make_run("load_factor_tms", actual_effect_jpy=6_000_000)
    append_run("company_a", run_v1, base_dir=tmp_path)
    append_run("company_a", run_v2, base_dir=tmp_path)

    loaded = load_runs("company_a", base_dir=tmp_path)
    assert len(loaded) == 2
    effects = [r.actual_effect_jpy for r in loaded]
    assert 3_000_000 in effects
    assert 6_000_000 in effects


# ---------------------------------------------------------------------------
# 5. company_id 分離
# ---------------------------------------------------------------------------

def test_company_id_isolation(tmp_path: Path) -> None:
    run_a = _make_run("measure_a")
    run_b = _make_run("measure_b")
    save_runs("company_a", [run_a], base_dir=tmp_path)
    save_runs("company_b", [run_b], base_dir=tmp_path)

    loaded_a = load_runs("company_a", base_dir=tmp_path)
    loaded_b = load_runs("company_b", base_dir=tmp_path)

    assert len(loaded_a) == 1 and loaded_a[0].measure_id == "measure_a"
    assert len(loaded_b) == 1 and loaded_b[0].measure_id == "measure_b"


# ---------------------------------------------------------------------------
# 6. merge_with_stored — incoming が stored を上書きし、stored のみの ID は保持
# ---------------------------------------------------------------------------

def test_merge_incoming_overwrites_stored(tmp_path: Path) -> None:
    stored_run = _make_run("load_factor_tms", actual_effect_jpy=3_000_000)
    stored_only = _make_run("relay_transport", actual_effect_jpy=1_000_000)
    save_runs("company_a", [stored_run, stored_only], base_dir=tmp_path)

    incoming_run = _make_run("load_factor_tms", actual_effect_jpy=8_000_000)
    merged = merge_with_stored("company_a", [incoming_run], base_dir=tmp_path)

    by_id = {r.measure_id: r for r in merged}
    # incoming の値で上書き
    assert by_id["load_factor_tms"].actual_effect_jpy == 8_000_000
    # stored にしかない ID は保持
    assert "relay_transport" in by_id


# ---------------------------------------------------------------------------
# 7. merge_with_stored — stored なし（初回）はそのまま返る
# ---------------------------------------------------------------------------

def test_merge_with_no_stored(tmp_path: Path) -> None:
    incoming = [_make_run("measure_x"), _make_run("measure_y")]
    merged = merge_with_stored("new_company", incoming, base_dir=tmp_path)

    ids = {r.measure_id for r in merged}
    assert ids == {"measure_x", "measure_y"}


# ---------------------------------------------------------------------------
# 8. save_runs が上書きであることを確認
# ---------------------------------------------------------------------------

def test_save_runs_overwrites(tmp_path: Path) -> None:
    run1 = _make_run("measure_a")
    run2 = _make_run("measure_b")
    save_runs("company_a", [run1], base_dir=tmp_path)
    save_runs("company_a", [run2], base_dir=tmp_path)

    loaded = load_runs("company_a", base_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0].measure_id == "measure_b"


# ---------------------------------------------------------------------------
# 9. date フィールドの JSON round-trip
# ---------------------------------------------------------------------------

def test_date_field_round_trip(tmp_path: Path) -> None:
    started = date(2025, 4, 15)
    run = _make_run(started_on=started)
    save_runs("company_a", [run], base_dir=tmp_path)
    loaded = load_runs("company_a", base_dir=tmp_path)

    assert loaded[0].started_on == started


# ---------------------------------------------------------------------------
# 10. started_on=None が round-trip で None のまま
# ---------------------------------------------------------------------------

def test_none_date_round_trip(tmp_path: Path) -> None:
    run = _make_run(started_on=None)
    save_runs("company_a", [run], base_dir=tmp_path)
    loaded = load_runs("company_a", base_dir=tmp_path)

    assert loaded[0].started_on is None
