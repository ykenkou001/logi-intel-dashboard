"""core/legal/article_resolver.py の単体テスト。"""
from __future__ import annotations

from core.legal.article_resolver import (
    expected_plan_article_number,
    resolve_clo_appointment_law_article_label,
    resolve_plan_law_article_label,
)
from core.legal.eligibility import EligibilityResult


def _eligibility(*categories: str) -> EligibilityResult:
    """テスト用の EligibilityResult を組み立てる。"""
    return EligibilityResult(
        categories=list(categories),  # type: ignore[arg-type]
        annual_freight_tons_used=100_000,
        is_estimate=False,
    )


# ---- resolve_plan_law_article_label ----


def test_chain_franchise_resolves_to_article65() -> None:
    label = resolve_plan_law_article_label(_eligibility("chain_franchise"))
    assert "第65条" in label
    assert "連鎖化事業者" in label


def test_first_class_shipper_resolves_to_article46() -> None:
    label = resolve_plan_law_article_label(_eligibility("first_class_shipper"))
    assert "第46条" in label
    assert "荷主" in label


def test_second_class_shipper_resolves_to_article46() -> None:
    label = resolve_plan_law_article_label(_eligibility("second_class_shipper"))
    assert "第46条" in label


def test_both_shipper_classes_resolve_to_article46() -> None:
    """第一種・第二種双方該当でも第46条で正しい。"""
    label = resolve_plan_law_article_label(
        _eligibility("first_class_shipper", "second_class_shipper"),
    )
    assert "第46条" in label


def test_chain_franchise_takes_precedence_over_shipper() -> None:
    """連鎖化と荷主が両方該当しても連鎖化（第65条）が優先される。"""
    label = resolve_plan_law_article_label(
        _eligibility("chain_franchise", "first_class_shipper"),
    )
    assert "第65条" in label
    assert "第46条" not in label


def test_none_returns_no_clo_obligation_label() -> None:
    label = resolve_plan_law_article_label(_eligibility("none"))
    assert "該当条文なし" in label or "義務なし" in label


# ---- resolve_clo_appointment_law_article_label ----


def test_clo_appointment_label_when_required() -> None:
    label = resolve_clo_appointment_law_article_label(
        _eligibility("first_class_shipper"),
    )
    assert label is not None
    assert "第66条" in label
    assert "CLO" in label


def test_clo_appointment_label_returns_none_when_not_required() -> None:
    """CLO 選任義務なし → None。"""
    label = resolve_clo_appointment_law_article_label(_eligibility("none"))
    assert label is None


# ---- expected_plan_article_number ----


def test_expected_article_chain_franchise_is_65() -> None:
    assert expected_plan_article_number(_eligibility("chain_franchise")) == 65


def test_expected_article_shipper_is_46() -> None:
    assert expected_plan_article_number(_eligibility("first_class_shipper")) == 46


def test_expected_article_none_returns_none() -> None:
    assert expected_plan_article_number(_eligibility("none")) is None
