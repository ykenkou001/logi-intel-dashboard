"""CLO 支援エンドポイント群。

`mcp_server/tools/clo_tools.py` と同じ core/ 関数を呼び出し、ToolResponse を JSON 化して返す。
MCP ツールと REST API で出力構造が完全に一致するため、Web フロントは MCP と同じ
スキーマで表示できる。
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

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
from core.analytics.operation_cockpit import (
    CockpitResult,
    DecisionRecord,
    DecisionStatus,
    append_decision,
    build_cockpit_summary,
    build_daily_cockpit,
)
from core.analytics.periodic_report import (
    build_periodic_report_summary,
    generate_periodic_report,
)
from core.analytics.plan_draft import build_plan_draft_summary, generate_plan_draft
from core.analytics.scenario_sim import build_scenario_summary, simulate_scenarios
from core.analytics.simulator import build_simulation_summary, simulate_measures
from core.analytics.standardization_score import (
    build_standardization_summary,
    compute_standardization_score,
)
from core.analytics.target_proposal import build_target_proposal_summary, propose_targets
from core.analytics.wait_time_heatmap import HeatmapResult, build_wait_time_heatmap
from core.analytics.waste_trap import (
    MeasureExecutionRecord,
    build_waste_trap_summary,
    detect_waste_traps,
)
from core.export.citation import Citation, logistics_efficiency_law_citation
from core.export.ppt_writer import write_clo_executive_brief
from core.export.response import ToolResponse
from core.io.measure_run_store import load_runs, merge_with_stored, save_runs
from core.io.override_store import load_override
from core.io.profile_resolver import ProfileNotFoundError, resolve_profile
from core.legal.eligibility import evaluate_eligibility
from core.playbook.filters import PlaybookFilter, build_search_summary, filter_playbook
from core.playbook.industry_packages import (
    CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE,
    build_industry_package_summary,
    get_package,
    resolve_company_package,
)
from core.playbook.measures import get_measure
from core.static._freshness import all_warnings
from core.static.efficiency_law_certified import IndustryCategory, MeasureType
from core.static.jsic import category_of
from core.static.sample_company import CompanyProfile
from core.storage import get_storage
from core.validators.submission_validator import (
    build_validation_summary,
    validate_submission,
)

router = APIRouter(prefix="/api/v1/clo", tags=["clo"])


def _resolve_profile_or_404(company_id: str) -> CompanyProfile:
    try:
        return resolve_profile(company_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


# ─── フェーズ4.1 a.3: 経営会議 3 スライド要約 ─────────────────────
@router.get("/executive-brief/{company_id}", response_model=ToolResponseModel)
async def executive_brief(company_id: str) -> ToolResponseModel:
    """経営会議直前 3 分要約 PPT（3 スライド版）を生成して返す。

    内部で measure_eval + feasibility_check + financial_translate を呼び、
    やる 3 件 / やらない 3 件 / 経営サマリーを 3 スライド PPT に圧縮する。
    """
    profile = _resolve_profile_or_404(company_id)
    eval_result = evaluate_measures(profile=profile)
    feas_result = check_feasibility(profile=profile)
    main_prefecture = profile.sites[0].prefecture if profile.sites else "東京都"
    sim_result = simulate_measures(
        jsic_code=profile.jsic_code,
        prefecture=main_prefecture,
        revenue_jpy=profile.annual_revenue_jpy,
        annual_freight_tons=profile.annual_freight_tons_total,
    )
    fin_result = translate_to_pnl_impact(profile, sim_result)

    op_profit_oku = (fin_result.total_operating_profit_increase_jpy * 0.7) / 1e8
    co2_t = (sim_result.total_co2_reduction_kg * 0.7) / 1000
    npv_oku = fin_result.total_5y_npv_jpy / 1e8
    carbon_low_m = fin_result.total_carbon_avoidance_jpy_low / 1e6
    carbon_high_m = fin_result.total_carbon_avoidance_jpy_high / 1e6
    executive_summary = [
        f"営業利益(標準): +{op_profit_oku:.2f}億円/年",
        f"CO2削減(標準): 約 {co2_t:,.0f}トン-CO2/年",
        f"炭素価格回避: {carbon_low_m:.0f}〜{carbon_high_m:.0f}百万円/年",
        f"5年累積NPV: 約 {npv_oku:.2f}億円 (割引率3%)",
        f"会社名: {profile.name}（JSIC {profile.jsic_code}）",
        f"CLO: {profile.clo_name} / 計画期間 "
        f"FY{profile.plan_period_start_fy}〜FY{profile.plan_period_end_fy}",
        f"年間売上 {profile.annual_revenue_jpy / 1e8:.0f}億円 / "
        f"取扱量 {profile.annual_freight_tons_total:,.0f}トン",
    ]

    actions_to_pursue: list[str] = []
    for s in eval_result.top_recommendations[:3]:
        cost_oku = (s.estimated_annual_cost_saving_jpy or 0) / 1e8
        actions_to_pursue.append(
            f"{s.measure.name}（年 +{cost_oku:.2f}億円・スコア{s.total_score:.0f}）"
        )

    red_verdicts = [v for v in feas_result.measure_verdicts if v.level == "red"][:3]
    actions_to_skip: list[str] = [f"{v.measure.name}（{v.primary_reason}）" for v in red_verdicts]
    if len(actions_to_skip) < 3:
        for s in eval_result.bottom_candidates[: 3 - len(actions_to_skip)]:
            actions_to_skip.append(f"{s.measure.name}（{s.comparison_note or '優先度低'}）")

    citations: list[Citation] = []
    seen_urls: set[str] = set()
    for c in eval_result.citations + feas_result.citations:
        if c.url not in seen_urls:
            citations.append(c)
            seen_urls.add(c.url)

    plan_period = f"FY{profile.plan_period_start_fy}〜FY{profile.plan_period_end_fy}"
    path = write_clo_executive_brief(
        company_name=profile.name,
        company_id=profile.company_id,
        plan_period=plan_period,
        executive_summary=executive_summary,
        actions_to_pursue=actions_to_pursue,
        actions_to_skip=actions_to_skip,
        next_decision_due="次回 取締役会（経営層と確認）",
        citations=citations,
    )

    summary_lines = [
        f"📄 経営会議向け 3 分要約 PPT を生成: {path.name}",
        "",
        "【経営サマリー】",
        *executive_summary[:4],
        "",
        "【やる】",
        *[f"  ✅ {a}" for a in actions_to_pursue],
        "",
        "【やらない】",
        *([f"  🚫 {a}" for a in actions_to_skip] if actions_to_skip else ["  （除外候補なし）"]),
    ]

    warnings = list(
        dict.fromkeys(
            [*eval_result.freshness_warnings, *feas_result.freshness_warnings, *all_warnings()]
        )
    )

    response = ToolResponse(
        summary="\n".join(summary_lines),
        citations=citations,
        freshness_warnings=warnings,
        data_source=profile.data_source,
        files={"pptx": str(path)},
    )
    _publish_files(response)
    return _to_model(response)


# ─── フェーズ4.1 a.1: 拠点別待機時間ヒートマップ ─────────────────────
@router.get("/wait-heatmap", response_model=ToolResponseModel)
async def wait_heatmap(
    company_id: Annotated[str, Query(description="サンプル/取込済 企業ID")],
) -> ToolResponseModel:
    """拠点 × 時間帯（朝/昼/夕/夜）の荷待ち時間ヒートマップを生成する。

    cells / site_names / time_slots / overall_* / threshold_* / avg_target_* を
    ToolResponseModel.metadata 経由で渡し、Web フロント（wait-heatmap/page.tsx）が
    可視化する。summary はテキスト要約として軸 A 表示にも使う。
    """
    profile = _resolve_profile_or_404(company_id)
    result: HeatmapResult = build_wait_time_heatmap(profile)

    response = ToolResponse(
        summary=result.summary,
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        data_source=profile.data_source,
    )
    model = _to_model(response)
    # metadata に詳細データを乗せて Web フロントで可視化する
    model.metadata = {
        "company_id": result.company_id,
        "company_name": result.company_name,
        "site_names": result.site_names,
        "time_slots": result.time_slots,
        "cells": [
            {
                "site_name": c.site_name,
                "time_slot": c.time_slot,
                "avg_minutes": c.avg_minutes,
                "max_minutes": c.max_minutes,
                "measured_count": c.measured_count,
                "over_2h_count": c.over_2h_count,
                "severity": c.severity,
                "confidence_low": c.confidence_low,
            }
            for c in result.cells
        ],
        "overall_avg_minutes": result.overall_avg_minutes,
        "overall_max_minutes": result.overall_max_minutes,
        "threshold_minutes": result.threshold_minutes,
        "avg_target_minutes": result.avg_target_minutes,
    }
    return model


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


# ─── フェーズ4.5 b: J3 デイリーコックピット ────────────────────────────


def _cockpit_to_metadata(result: CockpitResult) -> dict[str, object]:
    """CockpitResult を Web フロントが描画する metadata dict に直列化する。"""
    return {
        "company_id": result.company_id,
        "company_name": result.company_name,
        "generated_at": result.generated_at.isoformat(),
        "data_source": result.data_source,
        "overall_health": result.overall_health,
        "one_line_summary": result.one_line_summary,
        "delta_from_yesterday": result.delta_from_yesterday,
        "snapshot": {
            "snapshot_date": result.snapshot.snapshot_date.isoformat(),
            "load_factor_pct": result.snapshot.load_factor_pct,
            "wait_time_avg_min": result.snapshot.wait_time_avg_min,
            "wait_time_max_min": result.snapshot.wait_time_max_min,
            "handling_time_avg_min": result.snapshot.handling_time_avg_min,
            "co2_intensity_g_per_tonkm": result.snapshot.co2_intensity_g_per_tonkm,
            "over_2h_count_total": result.snapshot.over_2h_count_total,
            "compliance_overall": result.snapshot.compliance_overall,
            "feasibility_kpi_level": result.snapshot.feasibility_kpi_level,
            "open_items": list(result.snapshot.open_items),
        },
        "items": [
            {
                "item_id": item.item_id,
                "decision_axis": item.decision_axis,
                "card_state": item.card_state,
                "headline": item.headline,
                "rationale": item.rationale,
                "urgency_score": item.urgency_score,
                "impact_score": item.impact_score,
                "confidence_score": item.confidence_score,
                "total_score": item.total_score,
                "related_measure_id": item.related_measure_id,
                "related_kpi_name": item.related_kpi_name,
                "related_compliance_item": item.related_compliance_item,
                "suggested_action": item.suggested_action,
                "deadline_label": item.deadline_label,
                "next_review_due": (
                    item.next_review_due.isoformat() if item.next_review_due else None
                ),
                "days_pending": item.days_pending,
                "delta_from_last": item.delta_from_last,
                "estimated_pnl_jpy": item.estimated_pnl_jpy,
                "citation_keys": list(item.citation_keys),
                "anticipated_objections": [
                    {
                        "role": o.role,
                        "objection": o.objection,
                        "rebuttal": o.rebuttal,
                        "evidence_axis": o.evidence_axis,
                    }
                    for o in item.anticipated_objections
                ],
            }
            for item in result.items
        ],
    }


@router.get("/today-decisions/{company_id}", response_model=ToolResponseModel)
async def today_decisions(
    company_id: str,
    target_year: Annotated[int, Query(ge=2024, le=2050)] = 2030,
    persist_snapshot: Annotated[bool, Query()] = True,
) -> ToolResponseModel:
    """CLO デイリーコックピット（今日の3判断）を生成。

    軸 A 法令準拠 / 軸 B KPI 達成見通し / 軸 C 今週決める施策の 3 件を、
    緊急度・経営インパクト・自信度・想定反論まで揃えて返す。
    Web は ToolResponseModel.metadata から構造化データを描画する。
    """
    profile = _resolve_profile_or_404(company_id)
    result: CockpitResult = build_daily_cockpit(
        profile,
        target_year=target_year,
        persist_snapshot=persist_snapshot,
    )

    response = ToolResponse(
        summary=build_cockpit_summary(result),
        citations=result.citations,
        freshness_warnings=result.freshness_warnings,
        data_source=result.data_source,
    )
    model = _to_model(response)
    model.metadata = _cockpit_to_metadata(result)
    return model


class DecisionLogRequest(BaseModel):
    """POST /decisions の入力スキーマ。

    record_id と decided_at はサーバー側で生成する。CLO 名やボタン操作の結果を
    そのまま append-only ログに追記する。
    """

    cockpit_item_id: str = Field(description="CockpitItem.item_id（必須）")
    decision: DecisionStatus = Field(description="採用/保留/却下/エスカレーション")
    decided_by: str = Field(default="system", description="決定者（CLO 名 or 'system'）")
    rationale: str = Field(default="", description="決定の根拠（短文）")
    expected_effect_jpy: int | None = Field(
        default=None,
        description="採用時の想定経営効果（円）",
    )
    review_due: date | None = Field(
        default=None,
        description="次回レビュー期日（postpone/escalate 時）",
    )
    linked_alerts: list[str] = Field(
        default_factory=list,
        description="H1 アラート ID への参照",
    )


@router.post("/decisions/{company_id}", status_code=201)
async def decisions_log(
    company_id: str,
    body: Annotated[DecisionLogRequest, Body()],
) -> dict[str, str]:
    """意思決定ログ（I2）に DecisionRecord を 1 行 append する。

    UI でカードの採用/保留/却下ボタンが押されたとき呼ぶ。append-only なので
    既存レコードは書換えず、最新ステータスは jsonl の最後の行が示す。
    """
    _resolve_profile_or_404(company_id)

    record = DecisionRecord(
        record_id=str(uuid.uuid4()),
        company_id=company_id,
        cockpit_item_id=body.cockpit_item_id,
        decided_at=datetime.now(UTC),
        decided_by=body.decided_by,
        decision=body.decision,
        rationale=body.rationale,
        expected_effect_jpy=body.expected_effect_jpy,
        review_due=body.review_due,
        linked_alerts=list(body.linked_alerts),
    )

    try:
        path = append_decision(record)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"jsonl append 失敗: {exc}") from exc

    return {
        "record_id": record.record_id,
        "company_id": company_id,
        "decision": record.decision,
        "log_path": str(path),
    }


# ─── フェーズ5.0 c.7: 業種別パッケージ + F2 / J2 スコアの公開 ───────────


@router.get("/industry-package/{company_id}", response_model=ToolResponseModel)
async def industry_package(company_id: str) -> ToolResponseModel:
    """業種別 CLO 標準パッケージ（Override 適用済）を返す。

    Web フロントは ToolResponseModel.metadata 経由で IndustryPackage 全体を
    受け取り、KPI / 施策 / 会議体 / レポート / データ項目を可視化する。
    """
    profile = _resolve_profile_or_404(company_id)

    base_industry = category_of(profile.jsic_code)
    if base_industry is None or base_industry == "other":
        raise HTTPException(
            status_code=400,
            detail=(
                f"jsic_code={profile.jsic_code!r} から CLO 標準パッケージの"
                "業種を解決できません（manufacturing / wholesale / retail / "
                "chain_franchise のいずれかが必要）"
            ),
        )
    if get_package(base_industry) is None:
        raise HTTPException(
            status_code=400,
            detail=f"業種 {base_industry!r} に対応する IndustryPackage が未定義",
        )

    override = load_override(profile.company_id)
    package = resolve_company_package(base_industry, override)

    # c.9 Web 表示用に施策の name / description / form3_section を解決して返す。
    # measure_id 単独では CLO 担当者に意味が伝わらないため、ALL_MEASURES から
    # 必要情報を引いて metadata に同梱する（Codex 勧告 2026-05-06）。
    measure_details = []
    for mid in package.measure_ids:
        m = get_measure(mid)
        if m is None:
            continue
        measure_details.append(
            {
                "measure_id": m.measure_id,
                "name": m.name,
                "description": m.description,
                "form3_section": m.form3_section,
                "measure_type": m.measure_type,
            }
        )

    chain_franchise_notice: dict[str, str] | None = None
    if base_industry == "chain_franchise":
        chain_franchise_notice = {
            "legal_article": CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE,
            "headline": (
                f"連鎖化事業者（特定連鎖化事業者）— 物流効率化法 "
                f"{CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE}"
            ),
            "scope_note": (
                "様式第3「第5条関係」では荷役等時間短縮セクションが対象外。"
                "倉庫DX（WMS）・パレット標準化・中継輸送等の loading 系施策は"
                "標準パッケージから除外され、Override 採用しても F2 標準化スコアで"
                "減点されます。"
            ),
        }

    response = ToolResponse(
        summary=build_industry_package_summary(package, override),
        citations=[logistics_efficiency_law_citation()],
        freshness_warnings=all_warnings(),
        data_source=profile.data_source,
    )
    model = _to_model(response)
    model.metadata = {
        "company_id": profile.company_id,
        "base_industry": base_industry,
        "package": package.model_dump(mode="json"),
        "override": override.model_dump(mode="json") if override else None,
        "measure_details": measure_details,
        "chain_franchise_notice": chain_franchise_notice,
    }
    return model


@router.get(
    "/standardization-score/{company_id}",
    response_model=ToolResponseModel,
)
async def standardization_score(company_id: str) -> ToolResponseModel:
    """F2 標準化スコア（業種別 CLO 標準パッケージへの準拠度 0-100）を算出する。

    coverage_pct と Override 4 分類別件数を分離して返すことで、UI 側で
    「coverage で○、deviation で×」の根拠を表示できる。
    """
    profile = _resolve_profile_or_404(company_id)
    override = load_override(profile.company_id)

    try:
        result = compute_standardization_score(profile, override)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ToolResponse(
        summary=build_standardization_summary(result),
        citations=list(result.citations),
        freshness_warnings=list(result.freshness_warnings),
        data_source=profile.data_source,
    )
    model = _to_model(response)
    model.metadata = result.model_dump(mode="json")
    return model


@router.post("/waste-traps/{company_id}", response_model=ToolResponseModel)
async def waste_traps(
    company_id: str,
    measure_runs: Annotated[
        list[MeasureExecutionRecord] | None,
        Body(
            description=(
                "施策実行記録のリスト。各レコードは measure_id / 開始日 / "
                "投資額 / 期待効果 / 実績効果 / 計測サンプル数 / "
                "データ完全度 / 季節性 / 外部要因 / 想定回収月数 / root cause を含む。"
                "空配列または null なら結果は 0 件で返る。"
            ),
        ),
    ] = None,
) -> ToolResponseModel:
    """J2 罠スコア（効果が出ていない施策を 6 軸セーフガード付きで検出）。

    立ち上げ期間 / データ欠損 / サンプル数不足 / 季節性 / 外部要因 / 投資回収前
    の 6 軸セーフガードが発火した場合は trap_severity=low に固定して誤検知を抑止する。

    受け取った measure_runs は outputs/measure_runs/<company_id>.json に永続化され、
    保存済みデータと measure_id ベースで merge（incoming 優先）して分析する。
    measure_runs が null/空の場合は保存済みデータのみで分析する。
    """
    profile = _resolve_profile_or_404(company_id)

    incoming = list(measure_runs) if measure_runs else []
    if incoming:
        runs = merge_with_stored(company_id, incoming)
        save_runs(company_id, runs)
    else:
        runs = load_runs(company_id)
    result = detect_waste_traps(profile, runs)

    response = ToolResponse(
        summary=build_waste_trap_summary(result),
        citations=list(result.citations),
        freshness_warnings=list(result.freshness_warnings),
        data_source=profile.data_source,
    )
    model = _to_model(response)
    model.metadata = result.model_dump(mode="json")
    return model
