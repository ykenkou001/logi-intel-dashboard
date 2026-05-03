"""core/validators/submission_validator.py の単体テスト。

実 e-Stat API を踏まないため、PlanDraftResult を合成 fixture で組み立てる。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.analytics.benchmark import BenchmarkResult
from core.analytics.certified_match import CertifiedMatchResult
from core.analytics.driver_gap import DriverGapResult
from core.analytics.financial_translate import translate_to_pnl_impact
from core.analytics.plan_draft import PlanDraftResult
from core.analytics.simulator import MeasureSimulation, SimulationResult
from core.analytics.target_proposal import NumericTarget, TargetProposalResult
from core.export.citation import (
    Citation,
    co2_factors_citation,
    logistics_efficiency_law_citation,
)
from core.export.docx_form3_writer import PlanMeasure, PlanSection, write_form3
from core.legal.eligibility import EligibilityResult
from core.static.sample_company import get_sample
from core.validators.submission_validator import (
    ValidationIssue,
    _compute_compliance_score,
    _validate_citations,
    _validate_compliance,
    _validate_form3_completeness,
    _validate_numeric_consistency,
    build_validation_summary,
)


@pytest.fixture(autouse=True)
def redirect_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """outputs/ を一時ディレクトリにリダイレクトする。"""
    monkeypatch.setattr("core.export.response.OUTPUTS_DIR", tmp_path)


def _make_valid_plan(tmp_path: Path) -> PlanDraftResult:
    """エラーなしの正常な PlanDraftResult を組み立てる。"""
    docx_path = write_form3(
        company_name="正常テスト株式会社",
        company_id="testok",
        main_business="その他の電子部品・デバイス製造業",
        jsic_code="3159",
        clo_name="専務 田中",
        plan_period="2026年度〜2030年度",
        sections=[
            PlanSection(
                title="Ⅱ 積載率向上",
                shipper_class="特定第一種荷主",
                measures=[PlanMeasure(
                    measure="積載率向上", description="TMS 導入で積載率 50%",
                    timing="2026〜2028年度",
                )],
            ),
            PlanSection(
                title="Ⅲ 荷待ち時間短縮",
                shipper_class="特定第一種荷主・第二種荷主",
                measures=[PlanMeasure(
                    measure="バース予約", description="VBS 導入で荷待ち半減",
                    timing="2026年度",
                )],
            ),
            PlanSection(
                title="Ⅳ 荷役等時間短縮",
                shipper_class="特定第一種荷主・第二種荷主",
                measures=[PlanMeasure(
                    measure="中継輸送", description="長距離分割で1運行2.5h削減",
                    timing="2027〜2029年度",
                )],
            ),
        ],
        is_chain_franchise=False,
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
    eligibility = EligibilityResult(
        categories=["first_class_shipper", "second_class_shipper"],
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
                citation=Citation(label="自動車輸送統計年報", url="https://www.mlit.go.jp/k-toukei/jidousyayusou.html"),
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
                name="モーダルシフト",
                description="500km超を鉄道シフト",
                co2_reduction_kg_per_year=1_000_000,
                cost_saving_jpy_per_year=72_000_000,
                driver_hours_saving_per_year=None,
                investment_jpy=5_000_000,
                payback_years=0.07,
                rationale="rationale",
                citation=co2_factors_citation(),
            ),
            MeasureSimulation(
                name="積載率向上",
                description="TMS 導入",
                co2_reduction_kg_per_year=2_500_000,
                cost_saving_jpy_per_year=150_000_000,
                driver_hours_saving_per_year=10_000,
                investment_jpy=3_000_000,
                payback_years=0.02,
                rationale="rationale",
                citation=co2_factors_citation(),
            ),
        ],
        citations=[co2_factors_citation()],
    )
    certified_matches = CertifiedMatchResult(
        jsic_code="3159", jsic_name="その他の電子部品",
        self_category="manufacturing",
        interested_measure_types=[],
    )

    profile = get_sample("sample_mfg_01")
    assert profile is not None
    financial = translate_to_pnl_impact(profile, simulation)

    return PlanDraftResult(
        company_id="testok",
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
        ],
    )


# ---- _compute_compliance_score ----


def test_compliance_score_no_issues_is_100() -> None:
    assert _compute_compliance_score(0, 0, total_checks=20) == 100.0


def test_compliance_score_with_errors_decreases() -> None:
    # error 2件 = 100 - 20 = 80
    assert _compute_compliance_score(2, 0, total_checks=20) == 80.0


def test_compliance_score_floor_zero() -> None:
    # error 20件 → -100 だが下限 0
    assert _compute_compliance_score(20, 0, total_checks=20) == 0.0


# ---- _validate_form3_completeness ----


def test_form3_completeness_all_present_no_errors(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    issues = _validate_form3_completeness(
        Path(plan.files["docx"]),
        is_chain_franchise=False,
    )
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], f"Expected no errors but got: {errors}"


def test_form3_completeness_missing_section_yields_error(tmp_path: Path) -> None:
    """荷役等時間短縮セクションが無いと error が出る（非連鎖化）。"""
    docx_path = write_form3(
        company_name="不備テスト",
        company_id="ng1",
        main_business="製造業",
        jsic_code="3159",
        clo_name="x",
        plan_period="2026〜2030",
        sections=[
            PlanSection(
                title="Ⅱ 積載率向上",
                measures=[PlanMeasure(measure="積載率", description="d", timing="2026")],
            ),
            PlanSection(
                title="Ⅲ 荷待ち時間短縮",
                measures=[PlanMeasure(measure="バース", description="d", timing="2026")],
            ),
        ],
        is_chain_franchise=False,
    )
    issues = _validate_form3_completeness(docx_path, is_chain_franchise=False)
    error_codes = [i.code for i in issues if i.severity == "error"]
    assert any("LOADING" in c for c in error_codes), f"Got codes: {error_codes}"


def test_form3_completeness_chain_franchise_skips_loading(tmp_path: Path) -> None:
    """連鎖化事業者は荷役等が無くても error にならない。"""
    docx_path = write_form3(
        company_name="連鎖テスト",
        company_id="chain",
        main_business="コンビニ本部",
        jsic_code="5891",
        clo_name="x",
        plan_period="2026〜2030",
        sections=[
            PlanSection(
                title="Ⅱ 積載率向上",
                measures=[PlanMeasure(measure="積載率", description="d", timing="2026")],
            ),
            PlanSection(
                title="Ⅲ 荷待ち時間短縮",
                measures=[PlanMeasure(measure="バース", description="d", timing="2026")],
            ),
        ],
        is_chain_franchise=True,
    )
    issues = _validate_form3_completeness(docx_path, is_chain_franchise=True)
    error_codes = [i.code for i in issues if i.severity == "error"]
    assert not any("LOADING" in c for c in error_codes), f"Got codes: {error_codes}"


def test_form3_completeness_empty_cell_yields_error(tmp_path: Path) -> None:
    """実施措置欄が空 → error。"""
    docx_path = write_form3(
        company_name="空欄テスト",
        company_id="empty1",
        main_business="製造業",
        jsic_code="3159",
        clo_name="x",
        plan_period="2026〜2030",
        sections=[
            PlanSection(
                title="Ⅱ 積載率向上",
                measures=[PlanMeasure(measure="", description="d", timing="2026")],
            ),
            PlanSection(
                title="Ⅲ 荷待ち時間短縮",
                measures=[PlanMeasure(measure="バース", description="d", timing="2026")],
            ),
            PlanSection(
                title="Ⅳ 荷役等時間短縮",
                measures=[PlanMeasure(measure="中継", description="d", timing="2027")],
            ),
        ],
        is_chain_franchise=False,
    )
    issues = _validate_form3_completeness(docx_path, is_chain_franchise=False)
    assert any(i.code == "FORM3_CELL_EMPTY" for i in issues)


def test_form3_completeness_file_not_found(tmp_path: Path) -> None:
    issues = _validate_form3_completeness(
        tmp_path / "nonexistent.docx",
        is_chain_franchise=False,
    )
    assert any(i.code == "FORM3_FILE_NOT_FOUND" for i in issues)


# ---- _validate_numeric_consistency ----


def test_numeric_consistency_negative_co2_yields_error(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    bad_measure = MeasureSimulation(
        name="壊れ施策", description="d",
        co2_reduction_kg_per_year=-100.0,
        cost_saving_jpy_per_year=0.0,
        driver_hours_saving_per_year=None,
        investment_jpy=1_000_000,
        payback_years=None,
        rationale="r",
        citation=co2_factors_citation(),
    )
    plan.simulation.measures.append(bad_measure)
    issues = _validate_numeric_consistency(plan)
    assert any(i.code == "CO2_NEGATIVE" for i in issues)


def test_numeric_consistency_target_pct_out_of_range(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    plan.target_proposal.targets.append(NumericTarget(
        name="壊れ目標",
        current_industry_avg=None, current_industry_avg_unit="%",
        proposed_target=200.0,  # %換算で範囲外
        proposed_target_unit="%（壊れ）",
        base_year=2013, target_year=2030,
        rationale="r",
        citation=co2_factors_citation(),
    ))
    issues = _validate_numeric_consistency(plan)
    assert any(i.code == "TARGET_PCT_OUT_OF_RANGE" for i in issues)


def test_numeric_consistency_excessive_payback_warning(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    plan.simulation.measures.append(MeasureSimulation(
        name="長期回収施策", description="d",
        co2_reduction_kg_per_year=1.0,
        cost_saving_jpy_per_year=1.0,
        driver_hours_saving_per_year=None,
        investment_jpy=1_000_000,
        payback_years=100.0,
        rationale="r",
        citation=co2_factors_citation(),
    ))
    issues = _validate_numeric_consistency(plan)
    assert any(i.code == "PAYBACK_TOO_LONG" for i in issues)


def test_numeric_consistency_benchmark_ratio_outlier_yields_warning(tmp_path: Path) -> None:
    """業界平均売上比 1000% 超で BENCHMARK_RATIO_OUTLIER warning が出る。"""
    plan = _make_valid_plan(tmp_path)
    plan.benchmark.revenue_vs_avg_pct = 64_000.0  # スマートマート再現
    issues = _validate_numeric_consistency(plan)
    outlier = [i for i in issues if i.code == "BENCHMARK_RATIO_OUTLIER"]
    assert len(outlier) == 1
    assert outlier[0].severity == "warning"
    assert "64000%" in outlier[0].message or "64,000%" in outlier[0].message


def test_numeric_consistency_benchmark_ratio_at_threshold_no_warning(tmp_path: Path) -> None:
    """境界値（1000% 丁度）では warning が出ない。"""
    plan = _make_valid_plan(tmp_path)
    plan.benchmark.revenue_vs_avg_pct = 1000.0
    issues = _validate_numeric_consistency(plan)
    assert not any(i.code == "BENCHMARK_RATIO_OUTLIER" for i in issues)


def test_numeric_consistency_benchmark_ratio_none_no_warning(tmp_path: Path) -> None:
    """revenue_vs_avg_pct が None なら warning は出ない。"""
    plan = _make_valid_plan(tmp_path)
    plan.benchmark.revenue_vs_avg_pct = None
    issues = _validate_numeric_consistency(plan)
    assert not any(i.code == "BENCHMARK_RATIO_OUTLIER" for i in issues)


# ---- _validate_citations ----


def test_citations_empty_yields_error(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    plan.citations = []
    issues = _validate_citations(plan)
    assert any(i.code == "CITATIONS_EMPTY" for i in issues)


def test_citations_missing_efficiency_law_yields_error(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    # CO2 ガイドラインのみ残し、物流効率化法を外す
    plan.citations = [co2_factors_citation()]
    issues = _validate_citations(plan)
    assert any(i.code == "CITATION_EFFICIENCY_LAW_MISSING" for i in issues)


def test_citations_invalid_url_yields_error(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    plan.citations.append(Citation(label="壊れ出典", url="not-a-url"))
    issues = _validate_citations(plan)
    assert any(i.code == "CITATION_URL_INVALID" for i in issues)


# ---- _validate_compliance ----


def test_compliance_load_factor_over_100_yields_error(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    # 既存の積載率目標を 120% に書き換える
    new_targets = []
    for t in plan.target_proposal.targets:
        if "積載率" in t.name:
            new_targets.append(NumericTarget(
                name=t.name,
                current_industry_avg=t.current_industry_avg,
                current_industry_avg_unit=t.current_industry_avg_unit,
                proposed_target=120.0,
                proposed_target_unit="%",
                base_year=t.base_year, target_year=t.target_year,
                rationale=t.rationale, citation=t.citation,
            ))
        else:
            new_targets.append(t)
    plan.target_proposal.targets = new_targets
    issues = _validate_compliance(plan)
    assert any(i.code == "LOAD_FACTOR_OVER_100" for i in issues)


def test_compliance_co2_below_national_target_yields_warning(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    new_targets = []
    for t in plan.target_proposal.targets:
        if "CO2" in t.name:
            new_targets.append(NumericTarget(
                name=t.name,
                current_industry_avg=t.current_industry_avg,
                current_industry_avg_unit=t.current_industry_avg_unit,
                proposed_target=-10.0,  # ▲10% は国家目標 ▲23.4% を下回る
                proposed_target_unit="%",
                base_year=t.base_year, target_year=t.target_year,
                rationale=t.rationale, citation=t.citation,
            ))
        else:
            new_targets.append(t)
    plan.target_proposal.targets = new_targets
    issues = _validate_compliance(plan)
    assert any(i.code == "CO2_BELOW_NATIONAL_TARGET" for i in issues)


# ---- build_validation_summary ----


def test_build_validation_summary_pass(tmp_path: Path) -> None:
    plan = _make_valid_plan(tmp_path)
    from core.validators.submission_validator import ValidationReport
    report = ValidationReport(
        company_id=plan.company_id, company_name=plan.company_name,
        overall_pass=True, compliance_score_pct=100.0,
        checked_files=plan.files, issues=[],
    )
    text = build_validation_summary(report)
    assert "PASS" in text
    assert "100.0%" in text


def test_build_validation_summary_fail_lists_errors(tmp_path: Path) -> None:
    from core.validators.submission_validator import ValidationReport
    issues = [ValidationIssue(
        severity="error", category="form3_completeness",
        code="FORM3_CELL_EMPTY", message="セル空欄",
        suggestion="埋めてください",
    )]
    report = ValidationReport(
        company_id="x", company_name="X",
        overall_pass=False, compliance_score_pct=90.0,
        checked_files={}, issues=issues,
    )
    text = build_validation_summary(report)
    assert "FAIL" in text
    assert "FORM3_CELL_EMPTY" in text
    assert "埋めてください" in text
