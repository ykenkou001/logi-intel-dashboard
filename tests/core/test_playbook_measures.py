"""core/playbook/measures.py の単体テスト。"""
from __future__ import annotations

from core.playbook.measures import (
    ALL_MEASURES,
    get_measure,
    measures_by_section,
)


def test_all_measures_have_unique_ids() -> None:
    ids = [m.measure_id for m in ALL_MEASURES]
    assert len(ids) == len(set(ids)), "measure_id に重複あり"


def test_all_measures_have_required_fields() -> None:
    """全施策に最低限のメタデータが揃っている。"""
    for m in ALL_MEASURES:
        assert m.measure_id
        assert m.name
        assert m.description
        assert m.measure_type
        assert m.form3_section in {"load", "wait", "loading"}
        assert 1 <= m.implementation_difficulty <= 5
        assert m.typical_investment_jpy_low <= m.typical_investment_jpy_high
        assert m.citation is not None


def test_get_measure_returns_correct_item() -> None:
    m = get_measure("modal_shift_to_rail")
    assert m is not None
    assert m.name == "鉄道貨物へのモーダルシフト"


def test_get_measure_returns_none_for_unknown() -> None:
    assert get_measure("nonexistent_measure") is None


def test_measures_by_section_load() -> None:
    load_measures = measures_by_section("load")
    assert len(load_measures) >= 3  # 積載率・モーダルシフト・共同配送 等
    assert all(m.form3_section == "load" for m in load_measures)


def test_measures_by_section_wait() -> None:
    wait_measures = measures_by_section("wait")
    assert len(wait_measures) >= 1  # バース予約 等
    assert all(m.form3_section == "wait" for m in wait_measures)


def test_measures_by_section_loading() -> None:
    loading_measures = measures_by_section("loading")
    assert len(loading_measures) >= 1  # 中継輸送 等
    assert all(m.form3_section == "loading" for m in loading_measures)


def test_modal_shift_has_long_distance_resource() -> None:
    """モーダルシフトは長距離輸送が前提。"""
    m = get_measure("modal_shift_to_rail")
    assert m is not None
    assert "long_distance_transport" in m.required_resources


def test_relay_transport_has_high_difficulty() -> None:
    """中継輸送は実装難易度が高い（拠点・労使協定）。"""
    m = get_measure("relay_transport")
    assert m is not None
    assert m.implementation_difficulty >= 4


def test_visualization_has_lowest_difficulty() -> None:
    """物流実態の把握・可視化は前提施策で難易度最小。"""
    m = get_measure("visualization_baseline")
    assert m is not None
    assert m.implementation_difficulty == 1
