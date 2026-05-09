"""施策評価エンジン — プレイブックを自社プロフィールでスコアリングする。

CLO 計画書の意思決定支援の核心: 「どの施策を選ぶべきか」に答えるエンジン。
プレイブック 10 施策を 4 軸（ROI / 実装可能性 / 法令適合度 / 補助金カバー率）で
スコアリングし、Top 3 推薦と全件ランキングを返す。

設計方針:
    - 4 軸の重み付け加算（ROI 35% / 実装可能性 30% / 法令適合度 25% / 補助金 10%）
    - 期待効果は industry_freight_coef + INDUSTRY_AVG_LOGISTICS_RATIO で算定
    - 連鎖化事業者は荷役等セクションを必須から除外
    - 各推薦に「選定根拠テキスト」を付与（経営会議で「なぜこれを選んだのか」即答用）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analytics.benchmark import INDUSTRY_AVG_LOGISTICS_RATIO
from core.export.citation import Citation, logistics_efficiency_law_citation
from core.export.formatter import format_jpy
from core.playbook.filters import PlaybookFilter, filter_playbook
from core.playbook.measures import PlaybookMeasure, RequiredResource
from core.static._freshness import all_warnings
from core.static.jsic import category_of
from core.static.sample_company import CompanyProfile

# 加重平均の重み
_WEIGHT_ROI: float = 0.35
_WEIGHT_FEASIBILITY: float = 0.30
_WEIGHT_COMPLIANCE: float = 0.25
_WEIGHT_SUBSIDY: float = 0.10

# Top N 推薦 / Bottom N 不採用提示（judgment trail）
_TOP_N: int = 3
_BOTTOM_N: int = 3
_BOTTOM_MIN_TOTAL: int = 6  # 評価対象が 6 件未満なら Bottom は省略

# 必須 form3 セクション（特定荷主 / 連鎖化事業者）
_REQUIRED_SECTIONS_NON_CHAIN = ("load", "wait", "loading")
_REQUIRED_SECTIONS_CHAIN = ("load", "wait")

# 措置タイプ別の対象コスト割合（物流コスト全体の何割を addressable と見るか）
_ADDRESSABLE_SHARE: dict[str, float] = {
    "modal_shift": 0.30,  # 中長距離輸送が対象
    "load_factor": 0.80,  # ほぼ全輸送
    "joint_delivery": 0.40,  # 共同化可能エリア
    "relay_transport": 0.25,  # 長距離運行のみ
    "berth_booking": 0.50,  # 拘束時間関連
    "warehouse_dx": 0.60,  # 倉庫オペ全般
}

# 実行カード簡易版（Codex 2 軽量取込）— 各施策の主管部門・想定月次 KPI・依存関係。
# フル版（関係部門・外部関係者・決裁事項・リスク 等）はフェーズ4.5 で対応。
_EXECUTION_CARDS: dict[str, tuple[str, str, list[str]]] = {
    "modal_shift_to_rail": (
        "物流部・調達部",
        "鉄道貨物トンキロ比率 月次 +0.5pp",
        ["JR貨物との運送契約", "鉄道発着拠点の立地評価", "対象荷種の温湿度要件確認"],
    ),
    "load_factor_tms": (
        "物流部・情報システム部",
        "営業用普通貨物車 積載率 月次 +0.5pp",
        ["TMS 導入（パッケージ選定+検収）", "拠点別積載率の可視化基盤"],
    ),
    "joint_delivery_competitor": (
        "物流部・営業部",
        "共同配送便数 月次 +5%",
        ["同業他社との協定締結", "個建て運賃のシェア合意", "競争法リスクレビュー"],
    ),
    "pallet_standardization": (
        "物流部・調達部",
        "T11/T12 標準パレット使用率 月次 +5pp",
        ["取引先パレット規格合意", "パレットプール契約"],
    ),
    "visualization_baseline": (
        "物流部・情報システム部",
        "拠点別データ取得率 月次 +10pp（最終 100%）",
        ["拠点別データ収集体制", "BI ダッシュボード基盤"],
    ),
    "lead_time_review": (
        "営業部・物流部",
        "平均注文ロット 月次 +5%",
        ["着荷主との発注ロット見直し合意", "受発注 EDI 対応"],
    ),
    "berth_booking_vbs": (
        "物流部・情報システム部",
        "平均荷待ち時間 月次 -10 分",
        ["VBS（バース予約）導入", "運送会社向け予約ガイドライン整備"],
    ),
    "delivery_time_distribution": (
        "物流部・営業部",
        "配送時間帯分散度（HHI 換算）月次 -5%",
        ["着荷主との納入時間帯合意", "配車計画の刷新"],
    ),
    "relay_transport": (
        "物流部",
        "中継拠点利用率 月次 +5pp",
        ["パートナー運送会社との連携契約", "中継拠点の立地確保"],
    ),
    "warehouse_dx_wms": (
        "物流部・情報システム部",
        "倉庫稼働率 月次 +3pp / ピッキング誤出荷率 月次 -10%",
        ["WMS 導入（パッケージ選定+検収）", "ハンディターミナル整備"],
    ),
}

_DEFAULT_EXECUTION_CARD: tuple[str, str, list[str]] = (
    "物流部",
    "施策固有の月次 KPI を定義してください",
    ["主管部門・KPI 定義の社内合意"],
)


@dataclass
class MeasureScore:
    """単一施策の評価スコア。"""

    measure: PlaybookMeasure

    # 4 軸スコア（0-100）
    roi_score: float
    feasibility_score: float
    compliance_score: float
    subsidy_score: float

    # 加重合計（0-100）
    total_score: float

    # 期待効果（試算値）
    estimated_annual_cost_saving_jpy: float | None
    estimated_annual_co2_reduction_kg: float | None
    estimated_payback_years: float | None

    # 選定根拠テキスト（CLO/経営層への説明用）
    selection_reason: str

    # リソース充足判定
    missing_resources: list[RequiredResource]

    # 実行カード簡易版（Codex 2 軽量取込・短期3）
    responsible_dept: str = ""
    monthly_kpi: str = ""
    dependencies: list[str] = field(default_factory=list)

    # 他施策との比較ポイント（judgment trail・短期3）
    # Top 推薦時は「他より優れた点」、Bottom 時は「不採用理由」を入れる。
    comparison_note: str = ""


@dataclass
class MeasureEvalResult:
    """施策評価結果。"""

    company_id: str
    company_name: str
    industry: str
    derived_resources: list[RequiredResource]

    eligible_count: int  # filter_playbook で残った件数
    scored_count: int

    top_recommendations: list[MeasureScore] = field(default_factory=list)
    bottom_candidates: list[MeasureScore] = field(default_factory=list)
    """不採用施策（最下位 _BOTTOM_N 件）。judgment trail 用。
    eligible_count < _BOTTOM_MIN_TOTAL のときは空リスト。"""

    all_scored: list[MeasureScore] = field(default_factory=list)

    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


def evaluate_measures(
    profile: CompanyProfile,
    available_resources: list[RequiredResource] | None = None,
    max_difficulty: int | None = None,
) -> MeasureEvalResult:
    """自社プロフィールを与えてプレイブック施策を評価し、Top 3 推薦を返す。

    Args:
        profile: 自社プロフィール（営業利益・売上原価・拠点・取扱量）
        available_resources: 自社が保有するリソース。None なら profile から自動推定
        max_difficulty: 許容実装難易度（1-5）。None なら制約なし

    Returns:
        MeasureEvalResult: Top 3 + 全件ランキング + 選定根拠
    """
    industry = category_of(profile.jsic_code) or "other"
    resources = (
        available_resources
        if available_resources is not None
        else _derive_available_resources(profile)
    )

    # まずプレイブックを業種・規模・取扱量で絞り込む（リソースは個別判定で警告化）
    filter_ = PlaybookFilter(
        industry=industry,
        revenue_jpy=profile.annual_revenue_jpy,
        freight_tons=profile.annual_freight_tons_total,
        max_difficulty=max_difficulty,
    )
    eligible = filter_playbook(filter_=filter_)

    is_chain = profile.is_chain_franchise
    logistics_ratio = INDUSTRY_AVG_LOGISTICS_RATIO.get(industry) or 0.030
    estimated_annual_logistics_cost = profile.cost_of_goods_sold_jpy * logistics_ratio

    scored: list[MeasureScore] = []
    for m in eligible:
        scored.append(
            _score_measure(
                m,
                profile=profile,
                available_resources=resources,
                estimated_annual_logistics_cost=estimated_annual_logistics_cost,
                is_chain=is_chain,
            )
        )

    # 合計スコア降順
    scored.sort(key=lambda s: s.total_score, reverse=True)

    top = scored[:_TOP_N]
    bottom = list(reversed(scored[-_BOTTOM_N:])) if len(scored) >= _BOTTOM_MIN_TOTAL else []

    # judgment trail: Top と Bottom それぞれに比較ノートを付与
    # 経営会議「なぜ採用/不採用？」に即答できる形にする
    _annotate_comparison_notes(top, bottom)

    return MeasureEvalResult(
        company_id=profile.company_id,
        company_name=profile.name,
        industry=industry,
        derived_resources=resources,
        eligible_count=len(eligible),
        scored_count=len(scored),
        top_recommendations=top,
        bottom_candidates=bottom,
        all_scored=scored,
        citations=[
            logistics_efficiency_law_citation(),
        ],
        freshness_warnings=all_warnings(),
    )


def _annotate_comparison_notes(
    top: list[MeasureScore],
    bottom: list[MeasureScore],
) -> None:
    """Top/Bottom 双方に「なぜ採用/不採用か」の比較テキストを付与する。

    判断根拠を残すため、各推薦と各不採用に最大の差分軸を 1〜2 つ提示する。
    """
    if not top:
        return

    top_avg_roi = sum(s.roi_score for s in top) / len(top)
    top_avg_feas = sum(s.feasibility_score for s in top) / len(top)
    top_avg_comp = sum(s.compliance_score for s in top) / len(top)

    for s in top:
        s.comparison_note = _build_top_comparison(
            s,
            top_avg_roi,
            top_avg_feas,
            top_avg_comp,
        )

    for s in bottom:
        s.comparison_note = _build_bottom_comparison(
            s,
            top_avg_roi,
            top_avg_feas,
            top_avg_comp,
        )


def _build_top_comparison(
    s: MeasureScore,
    avg_roi: float,
    avg_feas: float,
    avg_comp: float,
) -> str:
    """Top 推薦施策の「他施策との比較ポイント」を生成する。"""
    diffs = [
        ("ROI", s.roi_score - avg_roi),
        ("実装可能性", s.feasibility_score - avg_feas),
        ("法令適合", s.compliance_score - avg_comp),
    ]
    diffs.sort(key=lambda x: x[1], reverse=True)
    best_axis, best_delta = diffs[0]
    if best_delta >= 5.0:
        return f"Top 3 内で {best_axis} が +{best_delta:.0f}pt 優位"
    return "Top 3 内では総合バランス型（突出した優位軸なし）"


def _build_bottom_comparison(
    s: MeasureScore,
    avg_roi: float,
    avg_feas: float,
    avg_comp: float,
) -> str:
    """Bottom（不採用）施策の不採用理由を生成する。"""
    deltas = [
        ("ROI", avg_roi - s.roi_score),
        ("実装可能性", avg_feas - s.feasibility_score),
        ("法令適合", avg_comp - s.compliance_score),
    ]
    deltas.sort(key=lambda x: x[1], reverse=True)
    worst_axis, worst_delta = deltas[0]
    parts: list[str] = []
    if worst_delta >= 5.0:
        parts.append(f"Top 3 平均比 {worst_axis} ▲{worst_delta:.0f}pt")
    if s.missing_resources:
        parts.append(f"前提リソース不足: {', '.join(s.missing_resources)}")
    if not parts:
        parts.append("総合スコア僅差での不採用")
    return " / ".join(parts)


def _derive_available_resources(profile: CompanyProfile) -> list[RequiredResource]:
    """CompanyProfile からリソース集合を自動推定する。

    保守的に「あると確認できるリソース」のみ追加。joint_partner_network のような
    主観判断が必要なものは含めず、ユーザー指定に委ねる。
    """
    resources: list[RequiredResource] = ["it_capability"]  # 多くの企業は最低限保有

    if len(profile.sites) >= 2:
        resources.append("multi_site")
    if profile.fleet_count_owned > 0:
        resources.append("fleet_owned")
    if any(s.site_type in ("dc", "warehouse", "factory") for s in profile.sites):
        resources.append("warehouse_management")

    # 都道府県跨ぎで 3 地域以上 → 長距離輸送ありと判定
    prefectures = {s.prefecture for s in profile.sites}
    if len(prefectures) >= 3:
        resources.append("long_distance_transport")

    return resources


def _score_measure(
    m: PlaybookMeasure,
    profile: CompanyProfile,
    available_resources: list[RequiredResource],
    estimated_annual_logistics_cost: float,
    is_chain: bool,
) -> MeasureScore:
    """単一施策のスコアを算出する。"""
    # 期待効果の試算
    est_cost_saving = _estimate_annual_cost_saving(m, estimated_annual_logistics_cost)
    est_co2_reduction = _estimate_annual_co2_reduction(m, estimated_annual_logistics_cost)
    est_investment = (m.typical_investment_jpy_low + m.typical_investment_jpy_high) / 2.0
    est_payback = (
        est_investment / est_cost_saving if est_cost_saving and est_cost_saving > 0 else None
    )

    # リソース充足判定
    available_set = set(available_resources)
    missing = [r for r in m.required_resources if r not in available_set]

    # 4 軸スコア
    roi = _score_roi(est_cost_saving, est_investment)
    feasibility = _score_feasibility(m.implementation_difficulty, missing)
    compliance = _score_compliance(m, is_chain)
    subsidy = _score_subsidy(m.eligible_subsidies)

    total = (
        roi * _WEIGHT_ROI
        + feasibility * _WEIGHT_FEASIBILITY
        + compliance * _WEIGHT_COMPLIANCE
        + subsidy * _WEIGHT_SUBSIDY
    )

    reason = _build_selection_reason(
        m,
        roi,
        feasibility,
        compliance,
        subsidy,
        est_cost_saving,
        est_payback,
        missing,
    )

    responsible_dept, monthly_kpi, dependencies = _EXECUTION_CARDS.get(
        m.measure_id,
        _DEFAULT_EXECUTION_CARD,
    )

    return MeasureScore(
        measure=m,
        roi_score=roi,
        feasibility_score=feasibility,
        compliance_score=compliance,
        subsidy_score=subsidy,
        total_score=total,
        estimated_annual_cost_saving_jpy=est_cost_saving,
        estimated_annual_co2_reduction_kg=est_co2_reduction,
        estimated_payback_years=est_payback,
        selection_reason=reason,
        missing_resources=missing,
        responsible_dept=responsible_dept,
        monthly_kpi=monthly_kpi,
        dependencies=list(dependencies),
    )


def _estimate_annual_cost_saving(
    m: PlaybookMeasure,
    estimated_annual_logistics_cost: float,
) -> float | None:
    """施策の期待コスト削減額を年間ベースで試算する。"""
    if m.expected_cost_reduction_pct is None:
        return None
    addressable_share = _ADDRESSABLE_SHARE.get(m.measure_type, 0.50)
    addressable_cost = estimated_annual_logistics_cost * addressable_share
    return addressable_cost * m.expected_cost_reduction_pct / 100.0


def _estimate_annual_co2_reduction(
    m: PlaybookMeasure,
    estimated_annual_logistics_cost: float,
) -> float | None:
    """CO2 削減量の概算（kg/年）。

    コスト削減と同じ addressable_share を使い、業界平均原単位を仮定して算出。
    精緻化はフェーズ4 で実データに置き換え。
    """
    if m.expected_co2_reduction_pct is None:
        return None
    # 物流コスト 1 円あたり概ね 0.05 kg-CO2（業界推計値・大型トラック原単位ベース）
    co2_per_jpy = 0.05
    addressable_share = _ADDRESSABLE_SHARE.get(m.measure_type, 0.50)
    addressable_cost = estimated_annual_logistics_cost * addressable_share
    base_co2 = addressable_cost * co2_per_jpy
    return base_co2 * m.expected_co2_reduction_pct / 100.0


def _score_roi(est_cost_saving: float | None, investment: float) -> float:
    """ROI スコア（0-100）。年間コスト削減 / 投資額 の比率を 5 段階で評価。

    効果なしの前提施策（visualization_baseline 等）は 30 点固定。
    """
    if est_cost_saving is None or est_cost_saving <= 0:
        return 30.0
    if investment <= 0:
        return 100.0
    ratio = est_cost_saving / investment
    if ratio >= 10:
        return 100.0
    if ratio >= 5:
        return 80.0
    if ratio >= 2:
        return 60.0
    if ratio >= 1:
        return 40.0
    return 20.0


def _score_feasibility(
    difficulty: int,
    missing_resources: list[RequiredResource],
) -> float:
    """実装可能性スコア（0-100）。難易度ベース + リソース欠如ペナルティ。"""
    base = 120.0 - difficulty * 20.0  # 難易度1→100, 5→20
    penalty = len(missing_resources) * 20.0
    return max(0.0, base - penalty)


def _score_compliance(m: PlaybookMeasure, is_chain: bool) -> float:
    """法令適合度スコア（0-100）。

    様式第3 の必須セクション該当 +80 / 法令条文紐付き +20。
    連鎖化事業者は荷役等セクションを必須から除外。
    """
    required_sections = _REQUIRED_SECTIONS_CHAIN if is_chain else _REQUIRED_SECTIONS_NON_CHAIN
    score = 0.0
    if m.form3_section in required_sections:
        score += 80.0
    else:
        score += 30.0  # 任意領域でも法令準拠の補助になる
    if m.relevant_law_articles:
        score += 20.0
    return min(100.0, score)


def _score_subsidy(eligible_subsidies: list[str]) -> float:
    """補助金カバー率スコア（0-100）。0件→0 / 1件→50 / 2件以上→100。"""
    n = len(eligible_subsidies)
    if n == 0:
        return 0.0
    if n == 1:
        return 50.0
    return 100.0


def _build_selection_reason(
    m: PlaybookMeasure,
    roi: float,
    feasibility: float,
    compliance: float,
    subsidy: float,
    est_cost_saving: float | None,
    est_payback: float | None,
    missing_resources: list[RequiredResource],
) -> str:
    """選定根拠テキストを生成する（経営層への説明用）。"""
    parts: list[str] = []

    if roi >= 80:
        if est_cost_saving and est_payback is not None:
            payback_str = "回収 1年未満" if est_payback < 0.1 else f"回収 約{est_payback:.1f}年"
            parts.append(
                "投資対効果が高い（"
                f"年 約{format_jpy(est_cost_saving, digits=2)}削減・{payback_str}）"
            )
        else:
            parts.append("投資対効果が高い")
    elif roi >= 60:
        parts.append("投資対効果は中程度")
    elif roi <= 30:
        parts.append("コスト削減効果は限定的（前提施策または間接効果中心）")

    if feasibility >= 80:
        parts.append(f"実装難易度が低い（{m.implementation_difficulty}/5）")
    elif feasibility <= 40:
        parts.append(f"実装難易度が高い（{m.implementation_difficulty}/5）")

    if missing_resources:
        parts.append(f"前提リソース不足: {', '.join(missing_resources)}")

    if compliance >= 80:
        parts.append("様式第3 必須項目に直接対応")

    if subsidy >= 50 and m.eligible_subsidies:
        parts.append(f"補助金あり（{m.eligible_subsidies[0]}）")

    if not parts:
        parts.append("総合バランス型")

    return " / ".join(parts)


def build_eval_summary(r: MeasureEvalResult) -> str:
    """MeasureEvalResult から CLO 向けサマリーテキストを生成する。

    Top 3 には実行カード簡易版（主管・月次KPI・依存関係）と他施策との比較ポイント、
    Bottom 3 には不採用理由を併記し、judgment trail として経営会議で
    「なぜ採用/不採用？」即答できる形で出力する。
    """
    lines: list[str] = [
        f"=== 施策評価: {r.company_name} ===",
        f"業種: {r.industry} / 推定リソース: {', '.join(r.derived_resources) or '（なし）'}",
        f"評価対象施策: {r.eligible_count} 件（プレイブック全 10 件中）",
        "",
        "【Top 3 推薦】",
    ]
    section_labels = {
        "load": "Ⅱ 積載率向上",
        "wait": "Ⅲ 荷待ち時間短縮",
        "loading": "Ⅳ 荷役等時間短縮",
    }
    for i, s in enumerate(r.top_recommendations, start=1):
        lines.extend(_format_score_block(s, rank=i, section_labels=section_labels))
        lines.append(f"     主管部門: {s.responsible_dept}")
        lines.append(f"     想定月次 KPI: {s.monthly_kpi}")
        if s.dependencies:
            lines.append(f"     依存関係: {' / '.join(s.dependencies)}")
        lines.append(f"     選定根拠: {s.selection_reason}")
        if s.comparison_note:
            lines.append(f"     他施策との比較: {s.comparison_note}")
        lines.append("")

    if r.bottom_candidates:
        lines.append("【不採用候補（Bottom 3 / judgment trail）】")
        for s in r.bottom_candidates:
            lines.append(
                f"  ✗ [{s.measure.measure_id}] {s.measure.name}  総合 {s.total_score:.1f}/100"
            )
            lines.append(
                f"     スコア: ROI {s.roi_score:.0f} / 実装可能性 {s.feasibility_score:.0f}"
                f" / 法令適合 {s.compliance_score:.0f} / 補助金 {s.subsidy_score:.0f}"
            )
            if s.comparison_note:
                lines.append(f"     不採用理由: {s.comparison_note}")
        lines.append("")

    if r.top_recommendations and r.bottom_candidates:
        lines.append("【Top/Bottom スコア対比】")
        lines.append("  軸          Top 3 平均  Bottom 3 平均  差分")
        for axis, top_attr, bot_attr in [
            ("総合      ", "total_score", "total_score"),
            ("ROI       ", "roi_score", "roi_score"),
            ("実装可能性", "feasibility_score", "feasibility_score"),
            ("法令適合  ", "compliance_score", "compliance_score"),
            ("補助金    ", "subsidy_score", "subsidy_score"),
        ]:
            top_avg = sum(getattr(s, top_attr) for s in r.top_recommendations) / len(
                r.top_recommendations,
            )
            bot_avg = sum(getattr(s, bot_attr) for s in r.bottom_candidates) / len(
                r.bottom_candidates,
            )
            lines.append(
                f"  {axis}    {top_avg:5.1f}        {bot_avg:5.1f}     +{top_avg - bot_avg:.1f}pt"
            )
        lines.append("")

    if len(r.all_scored) > _TOP_N:
        lines.append("【全施策ランキング（参考）】")
        for s in r.all_scored:
            if s in r.top_recommendations:
                marker = "★"
            elif s in r.bottom_candidates:
                marker = "✗"
            else:
                marker = "  "
            lines.append(
                f"  {marker} {s.total_score:5.1f}  [{s.measure.measure_id}] {s.measure.name}"
            )

    return "\n".join(lines)


def _format_score_block(
    s: MeasureScore,
    rank: int,
    section_labels: dict[str, str],
) -> list[str]:
    """単一スコアの基本ブロック（ランキング・分類・スコア・期待効果）を返す。"""
    block: list[str] = [
        (f"  {rank}. [{s.measure.measure_id}] {s.measure.name}  総合 {s.total_score:.1f}/100"),
        (
            f"     分類: {section_labels.get(s.measure.form3_section, s.measure.form3_section)}"
            f" / 難易度 {s.measure.implementation_difficulty}/5"
        ),
        (
            f"     スコア: ROI {s.roi_score:.0f} / 実装可能性 {s.feasibility_score:.0f}"
            f" / 法令適合 {s.compliance_score:.0f} / 補助金 {s.subsidy_score:.0f}"
        ),
    ]
    if s.estimated_annual_cost_saving_jpy:
        line = f"     期待効果: 年 約{format_jpy(s.estimated_annual_cost_saving_jpy, digits=2)}削減"
        if s.estimated_payback_years is not None:
            if s.estimated_payback_years < 0.1:
                line += " / 回収 1年未満"
            else:
                line += f" / 回収 約{s.estimated_payback_years:.1f}年"
        block.append(line)
    if s.estimated_annual_co2_reduction_kg:
        block.append(
            f"     CO2 削減: 約 {s.estimated_annual_co2_reduction_kg / 1000:,.0f}トン-CO2/年"
        )
    return block
