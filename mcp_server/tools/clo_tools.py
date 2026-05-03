"""CLO（物流統括管理者）支援ツール群。

フェーズ3: core/analytics/ を活用した CLO 計画書策定支援 MCP ツール。
全ツールの戻り値は ToolResponse 構造（summary/files/citations/freshness_warnings）。
"""
from __future__ import annotations

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
from core.analytics.plan_draft import (
    PlanDraftResult,
    build_plan_draft_summary,
    generate_plan_draft,
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
from core.export.citation import (
    Citation,
    logistics_efficiency_law_citation,
)
from core.export.response import ToolResponse
from core.legal.eligibility import evaluate_eligibility
from core.playbook.filters import (
    PlaybookFilter,
    build_search_summary,
    filter_playbook,
)
from core.static._freshness import all_warnings
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
                    url=(
                        "https://www.mlit.go.jp/sogoseisaku/transport/"
                        "butsuryu06100.html"
                    ),
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
        profile = get_sample(company_id)
        if profile is None:
            return ToolResponse(
                summary=(
                    f"サンプル企業 '{company_id}' が見つかりません。"
                    "利用可能: sample_mfg_01 / sample_wholesale_01 / sample_chain_01"
                ),
            ).to_dict()

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
                "sample_chain_01"）
            max_difficulty: 許容実装難易度の上限（1-5）。None で制約なし
            available_resources: 自社が保有するリソース。
                未指定なら CompanyProfile から自動推定（拠点数・自社保有車両・拠点跨ぎ等）

        Returns:
            ToolResponse 構造:
            - summary: Top 3 推薦 + 4軸スコア + 選定根拠 + 全件ランキング
            - citations: 物流効率化法・プレイブック出典
            - freshness_warnings: 静的データの鮮度警告
        """
        profile = get_sample(company_id)
        if profile is None:
            return ToolResponse(
                summary=(
                    f"サンプル企業 '{company_id}' が見つかりません。"
                    "利用可能: sample_mfg_01 / sample_wholesale_01 / sample_chain_01"
                ),
            ).to_dict()

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
                "sample_chain_01"）。内部で logi_clo_plan_draft を再実行する。

        Returns:
            ToolResponse 構造:
            - summary: 施策別 P&L インパクト・合算・定性記述
            - citations: 共同ガイドライン Ver.3.2・J-クレジット・GX-ETS・物流効率化法
            - freshness_warnings: 静的データの鮮度警告
        """
        profile = get_sample(company_id)
        if profile is None:
            return ToolResponse(
                summary=(
                    f"サンプル企業 '{company_id}' が見つかりません。"
                    "利用可能: sample_mfg_01 / sample_wholesale_01 / sample_chain_01"
                ),
            ).to_dict()

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
                "sample_chain_01"）。内部で logi_clo_plan_draft を再実行してから検査する。

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
