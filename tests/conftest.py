"""プロジェクト共通 pytest fixture。

テスト実行中に outputs/ 配下へ書き込まれたファイルがテスト間で持ち越されないよう、
各テスト後にクリーンアップする。
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_MEASURE_RUNS_DIR = Path("outputs/measure_runs")
# Tier S1 追加（フェーズ 5.5）: 既存 cockpit 単発 jsonl + 新 DecisionLog スナップショット jsonl
_DECISIONS_DIR = Path("outputs/decisions")
_DECISION_LOGS_DIR = Path("outputs/decision_logs")
# Tier S2 追加（フェーズ 5.5）: 月次 KPI 時系列スナップショット jsonl + 日次 cockpit_snapshots
_KPI_TIMESERIES_DIR = Path("outputs/kpi_timeseries")
_COCKPIT_SNAPSHOTS_DIR = Path("outputs/cockpit_snapshots")


@pytest.fixture(autouse=True)
def cleanup_runtime_dirs() -> None:
    """各テスト後に outputs/ 配下の永続化ディレクトリをリセットして副作用を遮断する。"""
    yield
    for d in (
        _MEASURE_RUNS_DIR,
        _DECISIONS_DIR,
        _DECISION_LOGS_DIR,
        _KPI_TIMESERIES_DIR,
        _COCKPIT_SNAPSHOTS_DIR,
    ):
        if d.is_dir():
            shutil.rmtree(d)
