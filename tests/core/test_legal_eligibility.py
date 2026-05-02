"""core/legal/eligibility.py の単体テスト。"""
from __future__ import annotations

from core.legal.eligibility import (
    CHAIN_FRANCHISE_THRESHOLD_JPY,
    SHIPPER_THRESHOLD_TONS,
    evaluate_eligibility,
)


def test_manufacturing_above_threshold_first_and_second_class() -> None:
    """製造業で 9 万トン超 → 第一種・第二種荷主 両方該当（既定動作）。"""
    result = evaluate_eligibility(
        jsic_code="3159",
        annual_freight_tons_total=120_000,
    )
    assert "first_class_shipper" in result.categories
    assert "second_class_shipper" in result.categories
    assert result.applies is True
    assert result.must_appoint_clo is True
    assert result.is_estimate is False


def test_manufacturing_below_threshold_none() -> None:
    """製造業でも 9 万トン未満 → 該当なし。"""
    result = evaluate_eligibility(
        jsic_code="3159",
        annual_freight_tons_total=50_000,
    )
    assert result.categories == ["none"]
    assert result.applies is False


def test_estimate_from_revenue_when_tons_missing() -> None:
    """取扱量未指定なら売上から推計する。"""
    # 売上 1,000 億円・電子部品（係数 19）→ 約 19,000 トン → 該当なし
    result = evaluate_eligibility(
        jsic_code="3159",
        annual_revenue_jpy=100_000_000_000,
    )
    assert result.is_estimate is True
    assert result.annual_freight_tons_used is not None
    assert result.categories == ["none"]


def test_estimate_borderline_warning() -> None:
    """ボーダーラインの推計値で注意喚起ノートが追加される。"""
    # 卸売（係数 380）の売上 250 億円 → 95,000 トン（9万トン直近）
    result = evaluate_eligibility(
        jsic_code="5141",
        annual_revenue_jpy=25_000_000_000,
    )
    assert result.is_estimate is True
    # 9 万トン超で第一種・第二種に該当
    assert "first_class_shipper" in result.categories
    # ボーダーライン警告
    assert any("ボーダーライン" in n for n in result.notes)


def test_chain_franchise_with_high_revenue() -> None:
    """連鎖化フラグ ON ＋ 売上閾値超 → 連鎖化事業者該当。"""
    result = evaluate_eligibility(
        jsic_code="5891",
        annual_freight_tons_total=450_000,
        annual_revenue_jpy=CHAIN_FRANCHISE_THRESHOLD_JPY * 3,
        is_chain_franchise=True,
    )
    assert "chain_franchise" in result.categories


def test_chain_franchise_low_revenue_fallback_note() -> None:
    """連鎖化フラグ ON でも売上閾値未満 → 注意ノート、連鎖化区分には入らない。"""
    result = evaluate_eligibility(
        jsic_code="5891",
        annual_freight_tons_total=50_000,
        annual_revenue_jpy=10_000_000_000,
        is_chain_franchise=True,
    )
    assert "chain_franchise" not in result.categories
    assert any("連鎖化閾値未満" in n for n in result.notes)


def test_transport_industry_not_shipper() -> None:
    """運送業（H 大分類）は荷主判定対象外。"""
    result = evaluate_eligibility(
        jsic_code="4411",   # 一般貨物自動車運送業
        annual_freight_tons_total=200_000,
    )
    # 運送業は category_of で transport なので shipper_industry=False
    assert result.categories == ["none"]
    assert any("運送業者" in n or "対象外" in n for n in result.notes)


def test_override_first_class_force_apply() -> None:
    """override_first_class=True で取扱量関係なく該当扱い。"""
    result = evaluate_eligibility(
        jsic_code="3159",
        annual_freight_tons_total=10_000,
        override_first_class=True,
    )
    assert "first_class_shipper" in result.categories


def test_override_second_class_force_exclude() -> None:
    """override_second_class=False で第二種から外せる。"""
    result = evaluate_eligibility(
        jsic_code="3159",
        annual_freight_tons_total=120_000,
        override_second_class=False,
    )
    assert "first_class_shipper" in result.categories
    assert "second_class_shipper" not in result.categories


def test_threshold_constants_are_law_compliant() -> None:
    """閾値定数が法令通り。"""
    assert SHIPPER_THRESHOLD_TONS == 90_000
