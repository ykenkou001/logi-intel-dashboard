"""core/static/improvement_standards.py の単体テスト。

告示数値が正確に保たれていることを検証する（数値が変わったらテストが落ちる仕組み）。
"""
from __future__ import annotations

from core.static.improvement_standards import (
    FRESHNESS,
    TRUCK_DRIVER_STANDARD,
    driver_capacity_reduction_factor,
)


def test_daily_working_hours_principle_is_13() -> None:
    """1日拘束時間 原則 13 時間。"""
    assert TRUCK_DRIVER_STANDARD.max_daily_working_hours_principle == 13


def test_daily_working_hours_max_is_15() -> None:
    """1日拘束時間 最大 15 時間。"""
    assert TRUCK_DRIVER_STANDARD.max_daily_working_hours_max == 15


def test_daily_working_hours_exception_is_16() -> None:
    """1日拘束時間 例外時上限 16 時間。"""
    assert TRUCK_DRIVER_STANDARD.max_daily_working_hours_exception == 16


def test_min_rest_hours_principle_is_11() -> None:
    """連続休息 原則 11 時間以上（2024年改正で上方修正）。"""
    assert TRUCK_DRIVER_STANDARD.min_rest_hours_principle == 11


def test_min_rest_hours_floor_is_9() -> None:
    """連続休息 下限 9 時間。"""
    assert TRUCK_DRIVER_STANDARD.min_rest_hours_floor == 9


def test_annual_working_hours_principle_is_3300() -> None:
    """年間総拘束時間 原則 3,300 時間。"""
    assert TRUCK_DRIVER_STANDARD.max_annual_working_hours_principle == 3300


def test_annual_overtime_is_960() -> None:
    """時間外労働 年間上限 960 時間（運送業特例）。"""
    assert TRUCK_DRIVER_STANDARD.max_annual_overtime_hours == 960


def test_continuous_driving_max_4h() -> None:
    """連続運転 4 時間 + 30 分休憩。"""
    assert TRUCK_DRIVER_STANDARD.max_continuous_driving_hours == 4
    assert TRUCK_DRIVER_STANDARD.min_break_per_4h_continuous_minutes == 30


def test_capacity_reduction_factor_in_industry_estimate_range() -> None:
    """2024年問題の稼働力減少係数が業界推計範囲（0.13-0.14）に収まる。"""
    factor = driver_capacity_reduction_factor()
    assert 0.13 <= factor <= 0.14


def test_freshness_label_set() -> None:
    """鮮度メタデータのラベルが設定済み。"""
    assert FRESHNESS.label == "改善基準告示（トラック運転者）"
    assert "mhlw.go.jp" in FRESHNESS.source_url


def test_freshness_as_needed_so_not_stale_immediately() -> None:
    """as_needed カデンスなので頻繁に stale 判定にならない。"""
    # 2022年告示なので 3 年程度経っても stale ではない（as_needed = 約 27 年）
    assert FRESHNESS.is_stale is False
