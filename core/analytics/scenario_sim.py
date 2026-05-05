"""シナリオシミュレータ — フェーズ3.5 Step 3（差別化の心臓部）。

選択された施策セット（または Step 2 Top 3 自動採用）に対して、
保守 / 標準 / 上振れの 3 区分（Codex 3 取込）× What-if 8 シナリオで
営業利益・CO2 削減・5 年 NPV を試算し、堅牢性を判定する。

設計方針:
    - 同 form3_section に 2 施策以上 → 効果合算に 0.7 倍を適用（重複ダンピング）
    - 各シナリオ × 3 区分（conservative 0.6 / standard 1.0 / upside 1.3）
    - 堅牢性判定: ストレスシナリオの standard 営業利益 / baseline standard
        - 70% 以上 → 緑 / 50-70% → 黄 / 50% 未満 → 赤
    - 「燃料 +20% でも黒字維持」をフェーズ3.5 完了条件として明示判定
    - NPV: 投資は初年度 / 削減は 1〜5 年目 / 割引率 3%
    - 全数値に出典付与（経営会議「出典は？」即答用）
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from core.analytics.benchmark import INDUSTRY_AVG_LOGISTICS_RATIO
from core.analytics.measure_eval import evaluate_measures
from core.export.citation import (
    Citation,
    co2_factors_citation,
    logistics_efficiency_law_citation,
)
from core.playbook.measures import PlaybookMeasure, get_measure
from core.static._freshness import all_warnings
from core.static.financial_factors import NPV_PARAMS
from core.static.jsic import category_of
from core.static.sample_company import CompanyProfile

# 3 区分の効果倍率（Codex 3 取込）
# conservative は実装費・運用費・サービスレベル低下リスクを織り込んだ下振れ
# upside は楽観前提（取引先協力・補助金フル取得・繁忙期効果が想定通り）
_CONSERVATIVE_FACTOR: float = 0.6
_STANDARD_FACTOR: float = 1.0
_UPSIDE_FACTOR: float = 1.3

# 同 form3_section に 2 施策以上ある場合の効果合算ダンピング
_SECTION_OVERLAP_DAMP: float = 0.7

# 堅牢性しきい値（baseline standard 営業利益増との比率）
_ROBUSTNESS_GREEN: float = 0.70
_ROBUSTNESS_YELLOW: float = 0.50

# 自動採用時の Top N（Step 2 measure_eval から取得）
_AUTO_TOP_N: int = 3

# 物流コスト 1 円あたり概ね 0.05 kg-CO2（measure_eval._estimate_annual_co2_reduction と整合）
_CO2_PER_JPY: float = 0.05

# 措置タイプ別 addressable_share（measure_eval._ADDRESSABLE_SHARE と同じ係数）
_ADDRESSABLE_SHARE: dict[str, float] = {
    "modal_shift": 0.30,
    "load_factor": 0.80,
    "joint_delivery": 0.40,
    "relay_transport": 0.25,
    "berth_booking": 0.50,
    "warehouse_dx": 0.60,
}


@dataclass(frozen=True)
class ScenarioParameters:
    """What-if シナリオパラメータ。"""

    name: str
    label: str
    cost_saving_multiplier: float
    investment_multiplier: float
    co2_multiplier: float
    description: str


@dataclass(frozen=True)
class ThreeBandValue:
    """3 区分（保守 / 標準 / 上振れ）の値。

    CFO 質問「最低でも保守シナリオで X 億円か？」に答えるためのデータ構造。
    """

    conservative: float
    standard: float
    upside: float


@dataclass(frozen=True)
class ScenarioResult:
    """単一シナリオの結果。3 区分で値を持つ。"""

    scenario: ScenarioParameters
    annual_co2_reduction_kg: ThreeBandValue
    annual_cost_saving_jpy: ThreeBandValue
    annual_operating_profit_increase_jpy: ThreeBandValue
    total_investment_jpy: float
    five_year_npv_jpy: ThreeBandValue
    operating_profit_ratio_to_baseline: float
    """baseline standard 営業利益増 に対する本シナリオ standard 値の比率。"""

    robustness_level: Literal["green", "yellow", "red"]
    robustness_message: str


@dataclass
class ScenarioSimResult:
    """シナリオシミュレーション結果。"""

    company_id: str
    company_name: str
    industry: str
    selected_measures: list[PlaybookMeasure]
    measure_selection_source: Literal["explicit", "auto_top3"]
    section_overlap_count: dict[str, int]
    synergy_multiplier: float
    baseline: ScenarioResult
    stress_scenarios: list[ScenarioResult]
    summary_message: str = ""
    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


# What-if プリセット（baseline + 7 ストレス = 8 種）
_BASELINE_PARAMS = ScenarioParameters(
    name="baseline",
    label="ベースライン",
    cost_saving_multiplier=1.00,
    investment_multiplier=1.00,
    co2_multiplier=1.00,
    description="想定どおりの施策効果（外的ショックなし）",
)

_STRESS_PRESETS: list[ScenarioParameters] = [
    ScenarioParameters(
        name="fuel_up_20",
        label="燃料 +20%",
        cost_saving_multiplier=1.05,
        investment_multiplier=1.00,
        co2_multiplier=1.00,
        description="燃料価格 +20% で燃費起因の削減効果が 5% 拡大",
    ),
    ScenarioParameters(
        name="fuel_down_20",
        label="燃料 -20%",
        cost_saving_multiplier=0.95,
        investment_multiplier=1.00,
        co2_multiplier=1.00,
        description="燃料価格 -20% で削減効果が 5% 縮小",
    ),
    ScenarioParameters(
        name="freight_up_10",
        label="運賃 +10%",
        cost_saving_multiplier=1.10,
        investment_multiplier=1.00,
        co2_multiplier=1.00,
        description="運賃上昇で削減効果が 10% 拡大",
    ),
    ScenarioParameters(
        name="freight_down_10",
        label="運賃 -10%",
        cost_saving_multiplier=0.90,
        investment_multiplier=1.00,
        co2_multiplier=1.00,
        description="運賃下落で削減効果が 10% 縮小",
    ),
    ScenarioParameters(
        name="demand_up_10",
        label="需要 +10%",
        cost_saving_multiplier=1.10,
        investment_multiplier=1.00,
        co2_multiplier=1.10,
        description="輸送量増で削減・CO2 効果が 10% 拡大",
    ),
    ScenarioParameters(
        name="demand_down_10",
        label="需要 -10%",
        cost_saving_multiplier=0.90,
        investment_multiplier=1.00,
        co2_multiplier=0.90,
        description="輸送量減で削減・CO2 効果が 10% 縮小",
    ),
    ScenarioParameters(
        name="improvement_standard_strict",
        label="改善基準強化",
        cost_saving_multiplier=0.80,
        investment_multiplier=1.30,
        co2_multiplier=1.00,
        description="改善基準告示の更なる強化により投資 30% 増・効果 20% 縮小",
    ),
]


def simulate_scenarios(
    profile: CompanyProfile,
    selected_measure_ids: list[str] | None = None,
) -> ScenarioSimResult:
    """シナリオシミュレーションを実行する。

    Args:
        profile: 自社プロフィール
        selected_measure_ids: 評価対象施策の measure_id リスト。
            None なら logi_clo_measure_eval の Top 3 を自動採用。

    Returns:
        ScenarioSimResult: baseline + 7 ストレスシナリオ × 3 区分

    Raises:
        ValueError: 不正な measure_id 指定 / 評価対象施策が空の場合
    """
    measures, source = _resolve_measures(profile, selected_measure_ids)
    if not measures:
        raise ValueError(
            "評価対象施策が空です。"
            "selected_measure_ids を指定するか、Step 2 で Top 3 が出る規模か確認してください。"
        )

    industry = category_of(profile.jsic_code) or "other"
    logistics_ratio = INDUSTRY_AVG_LOGISTICS_RATIO.get(industry) or 0.030
    logistics_cost = profile.cost_of_goods_sold_jpy * logistics_ratio

    section_count: Counter[str] = Counter(m.form3_section for m in measures)
    synergy = _compute_synergy_multiplier(section_count)

    # 各施策の baseline standard 値を集計（シナジー適用後）
    base_cost = _aggregate_cost_saving(measures, section_count, logistics_cost)
    base_co2 = _aggregate_co2_reduction(measures, section_count, logistics_cost)
    base_invest = _aggregate_investment(measures)

    baseline = _build_scenario_result(
        scenario=_BASELINE_PARAMS,
        base_cost_saving=base_cost,
        base_co2_reduction=base_co2,
        base_investment=base_invest,
        baseline_standard_op_increase=base_cost,  # baseline 自身が基準値
    )

    stress_results: list[ScenarioResult] = [
        _build_scenario_result(
            scenario=params,
            base_cost_saving=base_cost,
            base_co2_reduction=base_co2,
            base_investment=base_invest,
            baseline_standard_op_increase=(
                baseline.annual_operating_profit_increase_jpy.standard
            ),
        )
        for params in _STRESS_PRESETS
    ]

    result = ScenarioSimResult(
        company_id=profile.company_id,
        company_name=profile.name,
        industry=industry,
        selected_measures=measures,
        measure_selection_source=source,
        section_overlap_count=dict(section_count),
        synergy_multiplier=synergy,
        baseline=baseline,
        stress_scenarios=stress_results,
        citations=[
            logistics_efficiency_law_citation(),
            co2_factors_citation(),
        ],
        freshness_warnings=all_warnings(),
    )
    result.summary_message = build_scenario_summary(result)
    return result


def _resolve_measures(
    profile: CompanyProfile,
    selected_measure_ids: list[str] | None,
) -> tuple[list[PlaybookMeasure], Literal["explicit", "auto_top3"]]:
    """selected_measure_ids 指定なら明示採用、None なら Step 2 Top 3 を採用。"""
    if selected_measure_ids:
        measures: list[PlaybookMeasure] = []
        for mid in selected_measure_ids:
            m = get_measure(mid)
            if m is None:
                raise ValueError(
                    f"measure_id '{mid}' はプレイブックに登録されていません。"
                )
            measures.append(m)
        return measures, "explicit"

    eval_result = evaluate_measures(profile)
    return (
        [s.measure for s in eval_result.top_recommendations[:_AUTO_TOP_N]],
        "auto_top3",
    )


def _compute_synergy_multiplier(section_count: Counter[str]) -> float:
    """同 form3_section に 2 施策以上ある場合は 0.7 倍を返す。

    複数セクションで重複していても倍率は 1 つだけ適用（過剰ダンピング回避）。
    セクション跨ぎだけなら 1.0 倍。
    """
    has_overlap = any(count >= 2 for count in section_count.values())
    return _SECTION_OVERLAP_DAMP if has_overlap else 1.0


def _aggregate_cost_saving(
    measures: list[PlaybookMeasure],
    section_count: Counter[str],
    logistics_cost: float,
) -> float:
    """選択施策の年間コスト削減合算（セクション内重複ダンピング込み）。"""
    total = 0.0
    for m in measures:
        if m.expected_cost_reduction_pct is None:
            continue
        share = _ADDRESSABLE_SHARE.get(m.measure_type, 0.50)
        cost = logistics_cost * share * m.expected_cost_reduction_pct / 100.0
        if section_count[m.form3_section] >= 2:
            cost *= _SECTION_OVERLAP_DAMP
        total += cost
    return total


def _aggregate_co2_reduction(
    measures: list[PlaybookMeasure],
    section_count: Counter[str],
    logistics_cost: float,
) -> float:
    """選択施策の年間 CO2 削減合算（kg／セクション内重複ダンピング込み）。"""
    total = 0.0
    for m in measures:
        if m.expected_co2_reduction_pct is None:
            continue
        share = _ADDRESSABLE_SHARE.get(m.measure_type, 0.50)
        addressable_cost = logistics_cost * share
        base_co2 = addressable_cost * _CO2_PER_JPY
        co2 = base_co2 * m.expected_co2_reduction_pct / 100.0
        if section_count[m.form3_section] >= 2:
            co2 *= _SECTION_OVERLAP_DAMP
        total += co2
    return total


def _aggregate_investment(measures: list[PlaybookMeasure]) -> float:
    """選択施策の必要投資合算（投資はセクション内ダンピングしない）。"""
    return sum(
        (m.typical_investment_jpy_low + m.typical_investment_jpy_high) / 2.0
        for m in measures
    )


def _build_scenario_result(
    scenario: ScenarioParameters,
    base_cost_saving: float,
    base_co2_reduction: float,
    base_investment: float,
    baseline_standard_op_increase: float,
) -> ScenarioResult:
    """単一シナリオの 3 区分結果を構築する。"""
    cost_std = base_cost_saving * scenario.cost_saving_multiplier
    co2_std = base_co2_reduction * scenario.co2_multiplier
    invest = base_investment * scenario.investment_multiplier

    # コスト削減 = 営業利益増（売上原価減 → 営業利益増の前提）
    cost_band = ThreeBandValue(
        conservative=cost_std * _CONSERVATIVE_FACTOR,
        standard=cost_std * _STANDARD_FACTOR,
        upside=cost_std * _UPSIDE_FACTOR,
    )
    co2_band = ThreeBandValue(
        conservative=co2_std * _CONSERVATIVE_FACTOR,
        standard=co2_std * _STANDARD_FACTOR,
        upside=co2_std * _UPSIDE_FACTOR,
    )
    op_increase_band = cost_band  # 営業利益増 = コスト削減と同値
    npv_band = ThreeBandValue(
        conservative=_calculate_npv(cost_band.conservative, invest),
        standard=_calculate_npv(cost_band.standard, invest),
        upside=_calculate_npv(cost_band.upside, invest),
    )

    # 堅牢性判定: 本シナリオ standard / baseline standard
    if baseline_standard_op_increase > 0:
        ratio = op_increase_band.standard / baseline_standard_op_increase
    else:
        ratio = 1.0

    if ratio >= _ROBUSTNESS_GREEN:
        level: Literal["green", "yellow", "red"] = "green"
        msg = "🟢 baseline 効果の 70% 以上を維持（投資判断は堅牢）"
    elif ratio >= _ROBUSTNESS_YELLOW:
        level = "yellow"
        msg = "🟡 baseline 効果の 50-70% を維持（要モニタリング）"
    else:
        level = "red"
        msg = "🔴 baseline 効果の 50% 未満（投資判断却下リスク）"

    return ScenarioResult(
        scenario=scenario,
        annual_co2_reduction_kg=co2_band,
        annual_cost_saving_jpy=cost_band,
        annual_operating_profit_increase_jpy=op_increase_band,
        total_investment_jpy=invest,
        five_year_npv_jpy=npv_band,
        operating_profit_ratio_to_baseline=ratio,
        robustness_level=level,
        robustness_message=msg,
    )


def _calculate_npv(annual_saving: float, investment: float) -> float:
    """5 年累積 NPV（割引率 3%・投資は初年度・効果は 1〜5 年目）。

    financial_translate._calculate_npv と同じ式。
    """
    if annual_saving <= 0:
        return -investment
    r = NPV_PARAMS.discount_rate_pct / 100.0
    pv = sum(
        annual_saving / ((1.0 + r) ** t)
        for t in range(1, NPV_PARAMS.horizon_years + 1)
    )
    return pv - investment


def _format_yen(amount_jpy: float) -> str:
    """円を読みやすい単位に整形する（億円 / 万円）。"""
    if abs(amount_jpy) >= 100_000_000:
        return f"{amount_jpy / 100_000_000:.2f}億円"
    if abs(amount_jpy) >= 10_000:
        return f"{amount_jpy / 10_000:,.0f}万円"
    return f"{amount_jpy:,.0f}円"


def _format_co2(kg: float) -> str:
    """CO2 削減量を読みやすい単位に整形する。"""
    if abs(kg) >= 1_000_000:
        return f"{kg / 1_000_000:.1f}万トン"
    if abs(kg) >= 1_000:
        return f"{kg / 1_000:,.0f}トン"
    return f"{kg:,.0f}kg"


def build_scenario_summary(r: ScenarioSimResult) -> str:
    """ScenarioSimResult から CLO 向けサマリーテキストを生成する。"""
    source_label = (
        "引数指定" if r.measure_selection_source == "explicit"
        else "Step 2 Top 3 自動採用"
    )
    lines: list[str] = [
        f"=== シナリオシミュレーション: {r.company_name} ===",
        f"業種: {r.industry} / 選択施策: {len(r.selected_measures)} 件 ({source_label})",
        "",
        "【選択施策】",
    ]
    for m in r.selected_measures:
        lines.append(
            f"  ・[{m.measure_id}] {m.name}（{m.form3_section}）"
        )
    lines.append("")

    lines.append("【施策組合せの重複処理】")
    overlap_sections = [
        f"{sec} {count} 件"
        for sec, count in r.section_overlap_count.items()
        if count >= 2
    ]
    if overlap_sections:
        lines.append(
            f"  同セクション重複あり ({', '.join(overlap_sections)})"
            f" → 効果合算に {r.synergy_multiplier} 倍を適用（30% ディスカウント）"
        )
    else:
        lines.append(
            "  セクション跨ぎのみ → 倍率 1.0（重複ダンピングなし）"
        )
    lines.append("")

    b = r.baseline
    lines += [
        "【ベースラインシナリオ（標準値中心）】",
        (
            f"  営業利益増加: {_format_yen(b.annual_operating_profit_increase_jpy.standard)}"
            f"/年（保守 {_format_yen(b.annual_operating_profit_increase_jpy.conservative)}"
            f" 〜 上振れ {_format_yen(b.annual_operating_profit_increase_jpy.upside)}）"
        ),
        (
            f"  CO2 削減: {_format_co2(b.annual_co2_reduction_kg.standard)}/年"
            f"（保守 {_format_co2(b.annual_co2_reduction_kg.conservative)}"
            f" 〜 上振れ {_format_co2(b.annual_co2_reduction_kg.upside)}）"
        ),
        f"  必要投資: {_format_yen(b.total_investment_jpy)}",
        (
            f"  5年累積 NPV: {_format_yen(b.five_year_npv_jpy.standard)}"
            f"（保守 {_format_yen(b.five_year_npv_jpy.conservative)}"
            f" 〜 上振れ {_format_yen(b.five_year_npv_jpy.upside)}）"
        ),
        "",
    ]

    lines.append("【What-if ストレステスト（営業利益増・standard 値ベース）】")
    lines.append(
        "  | シナリオ          | 営業利益増(標準)  | 保守             | baseline比 | 堅牢性 |"
    )
    lines.append(
        "  |-------------------|-------------------|------------------|------------|--------|"
    )
    for s in r.stress_scenarios:
        marker = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[s.robustness_level]
        lines.append(
            f"  | {s.scenario.label:<17} "
            f"| {_format_yen(s.annual_operating_profit_increase_jpy.standard):<17} "
            f"| {_format_yen(s.annual_operating_profit_increase_jpy.conservative):<16} "
            f"| {s.operating_profit_ratio_to_baseline * 100:>6.1f}%   "
            f"| {marker}     |"
        )
    lines.append("")

    # フェーズ3.5 完了条件: 燃料 +20% でも黒字維持
    fuel_up = next(
        (s for s in r.stress_scenarios if s.scenario.name == "fuel_up_20"),
        None,
    )
    if fuel_up is not None:
        std_value = fuel_up.annual_operating_profit_increase_jpy.standard
        if std_value > 0:
            lines.append(
                f"  ✅ 燃料 +20% でも黒字維持: 営業利益増 {_format_yen(std_value)}/年"
                f"（baseline 比 {fuel_up.operating_profit_ratio_to_baseline * 100:.1f}%）"
            )
        else:
            lines.append(
                "  ❌ 燃料 +20% で黒字維持できず — 施策見直しが必要"
            )
        lines.append("")

    # 堅牢性総合判定 + 最悪ストレスシナリオ
    levels = [s.robustness_level for s in r.stress_scenarios]
    level_rank = {"green": 0, "yellow": 1, "red": 2}
    worst = max(
        r.stress_scenarios,
        key=lambda s: (
            level_rank[s.robustness_level],
            -s.operating_profit_ratio_to_baseline,
        ),
    )
    if all(level == "green" for level in levels):
        overall = "🟢 全 7 ストレスシナリオで baseline の 70% 以上を維持"
    elif "red" in levels:
        overall = "🔴 一部シナリオで baseline の 50% 未満 — 投資判断却下リスクあり"
    else:
        overall = "🟡 一部シナリオで baseline の 50-70% — 要モニタリング"
    lines += [
        "【堅牢性総合判定】",
        f"  {overall}",
        (
            f"  最悪ストレス: {worst.scenario.label}（baseline 比 "
            f"{worst.operating_profit_ratio_to_baseline * 100:.1f}%）"
        ),
        "",
        "【経営会議向け要約（CFO 質問対応）】",
        (
            f"  ・最低でも保守シナリオで年 "
            f"{_format_yen(r.baseline.annual_operating_profit_increase_jpy.conservative)}"
            f" の営業利益増が見込める"
        ),
        (
            f"  ・最大上振れでは年 "
            f"{_format_yen(r.baseline.annual_operating_profit_increase_jpy.upside)} まで到達"
        ),
        (
            f"  ・必要投資 {_format_yen(r.baseline.total_investment_jpy)} に対し"
            f" 5年累積 NPV(標準) {_format_yen(r.baseline.five_year_npv_jpy.standard)}"
        ),
    ]

    return "\n".join(lines)


__all__ = [
    "ScenarioParameters",
    "ScenarioResult",
    "ScenarioSimResult",
    "ThreeBandValue",
    "build_scenario_summary",
    "simulate_scenarios",
]
