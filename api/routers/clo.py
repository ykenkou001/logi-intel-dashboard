"""CLO 支援エンドポイント群。

`mcp_server/tools/clo_tools.py` と同じ core/ 関数を呼び出し、ToolResponse を JSON 化して返す。
MCP ツールと REST API で出力構造が完全に一致するため、Web フロントは MCP と同じ
スキーマで表示できる。
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from api.schemas.responses import ToolResponseModel
from core.analytics.benchmark import analyze_benchmark, build_benchmark_summary
from core.analytics.certified_match import build_certified_match_summary, find_matches
from core.analytics.driver_gap import analyze_driver_gap, build_driver_gap_summary
from core.analytics.eligibility_analysis import build_eligibility_summary
from core.analytics.feasibility_check import build_feasibility_summary, check_feasibility
from core.analytics.financial_translate import (
    build_financial_translate_summary,
    translate_to_pnl_impact,
)
from core.analytics.measure_eval import build_eval_summary, evaluate_measures
from core.analytics.periodic_report import (
    build_periodic_report_summary,
    generate_periodic_report,
)
from core.analytics.plan_draft import build_plan_draft_summary, generate_plan_draft
from core.analytics.scenario_sim import build_scenario_summary, simulate_scenarios
from core.analytics.simulator import build_simulation_summary, simulate_measures
from core.analytics.target_proposal import build_target_proposal_summary, propose_targets
from core.export.citation import Citation, logistics_efficiency_law_citation
from core.export.response import ToolResponse
from core.legal.eligibility import evaluate_eligibility
from core.playbook.filters import PlaybookFilter, build_search_summary, filter_playbook
from core.static._freshness import all_warnings
from core.static.efficiency_law_certified import IndustryCategory, MeasureType
from core.static.sample_company import get_sample
from core.storage import get_storage
from core.validators.submission_validator import (
    build_validation_summary,
    validate_submission,
)

router = APIRouter(prefix="/api/v1/clo", tags=["clo"])

_VALID_SAMPLE_IDS = ("sample_mfg_01", "sample_wholesale_01", "sample_chain_01")


def _resolve_profile_or_404(company_id: str):  # type: ignore[no-untyped-def]
    profile = get_sample(company_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"会社 ID '{company_id}' が見つかりません。サンプルは "
                f"{', '.join(_VALID_SAMPLE_IDS)}、または "
                "POST /api/v1/company/load で取込済みの ID が利用可能"
            ),
        )
    return profile


def _publish_files(response: ToolResponse) -> None:
    """ToolResponse.files の各値をストレージに公開しキーで上書きする。

    LocalStorage では outputs/ から見た相対パスに正規化、S3Storage では
    アップロード後 S3 オブジェクトキーに置換される。
    """
    if not response.files:
        return
    from pathlib import Path

    storage = get_storage()
    new_files: dict[str, str] = {}
    for key, value in response.files.items():
        try:
            new_files[key] = storage.publish(Path(value))
        except Exception:
            new_files[key] = value
    response.files = new_files


def _to_model(response: ToolResponse) -> ToolResponseModel:
    _publish_files(response)
    return ToolResponseModel.model_validate(response.to_dict())


# ─── Step 1: 業界ベンチマーク ──────────────────────────────────────────
@router.get("/benchmark", response_model=ToolResponseModel)
async def benchmark_position(
    jsic_code: Annotated[str, Query(description="JSIC 細分類4桁コード")],
    prefecture: Annotated[str, Query(description="都道府県名")],
    revenue_jpy: Annotated[int, Query(description="年間売上（円）", gt=0)],
    logistics_cost_jpy: Annotated[int | None, Query(description="年間物流コスト（円）")] = None,
) -> ToolResponseModel:
    """自社の業界ベンチマーク位置を分析する。"""
    try:
        result = await analyze_benchmark(
            jsic_code=jsic_code,
            prefecture=prefecture,
            revenue_jpy=revenue_jpy,
            logistics_cost_jpy=logistics_cost_jpy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_benchmark_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
    )
    return _to_model(response)


# ─── Step 2: ドライバー需給ギャップ ─────────────────────────────────────
@router.get("/driver-gap", response_model=ToolResponseModel)
async def driver_gap(
    prefecture: Annotated[str, Query(description="都道府県名")],
) -> ToolResponseModel:
    """指定都道府県のドライバー需給ギャップを分析する。"""
    try:
        result = await analyze_driver_gap(prefecture)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_driver_gap_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
    )
    return _to_model(response)


# ─── Step 3: 適用判定 ─────────────────────────────────────────────────
@router.get("/eligibility", response_model=ToolResponseModel)
async def eligibility(
    jsic_code: Annotated[str, Query(description="JSIC 細分類4桁コード")],
    annual_revenue_jpy: Annotated[int | None, Query(description="年間売上（円）")] = None,
    annual_freight_tons_total: Annotated[
        float | None, Query(description="年間取扱貨物量（実測トン）")
    ] = None,
    is_chain_franchise: Annotated[bool, Query(description="連鎖化事業者か")] = False,
    override_first_class: Annotated[bool | None, Query()] = None,
    override_second_class: Annotated[bool | None, Query()] = None,
) -> ToolResponseModel:
    """物流効率化法の特定荷主3区分（第46条／第65条）への適用判定。"""
    result = evaluate_eligibility(
        jsic_code=jsic_code,
        annual_freight_tons_total=annual_freight_tons_total,
        annual_revenue_jpy=annual_revenue_jpy,
        is_chain_franchise=is_chain_franchise,
        override_first_class=override_first_class,
        override_second_class=override_second_class,
    )
    summary = build_eligibility_summary(
        result=result,
        jsic_code=jsic_code,
        annual_revenue_jpy=annual_revenue_jpy,
        annual_freight_tons_total=annual_freight_tons_total,
        is_chain_franchise=is_chain_franchise,
    )
    citations: list[Citation] = [logistics_efficiency_law_citation()]
    if result.is_estimate:
        citations.append(
            Citation(
                label="業種別物流原単位（売上→取扱量推計／物流センサス2021ベース）",
                url="https://www.mlit.go.jp/sogoseisaku/transport/butsuryu06100.html",
                accessed_via="国交省 物流センサス（静的参照）",
            )
        )
    response = ToolResponse(
        summary=summary,
        citations=citations,
        freshness_warnings=all_warnings(),
    )
    return _to_model(response)


# ─── Step 4: 数値目標提案 ─────────────────────────────────────────────
@router.get("/target-proposal", response_model=ToolResponseModel)
async def target_proposal(
    jsic_code: Annotated[str, Query()],
    prefecture: Annotated[str, Query()],
    revenue_jpy: Annotated[int, Query(gt=0)],
    revenue_vs_industry_avg_pct: Annotated[float | None, Query()] = None,
) -> ToolResponseModel:
    """CLO 計画書「数値目標」セクション草稿を生成する。"""
    try:
        result = propose_targets(
            jsic_code=jsic_code,
            prefecture=prefecture,
            revenue_jpy=revenue_jpy,
            revenue_vs_industry_avg_pct=revenue_vs_industry_avg_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_target_proposal_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
    )
    return _to_model(response)


# ─── Step 5: 5施策効果シミュレータ ────────────────────────────────────
@router.get("/simulate-measures", response_model=ToolResponseModel)
async def simulate_measures_endpoint(
    jsic_code: Annotated[str, Query()],
    prefecture: Annotated[str, Query()],
    revenue_jpy: Annotated[int, Query(gt=0)],
    annual_freight_tons: Annotated[float | None, Query()] = None,
    avg_distance_km: Annotated[float, Query(gt=0)] = 500.0,
    long_distance_share_pct: Annotated[float, Query(ge=0, le=100)] = 30.0,
) -> ToolResponseModel:
    """5施策の効果（CO2/コスト/投資/回収期間）を同時試算。"""
    try:
        result = simulate_measures(
            jsic_code=jsic_code,
            prefecture=prefecture,
            revenue_jpy=revenue_jpy,
            annual_freight_tons=annual_freight_tons,
            avg_distance_km=avg_distance_km,
            long_distance_share_pct=long_distance_share_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_simulation_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
    )
    return _to_model(response)


# ─── 認定事業マッチング ────────────────────────────────────────────────
@router.get("/certified-match", response_model=ToolResponseModel)
async def certified_match(
    jsic_code: Annotated[str, Query()],
    interested_measure_types: Annotated[
        list[str] | None, Query(description="関心施策タイプ（複数指定可）")
    ] = None,
) -> ToolResponseModel:
    """物流効率化法 認定事業から類似事例を検索。"""
    try:
        result = find_matches(
            jsic_code=jsic_code,
            interested_measure_types=interested_measure_types,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_certified_match_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
    )
    return _to_model(response)


# ─── 計画書ドラフト統合生成 ──────────────────────────────────────────
@router.post("/plan-draft/{company_id}", response_model=ToolResponseModel)
async def plan_draft(company_id: str) -> ToolResponseModel:
    """CLO 中長期計画書ドラフトを統合生成し、PPT/Word/Excel/Markdown を出力。"""
    profile = _resolve_profile_or_404(company_id)
    try:
        result = await generate_plan_draft(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_plan_draft_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        files=result.files,
        data_source=profile.data_source,
    )
    return _to_model(response)


# ─── Step 3.5/1: プレイブック検索 ─────────────────────────────────────
@router.get("/playbook", response_model=ToolResponseModel)
async def playbook_search(
    industry: Annotated[str | None, Query()] = None,
    revenue_jpy: Annotated[int | None, Query()] = None,
    freight_tons: Annotated[float | None, Query()] = None,
    max_difficulty: Annotated[int | None, Query(ge=1, le=5)] = None,
    form3_section: Annotated[str | None, Query()] = None,
    measure_type: Annotated[str | None, Query()] = None,
) -> ToolResponseModel:
    """施策プレイブックライブラリから条件合致の標準施策を検索。"""
    from typing import cast

    filter_ = PlaybookFilter(
        industry=cast(IndustryCategory, industry) if industry else None,
        revenue_jpy=revenue_jpy,
        freight_tons=freight_tons,
        max_difficulty=max_difficulty,
        form3_section=form3_section if form3_section else None,
        measure_type=cast(MeasureType, measure_type) if measure_type else None,
    )
    results = filter_playbook(filter_=filter_)
    response = ToolResponse(
        summary=build_search_summary(results, filter_),
        citations=[logistics_efficiency_law_citation()],
        freshness_warnings=all_warnings(),
    )
    return _to_model(response)


# ─── Step 3.5/2: 施策評価エンジン ─────────────────────────────────────
@router.get("/measure-eval/{company_id}", response_model=ToolResponseModel)
async def measure_eval(
    company_id: str,
    max_difficulty: Annotated[int | None, Query(ge=1, le=5)] = None,
    available_resources: Annotated[list[str] | None, Query()] = None,
) -> ToolResponseModel:
    """自社プロフィール × プレイブック施策のスコアリング Top 3。"""
    profile = _resolve_profile_or_404(company_id)
    result = evaluate_measures(
        profile=profile,
        available_resources=available_resources if available_resources else None,
        max_difficulty=max_difficulty,
    )
    response = ToolResponse(
        summary=build_eval_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        data_source=profile.data_source,
    )
    return _to_model(response)


# ─── Step 3.5/3: シナリオシミュレータ ────────────────────────────────
@router.post("/scenario-sim/{company_id}", response_model=ToolResponseModel)
async def scenario_sim(
    company_id: str,
    selected_measure_ids: Annotated[
        list[str] | None,
        Query(description="評価対象施策の measure_id リスト。None で Top 3 自動採用"),
    ] = None,
) -> ToolResponseModel:
    """保守/標準/上振れ × What-if 8 種のシナリオシミュレーション。"""
    profile = _resolve_profile_or_404(company_id)
    try:
        result = simulate_scenarios(
            profile=profile,
            selected_measure_ids=selected_measure_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_scenario_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        data_source=profile.data_source,
    )
    return _to_model(response)


# ─── Step 3.5/4: 財務翻訳レイヤ ───────────────────────────────────────
@router.post("/financial-translate/{company_id}", response_model=ToolResponseModel)
async def financial_translate(company_id: str) -> ToolResponseModel:
    """物流 KPI を P&L インパクト（営業利益・炭素回避額・5年 NPV）に翻訳。"""
    profile = _resolve_profile_or_404(company_id)
    try:
        plan = await generate_plan_draft(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = translate_to_pnl_impact(profile, plan.simulation)
    response = ToolResponse(
        summary=build_financial_translate_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        data_source=profile.data_source,
    )
    return _to_model(response)


# ─── Step 3.5/5: 実現可能性チェッカー ────────────────────────────────
@router.get("/feasibility/{company_id}", response_model=ToolResponseModel)
async def feasibility_check(
    company_id: str,
    target_year: Annotated[int, Query(ge=2024, le=2050)] = 2030,
    available_resources: Annotated[list[str] | None, Query()] = None,
) -> ToolResponseModel:
    """施策の実行可否と KPI 到達可能性を 緑/黄/赤 で判定。"""
    profile = _resolve_profile_or_404(company_id)
    result = check_feasibility(
        profile=profile,
        target_year=target_year,
        available_resources=available_resources if available_resources else None,
    )
    response = ToolResponse(
        summary=build_feasibility_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        data_source=profile.data_source,
    )
    return _to_model(response)


# ─── Step 3.5/6: 提出前バリデータ ─────────────────────────────────────
@router.post("/submission-validate/{company_id}", response_model=ToolResponseModel)
async def submission_validate(company_id: str) -> ToolResponseModel:
    """計画書ドラフトの提出前バリデータ（網羅性・数値整合性・出典・告示準拠）。"""
    profile = _resolve_profile_or_404(company_id)
    try:
        report = await validate_submission(company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_validation_summary(report),
        citations=[logistics_efficiency_law_citation()],
        freshness_warnings=all_warnings(),
        files=dict(report.checked_files),
        data_source=profile.data_source,
    )
    return _to_model(response)


# ─── Step 3.5/7: 定期報告書（様式第5）ドラフト ───────────────────────
@router.post("/periodic-report/{company_id}", response_model=ToolResponseModel)
async def periodic_report(
    company_id: str,
    report_fy: Annotated[int, Query(ge=2024, le=2050)] = 2026,
) -> ToolResponseModel:
    """様式第5（定期報告書）ドラフトを生成。毎年7月末提出に対応。"""
    _resolve_profile_or_404(company_id)
    try:
        result = await generate_periodic_report(
            company_id=company_id,
            report_fy=report_fy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_periodic_report_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        files=dict(result.files),
        data_source=result.data_source,
    )
    return _to_model(response)
