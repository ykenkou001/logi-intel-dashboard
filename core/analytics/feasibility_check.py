"""実現可能性チェッカー — 施策の実行可否と KPI 到達可能性を判定する。

Step 2（measure_eval）が「相対ランキング」で施策を比較するのに対し、
本モジュールは **絶対的な実行可否（緑/黄/赤）** を判定する。
「この施策はあなたの会社では難しい」を明確に伝える勇気を持つことで、
CLO が無理筋な計画を提出して罰則リスク（勧告→命令→企業名公表）を負わないよう支援する。

設計方針:
    - 各施策に 緑/黄/赤 判定を付与（リソース・規模・難易度の組合せで決定）
    - 連鎖化事業者は荷役等セクション施策を red 固定（仕様で必須でない）
    - KPI 到達可能性として「積載率 38→50%」が指定目標年に届くかを業界実績と比較
    - 「やめておけ」のメッセージは具体的に（経営判断材料として）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from core.analytics.measure_eval import _derive_available_resources
from core.export.citation import (
    Citation,
    co2_factors_citation,
    logistics_efficiency_law_citation,
)
from core.playbook.filters import PlaybookFilter, filter_playbook
from core.playbook.measures import (
    ALL_MEASURES,
    PlaybookMeasure,
    RequiredResource,
)
from core.static._freshness import all_warnings
from core.static.jsic import category_of
from core.static.sample_company import CompanyProfile

VerdictLevel = Literal["green", "yellow", "red"]

# 業界実績ベースの年間積載率改善幅（pp/年）— 国交省「持続可能な物流の実現に向けた検討会」
# 標準的な企業で 1〜2pp/年が現実的レンジ
_INDUSTRY_TYPICAL_LOAD_FACTOR_IMPROVEMENT_PP_PER_YEAR: float = 1.5

# 積載率目標（業界平均 38% → 国交省「目指すべき水準」50%）
_LOAD_FACTOR_BASELINE_PCT: float = 38.0
_LOAD_FACTOR_TARGET_PCT: float = 50.0

# 規模ボーダーライン判定: 施策の min_revenue_jpy / min_freight_tons の ±30% 以内
_BORDERLINE_TOLERANCE_PCT: float = 30.0

# 難易度判定の閾値
_DIFFICULTY_GREEN_MAX: int = 3
_DIFFICULTY_YELLOW_MAX: int = 4
# 5 は red (リソース不足を伴う場合のみ)


@dataclass(frozen=True)
class FeasibilityVerdict:
    """単一施策の実行可否判定。"""

    measure: PlaybookMeasure
    level: VerdictLevel
    primary_reason: str
    """1 文で判定理由（経営層への第一印象）。"""

    detailed_reasons: list[str]
    """詳細判定根拠（複数）。"""

    recommendation: str
    """推奨アクション（「実施推奨」「条件付き実施」「再検討」等）。"""

    missing_resources: list[RequiredResource]


@dataclass(frozen=True)
class TargetReachability:
    """KPI 到達可能性判定。"""

    kpi_name: str
    current_baseline: float
    target_value: float
    target_year: int
    current_year: int

    annual_required_improvement: float
    """年間必要改善幅（pp 等の単位は kpi_name に従う）。"""

    industry_typical_improvement: float
    """業界実績の年間改善幅（業界統計ベース）。"""

    feasibility_level: VerdictLevel
    rationale: str


@dataclass
class FeasibilityResult:
    """実現可能性チェッカー全体結果。"""

    company_id: str
    company_name: str
    industry: str
    target_year: int
    derived_resources: list[RequiredResource]

    measure_verdicts: list[FeasibilityVerdict] = field(default_factory=list)
    kpi_reachability: list[TargetReachability] = field(default_factory=list)

    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0

    overall_message: str = ""

    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


def check_feasibility(
    profile: CompanyProfile,
    target_year: int = 2030,
    available_resources: list[RequiredResource] | None = None,
) -> FeasibilityResult:
    """施策の実行可否と KPI 到達可能性を判定する。

    Args:
        profile: 自社プロフィール
        target_year: KPI 達成目標年（デフォルト 2030 年 = 計画期間終了）
        available_resources: 自社が保有するリソース。None なら自動推定

    Returns:
        FeasibilityResult: 施策別 verdict + KPI 到達可能性 + 全体メッセージ
    """
    industry = category_of(profile.jsic_code) or "other"
    resources = (
        available_resources
        if available_resources is not None
        else _derive_available_resources(profile)
    )
    is_chain = profile.is_chain_franchise

    # まず業種・規模で適用可能な施策を抽出
    eligible = filter_playbook(
        filter_=PlaybookFilter(
            industry=industry,
            revenue_jpy=profile.annual_revenue_jpy,
            freight_tons=profile.annual_freight_tons_total,
        )
    )

    # 適用外施策も含めて全施策に verdict を付与（除外理由を明示するため）
    verdicts: list[FeasibilityVerdict] = []
    eligible_ids = {m.measure_id for m in eligible}
    for m in ALL_MEASURES:
        verdicts.append(
            _assess_measure(
                measure=m,
                profile=profile,
                available_resources=resources,
                is_eligible_by_scale=m.measure_id in eligible_ids,
                is_chain=is_chain,
            )
        )

    # KPI 到達可能性
    kpi_reachability = [
        _assess_load_factor_reachability(target_year=target_year),
    ]

    green = sum(1 for v in verdicts if v.level == "green")
    yellow = sum(1 for v in verdicts if v.level == "yellow")
    red = sum(1 for v in verdicts if v.level == "red")

    overall = _build_overall_message(green, yellow, red, kpi_reachability)

    return FeasibilityResult(
        company_id=profile.company_id,
        company_name=profile.name,
        industry=industry,
        target_year=target_year,
        derived_resources=resources,
        measure_verdicts=verdicts,
        kpi_reachability=kpi_reachability,
        green_count=green,
        yellow_count=yellow,
        red_count=red,
        overall_message=overall,
        citations=[
            logistics_efficiency_law_citation(),
            co2_factors_citation(),
        ],
        freshness_warnings=all_warnings(),
    )


def _assess_measure(
    measure: PlaybookMeasure,
    profile: CompanyProfile,
    available_resources: list[RequiredResource],
    is_eligible_by_scale: bool,
    is_chain: bool,
) -> FeasibilityVerdict:
    """単一施策の実行可否を判定する。"""
    available_set = set(available_resources)
    missing = [r for r in measure.required_resources if r not in available_set]
    detailed: list[str] = []

    # 連鎖化事業者の荷役等セクション施策は red 固定
    if is_chain and measure.form3_section == "loading":
        return FeasibilityVerdict(
            measure=measure,
            level="red",
            primary_reason="連鎖化事業者は荷役等時間短縮セクションが必須でない（実施しない方が合理的）",
            detailed_reasons=[
                "様式第3「第5条関係」では荷役等時間短縮の記載は不要",
                "リソースを必須2項目（積載率向上・荷待ち時間短縮）に集中投下すべき",
            ],
            recommendation="再検討（荷主向け施策にリソース転用）",
            missing_resources=missing,
        )

    # 適用外（業種・規模・取扱量のいずれかが合わない）→ red
    if not is_eligible_by_scale:
        return _build_ineligible_verdict(measure, profile, missing)

    # ボーダーライン規模判定（min から +30% 以内なら yellow 候補）
    is_borderline = _is_borderline_scale(measure, profile)

    # リソース不足の重み付け
    if len(missing) >= 3:
        return FeasibilityVerdict(
            measure=measure,
            level="red",
            primary_reason=f"必要リソース {len(missing)} 件不足",
            detailed_reasons=[
                f"不足リソース: {', '.join(missing)}",
                "リソース整備に追加投資・組織変更が必要",
            ],
            recommendation="まずリソース整備（前提施策の visualization_baseline 等）から着手",
            missing_resources=missing,
        )

    # 難易度 5 + リソース不足 → red
    if measure.implementation_difficulty == 5 and missing:
        return FeasibilityVerdict(
            measure=measure,
            level="red",
            primary_reason="高難易度かつ前提リソース不足",
            detailed_reasons=[
                f"難易度: {measure.implementation_difficulty}/5",
                f"不足リソース: {', '.join(missing)}",
            ],
            recommendation="他社事例ヒアリング・コンサル支援検討。単独実施は推奨しない",
            missing_resources=missing,
        )

    # 難易度 5（リソース充足）→ yellow
    if measure.implementation_difficulty == 5:
        return FeasibilityVerdict(
            measure=measure,
            level="yellow",
            primary_reason="高難易度（合意形成・調整負荷大）",
            detailed_reasons=[
                f"難易度: {measure.implementation_difficulty}/5",
                "失敗パターン: " + "; ".join(measure.common_pitfalls[:2]),
            ],
            recommendation="条件付き実施（推進体制・KPI モニタリング必須）",
            missing_resources=missing,
        )

    # リソース 1-2 件不足 → yellow
    if missing:
        return FeasibilityVerdict(
            measure=measure,
            level="yellow",
            primary_reason=f"前提リソース {len(missing)} 件不足（取得可能範囲）",
            detailed_reasons=[
                f"不足リソース: {', '.join(missing)}",
                "リソース整備と並行して着手可能",
            ],
            recommendation="条件付き実施（不足リソースの取得計画を計画書に明記）",
            missing_resources=missing,
        )

    # ボーダーライン規模 → yellow
    if is_borderline:
        return FeasibilityVerdict(
            measure=measure,
            level="yellow",
            primary_reason="自社規模が施策の最小推奨レンジ近傍（投資効率に注意）",
            detailed_reasons=[
                f"自社売上 {profile.annual_revenue_jpy / 1e8:.1f}億円 vs "
                f"推奨最小 {_fmt_yen(measure.min_revenue_jpy)}",
                "規模の経済が効きにくい可能性",
            ],
            recommendation="条件付き実施（パイロット拠点で効果検証してから全社展開）",
            missing_resources=missing,
        )

    # 難易度 4 → yellow
    if measure.implementation_difficulty == _DIFFICULTY_YELLOW_MAX:
        return FeasibilityVerdict(
            measure=measure,
            level="yellow",
            primary_reason=f"中〜高難易度（{measure.implementation_difficulty}/5）",
            detailed_reasons=[
                "計画的な投資・推進体制が必須",
                "失敗パターン: " + "; ".join(measure.common_pitfalls[:2]),
            ],
            recommendation="条件付き実施（フェーズ分けで段階展開）",
            missing_resources=missing,
        )

    # ここまで来れば green（難易度 ≤3 + リソース充足 + 規模適合）
    detailed.append(f"難易度 {measure.implementation_difficulty}/5（実施容易）")
    detailed.append("前提リソース充足")
    detailed.append("規模適合性 OK")
    if measure.eligible_subsidies:
        detailed.append(f"補助金あり: {measure.eligible_subsidies[0]}")

    return FeasibilityVerdict(
        measure=measure,
        level="green",
        primary_reason="リソース・規模・難易度のいずれもクリア",
        detailed_reasons=detailed,
        recommendation="実施推奨（CLO 計画書の主軸施策に採用可）",
        missing_resources=missing,
    )


def _build_ineligible_verdict(
    measure: PlaybookMeasure,
    profile: CompanyProfile,
    missing: list[RequiredResource],
) -> FeasibilityVerdict:
    """filter_playbook で除外された施策の red verdict を構築する。

    除外理由を 業種非適合 / 売上未達 / 取扱量未達 のいずれかに分類する。
    """
    industry = category_of(profile.jsic_code) or "other"

    # 1. 業種非適合
    if measure.applicable_industries and industry not in measure.applicable_industries:
        return FeasibilityVerdict(
            measure=measure,
            level="red",
            primary_reason=(f"業種非適合（自社業種 {industry} は施策の対象外）"),
            detailed_reasons=[
                f"施策の対象業種: {', '.join(measure.applicable_industries)}",
                f"自社業種: {industry}",
                "業種特性に合わないため、無理に実施しても効果発現が見込みにくい",
            ],
            recommendation="再検討（自社業種に適した別施策を選定）",
            missing_resources=missing,
        )

    # 2. 売上未達
    if measure.min_revenue_jpy is not None and profile.annual_revenue_jpy < measure.min_revenue_jpy:
        return FeasibilityVerdict(
            measure=measure,
            level="red",
            primary_reason=(
                f"売上未達（自社 {profile.annual_revenue_jpy / 1e8:.1f}億円 < "
                f"推奨最小 {measure.min_revenue_jpy / 1e8:.1f}億円）"
            ),
            detailed_reasons=[
                f"施策の最小推奨売上: {_fmt_yen(measure.min_revenue_jpy)}",
                f"自社売上: {profile.annual_revenue_jpy / 1e8:.1f}億円",
                "投資対効果が見込みにくい規模",
            ],
            recommendation="自社規模では効果発現が限定的。別の規模適合施策を検討",
            missing_resources=missing,
        )

    # 3. 取扱量未達
    if (
        measure.min_freight_tons is not None
        and profile.annual_freight_tons_total < measure.min_freight_tons
    ):
        return FeasibilityVerdict(
            measure=measure,
            level="red",
            primary_reason=(
                f"取扱量未達（自社 {profile.annual_freight_tons_total:,.0f}トン < "
                f"推奨最小 {measure.min_freight_tons:,.0f}トン）"
            ),
            detailed_reasons=[
                f"施策の最小推奨取扱量: {_fmt_tons(measure.min_freight_tons)}",
                f"自社取扱量: {profile.annual_freight_tons_total:,.0f}トン",
                "輸送量の規模が施策効果のしきい値に達していない",
            ],
            recommendation="再検討（取扱量に応じた小規模向け施策を選定）",
            missing_resources=missing,
        )

    # その他（理論上ここに来ないはずだが防御的に）
    return FeasibilityVerdict(
        measure=measure,
        level="red",
        primary_reason="プレイブックフィルタで除外（理由不明）",
        detailed_reasons=["filter_playbook と _build_ineligible_verdict の判定ロジック差異"],
        recommendation="再検討（評価ロジックの確認が必要）",
        missing_resources=missing,
    )


def _is_borderline_scale(
    measure: PlaybookMeasure,
    profile: CompanyProfile,
) -> bool:
    """規模が施策の min から +30% 以内ならボーダーライン判定。"""
    if measure.min_revenue_jpy:
        upper = measure.min_revenue_jpy * (1.0 + _BORDERLINE_TOLERANCE_PCT / 100.0)
        if measure.min_revenue_jpy <= profile.annual_revenue_jpy <= upper:
            return True
    if measure.min_freight_tons:
        upper = measure.min_freight_tons * (1.0 + _BORDERLINE_TOLERANCE_PCT / 100.0)
        if measure.min_freight_tons <= profile.annual_freight_tons_total <= upper:
            return True
    return False


def _assess_load_factor_reachability(target_year: int) -> TargetReachability:
    """積載率 38→50% 目標の到達可能性を業界実績と比較する。"""
    current_year = 2026  # 計画書提出年
    years_remaining = max(target_year - current_year, 1)
    required_improvement = (_LOAD_FACTOR_TARGET_PCT - _LOAD_FACTOR_BASELINE_PCT) / years_remaining

    industry_typical = _INDUSTRY_TYPICAL_LOAD_FACTOR_IMPROVEMENT_PP_PER_YEAR

    if required_improvement <= industry_typical:
        level: VerdictLevel = "green"
        rationale = (
            f"年間必要改善 {required_improvement:.1f}pp は業界実績 "
            f"{industry_typical:.1f}pp/年の範囲内。実現可能"
        )
    elif required_improvement <= industry_typical * 2:
        level = "yellow"
        rationale = (
            f"年間必要改善 {required_improvement:.1f}pp は業界実績 "
            f"{industry_typical:.1f}pp/年の 1〜2 倍。複数施策の同時実施で達成余地"
        )
    else:
        level = "red"
        rationale = (
            f"年間必要改善 {required_improvement:.1f}pp は業界実績 "
            f"{industry_typical:.1f}pp/年の 2 倍超。目標年の延長または"
            "目標値の見直しを推奨"
        )

    return TargetReachability(
        kpi_name=f"積載率向上（{_LOAD_FACTOR_BASELINE_PCT:.0f}%→{_LOAD_FACTOR_TARGET_PCT:.0f}%）",
        current_baseline=_LOAD_FACTOR_BASELINE_PCT,
        target_value=_LOAD_FACTOR_TARGET_PCT,
        target_year=target_year,
        current_year=current_year,
        annual_required_improvement=required_improvement,
        industry_typical_improvement=industry_typical,
        feasibility_level=level,
        rationale=rationale,
    )


def _build_overall_message(
    green: int,
    yellow: int,
    red: int,
    kpi_reachability: list[TargetReachability],
) -> str:
    """全体メッセージを生成する。"""
    parts: list[str] = [f"実施推奨 {green} 件 / 条件付き {yellow} 件 / 再検討 {red} 件"]
    if green == 0:
        parts.append(
            "⚠️ 緑判定の施策がゼロ。リソース整備（visualization_baseline 等）から着手すべき",
        )
    elif green >= 5:
        parts.append("十分な施策数が緑判定。CLO 計画書の充実度は高い")

    for kpi in kpi_reachability:
        if kpi.feasibility_level == "red":
            parts.append(
                f"❌ KPI「{kpi.kpi_name}」が目標年 {kpi.target_year} に到達困難 "
                "→ 目標年延長または目標値の見直しを推奨"
            )
        elif kpi.feasibility_level == "yellow":
            parts.append(f"⚠️ KPI「{kpi.kpi_name}」は複数施策の同時実施が必須")

    return " / ".join(parts)


def _fmt_yen(jpy: int | None) -> str:
    if jpy is None:
        return "制約なし"
    return f"{jpy / 1e8:.1f}億円"


def _fmt_tons(tons: float | None) -> str:
    if tons is None:
        return "制約なし"
    return f"{tons:,.0f}トン"


def build_feasibility_summary(r: FeasibilityResult) -> str:
    """FeasibilityResult から CLO 向けサマリーテキストを生成する。"""
    lines: list[str] = [
        f"=== 実現可能性チェック: {r.company_name} ===",
        f"業種: {r.industry} / 目標年: {r.target_year} / "
        f"推定リソース: {', '.join(r.derived_resources) or '（なし）'}",
        "",
        f"【全体判定】 {r.overall_message}",
        "",
    ]

    level_marks = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    section_labels = {
        "load": "積載率向上",
        "wait": "荷待ち時間短縮",
        "loading": "荷役等時間短縮",
    }

    # 緑 → 黄 → 赤 の順で表示
    for level in ("green", "yellow", "red"):
        verdicts = [v for v in r.measure_verdicts if v.level == level]
        if not verdicts:
            continue
        label = {"green": "実施推奨", "yellow": "条件付き実施", "red": "再検討"}[level]
        lines.append(f"【{level_marks[level]} {label}（{len(verdicts)} 件）】")
        for v in verdicts:
            section = section_labels.get(v.measure.form3_section, v.measure.form3_section)
            lines.append(
                f"  {level_marks[level]} [{v.measure.measure_id}] {v.measure.name}"
                f"  ({section} / 難易度 {v.measure.implementation_difficulty}/5)"
            )
            lines.append(f"     判定理由: {v.primary_reason}")
            lines.append(f"     推奨アクション: {v.recommendation}")
            for d in v.detailed_reasons[:3]:
                lines.append(f"       - {d}")
        lines.append("")

    lines.append("【KPI 到達可能性】")
    for k in r.kpi_reachability:
        mark = level_marks[k.feasibility_level]
        lines.append(f"  {mark} {k.kpi_name}")
        lines.append(
            f"     現状 {k.current_baseline:.0f} → 目標 {k.target_value:.0f}"
            f"（目標年 {k.target_year}・残り {k.target_year - k.current_year} 年）"
        )
        lines.append(
            f"     年間必要改善 {k.annual_required_improvement:.1f}pp vs "
            f"業界実績 {k.industry_typical_improvement:.1f}pp/年"
        )
        lines.append(f"     {k.rationale}")

    return "\n".join(lines)
