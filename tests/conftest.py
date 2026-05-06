"""プロジェクト共通 pytest fixture。

テスト実行中に outputs/measure_runs/ へ書き込まれたファイルが
テスト間で持ち越されないよう、各テスト後にクリーンアップする。
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_MEASURE_RUNS_DIR = Path("outputs/measure_runs")


@pytest.fixture(autouse=True)
def cleanup_measure_runs_dir() -> None:
    """各テスト後に outputs/measure_runs/ をリセットして副作用を遮断する。"""
    yield
    if _MEASURE_RUNS_DIR.is_dir():
        shutil.rmtree(_MEASURE_RUNS_DIR)
