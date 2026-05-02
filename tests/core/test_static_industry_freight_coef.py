"""core/static/industry_freight_coef.py の単体テスト。"""
from __future__ import annotations

from core.static.industry_freight_coef import COEF, estimate_freight_tons


def test_estimate_with_jsic_specific_override() -> None:
    """細分類別の上書き値が優先される。"""
    # 電子部品（2911）: 19 トン/億円
    result = estimate_freight_tons("2911", 10_000_000_000)  # 100 億円
    assert result == 1900.0


def test_estimate_with_category_fallback() -> None:
    """細分類が未登録でもカテゴリのフォールバックが効く。"""
    # 自動車製造（3211）は BY_JSIC_CODE に登録あり（250.0）
    result = estimate_freight_tons("3211", 100_000_000_000)  # 1,000 億円
    assert result == 250_000.0


def test_estimate_unknown_jsic_returns_none() -> None:
    """未登録 JSIC は None。"""
    result = estimate_freight_tons("9999", 10_000_000_000)
    assert result is None


def test_estimate_transport_industry_returns_none() -> None:
    """運送業（4411 等）は荷主ではないため None または 0。"""
    # 4411 = 一般貨物自動車運送業（transport カテゴリ、係数 0）
    result = estimate_freight_tons("4411", 10_000_000_000)
    # 係数 0 のため None を返す（荷主判定対象外）
    assert result is None


def test_chain_franchise_coefficient() -> None:
    """連鎖化（コンビニ 5891）の推計が動作。"""
    # 100 億円 × 320 = 32,000 トン
    result = estimate_freight_tons("5891", 10_000_000_000)
    assert result == 32_000.0


def test_categories_have_positive_coefficients() -> None:
    """主要荷主カテゴリは正の係数を持つ。"""
    for cat in ("manufacturing", "wholesale", "retail", "chain_franchise"):
        assert COEF.BY_CATEGORY[cat] > 0
