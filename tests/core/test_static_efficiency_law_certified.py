"""core/static/efficiency_law_certified.py の単体テスト。"""
from __future__ import annotations

from typing import get_args, get_type_hints

from core.static.efficiency_law_certified import (
    CERTIFIED_CASES,
    CertifiedCase,
)


def test_certified_cases_include_mlit_and_meti_cases() -> None:
    """既存10件 + NotebookLM 取込7件以上が存在する。"""
    assert len(CERTIFIED_CASES) >= 17


def test_case_source_values_are_allowed_literals() -> None:
    """全 case_source が dataclass の Literal 許容値内。"""
    hints = get_type_hints(CertifiedCase)
    allowed_sources = set(get_args(hints["case_source"]))

    assert allowed_sources == {
        "mlit_certified",
        "meti_clo_handbook",
        "industry_press",
        "interview",
    }
    for case in CERTIFIED_CASES:
        assert case.case_source in allowed_sources


def test_meti_clo_handbook_cases_are_at_least_7() -> None:
    """経産省 CLO 取組事例集由来の case が7件以上ある。"""
    meti_cases = [
        case for case in CERTIFIED_CASES if case.case_source == "meti_clo_handbook"
    ]
    assert len(meti_cases) >= 7


def test_non_empty_before_after_descriptions_have_content() -> None:
    """before/after が指定されている case は短すぎない。"""
    for case in CERTIFIED_CASES:
        if case.before_description != "":
            assert len(case.before_description) >= 10
        if case.after_description != "":
            assert len(case.after_description) >= 10


def test_investment_band_order_when_present() -> None:
    """投資レンジがある場合は下限 <= 上限。"""
    for case in CERTIFIED_CASES:
        if case.investment_jpy_band is not None:
            lower, upper = case.investment_jpy_band
            assert lower <= upper


def test_payback_months_positive_when_present() -> None:
    """回収期間がある場合は正の整数。"""
    for case in CERTIFIED_CASES:
        if case.payback_months is not None:
            assert isinstance(case.payback_months, int)
            assert case.payback_months > 0

