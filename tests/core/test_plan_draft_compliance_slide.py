"""Tier S4: plan_draft._build_compliance_risk_slide / _classify_compliance_step テスト。

generate_plan_draft 全体は e-Stat を踏むため、本ファイルでは:
- `_classify_compliance_step`: 純関数として 5 段すべての境界をテスト
- `_build_compliance_risk_slide`: 合成 PlanDraftResult を validator に渡して
  ChartSpec データ構造を検証

合成 PlanDraftResult は tests/core/test_validators_submission.py と同様のパターン。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.analytics.benchmark import BenchmarkResult
from core.analytics.certified_match import CertifiedMatchResult
from core.analytics.driver_gap import DriverGapResult
from core.analytics.financial_translate import translate_to_pnl_impact
from core.analytics.plan_draft import (
    PlanDraftResult,
    _build_compliance_risk_slide,
    _classify_compliance_step,
)
from core.analytics.simulator import MeasureSimulation, SimulationResult
from core.analytics.target_proposal import NumericTarget, TargetProposalResult
from core.export.citation import (
    Citation,
    co2_factors_citation,
    logistics_efficiency_law_article46_citation,
    logistics_efficiency_law_article65_citation,
    logistics_efficiency_law_article66_citation,
    logistics_efficiency_law_citation,
)
from core.export.docx_form3_writer import PlanMeasure, PlanSection, write_form3
from core.legal.eligibility import EligibilityResult
from core.static.sample_company import get_sample


@pytest.fixture(autouse=True)
def redirect_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """outputs/ を一時ディレクトリにリダイレクトする。"""
    monkeypatch.setattr("core.export.response.OUTPUTS_DIR", tmp_path)


# ---- _classify_compliance_step ----


def test_classify_ok_when_score_100_zero_errors() -> None:
    assert _classify_compliance_step(100.0, 0) == "ok"


def test_classify_guidance_when_score_in_70s_and_one_error() -> None:
    assert _classify_compliance_step(75.0, 1) == "guidance"


def test_classify_recommendation_when_score_in_50s() -> None:
    assert _classify_compliance_step(55.0, 2) == "recommendation"


def test_classify_publication_when_score_in_20s() -> None:
    assert _classify_compliance_step(25.0, 4) == "publication"


def test_classify_fine_when_score_zero() -> None:
    assert _classify_compliance_step(0.0, 8) == "fine"


def test_classify_fine_when_too_many_errors_even_if_score_positive() -> None:
    # error 6 件以上は publication 上限超えで fine
    assert _classify_compliance_step(30.0, 6) == "fine"


# ---- _build_compliance_risk_slide ----


def _make_valid_plan(company_id: str = "testok", is_chain: bool = False) -> PlanDraftResult:
    """エラーなしの正常な PlanDraftResult を組み立てる（compliance slide ビルド用）。"""
    docx_path = write_form3(
        company_name="正常テスト株式会社",
        company_id=company_id,
        main_business="その他の電子部品・デバイス製造業" if not is_chain else "コンビニ本部",
        jsic_code="3159" if not is_chain else "5891",
        clo_name="専務 田中",
        plan_period="2026年度〜2030年度",
        sections=[
            PlanSection(
                title="Ⅱ 積載率向上",
                shipper_class="特定第一種荷主",
                measures=[
                    PlanMeasure(
                        measure="積載率向上",
                        description="TMS 導入で積載率 50%",
                        timing="2026〜2028年度",
                    )
                ],
            ),
            PlanSection(
                title="Ⅲ 荷待ち時間短縮",
                shipper_class="特定第一種荷主",
                measures=[
                    PlanMeasure(
                        measure="バース予約", description="VBS 導入", timing="2026年度"
                    )
                ],
            ),
            PlanSection(
                title="Ⅳ 荷役等時間短縮",
                shipper_class="特定第一種荷主",
                measures=[
                    PlanMeasure(
                        measure="中継輸送", description="長距離分割", timing="2027〜2029年度"
                    )
                ],
            ),
        ] if not is_chain else [
            PlanSection(
                title="Ⅱ 積載率向上",
                measures=[PlanMeasure(measure="積載率", description="d", timing="2026")],
            ),
            PlanSection(
                title="Ⅲ 荷待ち時間短縮",
                measures=[PlanMeasure(measure="バース", description="d", timing="2026")],
            ),
        ],
        is_chain_franchise=is_chain,
    )
    benchmark = BenchmarkResult(
        jsic_code="3159", jsic_name="その他の電子部品",
        category="manufacturing", prefecture="愛知県",
        revenue_jpy=85_000_000_000, logistics_cost_jpy=None,
        estat_minor_code="315",
        national_peer_count=10000, regional_peer_count=1500,
        industry_avg_revenue_jpy=5e9, revenue_vs_avg_pct=800.0,
        revenue_ratio_reliability="large_scale",
        revenue_ratio_warning=None,
        logistics_cost_ratio=None, industry_avg_logistics_ratio=0.018,
        logistics_cost_gap_pct=None,
        co2_intensity_target_pct=23.4,
    )
    driver_gap = DriverGapResult(
        prefecture="愛知県",
        national_workers=1_700_000, regional_workers=120_000,
        regional_share_pct=7.0,
        capacity_reduction_factor=0.135,
        national_capacity_loss=229_500, regional_capacity_loss=16_200,
        annual_overtime_limit_hours=960, annual_working_hours_principle=3300,
        mlit_2030_shortage_pct=34.1,
    )
    categories = ["chain_franchise"] if is_chain else [
        "first_class_shipper", "second_class_shipper"
    ]
    eligibility = EligibilityResult(
        categories=categories,
        annual_freight_tons_used=120_000.0,
        is_estimate=False,
    )
    target_proposal = TargetProposalResult(
        jsic_code="3159", jsic_name="その他の電子部品",
        category="manufacturing", prefecture="愛知県",
        revenue_jpy=85_000_000_000,
        targets=[
            NumericTarget(
                name="輸送量当たりCO2排出原単位",
                current_industry_avg=None, current_industry_avg_unit="g-CO2/トンキロ",
                proposed_target=-23.4, proposed_target_unit="%（2013年度比削減）",
                base_year=2013, target_year=2030,
                rationale="物流分野固有 国家目標",
                citation=co2_factors_citation(),
            ),
            NumericTarget(
                name="営業用普通貨物車 積載率",
                current_industry_avg=38.0, current_industry_avg_unit="%",
                proposed_target=50.0, proposed_target_unit="%",
                base_year=2022, target_year=2030,
                rationale="国交省目指すべき水準",
                citation=Citation(
                    label="自動車輸送統計年報",
                    url="https://www.mlit.go.jp/k-toukei/jidousyayusou.html",
                ),
            ),
        ],
        citations=[co2_factors_citation()],
    )
    simulation = SimulationResult(
        jsic_code="3159", jsic_name="その他の電子部品",
        prefecture="愛知県", revenue_jpy=85_000_000_000,
        annual_freight_tons=120_000.0, is_estimate=False,
        avg_distance_km=500.0, long_distance_share_pct=30.0,
        measures=[
            MeasureSimulation(
                name="モーダルシフト", description="500km超を鉄道シフト",
                co2_reduction_kg_per_year=1_000_000,
                cost_saving_jpy_per_year=72_000_000,
                driver_hours_saving_per_year=None,
                investment_jpy=5_000_000, payback_years=0.07,
                rationale="rationale", citation=co2_factors_citation(),
            ),
            MeasureSimulation(
                name="積載率向上", description="TMS 導入",
                co2_reduction_kg_per_year=2_500_000,
                cost_saving_jpy_per_year=150_000_000,
                driver_hours_saving_per_year=10_000,
                investment_jpy=3_000_000, payback_years=0.02,
                rationale="rationale", citation=co2_factors_citation(),
            ),
        ],
        citations=[co2_factors_citation()],
    )
    certified_matches = CertifiedMatchResult(
        jsic_code="3159", jsic_name="その他の電子部品",
        self_category="manufacturing",
        interested_measure_types=[],
    )
    profile = get_sample("sample_chain_01" if is_chain else "sample_mfg_01")
    assert profile is not None
    financial = translate_to_pnl_impact(profile, simulation)

    article_citation = (
        logistics_efficiency_law_article65_citation()
        if is_chain
        else logistics_efficiency_law_article46_citation()
    )
    return PlanDraftResult(
        company_id=company_id,
        company_name="正常テスト株式会社",
        plan_period="2026年度〜2030年度",
        benchmark=benchmark,
        driver_gap=driver_gap,
        eligibility=eligibility,
        target_proposal=target_proposal,
        simulation=simulation,
        certified_matches=certified_matches,
        financial=financial,
        files={"docx": str(docx_path)},
        citations=[
            co2_factors_citation(),
            logistics_efficiency_law_citation(),
            article_citation,
            logistics_efficiency_law_article66_citation(),
        ],
    )


@pytest.mark.asyncio
async def test_compliance_risk_slide_returns_chart_spec() -> None:
    """正常 PlanDraft で compliance_risk_step スライドが返り、ChartSpec.kind が正しい。"""
    plan = _make_valid_plan()
    slide = await _build_compliance_risk_slide(plan, is_chain_franchise=False)

    assert slide.title == "罰則・社名公表リスクステップ"
    assert slide.chart is not None
    assert slide.chart.kind == "compliance_risk_step"

    data = slide.chart.data
    assert "compliance_score_pct" in data
    assert "error_count" in data
    assert "warning_count" in data
    assert "current_step" in data
    assert data["current_step"] in {"ok", "guidance", "recommendation", "publication", "fine"}
    assert data["is_chain_franchise"] is False
    # missing_actions は list 型
    assert isinstance(data["missing_actions"], list)
    assert len(data["missing_actions"]) <= 5  # 仕様: 最大 5 件


@pytest.mark.asyncio
async def test_compliance_risk_slide_passes_chain_flag_through() -> None:
    """is_chain_franchise=True が ChartSpec.data に伝搬する（条文文言切替用）。"""
    plan = _make_valid_plan(company_id="chaintest", is_chain=True)
    slide = await _build_compliance_risk_slide(plan, is_chain_franchise=True)

    assert slide.chart is not None
    assert slide.chart.data["is_chain_franchise"] is True


@pytest.mark.asyncio
async def test_compliance_risk_slide_extracts_suggestion_text() -> None:
    """validator の error suggestion が missing_actions に含まれる。"""
    # わざと不備のある docx を作って error を発生させる
    bad_docx = write_form3(
        company_name="不備テスト",
        company_id="bad1",
        main_business="製造業",
        jsic_code="3159",
        clo_name="x",
        plan_period="2026〜2030",
        sections=[
            PlanSection(
                title="Ⅱ 積載率向上",
                measures=[PlanMeasure(measure="積載率", description="d", timing="2026")],
            ),
            # 荷待ち時間短縮 / 荷役等時間短縮 を意図的に欠落させる
        ],
        is_chain_franchise=False,
    )
    plan = _make_valid_plan(company_id="bad1")
    # docx を不備版に差し替え
    plan.files["docx"] = str(bad_docx)

    slide = await _build_compliance_risk_slide(plan, is_chain_franchise=False)
    assert slide.chart is not None
    data = slide.chart.data
    # error/warning が立っているはず
    assert data["error_count"] > 0
    # 段階は guidance〜fine のいずれか
    assert data["current_step"] in {"guidance", "recommendation", "publication", "fine"}
    # missing_actions に文字列が入っている
    assert all(isinstance(s, str) and s for s in data["missing_actions"])
