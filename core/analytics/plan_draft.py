"""CLO 中長期計画書ドラフトの統合生成。

Step 1〜6 を順次実行し、その結果を統合して
**PPT / Word（様式第3別紙）/ Excel / Markdown** を一括出力する。
フェーズ3 のクライマックスに位置するエンドツーエンド機能。

設計方針:
    - サンプル企業プロフィール（core/static/sample_company.py）を入力に受け取る
    - メイン拠点（sites[0]）の都道府県を benchmark / driver_gap で利用
    - 連鎖化事業者は様式第3「第5条関係」、それ以外は「第46条関係」で出力
    - 全成果物のパスを ToolResponse.files に格納
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from core.analytics.benchmark import (
    BenchmarkResult,
    analyze_benchmark,
    build_benchmark_summary,
)
from core.analytics.certified_match import (
    CertifiedMatchResult,
    build_certified_match_summary,
    find_matches,
)
from core.analytics.driver_gap import (
    DriverGapResult,
    analyze_driver_gap,
    build_driver_gap_summary,
)
from core.analytics.eligibility_analysis import build_eligibility_summary
from core.analytics.simulator import (
    SimulationResult,
    build_simulation_summary,
    simulate_measures,
)
from core.analytics.target_proposal import (
    TargetProposalResult,
    build_target_proposal_summary,
    propose_targets,
)
from core.export.citation import Citation
from core.export.docx_form3_writer import PlanMeasure, PlanSection, write_form3
from core.export.excel_writer import write_data_table
from core.export.markdown_writer import write_clo_plan_draft as write_md_plan
from core.export.ppt_writer import SlideContent
from core.export.ppt_writer import write_clo_plan_draft as write_ppt_plan
from core.legal.eligibility import EligibilityResult, evaluate_eligibility
from core.static._freshness import all_warnings
from core.static.sample_company import CompanyProfile, get_sample


@dataclass
class PlanDraftResult:
    """CLO 計画書ドラフト統合生成の結果。"""

    company_id: str
    company_name: str
    plan_period: str

    benchmark: BenchmarkResult
    driver_gap: DriverGapResult
    eligibility: EligibilityResult
    target_proposal: TargetProposalResult
    simulation: SimulationResult
    certified_matches: CertifiedMatchResult

    files: dict[str, str] = field(default_factory=dict)
    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


async def generate_plan_draft(company_id: str) -> PlanDraftResult:
    """サンプル企業プロフィールから CLO 計画書ドラフトを統合生成する。

    Args:
        company_id: サンプル企業ID（例: "sample_mfg_01", "sample_wholesale_01",
                                    "sample_chain_01"）

    Returns:
        PlanDraftResult — 4種類の成果物パスと各 Step 結果を含む

    Raises:
        ValueError: company_id が未登録、または拠点情報が不足の場合
    """
    profile = get_sample(company_id)
    if profile is None:
        raise ValueError(
            f"サンプル企業 '{company_id}' が見つかりません。"
            "利用可能: sample_mfg_01 / sample_wholesale_01 / sample_chain_01"
        )

    if not profile.sites:
        raise ValueError(f"プロフィール {company_id} に拠点情報がありません")

    main_prefecture = profile.sites[0].prefecture

    # Step 1, 2 を非同期で並列実行（e-Stat アクセス）
    benchmark, driver_gap = await asyncio.gather(
        analyze_benchmark(
            jsic_code=profile.jsic_code,
            prefecture=main_prefecture,
            revenue_jpy=profile.annual_revenue_jpy,
        ),
        analyze_driver_gap(prefecture=main_prefecture),
    )

    # Step 3 (eligibility) — 同期処理
    eligibility = evaluate_eligibility(
        jsic_code=profile.jsic_code,
        annual_freight_tons_total=profile.annual_freight_tons_total,
        annual_revenue_jpy=profile.annual_revenue_jpy,
        is_chain_franchise=profile.is_chain_franchise,
    )

    # Step 4 (target_proposal) — 同期処理
    target_proposal = propose_targets(
        jsic_code=profile.jsic_code,
        prefecture=main_prefecture,
        revenue_jpy=profile.annual_revenue_jpy,
        revenue_vs_industry_avg_pct=benchmark.revenue_vs_avg_pct,
    )

    # Step 5 (simulation) — 同期処理
    simulation = simulate_measures(
        jsic_code=profile.jsic_code,
        prefecture=main_prefecture,
        revenue_jpy=profile.annual_revenue_jpy,
        annual_freight_tons=profile.annual_freight_tons_total,
    )

    # Step 6 (certified matching) — 同期処理。関心施策は simulation 上位3つから推定
    interested_measure_types = _infer_interested_measures(simulation)
    certified_matches = find_matches(
        jsic_code=profile.jsic_code,
        interested_measure_types=interested_measure_types,
    )

    # 出典統合（全 Step の citations を URL ベースで重複排除）
    citations = _merge_citations(
        benchmark.citations,
        driver_gap.citations,
        target_proposal.citations,
        simulation.citations,
        certified_matches.citations,
    )

    plan_period = f"{profile.plan_period_start_fy}年度〜{profile.plan_period_end_fy}年度"

    # 成果物生成
    files: dict[str, str] = {}

    # 1. Markdown
    md_sections = _build_markdown_sections(
        benchmark, driver_gap, eligibility, target_proposal,
        simulation, certified_matches, profile,
    )
    md_path = write_md_plan(
        company_name=profile.name,
        company_id=profile.company_id,
        plan_period=plan_period,
        executive_summary=_build_executive_summary_text(
            profile, benchmark, eligibility, simulation,
        ),
        sections=md_sections,
        citations=citations,
    )
    files["markdown"] = str(md_path)

    # 2. PPT
    body_slides = _build_ppt_slides(
        benchmark, driver_gap, eligibility, target_proposal,
        simulation, certified_matches, profile,
    )
    ppt_path = write_ppt_plan(
        company_name=profile.name,
        company_id=profile.company_id,
        plan_period=plan_period,
        executive_summary=_build_executive_summary_lines(
            profile, benchmark, eligibility, simulation,
        ),
        body_slides=body_slides,
        citations=citations,
    )
    files["ppt"] = str(ppt_path)

    # 3. Excel
    excel_path = _build_excel(profile, target_proposal, simulation, citations)
    files["excel"] = str(excel_path)

    # 4. Word（様式第3別紙）
    docx_path = _build_form3(profile, target_proposal, simulation, plan_period)
    files["docx"] = str(docx_path)

    return PlanDraftResult(
        company_id=profile.company_id,
        company_name=profile.name,
        plan_period=plan_period,
        benchmark=benchmark,
        driver_gap=driver_gap,
        eligibility=eligibility,
        target_proposal=target_proposal,
        simulation=simulation,
        certified_matches=certified_matches,
        files=files,
        citations=citations,
        freshness_warnings=all_warnings(),
    )


def _merge_citations(*lists: list[Citation]) -> list[Citation]:
    """複数の citation リストを URL ベースで重複排除して結合する。"""
    seen: set[str] = set()
    merged: list[Citation] = []
    for lst in lists:
        for c in lst:
            if c.url not in seen:
                merged.append(c)
                seen.add(c.url)
    return merged


def _infer_interested_measures(sim: SimulationResult) -> list[str]:
    """シミュレーション結果からCO2削減効果が高い順に上位3施策を推定する。"""
    typed = []
    for m in sim.measures:
        co2 = m.co2_reduction_kg_per_year or 0.0
        if "モーダルシフト" in m.name:
            typed.append((co2, "modal_shift"))
        elif "積載率" in m.name:
            typed.append((co2, "load_factor"))
        elif "共同配送" in m.name:
            typed.append((co2, "joint_delivery"))
        elif "中継輸送" in m.name:
            typed.append((co2, "relay_transport"))
        elif "バース" in m.name:
            typed.append((co2, "berth_booking"))
    typed.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in typed[:3]]


_ELIGIBILITY_CATEGORY_LABELS: dict[str, str] = {
    "first_class_shipper": "特定第一種荷主（発荷主）",
    "second_class_shipper": "特定第二種荷主（着荷主）",
    "chain_franchise": "特定連鎖化事業者",
    "none": "該当なし",
}


def _build_executive_summary_lines(
    profile: CompanyProfile,
    benchmark: BenchmarkResult,
    eligibility: EligibilityResult,
    simulation: SimulationResult,
) -> list[str]:
    """PPT 2枚目固定のエグゼクティブサマリー（行のリスト）。"""
    obligation = "あり" if eligibility.must_appoint_clo else "なし"
    cat_labels = "、".join(
        _ELIGIBILITY_CATEGORY_LABELS.get(str(c), str(c)) for c in eligibility.categories
    )
    lines = [
        f"会社名: {profile.name}",
        f"主たる事業: {profile.main_business}（JSIC {profile.jsic_code}）",
        f"年間売上: {profile.annual_revenue_jpy / 1e8:.1f}億円 / "
        f"年間取扱量: {profile.annual_freight_tons_total:,.0f}トン",
        "",
        f"特定荷主3区分判定: CLO選任義務 {obligation}",
        f"  該当区分: {cat_labels}",
        "",
        f"業界平均売上比: {benchmark.revenue_vs_avg_pct:.0f}%"
        if benchmark.revenue_vs_avg_pct
        else "業界平均比: データ不足",
        f"5施策合算 CO2 削減: 約 {simulation.total_co2_reduction_kg / 1000:,.0f}トン-CO2/年",
        f"5施策合算 コスト削減: 約 {simulation.total_cost_saving_jpy / 1e8:.2f}億円/年",
        f"  必要投資 合計: 約 {simulation.total_investment_jpy / 1e4:,.0f}万円",
        "",
        "次のアクション: 様式第3別紙（添付Word）に署名・押印し、2026年10月末までに国交省へ提出",
    ]
    return lines


def _build_executive_summary_text(
    profile: CompanyProfile,
    benchmark: BenchmarkResult,
    eligibility: EligibilityResult,
    simulation: SimulationResult,
) -> str:
    """Markdown 用エグゼクティブサマリー（複数行テキスト）。"""
    return "\n".join(
        _build_executive_summary_lines(profile, benchmark, eligibility, simulation)
    )


def _build_markdown_sections(
    benchmark: BenchmarkResult,
    driver_gap: DriverGapResult,
    eligibility: EligibilityResult,
    target_proposal: TargetProposalResult,
    simulation: SimulationResult,
    certified_matches: CertifiedMatchResult,
    profile: CompanyProfile,
) -> list[tuple[str, str]]:
    """Markdown 出力のセクション (見出し, 本文) リスト。"""
    return [
        ("Step 1: 業界ベンチマーク", build_benchmark_summary(benchmark)),
        ("Step 2: ドライバー需給ギャップ", build_driver_gap_summary(driver_gap)),
        (
            "Step 3: 特定荷主3区分 適用判定",
            build_eligibility_summary(
                result=eligibility,
                jsic_code=profile.jsic_code,
                annual_revenue_jpy=profile.annual_revenue_jpy,
                annual_freight_tons_total=profile.annual_freight_tons_total,
                is_chain_franchise=profile.is_chain_franchise,
            ),
        ),
        ("Step 4: 数値目標提案", build_target_proposal_summary(target_proposal)),
        ("Step 5: 施策効果シミュレーション", build_simulation_summary(simulation)),
        (
            "Step 6: 物流効率化法 認定事業 類似マッチング",
            build_certified_match_summary(certified_matches),
        ),
    ]


def _build_ppt_slides(
    benchmark: BenchmarkResult,
    driver_gap: DriverGapResult,
    eligibility: EligibilityResult,
    target_proposal: TargetProposalResult,
    simulation: SimulationResult,
    certified_matches: CertifiedMatchResult,
    profile: CompanyProfile,
) -> list[SlideContent]:
    """PPT 本文スライドのリスト（3 枚目以降）。"""
    return [
        SlideContent(
            title="業界ベンチマーク",
            body_lines=build_benchmark_summary(benchmark).split("\n")[2:],
        ),
        SlideContent(
            title="ドライバー需給ギャップ",
            body_lines=build_driver_gap_summary(driver_gap).split("\n")[1:],
        ),
        SlideContent(
            title="特定荷主3区分 適用判定",
            body_lines=build_eligibility_summary(
                result=eligibility,
                jsic_code=profile.jsic_code,
                annual_revenue_jpy=profile.annual_revenue_jpy,
                annual_freight_tons_total=profile.annual_freight_tons_total,
                is_chain_franchise=profile.is_chain_franchise,
            ).split("\n")[1:],
        ),
        SlideContent(
            title="数値目標提案",
            body_lines=build_target_proposal_summary(target_proposal).split("\n")[1:],
        ),
        SlideContent(
            title="施策効果シミュレーション",
            body_lines=build_simulation_summary(simulation).split("\n")[1:],
        ),
        SlideContent(
            title="認定事業 類似マッチング",
            body_lines=build_certified_match_summary(certified_matches).split("\n")[1:],
        ),
    ]


def _build_excel(
    profile: CompanyProfile,
    target_proposal: TargetProposalResult,
    simulation: SimulationResult,
    citations: list[Citation],
) -> str:
    """Excel 数値表（数値目標 + 施策効果）を生成する。"""
    headers = ["指標／施策", "区分", "現状（業界平均）", "目標／効果", "出典"]
    rows: list[list[object]] = []

    for t in target_proposal.targets:
        avg = (
            f"{t.current_industry_avg:.1f}{t.current_industry_avg_unit}"
            if t.current_industry_avg is not None
            else "自社実績計測必要"
        )
        rows.append([
            t.name,
            "数値目標",
            avg,
            f"{t.proposed_target:.1f}{t.proposed_target_unit}",
            t.citation.label,
        ])

    for m in simulation.measures:
        effect_parts: list[str] = []
        if m.co2_reduction_kg_per_year:
            effect_parts.append(f"CO2 約{m.co2_reduction_kg_per_year / 1000:,.1f}トン/年削減")
        if m.cost_saving_jpy_per_year:
            effect_parts.append(
                f"コスト 約{m.cost_saving_jpy_per_year / 1e4:,.0f}万円/年削減"
            )
        rows.append([
            m.name,
            "施策効果（推計）",
            f"投資 約{m.investment_jpy / 1e4:,.0f}万円",
            "・".join(effect_parts) if effect_parts else "効果記載なし",
            m.citation.label,
        ])

    path = write_data_table(
        title=f"{profile.name} CLO 中長期計画書 数値目標・施策効果一覧",
        company_id=profile.company_id,
        headers=headers,
        rows=rows,
        citations=citations,
        purpose="clo_plan",
    )
    return str(path)


def _build_form3(
    profile: CompanyProfile,
    target_proposal: TargetProposalResult,
    simulation: SimulationResult,
    plan_period: str,
) -> str:
    """様式第3別紙 Word を生成する。

    必須3項目（積載率向上 / 荷待ち時間短縮 / 荷役等時間短縮）に
    施策をマッピングして実施措置・計画内容・実施時期を記載する。
    """
    measures_load: list[PlanMeasure] = []
    measures_wait: list[PlanMeasure] = []
    measures_loading: list[PlanMeasure] = []

    for m in simulation.measures:
        timing = _propose_timing(m.payback_years)
        plan_measure = PlanMeasure(
            measure=m.name,
            description=m.description,
            timing=timing,
        )
        # 施策をテーマ別に振り分け
        if "積載率" in m.name or "モーダルシフト" in m.name or "共同配送" in m.name:
            measures_load.append(plan_measure)
        if "バース" in m.name:
            measures_wait.append(plan_measure)
        if "中継輸送" in m.name:
            measures_loading.append(plan_measure)

    sections = [
        PlanSection(
            title="Ⅱ 積載率向上",
            shipper_class="" if profile.is_chain_franchise else "特定第一種荷主",
            measures=measures_load,
        ),
        PlanSection(
            title="Ⅲ 荷待ち時間短縮",
            shipper_class="" if profile.is_chain_franchise else "特定第一種荷主・第二種荷主",
            measures=measures_wait,
        ),
    ]
    # 連鎖化事業者は荷役等項目なし
    if not profile.is_chain_franchise:
        sections.append(
            PlanSection(
                title="Ⅳ 荷役等時間短縮",
                shipper_class="特定第一種荷主・第二種荷主",
                measures=measures_loading,
            )
        )

    path = write_form3(
        company_name=profile.name,
        company_id=profile.company_id,
        main_business=profile.main_business,
        jsic_code=profile.jsic_code,
        clo_name=profile.clo_name,
        plan_period=plan_period,
        sections=sections,
        is_chain_franchise=profile.is_chain_franchise,
    )
    return str(path)


def _propose_timing(payback_years: float | None) -> str:
    """単純回収期間から実施時期文字列を提案する。"""
    if payback_years is None:
        return "2026〜2030年度（要詳細検討）"
    if payback_years < 1.0:
        return "2026年度（早期実施）"
    if payback_years < 2.0:
        return "2026〜2027年度"
    return "2026〜2030年度（段階実施）"


def build_plan_draft_summary(r: PlanDraftResult) -> str:
    """PlanDraftResult から CLO 向け統合サマリーテキストを生成する。"""
    lines: list[str] = [
        f"=== CLO 中長期計画書ドラフト統合生成: {r.company_name} ===",
        f"計画期間: {r.plan_period}",
        "",
        "【生成成果物】",
    ]
    file_labels = {
        "ppt": "PPT（経営会議用・エグゼクティブサマリー2枚目固定）",
        "docx": "Word（様式第3別紙・国交省提出フォーマット）",
        "excel": "Excel（数値表 + 出典シート）",
        "markdown": "Markdown（レビュー・整形用）",
    }
    for key, label in file_labels.items():
        if key in r.files:
            lines.append(f"  {label}: {r.files[key]}")

    lines += [
        "",
        "【サマリー】",
        f"  CLO 選任義務: {'あり' if r.eligibility.must_appoint_clo else 'なし'}",
        f"  業界平均売上比: {r.benchmark.revenue_vs_avg_pct:.0f}%"
        if r.benchmark.revenue_vs_avg_pct
        else "  業界平均比: データ不足",
        f"  5施策合算 CO2削減: 約 {r.simulation.total_co2_reduction_kg / 1000:,.0f}トン-CO2/年",
        f"  5施策合算 コスト削減: 約 {r.simulation.total_cost_saving_jpy / 1e8:.2f}億円/年",
        f"  必要投資 合計: 約 {r.simulation.total_investment_jpy / 1e4:,.0f}万円",
        "",
        "【次のアクション】",
        "  1. PPT を経営会議で説明（2枚目のエグゼクティブサマリーから始める）",
        "  2. Word（様式第3別紙）の社内レビュー → CLO 署名 → 2026年10月末までに国交省提出",
        "  3. Excel の出典シートで「全数値の根拠」を確認（経営会議『出典は？』即答用）",
    ]

    return "\n".join(lines)
