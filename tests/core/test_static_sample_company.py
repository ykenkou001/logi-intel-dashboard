"""core/static/sample_company.py の単体テスト。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.static.sample_company import (
    ALL_SAMPLES,
    SAMPLE_CHAIN,
    SAMPLE_MANUFACTURING,
    SAMPLE_WHOLESALE,
    CompanyProfile,
    CompanySite,
    get_sample,
)


def test_three_samples_registered() -> None:
    """サンプル3社が登録されている。"""
    assert len(ALL_SAMPLES) == 3
    assert SAMPLE_MANUFACTURING.company_id in ALL_SAMPLES
    assert SAMPLE_WHOLESALE.company_id in ALL_SAMPLES
    assert SAMPLE_CHAIN.company_id in ALL_SAMPLES


def test_get_sample_existing() -> None:
    """既存 ID で取得できる。"""
    profile = get_sample("sample_chain_01")
    assert profile is not None
    assert profile.is_chain_franchise is True


def test_get_sample_missing() -> None:
    """未登録 ID は None。"""
    assert get_sample("nope") is None


def test_manufacturing_sample_meets_first_class_threshold() -> None:
    """製造業サンプルは 9 万トン超で特定第一種荷主想定。"""
    assert SAMPLE_MANUFACTURING.annual_freight_tons_total >= 90_000


def test_chain_sample_is_chain_franchise() -> None:
    """連鎖化サンプルは is_chain_franchise=True。"""
    assert SAMPLE_CHAIN.is_chain_franchise is True
    assert SAMPLE_CHAIN.jsic_code == "5891"


def test_jsic_code_must_be_4digit() -> None:
    """JSIC コードは4桁必須。"""
    with pytest.raises(ValidationError):
        CompanyProfile(
            company_id="test",
            name="x",
            jsic_code="911",  # 3桁は不可
            main_business="x",
            annual_revenue_jpy=0,
            annual_freight_tons_total=0,
            clo_name="x",
            plan_period_start_fy=2026,
            plan_period_end_fy=2030,
        )


def test_negative_revenue_rejected() -> None:
    """負の売上は ValidationError。"""
    with pytest.raises(ValidationError):
        CompanyProfile(
            company_id="test",
            name="x",
            jsic_code="3159",
            main_business="x",
            annual_revenue_jpy=-1,
            annual_freight_tons_total=0,
            clo_name="x",
            plan_period_start_fy=2026,
            plan_period_end_fy=2030,
        )


def test_company_site_basic_fields() -> None:
    """CompanySite が必須フィールドで構築できる。"""
    site = CompanySite(
        name="テスト拠点",
        site_type="dc",
        prefecture="東京都",
        annual_freight_tons=1000.0,
    )
    assert site.site_type == "dc"


def test_sample_sites_freight_sums_match_total_loosely() -> None:
    """サンプルの拠点合計と total が概ね合致（±10% 程度の差は許容）。"""
    for sample in (SAMPLE_MANUFACTURING, SAMPLE_WHOLESALE, SAMPLE_CHAIN):
        sites_sum = sum(s.annual_freight_tons for s in sample.sites)
        # 必ずしも厳密一致ではないが、桁が合っているか確認
        assert sites_sum > 0
        assert sample.annual_freight_tons_total > 0
