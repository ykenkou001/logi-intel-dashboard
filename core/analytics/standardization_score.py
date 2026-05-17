"""F2 標準化スコア — 業種別 CLO 標準パッケージへの準拠度を 0-100 で評価する。

業種別 IndustryPackage（c.1〜c.3 で構築）に対して、個社が
    - 標準 KPI / 施策をどれだけ実装しているか（coverage）
    - 標準からの逸脱がどれだけあるか（deviation）
を統合した「標準化スコア」を返す。

設計方針（plans/b-c-flickering-pixel.md §段階 c.6 F2 完全反映）:
    - 減点対象は OverrideCategory="unmanaged_deviation" のみ（Codex 勧告④）
        * approved_better_practice / required_localization は減点なし
        * temporary_exception は期限切れのみ減点
    - 「実装済」の判定:
        * KPI: profile.kpi_history に該当 metric_id の履歴が 1 件以上
        * 施策: Override の target_kind="measure" かつ
                category in {"approved_better_practice", "required_localization"}
          を「採用済」とみなす（暫定。decision_log 連動は別 PR）
    - スコア式:
        coverage_pct = (実装済 KPI 数 + 実装済 施策数)
                       / (標準 KPI 総数 + 標準 施策総数) × 100
        deviation_penalty = 5pt × unmanaged 件数
                          + 3pt × 期限切れ temporary_exception 件数
        bonus = +5pt （approved_better_practice ≥ 2 件）
        score = max(0, min(100, coverage - penalty + bonus))

Codex 勧告で取り下げた点:
    - 「全 必須 KPI 実装 + 月次会議定着 → +10pt」の bonus は判定根拠が
      profile に乗らないため未実装。decision_log/会議出席率と連動できる
      ようになった段階で再導入予定。
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from core.export.citation import Citation, logistics_efficiency_law_citation
from core.playbook.industry_packages import (
    CHAIN_FRANCHISE_FORBIDDEN_FORM3_SECTIONS,
    CompanyPackageOverride,
    IndustryPackage,
    OverrideEntry,
    get_package,
)
from core.static._freshness import all_warnings
from core.static.jsic import JsicCategory, category_of
from core.static.sample_company import CompanyProfile

# ---------------------------------------------------------------------------
# 減点・加点の定数（Codex 議論で確定。境界条件テストで単調性を保証）
# ---------------------------------------------------------------------------

UNMANAGED_PENALTY_PER_ENTRY: float = 5.0
"""unmanaged_deviation 1 件あたりの減点 (pt)。"""

EXPIRED_TEMPORARY_PENALTY_PER_ENTRY: float = 3.0
"""期限切れ temporary_exception 1 件あたりの減点 (pt)。"""

APPROVED_PRACTICE_BONUS: float = 5.0
"""approved_better_practice ≥ 2 件で加点 (pt)。"""

APPROVED_PRACTICE_BONUS_MIN_COUNT: int = 2
"""bonus が発火する approved_better_practice の最低件数。"""


# ---------------------------------------------------------------------------
# 戻り値モデル
# ---------------------------------------------------------------------------


class StandardizationScoreResult(BaseModel):
    """F2 標準化スコアの結果。

    coverage_pct と各 deviation 件数を分離して返すことで、
    UI 側で「coverage で○、deviation で×」の説明がつくようにする。
    """

    model_config = ConfigDict(frozen=True)

    company_id: str
    base_package_category: JsicCategory
    coverage_pct: float = Field(
        description="標準パッケージの KPI/施策実装率 (0-100)",
    )
    deviation_count_unmanaged: int = Field(
        description="減点対象の unmanaged_deviation 件数",
    )
    deviation_count_total: int = Field(
        description="全 Override 件数（カテゴリ問わず）",
    )
    chain_franchise_loading_misuse_count: int = Field(
        default=0,
        description=(
            "連鎖化向けの追加減点件数（c.8）。Override で採用した施策が "
            "form3_section='loading' の場合に発火し、unmanaged 同等で減点する"
        ),
    )
    missing_kpi_ids: list[str] = Field(
        default_factory=list,
        description="標準 KPI のうち kpi_history に履歴が無い metric_id 一覧",
    )
    missing_measure_ids: list[str] = Field(
        default_factory=list,
        description="標準施策のうち未採用 (Override 不在) の measure_id 一覧",
    )
    score: float = Field(
        ge=0.0,
        le=100.0,
        description="標準化スコア (0-100、coverage - penalty + bonus)",
    )
    rationale: list[str] = Field(
        default_factory=list,
        description="スコア算出の説明 (UI 表示用)",
    )
    citations: list[Citation] = Field(default_factory=list)
    freshness_warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_standardization_score(
    profile: CompanyProfile,
    override: CompanyPackageOverride | None = None,
    *,
    today: date | None = None,
) -> StandardizationScoreResult:
    """F2 標準化スコアを算出する。

    Args:
        profile: 自社プロフィール (kpi_history で KPI 実装状況を判定)
        override: 個社差分 (None なら base パッケージのみ)
        today: 期限切れ判定の基準日 (None なら今日)

    Returns:
        StandardizationScoreResult: スコア + 不足 KPI/施策一覧 + 説明

    Raises:
        ValueError: profile.jsic_code から業種が解決できない場合
    """
    today_d = today or date.today()
    base_industry = category_of(profile.jsic_code)
    if base_industry is None or base_industry == "other":
        raise ValueError(
            f"jsic_code={profile.jsic_code!r} から CLO 標準パッケージの業種を解決できない",
        )
    pkg = get_package(base_industry)
    if pkg is None:
        raise ValueError(
            f"業種 {base_industry!r} に対応する IndustryPackage が未定義",
        )

    entries = list(override.entries) if override is not None else []

    implemented_kpi_ids = _implemented_kpi_ids(profile, pkg)
    missing_kpi_ids = sorted(
        {k.metric_id for k in pkg.kpis} - implemented_kpi_ids,
    )

    implemented_measure_ids = _implemented_measure_ids(pkg, entries)
    missing_measure_ids = sorted(
        set(pkg.measure_ids) - implemented_measure_ids,
    )

    coverage_pct = _coverage_pct(
        implemented_kpis=len(implemented_kpi_ids),
        implemented_measures=len(implemented_measure_ids),
        package=pkg,
    )

    unmanaged_count = sum(1 for e in entries if e.category == "unmanaged_deviation")
    expired_count = sum(
        1
        for e in entries
        if e.category == "temporary_exception"
        and e.expires_at is not None
        and e.expires_at < today_d
    )
    approved_count = sum(1 for e in entries if e.category == "approved_better_practice")
    chain_loading_misuse = _chain_franchise_loading_misuse_count(
        base_industry,
        entries,
    )

    penalty = (
        UNMANAGED_PENALTY_PER_ENTRY * unmanaged_count
        + EXPIRED_TEMPORARY_PENALTY_PER_ENTRY * expired_count
        + UNMANAGED_PENALTY_PER_ENTRY * chain_loading_misuse
    )
    bonus = APPROVED_PRACTICE_BONUS if approved_count >= APPROVED_PRACTICE_BONUS_MIN_COUNT else 0.0

    raw_score = coverage_pct - penalty + bonus
    score = max(0.0, min(100.0, raw_score))

    rationale = _build_rationale(
        package=pkg,
        coverage_pct=coverage_pct,
        unmanaged=unmanaged_count,
        expired=expired_count,
        approved=approved_count,
        chain_loading_misuse=chain_loading_misuse,
        penalty=penalty,
        bonus=bonus,
        score=score,
        missing_kpi_count=len(missing_kpi_ids),
        missing_measure_count=len(missing_measure_ids),
    )

    return StandardizationScoreResult(
        company_id=profile.company_id,
        base_package_category=base_industry,
        coverage_pct=round(coverage_pct, 2),
        deviation_count_unmanaged=unmanaged_count,
        deviation_count_total=len(entries),
        chain_franchise_loading_misuse_count=chain_loading_misuse,
        missing_kpi_ids=missing_kpi_ids,
        missing_measure_ids=missing_measure_ids,
        score=round(score, 2),
        rationale=rationale,
        citations=[logistics_efficiency_law_citation()],
        freshness_warnings=all_warnings(),
    )


def build_standardization_summary(result: StandardizationScoreResult) -> str:
    """経営層向けの 1 段落サマリー。"""
    lines = [
        f"標準化スコア: {result.score:.1f}/100 "
        f"(coverage {result.coverage_pct:.0f}% / "
        f"unmanaged {result.deviation_count_unmanaged} 件)",
    ]
    if result.chain_franchise_loading_misuse_count > 0:
        lines.append(
            f"⚠️ 連鎖化で loading 系施策誤用: {result.chain_franchise_loading_misuse_count} 件",
        )
    if result.missing_kpi_ids:
        lines.append(
            f"未計測 KPI: {len(result.missing_kpi_ids)} 件 "
            f"({', '.join(result.missing_kpi_ids[:3])}"
            f"{'…' if len(result.missing_kpi_ids) > 3 else ''})",
        )
    if result.missing_measure_ids:
        lines.append(
            f"未採用 施策: {len(result.missing_measure_ids)} 件 "
            f"({', '.join(result.missing_measure_ids[:3])}"
            f"{'…' if len(result.missing_measure_ids) > 3 else ''})",
        )
    return " / ".join(lines)


# ---------------------------------------------------------------------------
# 内部ヘルパ
# ---------------------------------------------------------------------------


def _implemented_kpi_ids(
    profile: CompanyProfile,
    package: IndustryPackage,
) -> set[str]:
    """kpi_history に履歴が 1 件以上ある KPI の metric_id 集合。"""
    history_metric_ids = {entry.metric for entry in profile.kpi_history}
    package_metric_ids = {k.metric_id for k in package.kpis}
    return package_metric_ids & history_metric_ids


def _implemented_measure_ids(
    package: IndustryPackage,
    entries: list[OverrideEntry],
) -> set[str]:
    """採用済とみなす measure_id の集合。

    暫定ルール: target_kind="measure" かつ category が
    approved_better_practice / required_localization のものを採用済とみなす。

    Tier S1（フェーズ 5.5）で `core/io/decision_log_store.query_decision_log_entries()`
    が利用可能になったが、本モジュールでは未連携。F2 算定ロジック側で
    DecisionLogEntry.selected_measures / rejected_measures から bonus/penalty を
    算出する変更は別 PR で `compute_standardization_score` の入力・F2 計算・テストを
    まとめて行う。
    """
    adopted_categories = {"approved_better_practice", "required_localization"}
    package_ids = set(package.measure_ids)
    return {
        e.target_id
        for e in entries
        if e.target_kind == "measure"
        and e.category in adopted_categories
        and e.target_id in package_ids
    }


def _chain_franchise_loading_misuse_count(
    base_industry: JsicCategory,
    entries: list[OverrideEntry],
) -> int:
    """連鎖化向けの追加減点用カウント（c.8）。

    Override で target_kind="measure" の施策が approved_better_practice /
    required_localization で適用されても、その施策が form3_section="loading"
    なら連鎖化では無効（様式第3 第5条関係に乗らない）ため unmanaged 同等で
    減点する。製造/卸/小売では常に 0。
    """
    if base_industry != "chain_franchise":
        return 0

    # 循環 import 回避のため遅延 import
    from core.playbook.measures import get_measure

    adopted_categories = {"approved_better_practice", "required_localization"}
    count = 0
    for entry in entries:
        if entry.target_kind != "measure":
            continue
        if entry.category not in adopted_categories:
            continue
        measure = get_measure(entry.target_id)
        if measure is None:
            continue
        if measure.form3_section in CHAIN_FRANCHISE_FORBIDDEN_FORM3_SECTIONS:
            count += 1
    return count


def _coverage_pct(
    *,
    implemented_kpis: int,
    implemented_measures: int,
    package: IndustryPackage,
) -> float:
    """coverage_pct = (実装済 KPI + 実装済 施策) / (標準 KPI + 標準 施策) × 100。

    分母 0 のケースは現状あり得ない（4 業種すべて KPI/施策 ≥1 件）が、
    防御的に 0.0 を返す。
    """
    denominator = len(package.kpis) + len(package.measure_ids)
    if denominator == 0:
        return 0.0
    return (implemented_kpis + implemented_measures) / denominator * 100.0


def _build_rationale(
    *,
    package: IndustryPackage,
    coverage_pct: float,
    unmanaged: int,
    expired: int,
    approved: int,
    chain_loading_misuse: int,
    penalty: float,
    bonus: float,
    score: float,
    missing_kpi_count: int,
    missing_measure_count: int,
) -> list[str]:
    """スコア算出の説明（UI 表示）。"""
    deviation_line = (
        f"deviation: unmanaged {unmanaged} 件 × "
        f"{UNMANAGED_PENALTY_PER_ENTRY:.0f}pt + "
        f"期限切れ temporary {expired} 件 × "
        f"{EXPIRED_TEMPORARY_PENALTY_PER_ENTRY:.0f}pt"
    )
    if chain_loading_misuse > 0:
        deviation_line += (
            f" + 連鎖化 loading 誤用 {chain_loading_misuse} 件 × "
            f"{UNMANAGED_PENALTY_PER_ENTRY:.0f}pt"
        )
    deviation_line += f" = -{penalty:.0f}pt"
    return [
        f"基準パッケージ: {package.label} (KPI {len(package.kpis)} 件 / "
        f"施策 {len(package.measure_ids)} 件)",
        f"coverage {coverage_pct:.1f}% "
        f"(未計測 KPI {missing_kpi_count} 件 / 未採用 施策 {missing_measure_count} 件)",
        deviation_line,
        f"approved_better_practice {approved} 件 → bonus +{bonus:.0f}pt"
        + (" (≥2 件で発火)" if approved < APPROVED_PRACTICE_BONUS_MIN_COUNT else ""),
        f"最終スコア: {score:.1f}/100 (max(0, min(100, coverage - penalty + bonus)))",
    ]


__all__ = [
    "APPROVED_PRACTICE_BONUS",
    "APPROVED_PRACTICE_BONUS_MIN_COUNT",
    "EXPIRED_TEMPORARY_PENALTY_PER_ENTRY",
    "UNMANAGED_PENALTY_PER_ENTRY",
    "StandardizationScoreResult",
    "build_standardization_summary",
    "compute_standardization_score",
]
