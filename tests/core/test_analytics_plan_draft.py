"""core/analytics/plan_draft.py の単体テスト（純関数のみ）。

generate_plan_draft 本体は e-Stat API を叩くため、ここでは純粋なヘルパー関数
（テーマ分類等）の単体テストに絞る。
"""
from __future__ import annotations

from core.analytics.plan_draft import _classify_form3_theme

# ---- _classify_form3_theme ----


def test_classify_load_factor_to_load() -> None:
    assert _classify_form3_theme("積載率向上（38% → 50%）") == "load"


def test_classify_modal_shift_to_load() -> None:
    assert _classify_form3_theme("モーダルシフト（トラック→鉄道貨物）") == "load"


def test_classify_joint_delivery_to_load() -> None:
    assert _classify_form3_theme("共同配送") == "load"


def test_classify_berth_to_wait() -> None:
    assert _classify_form3_theme("バース予約システム") == "wait"


def test_classify_relay_to_loading_non_chain() -> None:
    """非連鎖化事業者は中継輸送 → 荷役等（loading）に分類。"""
    assert _classify_form3_theme("中継輸送", is_chain_franchise=False) == "loading"


def test_classify_relay_to_wait_when_chain_franchise() -> None:
    """連鎖化事業者は荷役等セクションが無いため中継輸送 → 荷待ち（wait）に流用。"""
    assert _classify_form3_theme("中継輸送", is_chain_franchise=True) == "wait"


def test_classify_unknown_returns_none() -> None:
    assert _classify_form3_theme("未知の施策") is None


def test_classify_default_is_non_chain() -> None:
    """is_chain_franchise 引数の既定値は False（非連鎖化）。"""
    assert _classify_form3_theme("中継輸送") == "loading"
