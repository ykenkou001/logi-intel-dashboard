"""プレイブック施策のフィルタリング・検索機能。

自社プロフィールや絞り込み条件から適用候補施策を抽出する。
Step 2（評価エンジン）と Step 5（実現可能性チェッカー）で利用される。
"""

from __future__ import annotations

from dataclasses import dataclass

from core.export.formatter import format_jpy
from core.playbook.measures import (
    ALL_MEASURES,
    Form3Section,
    PlaybookMeasure,
    RequiredResource,
)
from core.static.efficiency_law_certified import IndustryCategory, MeasureType


@dataclass(frozen=True)
class PlaybookFilter:
    """プレイブック検索の絞り込み条件。

    全フィールド None なら全施策が対象。指定したフィールドのみが AND 条件として適用される。
    """

    industry: IndustryCategory | None = None
    """業種カテゴリで絞り込む。"""

    revenue_jpy: int | None = None
    """自社売上（円）。施策の min_revenue_jpy 以上であるものを返す。"""

    freight_tons: float | None = None
    """自社年間取扱量（トン）。施策の min_freight_tons 以上であるものを返す。"""

    available_resources: list[RequiredResource] | None = None
    """自社が保有するリソース。施策の required_resources を全て満たすものを返す。"""

    max_difficulty: int | None = None
    """許容する最大実装難易度（1-5）。これ以下のもののみ返す。"""

    measure_type: MeasureType | None = None
    """取組タイプで絞り込む（modal_shift / load_factor 等）。"""

    form3_section: Form3Section | None = None
    """様式第3 セクションで絞り込む（load / wait / loading）。"""


def filter_playbook(
    measures: list[PlaybookMeasure] | None = None,
    filter_: PlaybookFilter | None = None,
) -> list[PlaybookMeasure]:
    """フィルタ条件に合致する施策を抽出する。

    Args:
        measures: 検索対象施策。None なら ALL_MEASURES を使用
        filter_: 絞り込み条件。None なら全件返す

    Returns:
        合致する施策のリスト（元順序を保持）
    """
    source = measures if measures is not None else ALL_MEASURES
    if filter_ is None:
        return list(source)

    result: list[PlaybookMeasure] = []
    for m in source:
        if (
            filter_.industry is not None
            and m.applicable_industries
            and filter_.industry not in m.applicable_industries
        ):
            continue
        if (
            filter_.revenue_jpy is not None
            and m.min_revenue_jpy is not None
            and filter_.revenue_jpy < m.min_revenue_jpy
        ):
            continue
        if (
            filter_.freight_tons is not None
            and m.min_freight_tons is not None
            and filter_.freight_tons < m.min_freight_tons
        ):
            continue
        if filter_.available_resources is not None and m.required_resources:
            available = set(filter_.available_resources)
            if not set(m.required_resources).issubset(available):
                continue
        if (
            filter_.max_difficulty is not None
            and m.implementation_difficulty > filter_.max_difficulty
        ):
            continue
        if filter_.measure_type is not None and m.measure_type != filter_.measure_type:
            continue
        if filter_.form3_section is not None and m.form3_section != filter_.form3_section:
            continue
        result.append(m)
    return result


def build_filter_from_profile(
    industry: IndustryCategory,
    revenue_jpy: int,
    freight_tons: float,
    available_resources: list[RequiredResource] | None = None,
    max_difficulty: int | None = None,
) -> PlaybookFilter:
    """自社プロフィールから標準的なフィルタを組み立てる。

    Step 2 評価エンジンの初期スクリーニングで利用想定。
    """
    return PlaybookFilter(
        industry=industry,
        revenue_jpy=revenue_jpy,
        freight_tons=freight_tons,
        available_resources=available_resources,
        max_difficulty=max_difficulty,
    )


def build_search_summary(
    measures: list[PlaybookMeasure],
    filter_: PlaybookFilter | None = None,
) -> str:
    """検索結果のサマリーテキストを生成する（MCP ツール向け）。"""
    if not measures:
        return "=== プレイブック検索結果: 該当施策なし ===\n条件を緩和してください。"

    lines: list[str] = [
        f"=== プレイブック検索結果: {len(measures)} 件 ===",
    ]
    if filter_ is not None:
        cond_parts: list[str] = []
        if filter_.industry:
            cond_parts.append(f"業種={filter_.industry}")
        if filter_.revenue_jpy:
            cond_parts.append(f"売上≧{format_jpy(filter_.revenue_jpy)}")
        if filter_.freight_tons:
            cond_parts.append(f"取扱量≧{filter_.freight_tons:,.0f}トン")
        if filter_.max_difficulty:
            cond_parts.append(f"難易度≦{filter_.max_difficulty}")
        if filter_.form3_section:
            cond_parts.append(f"セクション={filter_.form3_section}")
        if cond_parts:
            lines.append(f"  条件: {' / '.join(cond_parts)}")
    lines.append("")

    section_labels = {
        "load": "Ⅱ 積載率向上",
        "wait": "Ⅲ 荷待ち時間短縮",
        "loading": "Ⅳ 荷役等時間短縮",
    }

    for m in measures:
        section_label = section_labels.get(m.form3_section, m.form3_section)
        invest_low = format_jpy(
            m.typical_investment_jpy_low, unit="man", digits=0, thousand_sep=True
        )
        invest_high = format_jpy(
            m.typical_investment_jpy_high, unit="man", digits=0, thousand_sep=True
        )
        co2_str = (
            f"CO2 ▲{m.expected_co2_reduction_pct:.0f}%"
            if m.expected_co2_reduction_pct is not None
            else "CO2 効果限定的"
        )
        cost_str = (
            f"コスト ▲{m.expected_cost_reduction_pct:.0f}%"
            if m.expected_cost_reduction_pct is not None
            else "コスト効果なし"
        )
        payback_str = (
            f"回収{m.typical_payback_years:.1f}年"
            if m.typical_payback_years is not None
            else "回収試算外"
        )
        lines += [
            f"◆ [{m.measure_id}] {m.name}",
            f"  分類: {section_label} / 難易度 {m.implementation_difficulty}/5",
            f"  投資: {invest_low}〜{invest_high}",
            f"  期待効果: {co2_str} / {cost_str} / {payback_str}",
            f"  概要: {m.description}",
        ]
        if m.eligible_subsidies:
            lines.append(f"  補助金: {', '.join(m.eligible_subsidies)}")
        if m.success_case_ids:
            lines.append(f"  成功事例: {', '.join(m.success_case_ids)}")
        if m.common_pitfalls:
            lines.append("  失敗パターン:")
            for p in m.common_pitfalls:
                lines.append(f"    - {p}")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "PlaybookFilter",
    "build_filter_from_profile",
    "build_search_summary",
    "filter_playbook",
]
