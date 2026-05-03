"""core/playbook/filters.py の単体テスト。"""
from __future__ import annotations

from core.playbook.filters import (
    PlaybookFilter,
    build_filter_from_profile,
    build_search_summary,
    filter_playbook,
)
from core.playbook.measures import ALL_MEASURES


def test_filter_no_condition_returns_all() -> None:
    result = filter_playbook(filter_=None)
    assert len(result) == len(ALL_MEASURES)


def test_filter_by_industry_manufacturing() -> None:
    result = filter_playbook(filter_=PlaybookFilter(industry="manufacturing"))
    assert len(result) >= 5
    # 全件 manufacturing が applicable_industries に含まれる
    for m in result:
        if m.applicable_industries:
            assert "manufacturing" in m.applicable_industries


def test_filter_by_revenue_excludes_large_scale_only_measures() -> None:
    """売上 10 億円企業はモーダルシフト（要 100 億円）が除外される。"""
    result = filter_playbook(filter_=PlaybookFilter(revenue_jpy=1_000_000_000))
    ids = [m.measure_id for m in result]
    assert "modal_shift_to_rail" not in ids


def test_filter_by_revenue_includes_modal_shift_for_large_company() -> None:
    """売上 100 億円超の企業はモーダルシフトが含まれる。"""
    result = filter_playbook(filter_=PlaybookFilter(revenue_jpy=10_000_000_000))
    ids = [m.measure_id for m in result]
    assert "modal_shift_to_rail" in ids


def test_filter_by_max_difficulty() -> None:
    """難易度 2 以下に絞ると共同配送（難易度 5）が除外される。"""
    result = filter_playbook(filter_=PlaybookFilter(max_difficulty=2))
    ids = [m.measure_id for m in result]
    assert "joint_delivery_competitor" not in ids
    # 全件 difficulty <= 2
    assert all(m.implementation_difficulty <= 2 for m in result)


def test_filter_by_form3_section() -> None:
    result = filter_playbook(filter_=PlaybookFilter(form3_section="wait"))
    assert all(m.form3_section == "wait" for m in result)


def test_filter_by_required_resources_excludes_when_missing() -> None:
    """available_resources にモーダルシフトの前提（long_distance_transport）が無いと除外。"""
    result = filter_playbook(
        filter_=PlaybookFilter(available_resources=["multi_site"]),
    )
    ids = [m.measure_id for m in result]
    assert "modal_shift_to_rail" not in ids
    assert "relay_transport" not in ids


def test_filter_by_required_resources_includes_when_satisfied() -> None:
    result = filter_playbook(
        filter_=PlaybookFilter(
            available_resources=["multi_site", "it_capability", "warehouse_management"],
        ),
    )
    ids = [m.measure_id for m in result]
    assert "load_factor_tms" in ids


def test_filter_combined_conditions_are_and() -> None:
    """複数条件は AND で適用される。"""
    result = filter_playbook(filter_=PlaybookFilter(
        industry="manufacturing",
        revenue_jpy=85_000_000_000,  # 850 億円
        max_difficulty=3,
        form3_section="load",
    ))
    for m in result:
        assert "manufacturing" in m.applicable_industries or not m.applicable_industries
        assert m.implementation_difficulty <= 3
        assert m.form3_section == "load"


def test_build_filter_from_profile() -> None:
    f = build_filter_from_profile(
        industry="wholesale",
        revenue_jpy=42_000_000_000,
        freight_tons=180_000.0,
        available_resources=["warehouse_management"],
        max_difficulty=4,
    )
    assert f.industry == "wholesale"
    assert f.revenue_jpy == 42_000_000_000
    assert f.max_difficulty == 4


def test_build_search_summary_lists_measures() -> None:
    result = filter_playbook(filter_=PlaybookFilter(form3_section="wait"))
    text = build_search_summary(result, PlaybookFilter(form3_section="wait"))
    assert "プレイブック検索結果" in text
    assert "Ⅲ 荷待ち時間短縮" in text
    assert "berth_booking_vbs" in text


def test_build_search_summary_empty_result() -> None:
    text = build_search_summary([], None)
    assert "該当施策なし" in text
    assert "条件を緩和" in text


def test_build_search_summary_includes_pitfalls_and_subsidies() -> None:
    result = filter_playbook(filter_=PlaybookFilter(measure_type="modal_shift"))
    assert len(result) >= 1
    text = build_search_summary(result, None)
    assert "失敗パターン" in text
    assert "補助金" in text
