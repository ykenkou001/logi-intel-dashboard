"""CLO（物流統括管理者）支援ツール群。

フェーズ3: core/analytics/ を活用した CLO 計画書策定支援 MCP ツール。
全ツールの戻り値は ToolResponse 構造（summary/files/citations/freshness_warnings）。
"""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

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
from core.analytics.feasibility_check import (
    build_feasibility_summary,
    check_feasibility,
)
from core.analytics.financial_translate import (
    build_financial_translate_summary,
    translate_to_pnl_impact,
)
from core.analytics.measure_eval import (
    build_eval_summary,
    evaluate_measures,
)
from core.analytics.operation_cockpit import (
    CockpitResult,
    build_cockpit_summary,
    build_daily_cockpit,
)
from core.analytics.periodic_report import (
    build_periodic_report_summary,
    generate_periodic_report,
)
from core.analytics.plan_draft import (
    PlanDraftResult,
    build_plan_draft_summary,
    generate_plan_draft,
)
from core.analytics.scenario_sim import (
    build_scenario_summary,
    simulate_scenarios,
)
from core.analytics.simulator import (
    SimulationResult,
    build_simulation_summary,
    simulate_measures,
)
from core.analytics.standardization_score import (
    build_standardization_summary,
    compute_standardization_score,
)
from core.analytics.target_proposal import (
    TargetProposalResult,
    build_target_proposal_summary,
    propose_targets,
)
from core.analytics.wait_time_heatmap import (
    HeatmapResult,
    build_wait_time_heatmap,
)
from core.analytics.waste_trap import (
    MeasureExecutionRecord,
    build_waste_trap_summary,
    detect_waste_traps,
)
from core.export.citation import (
    Citation,
    logistics_efficiency_law_citation,
)
from core.export.ppt_writer import write_clo_executive_brief
from core.export.response import ToolResponse
from core.io.company_loader import (
    load_company_profile_from_csv,
    load_company_profile_from_excel,
)
from core.io.company_store import save_company_profile
from core.io.measure_run_store import load_runs, merge_with_stored, save_runs
from core.io.override_store import load_override
from core.io.profile_resolver import ProfileNotFoundError, resolve_profile
from core.io.template_writer import (
    DEFAULT_TEMPLATE_PATH,
    VALID_PURPOSES,
    TemplatePurpose,
    write_company_template,
)
from core.legal.eligibility import evaluate_eligibility
from core.playbook.filters import (
    PlaybookFilter,
    build_search_summary,
    filter_playbook,
)
from core.playbook.industry_packages import (
    build_industry_package_summary,
    get_package,
    resolve_company_package,
)
from core.static._freshness import all_warnings
from core.static.jsic import category_of
from core.static.sample_company import get_sample
from core.validators.submission_validator import (
    build_validation_summary,
    validate_submission,
)


def register_tools(mcp: FastMCP) -> None:
    """MCP サーバーに CLO 支援ツールを登録する。"""

    @mcp.tool()
    async def logi_clo_benchmark_position(
        jsic_code: str,
        prefecture: str,
        revenue_jpy: int,
        logistics_cost_jpy: int | None = None,
    ) -> dict[str, object]:
        """自社の業界ベンチマーク位置を分析します。

        JSIC コードと売上をもとに、全国・都道府県内での同業種の規模感と、
        業界平均物流コスト比率との差異を算出します。
        CLO 計画書「現状分析」セクションの根拠数値として活用できます。

        Args:
            jsic_code: JSIC 細分類4桁コード（例: "5411" = 食料・飲料卸売業、
                       "4411" = 一般貨物自動車運送業、"1631" = 医薬品製造業）
            prefecture: 主たる拠点の都道府県名（例: "東京都", "大阪府"）
            revenue_jpy: 年間売上（円）（例: 5_000_000_000 = 50億円）
            logistics_cost_jpy: 年間物流コスト（円）。未入力時は物流コスト比較を省略

        Returns:
            ToolResponse 構造:
            - summary: 業界規模・売上相対位置・物流コスト比較・CO2目標のテキスト
            - citations: 経済センサス・JILS物流コスト調査の出典情報
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            result: BenchmarkResult = await analyze_benchmark(
                jsic_code=jsic_code,
                prefecture=prefecture,
                revenue_jpy=revenue_jpy,
                logistics_cost_jpy=logistics_cost_jpy,
            )
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        summary = build_benchmark_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_executive_brief(company_id: str) -> dict[str, object]:
        """経営会議直前 3 分要約 PPT（3 スライド版）を生成します。

        フェーズ4.1 a.3。100 ページの本格計画書（plan_draft）とは別経路で、
        朝のコックピットや経営会議直前に CLO が手元で生成する軽量版。

        スライド構成:
            1. 表紙
            2. 経営サマリー（KPI 4 カード + プロフィール 3 行）
            3. やる／やらない 結論（Top 3 採用施策 + Top 3 除外施策 + 次回意思決定期日）

        本ツールは内部で measure_eval（4 軸スコアリング）と feasibility_check
        （実行可否判定）を呼び出し、その結果を 3 スライドに圧縮します。

        Args:
            company_id: サンプル/取込済 企業 ID。

        Returns:
            ToolResponse 構造（files["pptx"] に生成パス、summary に Top3/Bottom3 概要）
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

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

        # KPI 4 行（金額換算）+ プロフィール 3 行
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
            f"取扱量 {profile.annual_freight_tons_total:,.0f}トン / "
            f"data_source={profile.data_source}",
        ]

        # 「やる」3 件: measure_eval Top 3
        actions_to_pursue: list[str] = []
        for s in eval_result.top_recommendations[:3]:
            cost_oku = (s.estimated_annual_cost_saving_jpy or 0) / 1e8
            actions_to_pursue.append(
                f"{s.measure.name}（年 +{cost_oku:.2f}億円・スコア{s.total_score:.0f}）"
            )

        # 「やらない」3 件: feasibility=red を優先、次に bottom_candidates
        red_verdicts = [v for v in feas_result.measure_verdicts if v.level == "red"][:3]
        actions_to_skip: list[str] = [
            f"{v.measure.name}（{v.primary_reason}）" for v in red_verdicts
        ]
        # red が 3 件未満なら bottom_candidates で埋める
        if len(actions_to_skip) < 3:
            for s in eval_result.bottom_candidates[: 3 - len(actions_to_skip)]:
                actions_to_skip.append(f"{s.measure.name}（{s.comparison_note or '優先度低'}）")

        # 次回意思決定期日（簡易: 計画期間の半年後を仮置き）
        # 実運用ではコックピット側から渡す予定
        next_decision_due = "次回 取締役会（経営層と確認）"

        # 出典は measure_eval / feasibility 統合
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
            next_decision_due=next_decision_due,
            citations=citations,
        )

        skip_lines = (
            [f"  🚫 {a}" for a in actions_to_skip] if actions_to_skip else ["  （除外候補なし）"]
        )
        summary_lines = [
            f"📄 経営会議向け 3 分要約 PPT を生成: {path.name}",
            "",
            "【経営サマリー（2 枚目）】",
            *executive_summary[:4],
            "",
            "【やる（3 枚目左）】",
            *[f"  ✅ {a}" for a in actions_to_pursue],
            "",
            "【やらない（3 枚目右）】",
            *skip_lines,
            "",
            f"📅 次回意思決定期日: {next_decision_due}",
        ]

        warnings = list(set(eval_result.freshness_warnings + feas_result.freshness_warnings))
        warnings.extend(all_warnings())
        # 重複除去（順序保持）
        warnings = list(dict.fromkeys(warnings))

        response = ToolResponse(
            summary="\n".join(summary_lines),
            citations=citations,
            freshness_warnings=warnings,
            data_source=profile.data_source,
            files={"pptx": str(path)},
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_wait_heatmap(company_id: str) -> dict[str, object]:
        """拠点 × 時間帯（朝/昼/夕/夜）の荷待ち時間ヒートマップを生成します。

        フェーズ4.1 a.1。CLO が「どの拠点が朝混むか」を 5 秒で把握し、
        是正アクション（バース予約・時間帯分散・トラック予約システム導入）の
        対象拠点を特定するための可視化ツール。

        集計仕様:
            - 縦軸: CompanyProfile.sites の拠点（site_name 指定の wait_time_rows のみ）
            - 横軸: morning(6-10) / midday(10-15) / evening(15-19) / night(19-翌6)
            - severity: green ≤30 分（目標）/ yellow ≤90 分 / red >90 分 / none 未計測
            - 計測便数 100 未満は confidence_low フラグ（統計的有意性に注意）

        Args:
            company_id: サンプル企業ID（"sample_retail_01" などヒートマップ対応）。
                site_name 未指定の wait_time_rows のみを持つ会社では cells が空になる

        Returns:
            ToolResponse 構造:
            - summary: 経営層向け 1 行要約（最悪セルの拠点・時間帯・平均分・件数）
            - citations: 改善基準告示・WaitTimeStandard の根拠
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        result: HeatmapResult = build_wait_time_heatmap(profile)
        # detail テキストを summary に追加
        detail_lines = [result.summary, ""]
        detail_lines.append(
            f"📊 全体平均 {result.overall_avg_minutes:.0f} 分・最大 "
            f"{result.overall_max_minutes:.0f} 分（基準 {result.threshold_minutes} 分／"
            f"目標 {result.avg_target_minutes} 分以下）"
            if result.overall_avg_minutes is not None
            else "📊 拠点別計測データがありません"
        )
        if result.cells:
            detail_lines.append("")
            detail_lines.append("拠点 × 時間帯 平均待機時間（分）:")
            time_label_short = {
                "morning": "朝",
                "midday": "昼",
                "evening": "夕",
                "night": "夜",
                "all_day": "全日",
            }
            # 拠点ごとに 1 行
            for site in result.site_names:
                cells_for_site = [c for c in result.cells if c.site_name == site]
                row_parts: list[str] = [f"  {site}:"]
                for slot in result.time_slots:
                    cell = next((c for c in cells_for_site if c.time_slot == slot), None)
                    if cell is None or cell.avg_minutes is None:
                        row_parts.append(f"{time_label_short.get(slot, slot)}=未計測")
                        continue
                    icon = {"green": "🟢", "yellow": "🟡", "red": "🔴", "none": "⚪"}[cell.severity]
                    row_parts.append(
                        f"{time_label_short.get(slot, slot)}={icon}{cell.avg_minutes:.0f}"
                    )
                detail_lines.append(" ".join(row_parts))
        summary_text = "\n".join(detail_lines)

        response = ToolResponse(
            summary=summary_text,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            data_source=profile.data_source,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_driver_gap(prefecture: str) -> dict[str, object]:
        """指定都道府県のドライバー需給ギャップを分析します。

        改善基準告示（2024年4月施行）の年間時間外上限960h規制により、
        トラック運転者の実効稼働力が約13.5%減少します。本ツールは
        e-Stat 経済センサスから道路貨物運送業（中分類44）の従業者数を取得し、
        2024年問題の影響規模と国交省の2030年試算を併せて出力します。
        CLO 計画書「ドライバー確保・労働時間管理」セクションの根拠数値として活用できます。

        Args:
            prefecture: 都道府県名（例: "東京都", "大阪府", "愛知県"）

        Returns:
            ToolResponse 構造:
            - summary: 道路貨物運送業の従業者数・実効稼働減・国家試算のテキスト
            - citations: 経済センサス・改善基準告示・国交省試算の出典
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            result: DriverGapResult = await analyze_driver_gap(prefecture)
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        summary = build_driver_gap_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_eligibility(
        jsic_code: str,
        annual_revenue_jpy: int | None = None,
        annual_freight_tons_total: float | None = None,
        is_chain_franchise: bool = False,
        override_first_class: bool | None = None,
        override_second_class: bool | None = None,
    ) -> dict[str, object]:
        """物流効率化法の特定荷主3区分（第46条／第65条）への適用判定を行います。

        年間取扱貨物9万トン以上の荷主は CLO 選任義務が発生します（2026年4月施行）。
        取扱量が未指定の場合は売上から業種別物流原単位で推計し、ボーダーライン
        （9万トン±30%）に該当する場合は実測データでの再判定を促します。

        Args:
            jsic_code: 自社の JSIC 細分類4桁コード（例: "5411"）
            annual_revenue_jpy: 年間売上（円）。連鎖化判定 + 取扱量推計に使用
            annual_freight_tons_total: 年間取扱貨物量（実測トン）。実測値が最優先
            is_chain_franchise: 連鎖化事業者（フランチャイズ本部）か
            override_first_class: 第一種荷主に該当を明示指定（ヒアリング結果優先）
            override_second_class: 第二種荷主に該当を明示指定

        Returns:
            ToolResponse 構造:
            - summary: 該当区分・CLO選任義務の有無・判定根拠・法令根拠のテキスト
            - citations: 物流効率化法の出典
            - freshness_warnings: 静的データの鮮度警告
        """
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
                    url=("https://www.mlit.go.jp/sogoseisaku/transport/butsuryu06100.html"),
                    accessed_via="国交省 物流センサス（静的参照）",
                )
            )

        response = ToolResponse(
            summary=summary,
            citations=citations,
            freshness_warnings=all_warnings(),
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_target_proposal(
        jsic_code: str,
        prefecture: str,
        revenue_jpy: int,
        revenue_vs_industry_avg_pct: float | None = None,
    ) -> dict[str, object]:
        """CLO 計画書「数値目標」セクション草稿を生成します。

        国家目標（物流分野CO2 ▲23.4%）と業界平均値を組み合わせ、
        様式第3別紙に直接転記できる粒度で 4 種類の数値目標を提示します:
          1. 輸送量当たりCO2排出原単位（▲23.4%・2030年/2013年比）
          2. 営業用普通貨物車 積載率（38% → 50%）
          3. モーダルシフト（鉄道貨物 +16%・2019→2030）
          4. 物流コスト/売上比率（業界平均比 ▲0.3〜0.5pt・荷主業種のみ）

        Args:
            jsic_code: JSIC 細分類4桁コード（Step 1 と同じコード）
            prefecture: 主たる拠点の都道府県名
            revenue_jpy: 年間売上（円）
            revenue_vs_industry_avg_pct: 業界平均比（%）。`logi_clo_benchmark_position` の
                出力（revenue_vs_avg_pct）を渡すと、規模優位企業に応じた目標を提案

        Returns:
            ToolResponse 構造:
            - summary: 4種類の数値目標と各根拠・出典のテキスト
            - citations: 物流効率化法・CO2ガイドライン・交通政策基本計画等の出典
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            result: TargetProposalResult = propose_targets(
                jsic_code=jsic_code,
                prefecture=prefecture,
                revenue_jpy=revenue_jpy,
                revenue_vs_industry_avg_pct=revenue_vs_industry_avg_pct,
            )
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        summary = build_target_proposal_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_simulate_measures(
        jsic_code: str,
        prefecture: str,
        revenue_jpy: int,
        annual_freight_tons: float | None = None,
        avg_distance_km: float = 500.0,
        long_distance_share_pct: float = 30.0,
    ) -> dict[str, object]:
        """5施策（モーダルシフト・積載率向上・共同配送・中継輸送・バース予約）の効果を同時試算します。

        各施策ごとに CO2 削減量・コスト削減額・ドライバー時間削減・必要投資・
        単純回収期間を業界統計の標準ファクターから概算で出力します。
        CLO 計画書「実施措置／計画内容」欄への直接転記用途。

        Args:
            jsic_code: JSIC 細分類4桁コード
            prefecture: 主たる拠点の都道府県名
            revenue_jpy: 年間売上（円）
            annual_freight_tons: 年間取扱量（実測トン）。None なら売上から推計
            avg_distance_km: モーダルシフト対象の平均輸送距離（デフォルト 500km）
            long_distance_share_pct: 中長距離輸送比率（デフォルト 30%）

        Returns:
            ToolResponse 構造:
            - summary: 5施策の効果と総合効果のテキスト
            - citations: CO2ガイドライン・自動車輸送統計・物流効率化法認定事例等の出典
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            result: SimulationResult = simulate_measures(
                jsic_code=jsic_code,
                prefecture=prefecture,
                revenue_jpy=revenue_jpy,
                annual_freight_tons=annual_freight_tons,
                avg_distance_km=avg_distance_km,
                long_distance_share_pct=long_distance_share_pct,
            )
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        summary = build_simulation_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_plan_draft(company_id: str) -> dict[str, object]:
        """CLO 中長期計画書ドラフトを統合生成し、PPT/Word/Excel/Markdown を出力します。

        フェーズ3 のクライマックス機能。Step 1〜6（業界ベンチマーク・ドライバー需給・
        適用判定・数値目標・施策効果・認定事業マッチング）をすべて実行し、結果を
        統合した4種類の成果物ファイルをディスクに出力します。

        Args:
            company_id: サンプル企業ID。
                - "sample_mfg_01": 製造業（電子部品メーカー・愛知県・売上850億）
                - "sample_wholesale_01": 卸売業（インテリア・千葉県・売上420億）
                - "sample_chain_01": 連鎖化事業者（コンビニ本部・埼玉県・売上3,200億）
                - "sample_retail_01": 小売業（ヒートマップ対応サンプル）
                ※ フェーズ4 で実データアップロード対応予定

        Returns:
            ToolResponse 構造:
            - summary: 統合サマリー（CLO選任義務・5施策合算効果・次のアクション）
            - files: { "ppt", "docx", "excel", "markdown" } の絶対パス
            - citations: Step 1-6 の出典を URL ベースで重複排除した統合リスト
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            result: PlanDraftResult = await generate_plan_draft(company_id)
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        profile = get_sample(company_id)
        summary = build_plan_draft_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            files=result.files,
            data_source=profile.data_source if profile else "estimated",
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_feasibility_check(
        company_id: str,
        target_year: int = 2030,
        available_resources: list[str] | None = None,
    ) -> dict[str, object]:
        """施策の実行可否と KPI 到達可能性を 緑/黄/赤 で判定します。

        フェーズ3.5 Step 5。Step 2（measure_eval）が「相対ランキング」で
        Top 3 を出すのに対し、本ツールは **絶対的な実行可否**を判定します。
        「この施策はあなたの会社では難しい」を明確に伝えることで、
        CLO が無理筋な計画を提出して罰則リスク（勧告→命令→企業名公表）を
        負わないよう支援します。

        判定ロジック:
        - 🟢 green: リソース充足 + 規模適合 + 難易度 ≤3
        - 🟡 yellow: リソース 1-2件不足 OR ボーダーライン規模 OR 難易度 4
        - 🔴 red: リソース ≥3件不足 OR 規模未達 OR 難易度 5+不足 OR 連鎖化×荷役等

        併せて積載率 38→50% の年率必要改善幅を業界実績（1.5pp/年）と比較し、
        目標年に到達可能か判定します。

        Args:
            company_id: サンプル企業ID
            target_year: KPI 達成目標年（デフォルト 2030 = 計画期間終了）
            available_resources: 自社が保有するリソース。None で自動推定

        Returns:
            ToolResponse 構造:
            - summary: 緑/黄/赤 の施策別判定 + 推奨アクション + KPI到達可能性
            - citations: 物流効率化法・CO2ガイドライン
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        result = check_feasibility(
            profile=profile,
            target_year=target_year,
            available_resources=available_resources if available_resources else None,
        )
        summary = build_feasibility_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            data_source=profile.data_source,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_measure_eval(
        company_id: str,
        max_difficulty: int | None = None,
        available_resources: list[str] | None = None,
    ) -> dict[str, object]:
        """自社プロフィール × プレイブック施策 → スコアリングして Top 3 を推薦します。

        フェーズ3.5 Step 2（差別化の心臓部）。「どの施策を選ぶべきか」に答える意思決定支援。
        プレイブック 10 施策を以下 4 軸で 0-100 スコアリングし、加重合計で Top 3 を推薦します:

        - **ROI**（投資対効果・重み 35%）: 年間期待コスト削減 / 投資額
        - **実装可能性**（重み 30%）: 難易度ベース + リソース欠如ペナルティ
        - **法令適合度**（重み 25%）: 様式第3 必須セクション該当 + 法令条文紐付き
        - **補助金カバー率**（重み 10%）: 適用補助金件数

        各推薦には期待コスト削減・期待 CO2 削減・回収期間 + 選定根拠テキストを付与。
        連鎖化事業者は荷役等セクションが必須から除外されます。

        Args:
            company_id: サンプル企業ID（"sample_mfg_01" / "sample_wholesale_01" /
                "sample_chain_01" / "sample_retail_01"）
            max_difficulty: 許容実装難易度の上限（1-5）。None で制約なし
            available_resources: 自社が保有するリソース。
                未指定なら CompanyProfile から自動推定（拠点数・自社保有車両・拠点跨ぎ等）

        Returns:
            ToolResponse 構造:
            - summary: Top 3 推薦 + 4軸スコア + 選定根拠 + 全件ランキング
            - citations: 物流効率化法・プレイブック出典
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        result = evaluate_measures(
            profile=profile,
            available_resources=available_resources if available_resources else None,
            max_difficulty=max_difficulty,
        )

        summary = build_eval_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            data_source=profile.data_source,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_playbook_search(
        industry: str | None = None,
        revenue_jpy: int | None = None,
        freight_tons: float | None = None,
        max_difficulty: int | None = None,
        form3_section: str | None = None,
        measure_type: str | None = None,
    ) -> dict[str, object]:
        """施策プレイブックライブラリから条件に合致する標準施策を検索します。

        フェーズ3.5 Step 1。Step 2（評価エンジン）/ Step 5（実現可能性チェッカー）の
        基盤データとなる標準施策セット（10件）から、業種・規模・難易度等で絞り込みます。
        各施策には投資レンジ・期待効果・補助金・成功事例参照・失敗パターンを保持。

        Args:
            industry: 業種カテゴリ（"manufacturing" / "wholesale" / "retail" /
                "chain_franchise" / "transport" / "other"）
            revenue_jpy: 自社売上（円）— min_revenue_jpy のフィルタに使用
            freight_tons: 自社年間取扱量（トン）— min_freight_tons のフィルタに使用
            max_difficulty: 許容実装難易度の上限（1-5）
            form3_section: 様式第3 セクション（"load" / "wait" / "loading"）
            measure_type: 取組タイプ（"modal_shift" / "load_factor" / "joint_delivery" /
                "relay_transport" / "berth_booking" / "warehouse_dx"）

        Returns:
            ToolResponse 構造:
            - summary: 該当施策の一覧（投資レンジ・期待効果・補助金・失敗パターン含む）
            - citations: 物流効率化法の出典
            - freshness_warnings: 静的データの鮮度警告
        """
        from typing import cast

        from core.static.efficiency_law_certified import (
            IndustryCategory,
            MeasureType,
        )

        filter_ = PlaybookFilter(
            industry=cast(IndustryCategory, industry) if industry else None,
            revenue_jpy=revenue_jpy,
            freight_tons=freight_tons,
            max_difficulty=max_difficulty,
            form3_section=form3_section if form3_section else None,
            measure_type=cast(MeasureType, measure_type) if measure_type else None,
        )
        results = filter_playbook(filter_=filter_)
        summary = build_search_summary(results, filter_)
        response = ToolResponse(
            summary=summary,
            citations=[logistics_efficiency_law_citation()],
            freshness_warnings=all_warnings(),
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_financial_translate(company_id: str) -> dict[str, object]:
        """物流 KPI を P&L インパクト（営業利益・炭素回避額・NPV）に翻訳します。

        フェーズ3.5 Step 4。経営層が「物流 KPI（積載率・荷待ち時間）」では響かないため、
        全施策の効果を **円単位の経営指標**に変換して提示します:

        1. 営業利益増加（コスト削減 = 売上原価減 → 営業利益増）
        2. 営業利益率改善（pp ベース）
        3. 炭素価格回避レンジ（J-クレジット 3,000円 〜 GX-ETS 5,000円）
        4. 5 年累積 NPV（割引率 3%）
        5. 不作為コスト（罰則 + ブランド毀損リスク）
        6. ESG プレミアム（定性記述）

        Args:
            company_id: サンプル企業ID（"sample_mfg_01" / "sample_wholesale_01" /
                "sample_chain_01" / "sample_retail_01"）。内部で logi_clo_plan_draft を再実行する。

        Returns:
            ToolResponse 構造:
            - summary: 施策別 P&L インパクト・合算・定性記述
            - citations: 共同ガイドライン Ver.3.2・J-クレジット・GX-ETS・物流効率化法
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        try:
            plan = await generate_plan_draft(company_id)
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        result = translate_to_pnl_impact(profile, plan.simulation)

        summary = build_financial_translate_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            data_source=profile.data_source,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_submission_validate(company_id: str) -> dict[str, object]:
        """CLO 計画書ドラフトの提出前バリデータを実行します。

        フェーズ3.5 Step 6（差別化の心臓部）。生成済みの様式第3別紙（Word）を読み、
        以下4観点で機械的に検査して「法定様式準拠率」を算出します:

        1. 網羅性: 必須3項目 ×（実施措置/計画内容/実施時期）= 9 項目が埋まっているか
           （連鎖化事業者は 6 項目）
        2. 数値整合性: CO2/コスト/投資/回収期間が非負・桁妥当か
        3. 出典欠落: CO2ガイドライン・物流効率化法・改善基準告示の出典が揃っているか
        4. 告示準拠: 数値目標が国家目標 ▲23.4%・物理的範囲（積載率 ≤100%）と整合か

        Args:
            company_id: サンプル企業ID（"sample_mfg_01" / "sample_wholesale_01" /
                "sample_chain_01" / "sample_retail_01"）。内部で logi_clo_plan_draft を再実行
                してから検査する。

        Returns:
            ToolResponse 構造:
            - summary: PASS/FAIL 判定・準拠率・エラー警告リスト・次のアクション
            - citations: 検査基準の出典（物流効率化法）
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            report = await validate_submission(company_id)
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        profile = get_sample(company_id)
        summary = build_validation_summary(report)
        response = ToolResponse(
            summary=summary,
            citations=[logistics_efficiency_law_citation()],
            freshness_warnings=all_warnings(),
            files=dict(report.checked_files),
            data_source=profile.data_source if profile else "estimated",
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_scenario_sim(
        company_id: str,
        selected_measure_ids: list[str] | None = None,
    ) -> dict[str, object]:
        """シナリオシミュレーション（保守/標準/上振れ × What-if 8 種）を実行します。

        フェーズ3.5 Step 3（差別化の心臓部）。Codex 3 取込で保守/標準/上振れの
        3 区分を持ち、CFO 質問「最低でも保守シナリオで X 億円か？」に答える形で
        baseline + 7 ストレスシナリオを試算します。

        ストレスシナリオ:
        - 燃料 ±20%: 燃料価格変動による削減効果の増減（±5%）
        - 運賃 ±10%: 運賃変動による削減効果の増減（±10%）
        - 需要 ±10%: 輸送量変動によるコスト・CO2 効果の増減（±10%）
        - 改善基準強化: 改善基準告示の追加強化（投資 +30% / 効果 -20%）

        重複処理: 同 form3_section に 2 施策以上 → 効果合算に 0.7 倍を適用。
        堅牢性判定: ストレス standard 営業利益増 / baseline standard
        - 🟢 70% 以上 / 🟡 50-70% / 🔴 50% 未満（投資判断却下リスク）

        Args:
            company_id: サンプル企業ID（"sample_mfg_01" / "sample_wholesale_01" /
                "sample_chain_01" / "sample_retail_01"）
            selected_measure_ids: 評価対象施策の measure_id リスト。
                None なら logi_clo_measure_eval の Top 3 を自動採用

        Returns:
            ToolResponse 構造:
            - summary: baseline + 7 ストレス × 3 区分の試算結果と堅牢性総合判定
            - citations: 物流効率化法・共同ガイドライン Ver.3.2
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        try:
            result = simulate_scenarios(
                profile=profile,
                selected_measure_ids=selected_measure_ids,
            )
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        summary = build_scenario_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            data_source=profile.data_source,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_periodic_report_draft(
        company_id: str,
        report_fy: int = 2026,
    ) -> dict[str, object]:
        """様式第5（定期報告書）ドラフトを生成します。

        フェーズ3.5 Step 7（フェーズ4.5「継続運用」への橋渡し）。
        毎年 7 月末提出の定期報告書ドラフトを Word で生成し、提出実務
        チェックリスト（Codex 1 取込）を最終ページに統合します。

        セクション構成:
        - Ⅰ 特定荷主の名称等
        - Ⅱ 判断基準の遵守状況（改善基準告示）
        - Ⅲ 判断基準を遵守できなかった場合の追加措置
        - Ⅳ 荷待ち時間等の計測データ
        - Ⅴ 中長期計画の進捗状況
        - Ⅵ 提出準備チェックリスト（提出経路・指定通知書番号・法人番号 等）

        計測データはサンプル別の標準値テンプレート（実データ取込はフェーズ4.0）。
        連鎖化事業者は荷役等項目を自動省略します。

        Args:
            company_id: サンプル企業ID（"sample_mfg_01" / "sample_wholesale_01" /
                "sample_chain_01" / "sample_retail_01"）
            report_fy: 報告対象年度（西暦・デフォルト 2026）

        Returns:
            ToolResponse 構造:
            - summary: 各セクションのサマリー + 提出実務チェックリスト
            - files: { "docx": 様式第5 Word のパス }
            - citations: 改善基準告示・物流効率化法・CO2 ガイドライン
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            result = await generate_periodic_report(
                company_id=company_id,
                report_fy=report_fy,
            )
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        summary = build_periodic_report_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            files=dict(result.files),
            data_source=result.data_source,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_certified_match(
        jsic_code: str,
        interested_measure_types: list[str] | None = None,
    ) -> dict[str, object]:
        """物流効率化法 認定事業から類似事例を検索します。

        自社の業種カテゴリと関心施策に基づき、参考になる先行事例（公表データ）を
        スコアリングして上位5件返します。CLO 計画書「実施措置」セクションで
        「業界の先行事例」として引用するため。

        Args:
            jsic_code: JSIC 細分類4桁コード（Step 1-5 と同じコード）
            interested_measure_types: 関心施策のリスト（省略可）。
                "modal_shift" / "joint_delivery" / "relay_transport" /
                "berth_booking" / "warehouse_dx" / "load_factor"

        Returns:
            ToolResponse 構造:
            - summary: 上位事例のリスト（主体企業・取組概要・効果）
            - citations: 各事例の出典 URL
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            result: CertifiedMatchResult = find_matches(
                jsic_code=jsic_code,
                interested_measure_types=interested_measure_types,
            )
        except ValueError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        summary = build_certified_match_summary(result)
        response = ToolResponse(
            summary=summary,
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
        )
        return response.to_dict()

    @mcp.tool()
    async def logi_clo_generate_template(
        output_path: str | None = None,
        purpose: str = "annual",
    ) -> dict[str, object]:
        """自社プロフィール入力 Excel テンプレートを生成します（フェーズ4.0 / 4.5）。

        CLO 担当者がこのテンプレを DL → 自社情報を記入 → logi_clo_load_company で
        取込、というフローの起点。サンプル3社からの脱却に必須。

        フェーズ4.5 B 軸で **用途別 3 種類** のテンプレに分割した:

        - ``annual``  : 計画策定用（既定）。profile / sites / wait_time(年集計) /
          handling_time / kpi_history / _jsic_reference の 6 シート構成。
          年 1 回の中長期計画策定で網羅入力する想定（現行互換）。
        - ``monthly`` : 月次集計用。wait_time の bucket_label を「2026-04 全体」
          のような月次集計形式にしたうえで handling_time / kpi_history を残す。
          月次レビュー会議の入力起点に使う。
        - ``daily``   : 日次運用入力用。wait_time のみの軽量版で site_name と
          time_slot を埋めて配布する（site×日付×slot の 8 サンプル行）。
          コックピット／ヒートマップ系の日次入力フローに使う。

        Args:
            output_path: 出力先のパス（省略時は outputs/templates/sample_company_template.xlsx）
            purpose: 利用用途。"daily" / "monthly" / "annual" のいずれか（既定 "annual"）。

        Returns:
            ToolResponse 構造:
            - summary: 生成完了メッセージ・含まれるシート一覧・記入手順
            - files: { "template_xlsx": Excel テンプレートのパス }
        """
        if purpose not in VALID_PURPOSES:
            return ToolResponse(
                summary=(
                    f"purpose は {list(VALID_PURPOSES)} のいずれかを指定してください: '{purpose}'"
                ),
            ).to_dict()
        purpose_typed: TemplatePurpose = purpose  # type: ignore[assignment]

        target = Path(output_path) if output_path else DEFAULT_TEMPLATE_PATH
        try:
            written = write_company_template(target, purpose=purpose_typed)
        except Exception as exc:
            return ToolResponse(summary=f"テンプレ生成に失敗しました: {exc}").to_dict()

        sheets_by_purpose = {
            "annual": (
                "profile / sites / wait_time(年集計) / handling_time / "
                "kpi_history / _jsic_reference"
            ),
            "monthly": (
                "profile / sites / wait_time(月集計) / handling_time / "
                "kpi_history / _jsic_reference"
            ),
            "daily": "profile / sites / wait_time(日次・site×slot) / _jsic_reference",
        }
        purpose_label = {
            "annual": "計画策定用（年 1 回・網羅版）",
            "monthly": "月次集計用（月次レビュー）",
            "daily": "日次運用入力用（コックピット／ヒートマップ）",
        }[purpose_typed]

        summary = (
            f"=== 自社プロフィール入力テンプレ生成完了 ===\n"
            f"用途: {purpose_typed}（{purpose_label}）\n"
            f"出力先: {written}\n"
            f"含まれるシート: {sheets_by_purpose[purpose_typed]}\n\n"
            "次の手順:\n"
            "  1. このファイルを開き、各シートを記入\n"
            "  2. 必須項目（[必須] と表記）はすべて埋める\n"
            "  3. 連鎖化事業者は handling_time シートを空にしてよい\n"
            '  4. 記入後 logi_clo_load_company(file_path="...") で取込\n'
            "  5. 取込が成功すると logi_clo_plan_draft(company_id) で実データ計画書を生成可能\n\n"
            "詳細記入ガイド: docs/data_input_guide.md"
        )
        return ToolResponse(
            summary=summary,
            files={"template_xlsx": str(written)},
            data_source="actual",
        ).to_dict()

    @mcp.tool()
    async def logi_clo_load_company(file_path: str) -> dict[str, object]:
        """記入済み Excel/CSV から CompanyProfile を構築し JSON 永続化します（フェーズ4.0）。

        Excel ファイル（.xlsx）または CSV ディレクトリの両方をサポート。
        取込が成功すると `outputs/profiles/<company_id>.json` に保存され、以降
        サンプル3社と同じ ID 解決ルートで `logi_clo_plan_draft` 等から参照可能。

        Args:
            file_path: 記入済み Excel ファイル（.xlsx）か CSV ディレクトリのパス。
                Excel の場合は `logi_clo_generate_template` で生成したテンプレを記入したもの。
                CSV の場合は profile.csv / sites.csv 等を含むディレクトリ。

        Returns:
            ToolResponse 構造:
            - summary: 取込結果の要約（company_id・拠点数・計測値件数・data_source）
            - files: { "profile_json": JSON ファイルのパス }
            - freshness_warnings: 必須項目の警告など
        """
        target = Path(file_path)
        try:
            if target.is_dir():
                profile = load_company_profile_from_csv(target)
            elif target.is_file():
                profile = load_company_profile_from_excel(target)
            else:
                return ToolResponse(
                    summary=f"ファイル/ディレクトリが見つかりません: {target}",
                ).to_dict()
        except (FileNotFoundError, ValueError) as exc:
            return ToolResponse(summary=f"取込に失敗しました: {exc}").to_dict()

        try:
            json_path = save_company_profile(profile)
        except OSError as exc:
            return ToolResponse(
                summary=f"JSON 永続化に失敗しました: {exc}",
            ).to_dict()

        summary = (
            f"=== 自社プロフィール取込完了 ===\n"
            f"company_id: {profile.company_id}\n"
            f"会社名: {profile.name}\n"
            f"業種: {profile.main_business} (JSIC {profile.jsic_code})\n"
            f"年間売上: {profile.annual_revenue_jpy / 1e8:.1f} 億円\n"
            f"年間取扱量: {profile.annual_freight_tons_total:,.0f} トン\n"
            f"連鎖化事業者: {'はい' if profile.is_chain_franchise else 'いいえ'}\n"
            f"拠点数: {len(profile.sites)} 件\n"
            f"荷待ち時間 計測区分: {len(profile.wait_time_rows)} 件\n"
            f"荷役等時間 計測区分: {len(profile.handling_time_rows)} 件\n"
            f"KPI 履歴: {len(profile.kpi_history)} 件\n"
            f"data_source: {profile.data_source}\n\n"
            f"永続化先: {json_path}\n\n"
            "次のアクション:\n"
            f'  - logi_clo_plan_draft(company_id="{profile.company_id}") で計画書ドラフト生成\n'
            f'  - logi_clo_periodic_report_draft(company_id="{profile.company_id}") で'
            "様式第5 ドラフト生成"
        )
        return ToolResponse(
            summary=summary,
            files={"profile_json": str(json_path)},
            data_source=profile.data_source,
        ).to_dict()

    @mcp.tool()
    async def logi_clo_today_decisions(
        company_id: str,
        target_year: int = 2030,
        persist_snapshot: bool = True,
    ) -> dict[str, object]:
        """CLO 今日の3判断（デイリーコックピット）を生成します。

        フェーズ4.5 J3 中核。朝 1 回開けば、未達 KPI ／ 放置リスク ／ 今週決める
        施策が 3 件だけ並び、緊急度・経営インパクト・自信度・推奨アクション・
        想定反論（J4 薄版）が付与されます。前日からの変化、未決滞留日数、
        次レビュー期日も含みます。

        判断軸 3 枠の構成:
            - compliance: 改善基準告示の違反/要注意/未計測（軸 A）
            - kpi_reach : 積載率 38→50% 等の到達可能性 yellow/red（軸 B）
            - measure_pick: 施策評価 Top 3 推薦（軸 C・上限 2 枠）

        埋め枠ルール（card_state）:
            - healthy           : 監視中で異常なし
            - insufficient_data : 計測データ未取込で判定不能
            - out_of_scope      : 連鎖化事業者の荷役等など対象外
            - attention_needed  : 通常の要対応カード

        Args:
            company_id: サンプル/取込済 企業 ID（sample_mfg_01, sample_wholesale_01,
                sample_chain_01, sample_retail_01 のいずれか、または取込済 ID）
            target_year: KPI 達成目標年（feasibility_check に渡す。既定 2030）
            persist_snapshot: True で当日 OperationKpiSnapshot を JSON 保存

        Returns:
            ToolResponse 構造:
            - summary: 経営会議用 1 ページ要約（軸別 3 件の headline + 根拠 + 推奨）
            - citations: 改善基準告示・物流効率化法等の出典の和集合
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        result: CockpitResult = build_daily_cockpit(
            profile,
            target_year=target_year,
            persist_snapshot=persist_snapshot,
        )

        return ToolResponse(
            summary=build_cockpit_summary(result),
            citations=result.citations,
            freshness_warnings=result.freshness_warnings,
            data_source=result.data_source,
        ).to_dict()

    # ─── フェーズ5.0 c.7: 業種別パッケージ + F2/J2 スコアの公開 ─────────

    @mcp.tool()
    async def logi_clo_industry_package(company_id: str) -> dict[str, object]:
        """業種別 CLO 標準パッケージを取得します（Override 4 分類を反映済）。

        フェーズ5.0 c.7。CompanyProfile の jsic_code から業種を解決し、
        ALL_PACKAGES の標準パッケージに outputs/profiles/<id>_override.json の
        個社差分（CompanyPackageOverride）を合成して返します。

        Override 4 分類の挙動:
            - approved_better_practice / required_localization: KPI target_value 上書き
            - temporary_exception: 期限内のみ上書き、期限後は base に戻る
            - unmanaged_deviation: 上書きせず、F2 標準化スコア側で減点される

        Args:
            company_id: サンプル/取込済 企業 ID（sample_mfg_01 / sample_wholesale_01 /
                sample_chain_01 / sample_retail_01 のいずれか、または取込済 ID）

        Returns:
            ToolResponse 構造（KPI / 施策 / 会議 / レポート / データ項目の総数 +
            Override 4 分類別件数の要約。詳細は REST API 経由で metadata 取得可能）
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        base_industry = category_of(profile.jsic_code)
        if base_industry is None or base_industry == "other":
            return ToolResponse(
                summary=(
                    f"jsic_code={profile.jsic_code!r} から CLO 標準パッケージの"
                    f"業種を解決できません（manufacturing / wholesale / retail / "
                    f"chain_franchise のいずれかが必要）"
                ),
                data_source=profile.data_source,
            ).to_dict()
        if get_package(base_industry) is None:
            return ToolResponse(
                summary=f"業種 {base_industry!r} に対応する IndustryPackage が未定義",
                data_source=profile.data_source,
            ).to_dict()

        override = load_override(profile.company_id)
        package = resolve_company_package(base_industry, override)
        summary = build_industry_package_summary(package, override)

        return ToolResponse(
            summary=summary,
            citations=[logistics_efficiency_law_citation()],
            freshness_warnings=all_warnings(),
            data_source=profile.data_source,
        ).to_dict()

    @mcp.tool()
    async def logi_clo_standardization_score(
        company_id: str,
    ) -> dict[str, object]:
        """F2 標準化スコア（業種別 CLO 標準パッケージへの準拠度 0-100）を算出します。

        フェーズ5.0 c.7。CompanyProfile.kpi_history（実装済 KPI）と Override
        （実装済 / 未管理 施策・期限切れ例外）を突き合わせ、標準化度合いを
        0-100 で返します。

        スコア算出（c.6 で実装。減点対象は unmanaged_deviation のみで単調性確保）:
            coverage_pct = (実装済 KPI 数 + 採用済 施策数)
                           / (標準 KPI 総数 + 標準 施策総数) × 100
            penalty = 5pt × unmanaged + 3pt × 期限切れ temporary_exception
            bonus = +5pt（approved_better_practice ≥ 2 件）
            score = max(0, min(100, coverage - penalty + bonus))

        Args:
            company_id: サンプル/取込済 企業 ID

        Returns:
            ToolResponse 構造:
            - summary: 標準化スコア + coverage / unmanaged 件数 +
              不足 KPI / 未採用 施策の要約
            - citations: 物流効率化法
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        override = load_override(profile.company_id)
        try:
            result = compute_standardization_score(profile, override)
        except ValueError as exc:
            return ToolResponse(
                summary=str(exc),
                data_source=profile.data_source,
            ).to_dict()

        return ToolResponse(
            summary=build_standardization_summary(result),
            citations=list(result.citations),
            freshness_warnings=list(result.freshness_warnings),
            data_source=profile.data_source,
        ).to_dict()

    @mcp.tool()
    async def logi_clo_waste_traps(
        company_id: str,
        measure_runs: list[MeasureExecutionRecord] | None = None,
    ) -> dict[str, object]:
        """J2 罠スコア（効果が出ていない施策を 6 軸セーフガード付きで検出）を算出します。

        フェーズ5.0 c.7。施策の投資額・期待効果・実績を比較し、罠（waste trap）を
        高/中/低 severity で検出します。立ち上げ期間 / データ欠損 / サンプル数不足 /
        季節性 / 外部要因 / 投資回収前の 6 軸セーフガードが発火した場合は
        trap_severity=low に固定し、誤検知を抑止します。

        actual_effect_jpy が None の MeasureExecutionRecord は判定保留扱いで、
        kpi_history からの自動逆算は次 PR の課題（c.7 持ち越し）。

        受け取った measure_runs は outputs/measure_runs/<company_id>.json に永続化され、
        保存済みデータと measure_id ベースで merge（incoming 優先）して分析する。
        measure_runs が null/空の場合は保存済みデータのみで分析する。

        Args:
            company_id: サンプル/取込済 企業 ID
            measure_runs: 施策実行記録のリスト（MeasureExecutionRecord）。
                各レコードは measure_id / 開始日 / 投資額 / 期待効果 / 実績効果 /
                計測サンプル数 / データ完全度 / 季節性 / 外部要因 / 想定回収月数 /
                root cause を含む。None または空配列なら保存済みデータのみで分析する。

        Returns:
            ToolResponse 構造:
            - summary: high / medium / low 件数 + 投資凍結推奨 + high 例の要約
            - citations: 物流効率化法
            - freshness_warnings: 静的データの鮮度警告
        """
        try:
            profile = resolve_profile(company_id)
        except ProfileNotFoundError as exc:
            return ToolResponse(summary=str(exc)).to_dict()

        incoming = list(measure_runs) if measure_runs else []
        if incoming:
            runs = merge_with_stored(company_id, incoming)
            save_runs(company_id, runs)
        else:
            runs = load_runs(company_id)
        result = detect_waste_traps(profile, runs)

        return ToolResponse(
            summary=build_waste_trap_summary(result),
            citations=list(result.citations),
            freshness_warnings=list(result.freshness_warnings),
            data_source=profile.data_source,
        ).to_dict()
