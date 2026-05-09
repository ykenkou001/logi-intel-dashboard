"""物流効率化法 認定事業マッチング。

自社プロフィール（業種カテゴリ・関心施策）から、参考になる認定事業を
スコアリングして上位を返す。CLO 計画書「実施措置」セクションで
「業界の先行事例」として引用するため。

設計方針:
    - 業種カテゴリ完全一致 +3 点
    - 取組タイプ一致 +2 点 / 件
    - 取組タイプ未指定の場合は業種一致のみで評価
    - 上位 5 件を返す（同点は認定年降順）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.export.citation import Citation
from core.static._freshness import all_warnings
from core.static.efficiency_law_certified import (
    CERTIFIED_CASES,
    CertifiedCase,
    IndustryCategory,
    MeasureType,
)
from core.static.jsic import lookup

_RESULT_LIMIT = 5


@dataclass(frozen=True)
class MatchedCase:
    """マッチング結果1件。"""

    case: CertifiedCase
    score: int
    matched_categories: list[str]
    matched_measure_types: list[str]


@dataclass
class CertifiedMatchResult:
    """認定事業マッチング全体結果。"""

    jsic_code: str
    jsic_name: str
    self_category: str
    interested_measure_types: list[str]

    matches: list[MatchedCase] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)


def _score_case(
    case: CertifiedCase,
    self_category: IndustryCategory,
    interested_types: list[MeasureType],
) -> tuple[int, list[str], list[str]]:
    """1事例のスコア + マッチ箇所を返す。"""
    score = 0
    matched_categories: list[str] = []
    matched_types: list[str] = []

    if self_category in case.industry_categories:
        score += 3
        matched_categories.append(self_category)

    for mt in interested_types:
        if mt in case.measure_types:
            score += 2
            matched_types.append(mt)

    return score, matched_categories, matched_types


def find_matches(
    jsic_code: str,
    interested_measure_types: list[str] | None = None,
) -> CertifiedMatchResult:
    """JSIC コードと関心施策から類似する認定事業を検索する。

    Args:
        jsic_code: JSIC 細分類4桁コード
        interested_measure_types: 関心のある取組タイプ（省略時は業種のみで評価）。
            "modal_shift" / "joint_delivery" / "relay_transport" / "berth_booking"
            / "warehouse_dx" / "load_factor" のいずれか

    Returns:
        CertifiedMatchResult

    Raises:
        ValueError: jsic_code が未収録の場合
    """
    entry = lookup(jsic_code)
    if entry is None:
        raise ValueError(
            f"JSIC コード '{jsic_code}' は未収録です。Step 1-5 と同じコードを指定してください。"
        )

    interested_types: list[MeasureType] = list(interested_measure_types or [])  # type: ignore[arg-type]
    self_category: IndustryCategory = entry.category

    scored: list[MatchedCase] = []
    for case in CERTIFIED_CASES:
        score, matched_cats, matched_mt = _score_case(case, self_category, interested_types)
        if score > 0:
            scored.append(
                MatchedCase(
                    case=case,
                    score=score,
                    matched_categories=matched_cats,
                    matched_measure_types=matched_mt,
                )
            )

    # スコア降順 → 認定年降順
    scored.sort(key=lambda m: (m.score, m.case.certified_year), reverse=True)
    top_matches = scored[:_RESULT_LIMIT]

    # 出典は表示順を保ちつつ重複排除
    citations: list[Citation] = []
    seen_urls: set[str] = set()
    for m in top_matches:
        if m.case.source_url not in seen_urls:
            citations.append(
                Citation(
                    label=f"{m.case.title}（物流効率化法 認定事業）",
                    url=m.case.source_url,
                    accessed_via="国交省 認定事業ポータル（静的参照）",
                )
            )
            seen_urls.add(m.case.source_url)

    return CertifiedMatchResult(
        jsic_code=jsic_code,
        jsic_name=entry.name,
        self_category=self_category,
        interested_measure_types=[str(t) for t in interested_types],
        matches=top_matches,
        citations=citations,
        freshness_warnings=all_warnings(),
    )


_MEASURE_TYPE_LABELS: dict[str, str] = {
    "modal_shift": "モーダルシフト",
    "joint_delivery": "共同配送",
    "relay_transport": "中継輸送",
    "berth_booking": "バース予約・荷待ち時間削減",
    "warehouse_dx": "倉庫・配送センター高度化",
    "load_factor": "積載率向上・パレット標準化",
}

_CATEGORY_LABELS: dict[str, str] = {
    "manufacturing": "製造業",
    "wholesale": "卸売業",
    "retail": "小売業",
    "chain_franchise": "連鎖化事業者",
    "transport": "運輸業",
    "other": "その他",
}


def build_certified_match_summary(r: CertifiedMatchResult) -> str:
    """CertifiedMatchResult から CLO 計画書用サマリーを生成する。"""
    self_cat_label = _CATEGORY_LABELS.get(r.self_category, r.self_category)
    interest_label = (
        "、".join(_MEASURE_TYPE_LABELS.get(t, t) for t in r.interested_measure_types)
        if r.interested_measure_types
        else "未指定（業種のみで評価）"
    )

    lines: list[str] = [
        "=== 物流効率化法 認定事業 類似マッチング ===",
        f"自社業種: {r.jsic_name}（{r.jsic_code}）/ {self_cat_label}",
        f"関心施策: {interest_label}",
        "",
    ]

    if not r.matches:
        lines += [
            "【マッチ結果】",
            "  該当する認定事業が見つかりませんでした。",
            "  業種カテゴリまたは関心施策を変更して再試行してください。",
        ]
        return "\n".join(lines)

    lines.append(f"【マッチ上位 {len(r.matches)} 件（スコア降順）】")
    for i, m in enumerate(r.matches, start=1):
        company_str = "、".join(m.case.main_companies)
        mt_str = "、".join(_MEASURE_TYPE_LABELS.get(t, t) for t in m.case.measure_types)
        lines += [
            "",
            f"  {i}. [{m.case.certified_year}年認定 / スコア {m.score}] {m.case.title}",
            f"     主体企業: {company_str}",
            f"     取組タイプ: {mt_str}",
            f"     概要: {m.case.summary}",
            f"     効果: {m.case.headline_effect}",
            f"     出典: {m.case.source_url}",
        ]

    lines += [
        "",
        "【CLO 計画書への反映】",
        "  ・様式第3別紙「実施措置」欄では、上記事例を参考にした取組内容を記載できる",
        "  ・経営会議で「他社はどうしている？」と聞かれたら本リストの主体企業名で回答",
        "  ・スコア高位の事例ほど自社業種・関心施策との合致度が高い",
        "",
        "【補足】",
        "  ・本リストは公表事例から代表 10 件を抽出した暫定サンプル",
        "  ・全件マッチング（数百件）はフェーズ3.5 で CSV 自動取込により対応予定",
    ]

    return "\n".join(lines)
