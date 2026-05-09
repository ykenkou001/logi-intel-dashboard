"""財務翻訳レイヤ — 物流 KPI を P&L インパクトに換算する。

CLO 計画書の核心は経営会議での説得。本モジュールは施策効果（CO2 削減・コスト削減・
ドライバー時間削減）を **円単位の経営指標**に変換し、経営層が直感的に判断できる形にする。

設計方針:
    - コスト削減 → 営業利益増として反映（売上原価減 = 営業利益増）
    - CO2 削減 → 炭素価格レンジ（J-クレジット〜GX-ETS 想定）で min/max 提示
    - ESG プレミアムは定性記述に留める（資本コスト改善の数値化は研究段階）
    - 不作為コストは罰則 + ブランド毀損リスクを併記
    - 5 年累積効果を NPV（割引率 3%）で算出
    - 全数値に出典を付与
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analytics._summary import SummaryResult
from core.analytics.simulator import MeasureSimulation, SimulationResult
from core.export.citation import (
    Citation,
    co2_factors_citation,
    logistics_efficiency_law_citation,
)
from core.export.formatter import format_jpy
from core.static._freshness import all_warnings
from core.static.financial_factors import (
    CARBON_PRICE,
    ESG_QUALITATIVE_NOTE,
    NPV_PARAMS,
    build_inaction_risk_note,
)
from core.static.sample_company import CompanyProfile

_J_CREDIT_REFERENCE_URL = "https://japancredit.go.jp/data/"


@dataclass(frozen=True)
class FinancialImpact:
    """単一施策の財務インパクト。"""

    measure_name: str
    cost_saving_jpy_per_year: float | None
    """コスト削減額（年・円）。simulator から転記。"""

    operating_profit_increase_jpy_per_year: float | None
    """営業利益増加額（年・円）。コスト削減 = 売上原価減 → 営業利益増を仮定。"""

    operating_profit_margin_lift_pp: float | None
    """営業利益率改善幅（pp = percentage points）。"""

    co2_reduction_kg_per_year: float | None
    """CO2 削減量（年・kg）。simulator から転記。"""

    carbon_avoidance_jpy_low: float | None
    """炭素価格回避額（年・円）— J-クレジット実勢価格ベース。"""

    carbon_avoidance_jpy_high: float | None
    """炭素価格回避額（年・円）— GX-ETS 想定価格ベース。"""

    investment_jpy: float
    payback_years: float | None

    five_year_npv_jpy: float | None
    """5 年累積コスト削減の NPV（割引率 3%・投資差し引き済み）。"""


@dataclass
class FinancialTranslateResult:
    """財務翻訳結果。"""

    company_id: str
    company_name: str
    base_revenue_jpy: int
    base_operating_profit_jpy: int
    base_operating_profit_margin_pct: float

    measures: list[FinancialImpact] = field(default_factory=list)

    # 合算
    total_operating_profit_increase_jpy: float = 0.0
    total_carbon_avoidance_jpy_low: float = 0.0
    total_carbon_avoidance_jpy_high: float = 0.0
    total_investment_jpy: float = 0.0
    total_5y_npv_jpy: float = 0.0
    operating_profit_margin_lift_pp_total: float = 0.0

    # 定性記述
    inaction_risk_note: str = ""
    esg_qualitative_note: str = ""

    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


def translate_to_pnl_impact(
    profile: CompanyProfile,
    simulation: SimulationResult,
) -> FinancialTranslateResult:
    """プラン実行結果を財務インパクトに翻訳する。

    Args:
        profile: 自社プロフィール（営業利益・売上原価を含む）
        simulation: 施策効果シミュレーション結果

    Returns:
        FinancialTranslateResult: 施策別の P&L 翻訳 + 合算 + 定性記述
    """
    base_margin_pct = (
        profile.operating_profit_jpy / profile.annual_revenue_jpy * 100.0
        if profile.annual_revenue_jpy > 0
        else 0.0
    )

    impacts: list[FinancialImpact] = []
    for m in simulation.measures:
        impacts.append(_translate_measure(m, profile.annual_revenue_jpy))

    total_op_increase = sum(i.operating_profit_increase_jpy_per_year or 0.0 for i in impacts)
    total_carbon_low = sum(i.carbon_avoidance_jpy_low or 0.0 for i in impacts)
    total_carbon_high = sum(i.carbon_avoidance_jpy_high or 0.0 for i in impacts)
    total_investment = sum(i.investment_jpy for i in impacts)
    total_npv = sum(i.five_year_npv_jpy or 0.0 for i in impacts)
    total_margin_lift = sum(i.operating_profit_margin_lift_pp or 0.0 for i in impacts)

    citations = _build_citations()

    return FinancialTranslateResult(
        company_id=profile.company_id,
        company_name=profile.name,
        base_revenue_jpy=profile.annual_revenue_jpy,
        base_operating_profit_jpy=profile.operating_profit_jpy,
        base_operating_profit_margin_pct=base_margin_pct,
        measures=impacts,
        total_operating_profit_increase_jpy=total_op_increase,
        total_carbon_avoidance_jpy_low=total_carbon_low,
        total_carbon_avoidance_jpy_high=total_carbon_high,
        total_investment_jpy=total_investment,
        total_5y_npv_jpy=total_npv,
        operating_profit_margin_lift_pp_total=total_margin_lift,
        inaction_risk_note=build_inaction_risk_note(),
        esg_qualitative_note=ESG_QUALITATIVE_NOTE,
        citations=citations,
        freshness_warnings=all_warnings(),
    )


def _translate_measure(
    m: MeasureSimulation,
    base_revenue_jpy: int,
) -> FinancialImpact:
    """単一施策の翻訳。"""
    cost_saving = m.cost_saving_jpy_per_year

    # 営業利益増 = コスト削減（売上原価減 → 営業利益増）
    op_increase = cost_saving if cost_saving and cost_saving > 0 else None
    margin_lift_pp = (
        op_increase / base_revenue_jpy * 100.0
        if op_increase is not None and base_revenue_jpy > 0
        else None
    )

    # 炭素価格回避（min/max レンジ）
    co2 = m.co2_reduction_kg_per_year
    carbon_low: float | None = None
    carbon_high: float | None = None
    if co2 is not None and co2 > 0:
        co2_tons = co2 / 1000.0
        carbon_low = co2_tons * CARBON_PRICE.low
        carbon_high = co2_tons * CARBON_PRICE.high

    # 5 年累積 NPV（割引率 3%・投資は初年度に発生・コスト削減は1〜5年目に発生）
    five_year_npv = (
        _calculate_npv(
            annual_saving=cost_saving or 0.0,
            investment=m.investment_jpy,
            years=NPV_PARAMS.horizon_years,
            discount_rate_pct=NPV_PARAMS.discount_rate_pct,
        )
        if cost_saving and cost_saving > 0
        else None
    )

    return FinancialImpact(
        measure_name=m.name,
        cost_saving_jpy_per_year=cost_saving,
        operating_profit_increase_jpy_per_year=op_increase,
        operating_profit_margin_lift_pp=margin_lift_pp,
        co2_reduction_kg_per_year=co2,
        carbon_avoidance_jpy_low=carbon_low,
        carbon_avoidance_jpy_high=carbon_high,
        investment_jpy=m.investment_jpy,
        payback_years=m.payback_years,
        five_year_npv_jpy=five_year_npv,
    )


def _calculate_npv(
    annual_saving: float,
    investment: float,
    years: int,
    discount_rate_pct: float,
) -> float:
    """単純 NPV を算出する。

    NPV = Σ (annual_saving / (1 + r)^t) for t in 1..years - investment

    Args:
        annual_saving: 年間コスト削減額（円）
        investment: 初期投資額（円）
        years: 評価期間（年）
        discount_rate_pct: 割引率（%）

    Returns:
        NPV（円）
    """
    r = discount_rate_pct / 100.0
    pv_savings = sum(annual_saving / ((1.0 + r) ** t) for t in range(1, years + 1))
    return pv_savings - investment


def _build_citations() -> list[Citation]:
    """財務翻訳の出典リスト。"""
    return [
        co2_factors_citation(),  # CO2 削減量の根拠
        Citation(
            label="J-クレジット制度 取引価格情報",
            url=_J_CREDIT_REFERENCE_URL,
            accessed_via="J-クレジット制度事務局（経産省・環境省・農水省）",
        ),
        Citation(
            label="GX 実現に向けた基本方針 / GX-ETS 試行段階",
            url=(
                "https://www.meti.go.jp/policy/energy_environment/global_warming/JCM/about_jcm.html"
            ),
            accessed_via="経産省・環境省 GX 関連資料",
        ),
        logistics_efficiency_law_citation(),  # 罰則根拠
    ]


def build_financial_translate_summary(r: FinancialTranslateResult) -> SummaryResult:
    """FinancialTranslateResult から CLO 向けサマリーテキストを生成する。"""
    lines: list[str] = [
        "",
        "【企業財務基準】",
        f"  売上: {format_jpy(r.base_revenue_jpy, thousand_sep=True)}",
        f"  営業利益: {format_jpy(r.base_operating_profit_jpy, digits=2, thousand_sep=True)} "
        f"(営業利益率 {r.base_operating_profit_margin_pct:.2f}%)",
        "",
        "【施策別 P&L インパクト（年間ベース）】",
    ]

    for i in r.measures:
        if i.operating_profit_increase_jpy_per_year:
            op_jpy = format_jpy(
                i.operating_profit_increase_jpy_per_year,
                digits=2,
                with_sign=True,
                thousand_sep=True,
            )
            op_str = f"営業利益 {op_jpy} (+{i.operating_profit_margin_lift_pp:.2f}pp)"
        else:
            op_str = "営業利益効果: 試算対象外"
        if i.carbon_avoidance_jpy_low and i.carbon_avoidance_jpy_high:
            carbon_low = format_jpy(i.carbon_avoidance_jpy_low, unit="million", thousand_sep=True)
            carbon_high = format_jpy(i.carbon_avoidance_jpy_high, unit="million", thousand_sep=True)
            carbon_str = f"炭素回避 {carbon_low}〜{carbon_high}/年"
        else:
            carbon_str = "炭素回避: なし"
        npv_str = (
            f"5年NPV {format_jpy(i.five_year_npv_jpy, digits=2, thousand_sep=True)}"
            if i.five_year_npv_jpy is not None
            else "5年NPV: 試算対象外"
        )
        lines.append(f"  ◆ {i.measure_name}")
        lines.append(f"    {op_str} / {carbon_str} / {npv_str}")

    total_op = format_jpy(r.total_operating_profit_increase_jpy, digits=2, thousand_sep=True)
    total_carbon_low = format_jpy(
        r.total_carbon_avoidance_jpy_low, unit="million", digits=0, thousand_sep=True
    )
    total_carbon_high = format_jpy(
        r.total_carbon_avoidance_jpy_high, unit="million", digits=0, thousand_sep=True
    )
    total_invest = format_jpy(r.total_investment_jpy, unit="man", digits=0, thousand_sep=True)
    total_npv = format_jpy(r.total_5y_npv_jpy, digits=2, thousand_sep=True)

    lines += [
        "",
        "【施策合算（重複あり・最大値の参考）】",
        f"  営業利益増加合計: 約 {total_op}/年",
        f"  営業利益率改善: 合算 +{r.operating_profit_margin_lift_pp_total:.2f}pp",
        f"  炭素価格回避レンジ: {total_carbon_low}〜{total_carbon_high}/年 "
        f"({CARBON_PRICE.low:,.0f}〜{CARBON_PRICE.high:,.0f}円/t-CO2)",
        f"  必要投資合計: 約 {total_invest}",
        f"  5年累積 NPV: 約 {total_npv} (割引率 {NPV_PARAMS.discount_rate_pct:.1f}%)",
        "",
        r.inaction_risk_note,
        "",
        "【ESG 効果（定性）】",
        f"  {r.esg_qualitative_note}",
    ]

    return SummaryResult(title=f"=== 財務翻訳: {r.company_name} ===", body=lines)
