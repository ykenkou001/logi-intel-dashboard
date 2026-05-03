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
from core.analytics.financial_translate import (
    FinancialTranslateResult,
    translate_to_pnl_impact,
)
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
    financial: FinancialTranslateResult

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

    # 財務翻訳（フェーズ3.5 Step 4）— P&L インパクト変換
    financial = translate_to_pnl_impact(profile, simulation)

    # 出典統合（全 Step + 財務翻訳の citations を URL ベースで重複排除）
    citations = _merge_citations(
        benchmark.citations,
        driver_gap.citations,
        target_proposal.citations,
        simulation.citations,
        certified_matches.citations,
        financial.citations,
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
            profile, benchmark, eligibility, simulation, financial,
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
            profile, benchmark, eligibility, simulation, financial,
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
        financial=financial,
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
    financial: FinancialTranslateResult,
) -> list[str]:
    """PPT 2枚目固定のエグゼクティブサマリー（行のリスト）。

    財務インパクト（営業利益・炭素回避レンジ・5年NPV）を含めて経営層が
    一目で「何を判断すべきか」が分かる形にする。
    """
    obligation = "あり" if eligibility.must_appoint_clo else "なし"
    cat_labels = "、".join(
        _ELIGIBILITY_CATEGORY_LABELS.get(str(c), str(c)) for c in eligibility.categories
    )
    lines = [
        f"会社名: {profile.name}",
        f"主たる事業: {profile.main_business}（JSIC {profile.jsic_code}）",
        f"年間売上: {profile.annual_revenue_jpy / 1e8:.1f}億円 / "
        f"営業利益: {profile.operating_profit_jpy / 1e8:.1f}億円 "
        f"(利益率 {financial.base_operating_profit_margin_pct:.2f}%)",
        f"年間取扱量: {profile.annual_freight_tons_total:,.0f}トン",
        "",
        f"特定荷主3区分判定: CLO選任義務 {obligation}",
        f"  該当区分: {cat_labels}",
        "",
        "【施策効果（5施策合算・年間ベース）】",
        f"  CO2 削減: 約 {simulation.total_co2_reduction_kg / 1000:,.0f}トン-CO2/年",
        f"  物流コスト削減（= 営業利益増）: "
        f"約 {simulation.total_cost_saving_jpy / 1e8:.2f}億円/年",
        f"  必要投資 合計: 約 {simulation.total_investment_jpy / 1e4:,.0f}万円",
        "",
        "【財務インパクト（経営指標換算）】",
        f"  営業利益 +{financial.total_operating_profit_increase_jpy / 1e8:.2f}億円/年 "
        f"(利益率 +{financial.operating_profit_margin_lift_pp_total:.2f}pp)",
        f"  炭素価格回避: {financial.total_carbon_avoidance_jpy_low / 1e6:.0f}〜"
        f"{financial.total_carbon_avoidance_jpy_high / 1e6:.0f}百万円/年 "
        "(J-クレジット〜GX-ETS想定)",
        f"  5年累積NPV: 約 {financial.total_5y_npv_jpy / 1e8:.2f}億円 (割引率3%)",
        "",
        "次のアクション: 様式第3別紙（添付Word）に署名・押印し、2026年10月末までに国交省へ提出",
    ]
    return lines


def _build_executive_summary_text(
    profile: CompanyProfile,
    benchmark: BenchmarkResult,
    eligibility: EligibilityResult,
    simulation: SimulationResult,
    financial: FinancialTranslateResult,
) -> str:
    """Markdown 用エグゼクティブサマリー（複数行テキスト）。"""
    return "\n".join(
        _build_executive_summary_lines(
            profile, benchmark, eligibility, simulation, financial,
        )
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

    実施時期の段階配置:
        - 投資額が小さく短期実施可能な施策を 2026 年度に
        - 中規模を 2027〜2028 年度に
        - 全社展開を 2029〜2030 年度に分散
    """
    # 施策ごとに（テーマ・実施措置短縮名・計画内容詳細）を生成し
    # 投資額の小さい順に2026/2027/2028/2029年度に段階配置する
    section_buckets: dict[str, list[tuple[float, PlanMeasure]]] = {
        "load": [],
        "wait": [],
        "loading": [],
    }

    for m in simulation.measures:
        theme = _classify_form3_theme(m.name, is_chain_franchise=profile.is_chain_franchise)
        if theme is None:
            continue
        measure_name, description = _split_measure_name_and_description(m, profile)
        section_buckets[theme].append(
            (m.investment_jpy, PlanMeasure(
                measure=measure_name,
                description=description,
                timing="",  # 後で段階配置で設定
            ))
        )

    # 投資額の小さい順にソートし、年度を割り当て
    for bucket in section_buckets.values():
        bucket.sort(key=lambda x: x[0])
        for i, (_, pm) in enumerate(bucket):
            pm.timing = _propose_staged_timing(i, len(bucket))

    sections = [
        PlanSection(
            title="Ⅱ 積載率向上",
            shipper_class="" if profile.is_chain_franchise else "特定第一種荷主",
            measures=[pm for _, pm in section_buckets["load"]],
        ),
        PlanSection(
            title="Ⅲ 荷待ち時間短縮",
            shipper_class="" if profile.is_chain_franchise else "特定第一種荷主・第二種荷主",
            measures=[pm for _, pm in section_buckets["wait"]],
        ),
    ]
    # 連鎖化事業者は荷役等項目なし
    if not profile.is_chain_franchise:
        sections.append(
            PlanSection(
                title="Ⅳ 荷役等時間短縮",
                shipper_class="特定第一種荷主・第二種荷主",
                measures=[pm for _, pm in section_buckets["loading"]],
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


def _classify_form3_theme(
    measure_name: str, is_chain_franchise: bool = False,
) -> str | None:
    """施策名を様式第3 の必須3項目のテーマに分類する。

    連鎖化事業者は様式第3「第5条関係」で荷役等時間短縮セクションを持たないため、
    本来 loading に分類される施策（中継輸送等）はドライバー拘束時間の文脈が近い
    荷待ち時間短縮（wait）に流用する。これにより、シミュレータで効果が計上されている
    施策が計画書に未記載となる脱落を防ぐ。
    """
    if "積載率" in measure_name or "モーダルシフト" in measure_name \
            or "共同配送" in measure_name:
        return "load"
    if "バース" in measure_name:
        return "wait"
    if "中継輸送" in measure_name:
        return "wait" if is_chain_franchise else "loading"
    return None


def _split_measure_name_and_description(
    measure: object,
    profile: CompanyProfile,
) -> tuple[str, str]:
    """様式第3 用に「実施措置（短縮名）」と「計画内容（具体的アクション）」を分離する。

    現状の MeasureSimulation は (name, description) を持つが、name が長く、
    description が技術的説明になっている。様式第3 では:
        - 実施措置: 短い見出し（「積載率向上」「モーダルシフト」等）
        - 計画内容: 具体的アクション（数量・対象範囲・自社固有の手段）
    として分離する。
    """
    m = measure  # 型はSimulationResult.measures の要素
    name = m.name  # type: ignore[attr-defined]
    desc = m.description  # type: ignore[attr-defined]

    # 実施措置は施策名から「（〜）」を除いた短縮形にする
    short = name.split("（")[0].strip()

    # 計画内容: 自社固有の事情を反映した具体的アクション
    site_count = len(profile.sites)
    if "モーダルシフト" in name:
        plan_content = (
            f"{desc}。{profile.name}の物流ネットワーク全体（拠点数 {site_count}）"
            "において、JR貨物コンテナ対応の積込設備整備および運送事業者との"
            "ラウンドユース契約締結を進める。"
        )
    elif "積載率" in name:
        plan_content = (
            f"{desc}。TMS（輸配送管理システム）導入と"
            f"パレット標準化（T11／T12）により、{site_count}拠点の"
            "出荷データを一元管理し、配車最適化を実現する。"
        )
    elif "共同配送" in name:
        plan_content = (
            f"{desc}。同業他社・荷主団体との協議を経て、"
            f"主要DC ({site_count}拠点) を起点とする共同配送スキームを構築。"
            "WMS連携で配送計画を統合する。"
        )
    elif "中継輸送" in name:
        plan_content = (
            f"{desc}。長距離幹線（500km超）の中間地点に中継拠点を設置し、"
            "ドライバー交代制を導入。改善基準告示準拠を担保する。"
        )
    elif "バース" in name:
        plan_content = (
            f"{desc}。トラック予約受付システム（VBS）を導入し、"
            f"{site_count}拠点の入出荷時間スロットを管理。"
            "予約遵守率の KPI を月次でモニタリング。"
        )
    else:
        plan_content = desc

    return short, plan_content


def _propose_staged_timing(index: int, total: int) -> str:
    """施策の年度配置を段階的に提案する。

    投資額が小さい順に index=0, 1, 2... を渡す前提で、年度を割り当てる。
    1〜2件: 2026年度に集中
    3件以上: 2026年度・2027〜2028年度・2029〜2030年度に分散
    """
    if total <= 0:
        return "2026〜2030年度"
    if index == 0:
        return "2026年度（先行実施）"
    if index == 1:
        return "2026〜2027年度"
    if index == 2:
        return "2027〜2028年度"
    return "2028〜2030年度（段階展開）"


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
        _format_revenue_ratio_line(r.benchmark),
        f"  5施策合算 CO2削減: 約 {r.simulation.total_co2_reduction_kg / 1000:,.0f}トン-CO2/年",
        f"  5施策合算 物流コスト削減（= 営業利益増）: "
        f"約 {r.simulation.total_cost_saving_jpy / 1e8:.2f}億円/年",
        f"  必要投資 合計: 約 {r.simulation.total_investment_jpy / 1e4:,.0f}万円",
        "",
        "【財務インパクト（経営指標換算）】",
        f"  営業利益 +{r.financial.total_operating_profit_increase_jpy / 1e8:.2f}億円/年 "
        f"(利益率 +{r.financial.operating_profit_margin_lift_pp_total:.2f}pp)",
        f"  炭素価格回避: {r.financial.total_carbon_avoidance_jpy_low / 1e6:.0f}〜"
        f"{r.financial.total_carbon_avoidance_jpy_high / 1e6:.0f}百万円/年",
        f"  5年累積NPV: 約 {r.financial.total_5y_npv_jpy / 1e8:.2f}億円 (割引率3%)",
        "",
        "【次のアクション】",
        "  1. PPT を経営会議で説明（2枚目のエグゼクティブサマリーから始める）",
        "  2. Word（様式第3別紙）の社内レビュー → CLO 署名 → 2026年10月末までに国交省提出",
        "  3. Excel の出典シートで「全数値の根拠」を確認（経営会議『出典は？』即答用）",
    ]

    return "\n".join(lines)


def _format_revenue_ratio_line(benchmark: BenchmarkResult) -> str:
    """業界平均売上比のサマリー行を信頼性区分で出し分ける。

    業界平均は経済センサスの 1 事業所あたり推計値で、母集団が小規模事業所中心。
    大企業の単純比較は桁外れになりやすいため、信頼性低下時は数値を出さず参考表記にする。
    """
    if benchmark.revenue_vs_avg_pct is None:
        return "  業界平均比: データ不足"
    if benchmark.revenue_ratio_reliability == "low_reliability":
        return (
            "  業界平均売上比: 規模優位企業（業界統計の母集団と乖離大のため数値表示は省略）"
        )
    return f"  業界平均売上比: {benchmark.revenue_vs_avg_pct:.0f}%"
