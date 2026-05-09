"""CLO 計画書「数値目標」セクションへの目標値提案。

国家目標（物流分野 CO2 ▲23.4%）と業界平均値を組み合わせて、
業種・売上規模に応じた具体的な数値目標を提示する。
出力は様式第3別紙「中長期計画書」の数値目標欄に直接転記できる粒度。

設計方針:
    - 国家目標は core/static/national_targets.py から取得
    - 業界平均物流コスト比率は core/analytics/benchmark.py の公開定数から取得
    - 業界平均積載率・モーダルシフト目標は公表値を本ファイル内で定義
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analytics._summary import SummaryResult
from core.analytics.benchmark import INDUSTRY_AVG_LOGISTICS_RATIO
from core.export.citation import (
    Citation,
    co2_factors_citation,
    logistics_efficiency_law_citation,
)
from core.export.formatter import format_jpy
from core.static._freshness import all_warnings
from core.static.jsic import JsicEntry, lookup
from core.static.national_targets import LOGISTICS_CO2_TARGET, MODAL_SHIFT_TARGET

# 営業用普通貨物車の全国平均積載率（自動車輸送統計年報の概算値）
# 出典: 国土交通省「自動車輸送統計年報」（年次）
_INDUSTRY_AVG_LOAD_FACTOR_PCT = 38.0
# 国交省が「目指すべき水準」として示す積載率（持続可能な物流検討会 2023年8月）
_TARGET_LOAD_FACTOR_PCT = 50.0

_LOAD_FACTOR_SOURCE_LABEL = "自動車輸送統計年報（国土交通省・年次）"
_LOAD_FACTOR_SOURCE_URL = "https://www.mlit.go.jp/k-toukei/jidousyayusou.html"
_TRANSPORT_POLICY_BASIC_PLAN_URL = (
    "https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_tk_000146.html"
)
_JILS_URL = "https://www.logistics.or.jp/survey/logistics_cost.html"


@dataclass(frozen=True)
class NumericTarget:
    """単一の数値目標。様式第3別紙の数値目標欄1項目に対応。"""

    name: str  # 指標名（例: "輸送量当たりCO2排出原単位"）
    current_industry_avg: float | None  # 業界平均値（基準）
    current_industry_avg_unit: str  # 業界平均値の単位
    proposed_target: float  # 提案目標値
    proposed_target_unit: str  # 提案目標値の単位
    base_year: int  # 基準年
    target_year: int  # 目標年
    rationale: str  # 提案根拠
    citation: Citation  # 出典


@dataclass
class TargetProposalResult:
    """数値目標提案結果。CLO 計画書「数値目標」セクション草稿として直接利用可能。"""

    jsic_code: str
    jsic_name: str
    category: str
    prefecture: str
    revenue_jpy: int

    targets: list[NumericTarget] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


def _build_co2_intensity_target() -> NumericTarget:
    """物流分野 CO2 排出原単位削減目標（国家目標連動）。"""
    return NumericTarget(
        name="輸送量当たりCO2排出原単位",
        current_industry_avg=None,  # 自社実績ベースのため業界平均は別途
        current_industry_avg_unit="g-CO2/トンキロ",
        proposed_target=-LOGISTICS_CO2_TARGET.intensity_reduction_pct,
        proposed_target_unit=f"%（{LOGISTICS_CO2_TARGET.base_year}年度比削減）",
        base_year=LOGISTICS_CO2_TARGET.base_year,
        target_year=LOGISTICS_CO2_TARGET.target_year,
        rationale=(
            f"物流分野固有の国家目標 ▲{LOGISTICS_CO2_TARGET.intensity_reduction_pct:.1f}%"
            "（地球温暖化対策計画／第3次交通政策基本計画）に整合"
        ),
        citation=Citation(
            label="第3次交通政策基本計画（令和5年8月閣議決定）",
            url=_TRANSPORT_POLICY_BASIC_PLAN_URL,
            accessed_via="国交省ポータル（静的参照）",
        ),
    )


def _build_load_factor_target() -> NumericTarget:
    """営業用トラック積載率向上目標。"""
    return NumericTarget(
        name="営業用普通貨物車 積載率",
        current_industry_avg=_INDUSTRY_AVG_LOAD_FACTOR_PCT,
        current_industry_avg_unit="%",
        proposed_target=_TARGET_LOAD_FACTOR_PCT,
        proposed_target_unit="%",
        base_year=2022,
        target_year=2030,
        rationale=(
            f"全国平均 {_INDUSTRY_AVG_LOAD_FACTOR_PCT:.0f}% に対し、"
            f"国交省「持続可能な物流の実現に向けた検討会」最終とりまとめが示す"
            f"目指すべき水準 {_TARGET_LOAD_FACTOR_PCT:.0f}% を提案"
        ),
        citation=Citation(
            label=_LOAD_FACTOR_SOURCE_LABEL,
            url=_LOAD_FACTOR_SOURCE_URL,
            accessed_via="国土交通省 自動車輸送統計（年次）",
        ),
    )


def _build_modal_shift_target() -> NumericTarget:
    """モーダルシフト推進目標（鉄道貨物 + 内航海運）。"""
    rail_growth_pct = (
        (
            MODAL_SHIFT_TARGET.rail_freight_tonkm_target_2030
            - MODAL_SHIFT_TARGET.rail_freight_tonkm_base_2019
        )
        / MODAL_SHIFT_TARGET.rail_freight_tonkm_base_2019
        * 100.0
    )
    return NumericTarget(
        name="鉄道・内航海運へのモーダルシフト率",
        current_industry_avg=MODAL_SHIFT_TARGET.rail_freight_tonkm_base_2019,
        current_industry_avg_unit="億トンキロ（鉄道貨物・全国実績）",
        proposed_target=MODAL_SHIFT_TARGET.rail_freight_tonkm_target_2030,
        proposed_target_unit=f"億トンキロ（鉄道貨物・全国目標／+{rail_growth_pct:.1f}%）",
        base_year=2019,
        target_year=2030,
        rationale=(
            f"全国目標 {MODAL_SHIFT_TARGET.rail_freight_tonkm_base_2019:.0f}→"
            f"{MODAL_SHIFT_TARGET.rail_freight_tonkm_target_2030:.0f}億トンキロ "
            f"(+{rail_growth_pct:.1f}%) に整合させ、"
            "中長距離（500km超）の鉄道シフト率を年次拡大"
        ),
        citation=Citation(
            label="第3次交通政策基本計画（モーダルシフト目標）",
            url=_TRANSPORT_POLICY_BASIC_PLAN_URL,
            accessed_via="国交省ポータル（静的参照）",
        ),
    )


def _build_logistics_cost_target(
    category: str, revenue_vs_avg_pct: float | None
) -> NumericTarget | None:
    """物流コスト/売上比率の削減目標。荷主業種のみ。

    自社売上が業界平均より大きい（規模優位）場合は ▲0.5pt、
    そうでない場合は ▲0.3pt を提案する。
    """
    avg_ratio = INDUSTRY_AVG_LOGISTICS_RATIO.get(category)
    if avg_ratio is None:
        return None  # 運輸業など荷主でない業種は対象外

    # 規模優位性に応じた削減目標（売上が業界平均の2倍以上ならスケール優位を活かす）
    reduction_pt = 0.5 if revenue_vs_avg_pct is not None and revenue_vs_avg_pct >= 200.0 else 0.3

    avg_pct = avg_ratio * 100.0
    target_pct = max(avg_pct - reduction_pt, 0.0)

    return NumericTarget(
        name="物流コスト/売上比率",
        current_industry_avg=avg_pct,
        current_industry_avg_unit="%",
        proposed_target=target_pct,
        proposed_target_unit=f"%（業界平均比 ▲{reduction_pt:.1f}pt）",
        base_year=2021,
        target_year=2030,
        rationale=(
            f"業界平均 {avg_pct:.1f}%（JILS 物流コスト実態調査）から"
            f"▲{reduction_pt:.1f}pt の改善を提案。"
            "積載率向上・共同配送・モーダルシフト等の組合せで実現可能水準"
        ),
        citation=Citation(
            label="物流コスト実態調査 2021年度（日本ロジスティクスシステム協会）",
            url=_JILS_URL,
            accessed_via="公開報告書（静的参照）",
        ),
    )


def propose_targets(
    jsic_code: str,
    prefecture: str,
    revenue_jpy: int,
    revenue_vs_industry_avg_pct: float | None = None,
) -> TargetProposalResult:
    """CLO 計画書用の数値目標を提案する。

    Args:
        jsic_code: JSIC 細分類4桁コード
        prefecture: 主たる拠点の都道府県名
        revenue_jpy: 年間売上（円）
        revenue_vs_industry_avg_pct: 業界平均比（%）。Step 1 の出力を渡す想定。
            None の場合は規模優位性なしとして扱う

    Returns:
        TargetProposalResult

    Raises:
        ValueError: jsic_code が未収録の場合
    """
    entry: JsicEntry | None = lookup(jsic_code)
    if entry is None:
        raise ValueError(
            f"JSIC コード '{jsic_code}' は未収録です。"
            "Step 1（logi_clo_benchmark_position）と同じコードを指定してください。"
        )

    targets: list[NumericTarget] = [
        _build_co2_intensity_target(),
        _build_load_factor_target(),
        _build_modal_shift_target(),
    ]

    cost_target = _build_logistics_cost_target(entry.category, revenue_vs_industry_avg_pct)
    if cost_target is not None:
        targets.append(cost_target)

    citations: list[Citation] = [
        logistics_efficiency_law_citation(),
        co2_factors_citation(),
    ]
    # 各目標の citation を重複排除して追加
    seen_urls = {c.url for c in citations}
    for t in targets:
        if t.citation.url not in seen_urls:
            citations.append(t.citation)
            seen_urls.add(t.citation.url)

    return TargetProposalResult(
        jsic_code=jsic_code,
        jsic_name=entry.name,
        category=entry.category,
        prefecture=prefecture,
        revenue_jpy=revenue_jpy,
        targets=targets,
        citations=citations,
        freshness_warnings=all_warnings(),
    )


_BUSINESS_CATEGORY_LABELS: dict[str, str] = {
    "manufacturing": "製造業",
    "wholesale": "卸売業",
    "retail": "小売業",
    "chain_franchise": "連鎖化事業者",
    "transport": "運輸業",
    "other": "その他",
}


def build_target_proposal_summary(r: TargetProposalResult) -> SummaryResult:
    """TargetProposalResult から CLO 計画書用サマリーテキストを生成する。"""
    category_label = _BUSINESS_CATEGORY_LABELS.get(r.category, r.category)

    lines: list[str] = [
        f"業種: {r.jsic_name}（{r.jsic_code}）/ {category_label}",
        f"都道府県: {r.prefecture}",
        f"年間売上: {format_jpy(r.revenue_jpy)}",
        "",
        "【推奨数値目標】",
    ]

    for i, t in enumerate(r.targets, start=1):
        avg_str = (
            f"{t.current_industry_avg:.1f}{t.current_industry_avg_unit}"
            if t.current_industry_avg is not None
            else "自社実績計測が必要"
        )
        target_str = f"{t.proposed_target:.1f}{t.proposed_target_unit}"
        lines += [
            "",
            f"  {i}. {t.name}",
            f"     基準（{t.base_year}年）: {avg_str}",
            f"     目標（{t.target_year}年）: {target_str}",
            f"     根拠: {t.rationale}",
            f"     出典: {t.citation.label}",
        ]

    lines += [
        "",
        "【法令上の記載義務】",
        (
            "  ・特定荷主: 物流効率化法 第46条 / 特定連鎖化事業者: 第65条 — "
            "中長期計画書（様式第3別紙）に数値目標の記載が必須"
        ),
        "  ・物流効率化法 第66条: 物流統括管理者（CLO）の選任義務（役員級）",
        "  ・経営会議で「なぜこの目標値か」を聞かれたら本サマリーの『根拠』欄を引用",
        "",
        "【次のステップ】",
        "  → Step 5 で施策効果シミュレーション（モーダルシフト・積載率向上・共同配送等）",
        "  → Step 7 で計画書ドラフト統合生成（PPT/Word/Excel/Markdown 一括出力）",
    ]

    return SummaryResult(
        title="=== 数値目標提案（中長期計画書 様式第3別紙）===",
        body=lines,
    )
