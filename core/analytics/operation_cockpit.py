"""J3 デイリーコックピット（CLO 今日の3判断）のデータモデルと統合エンジン。

CLO が朝 1 回開けば「未達 KPI ／ 放置リスク ／ 今週決める施策」が 3 件だけ並び、
緊急度・経営インパクト・自信度・推奨アクション・想定反論まで揃う形で返す。

設計方針:
    - 既存 3 エンジン（improvement_check / feasibility_check / measure_eval）の
      結果を 3 軸（compliance / kpi_reach / measure_pick）にマッピングして候補を
      生成し、urgency × impact × confidence の加重合計で Top 3 を抽出する。
    - 「3 件だけ」が「昨日と同じ」化しないよう、前回差分・未決 aging・次レビュー
      期日を主表示に据える（plans/b-c-flickering-pixel.md §段階 b.5 ②）。
    - 不足分は card_state 4 分類（healthy / insufficient_data / out_of_scope /
      attention_needed）で埋め、「該当なし」のノイズを避ける（同 ③）。
    - 各 CockpitItem に anticipated_objections（CFO/営業/現場の 3 反論+反論案）
      を J4 薄版として埋め込み、合意形成の素材まで一発で揃える（同 ⑥）。
    - 永続化は 2 系統:
        * outputs/cockpit_snapshots/<company_id>/<yyyymmdd>.json（日次）
        * outputs/decisions/<company_id>.jsonl（append-only 意思決定ログ）

Public API:
    build_daily_cockpit(profile, *, today=None, target_year=2030,
                         persist_snapshot=True) -> CockpitResult
    build_cockpit_summary(result: CockpitResult) -> str
"""

from __future__ import annotations

import os
from collections import OrderedDict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.analytics.feasibility_check import (
    FeasibilityResult,
    TargetReachability,
    check_feasibility,
)
from core.analytics.measure_eval import MeasureEvalResult, MeasureScore, evaluate_measures
from core.export.citation import (
    Citation,
    improvement_standards_citation,
    logistics_efficiency_law_citation,
)
from core.export.formatter import format_jpy
from core.legal.improvement_check import (
    ComplianceItem,
    ComplianceReport,
    ComplianceStatus,
    check_truck_driver_compliance,
)
from core.static._freshness import all_warnings
from core.static.sample_company import (
    CompanyProfile,
    DataSource,
    HandlingTimeRow,
    WaitTimeRow,
)

# ---------------------------------------------------------------------------
# 型エイリアス
# ---------------------------------------------------------------------------

DecisionAxis = Literal["compliance", "kpi_reach", "measure_pick"]
"""コックピット 3 枠の判断軸。

- "compliance" : 法令準拠リスク（軸 A）
- "kpi_reach"  : KPI 達成見通し（軸 B）
- "measure_pick": 今週決める施策（軸 C）
"""

CardState = Literal[
    "healthy",
    "insufficient_data",
    "out_of_scope",
    "attention_needed",
]
"""カードの状態 4 分類（Codex 勧告③）。

- "healthy"           : 監視中で異常なし（緑表示）
- "insufficient_data" : 計測データが集まっていない（黄、データ取込促進）
- "out_of_scope"      : 当該企業/業種で対象外（灰、説明文付き）
- "attention_needed"  : 要対応の判断（通常表示）
"""

ObjectionRole = Literal["cfo", "sales", "operation", "partner", "board"]
"""J4 薄版の想定反論ロール。"""

EvidenceAxis = Literal["cost", "legal", "supply", "brand_risk"]
"""反論案の論拠軸（経営会議で使う説得カテゴリ）。"""

DecisionStatus = Literal["pending", "adopt", "postpone", "reject", "escalate"]
"""I2 意思決定ログのステータス。append-only で履歴保持する。"""

VerdictLevel = Literal["green", "yellow", "red"]
"""総合健全性 overall_health の 3 値。feasibility_check.VerdictLevel と同形。"""


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# CLO 中長期計画 提出期限（2026年10月末）— ミッション宣言より
CLO_SUBMISSION_DEADLINE: date = date(2026, 10, 31)

# 加重合計の重み（urgency と impact が支配的、confidence は補正）
_WEIGHT_URGENCY: float = 0.40
_WEIGHT_IMPACT: float = 0.40
_WEIGHT_CONFIDENCE: float = 0.20

# 提出期限「迫る」判定の閾値（日数）
_SUBMISSION_RISK_DAYS: int = 30

# 軸 C の上限件数
_MAX_MEASURE_ITEMS: int = 2

# 軸 A の必須化セベリティ（plan §b.5 Codex 勧告 Q2）
_HIGH_SEVERITY_ITEMS: frozenset[str] = frozenset(
    {
        "1日拘束時間（原則）",
        "年間総拘束時間",
        "年間時間外労働",
        "連続休息時間",
        "荷待ち時間",
        "荷役等時間",
    }
)


def _outputs_root() -> Path:
    """LOGI_OUTPUTS_DIR を実行時に解決する（pytest tmp_path への差替対応）。"""
    return Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs"))


# ---------------------------------------------------------------------------
# データモデル（Pydantic v2）
# ---------------------------------------------------------------------------


class ObjectionItem(BaseModel):
    """J4 薄版：想定反論 + 返答案。

    各 CockpitItem に 3 件添付して、CFO・営業・現場の典型反論を先回りで潰す。
    本格 J4（経営会議反論シミュレーター）は段階 c で別実装。
    """

    model_config = ConfigDict(frozen=True)

    role: ObjectionRole = Field(description="反論者のロール")
    objection: str = Field(description="想定反論（1 文）")
    rebuttal: str = Field(description="反論案（1〜2 文）")
    evidence_axis: EvidenceAxis = Field(description="反論案の論拠軸")


class CockpitItem(BaseModel):
    """3 枠のうち 1 枠の中身。"""

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(
        description="識別子（例: 'compl_wait_max_violation_20260505'）",
    )
    decision_axis: DecisionAxis = Field(description="3 軸のいずれか")
    card_state: CardState = Field(description="カード状態 4 分類")

    headline: str = Field(description="経営層が見て分かる 1 行サマリー")
    rationale: str = Field(description="数値+出典付き 2-3 文の根拠")

    urgency_score: float = Field(ge=0, le=100, description="緊急度（0-100）")
    impact_score: float = Field(ge=0, le=100, description="経営インパクト（0-100）")
    confidence_score: float = Field(ge=0, le=100, description="自信度（0-100）")
    total_score: float = Field(
        ge=0,
        le=100,
        description="加重合計（urgency 0.4 + impact 0.4 + confidence 0.2）",
    )

    # 軸別の参照先（使う軸のみ非 None）
    related_measure_id: str | None = Field(
        default=None,
        description="軸 C の措置 ID（measure_pick 時）",
    )
    related_kpi_name: str | None = Field(
        default=None,
        description="軸 B の KPI 名（kpi_reach 時）",
    )
    related_compliance_item: str | None = Field(
        default=None,
        description="軸 A の compliance item 名（compliance 時）",
    )

    suggested_action: str = Field(
        description="「今週決める」レベルの動詞ベース推奨アクション",
    )
    deadline_label: str = Field(
        description="表示用期限ラベル（例: '即時' / '今週金曜' / '8月末'）",
    )
    next_review_due: date | None = Field(
        default=None,
        description="次回レビュー期日（日付）",
    )
    days_pending: int = Field(
        default=0,
        ge=0,
        description="この判断が pending のまま滞留している日数",
    )
    delta_from_last: str | None = Field(
        default=None,
        description="前回からの変化の説明（例: '前回比 +12 分悪化'）",
    )

    estimated_pnl_jpy: int | None = Field(
        default=None,
        description="施策採用時の年間営業利益インパクト（円）。軸 C 中心",
    )
    citation_keys: list[str] = Field(
        default_factory=list,
        description="CockpitResult.citations への参照キー（label 同名）",
    )
    anticipated_objections: list[ObjectionItem] = Field(
        default_factory=list,
        description="J4 薄版：想定反論 3 件（CFO / 営業 or 現場 / Partner or Board）",
    )


class OperationKpiSnapshot(BaseModel):
    """日次 KPI スナップショット（前日比トレンド計算の元データ）。

    outputs/cockpit_snapshots/<company_id>/<yyyymmdd>.json に保存される。
    """

    model_config = ConfigDict(frozen=True)

    company_id: str
    snapshot_date: date

    load_factor_pct: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="積載率（%）",
    )
    wait_time_avg_min: float | None = Field(
        default=None,
        ge=0,
        description="荷待ち時間 平均（分）",
    )
    wait_time_max_min: float | None = Field(
        default=None,
        ge=0,
        description="荷待ち時間 最大（分）",
    )
    handling_time_avg_min: float | None = Field(
        default=None,
        ge=0,
        description="荷役等時間 平均（分）",
    )
    co2_intensity_g_per_tonkm: float | None = Field(
        default=None,
        ge=0,
        description="CO2 原単位（g/トンキロ）",
    )
    over_2h_count_total: int = Field(
        default=0,
        ge=0,
        description="2 時間超過便数（合計）",
    )

    compliance_overall: ComplianceStatus = Field(
        description="改善基準告示 総合判定",
    )
    feasibility_kpi_level: VerdictLevel = Field(
        description="積載率到達可能性の verdict",
    )
    open_items: list[str] = Field(
        default_factory=list,
        description="未完 CockpitItem の item_id 一覧（aging 計算に使う）",
    )


class DecisionRecord(BaseModel):
    """I2 意思決定ログの 1 行。append-only の jsonl で保持する。

    UI でカードを開いた時点で status="pending" を append し、ボタン押下時に
    新しいレコードを追記する（直前レコード書換ではない、履歴を残すため）。
    """

    model_config = ConfigDict(frozen=True)

    record_id: str = Field(description="UUID4")
    company_id: str
    cockpit_item_id: str = Field(description="CockpitItem.item_id への参照")
    decided_at: datetime
    decided_by: str = Field(description="決定者（CLO 名 or 'system'）")
    decision: DecisionStatus

    rationale: str = Field(default="", description="決定の根拠（短文）")
    expected_effect_jpy: int | None = Field(
        default=None,
        description="採用時の想定経営効果（円）",
    )
    review_due: date | None = Field(
        default=None,
        description="次回レビュー期日（postpone/escalate 時）",
    )
    linked_alerts: list[str] = Field(
        default_factory=list,
        description="H1 ギャップアラート ID への参照（一方向）",
    )


class CockpitResult(BaseModel):
    """build_daily_cockpit の戻り値。

    items は必ず 3 件。compliance 必須化条件を満たさない時でも、
    healthy / insufficient_data / out_of_scope のいずれかで 3 枠を埋める。
    """

    model_config = ConfigDict(frozen=True)

    company_id: str
    company_name: str
    generated_at: datetime
    data_source: DataSource

    items: list[CockpitItem] = Field(
        min_length=3,
        max_length=3,
        description="3 枠ちょうど。順序は軸 A → B → C 優先で並べる",
    )
    snapshot: OperationKpiSnapshot

    delta_from_yesterday: dict[str, float | None] = Field(
        default_factory=dict,
        description=(
            "前日 snapshot との数値差分。"
            "キーは load_factor_pct / wait_time_avg_min / wait_time_max_min 等。"
            "前日 snapshot がない時は全値 None"
        ),
    )
    overall_health: VerdictLevel = Field(
        description="総合健全性（緑/黄/赤）",
    )
    one_line_summary: str = Field(
        description="overall_health バナー用 1 行サマリー",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="3 件の根拠出典の和集合（OrderedDict 経由で順序保持）",
    )
    freshness_warnings: list[str] = Field(
        default_factory=list,
        description="静的データの鮮度警告メッセージ",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_daily_cockpit(
    profile: CompanyProfile,
    *,
    today: date | None = None,
    target_year: int = 2030,
    persist_snapshot: bool = True,
) -> CockpitResult:
    """CLO デイリーコックピット 3 件を生成する。

    Args:
        profile: 自社プロフィール（サンプル / 取込済み JSON / Pydantic 直作成）
        today: 基準日（None なら今日）。テストで固定したい時に指定する
        target_year: KPI 達成目標年（feasibility_check に渡す）
        persist_snapshot: True なら当日の OperationKpiSnapshot を JSON 保存

    Returns:
        CockpitResult: items は必ず 3 件、軸 A → B → C 順
    """
    today_d = today or datetime.now(UTC).date()

    # 1. 既存 3 エンジン実行（並列でなくても十分高速）
    compliance = _run_compliance(profile)
    feasibility = check_feasibility(profile, target_year=target_year)
    measure_eval = evaluate_measures(profile)

    # 2. snapshot 構築
    open_items_placeholder: list[str] = []
    snapshot = _build_snapshot(
        profile=profile,
        today=today_d,
        compliance=compliance,
        feasibility=feasibility,
        open_items=open_items_placeholder,
    )

    # 3. 過去 snapshot ロード（delta 計算）
    prior = _load_prior_snapshot(profile.company_id, today_d)
    delta = _compute_delta(snapshot, prior)

    # 4. 未決ログから aging 計算
    pending = _load_pending_decisions(profile.company_id)

    # 5. 候補生成
    candidates: list[CockpitItem] = []
    candidates.extend(
        _collect_compliance_items(
            compliance=compliance,
            profile=profile,
            today=today_d,
            prior=prior,
            pending=pending,
        )
    )
    candidates.extend(
        _collect_kpi_reach_items(
            feasibility=feasibility,
            profile=profile,
            today=today_d,
            prior=prior,
            pending=pending,
        )
    )
    candidates.extend(
        _collect_measure_items(
            measure_eval=measure_eval,
            profile=profile,
            today=today_d,
            pending=pending,
        )
    )

    # 6. Top 3 抽出（軸 A 必須化条件 + 軸 C 上限 + 重複排除 + state card 補填）
    selected = _select_top_three(
        candidates=candidates,
        compliance=compliance,
        profile=profile,
        today=today_d,
    )

    # 7. open_items を確定して snapshot を作り直す（item_id の循環依存を回避）
    snapshot = snapshot.model_copy(
        update={
            "open_items": [
                item.item_id for item in selected if item.card_state == "attention_needed"
            ],
        }
    )

    # 8. 永続化（テストでは persist_snapshot=False で抑止）
    if persist_snapshot:
        _persist_snapshot(snapshot)

    # 9. 全体メッセージ
    overall_health = _compute_overall_health(compliance, feasibility, selected)
    one_line = _build_one_line_summary(profile, selected, overall_health, snapshot, delta)

    # 10. citations 和集合（OrderedDict で順序保持・重複排除）
    citation_pool: OrderedDict[str, Citation] = OrderedDict()
    citation_pool[improvement_standards_citation().label] = improvement_standards_citation()
    citation_pool[logistics_efficiency_law_citation().label] = logistics_efficiency_law_citation()
    for c in feasibility.citations:
        citation_pool.setdefault(c.label, c)
    for c in measure_eval.citations:
        citation_pool.setdefault(c.label, c)

    return CockpitResult(
        company_id=profile.company_id,
        company_name=profile.name,
        generated_at=datetime.now(UTC),
        data_source=profile.data_source,
        items=selected,
        snapshot=snapshot,
        delta_from_yesterday=delta,
        overall_health=overall_health,
        one_line_summary=one_line,
        citations=list(citation_pool.values()),
        freshness_warnings=all_warnings(),
    )


def build_cockpit_summary(result: CockpitResult) -> str:
    """CockpitResult から経営会議用 1 ページ要約テキストを生成する。

    overall_health バナー → 3 件の headline + rationale + suggested_action →
    delta_from_yesterday → 出典の順で並ぶ。CockpitItem の anticipated_objections
    は折りたたみ相当（要約には含めず詳細表示で出す）。
    """
    health_marks = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    axis_labels = {
        "compliance": "軸A 法令準拠リスク",
        "kpi_reach": "軸B KPI達成見通し",
        "measure_pick": "軸C 今週決める施策",
    }

    lines: list[str] = [
        f"=== CLO 今日の3判断: {result.company_name} "
        f"({result.generated_at.date().isoformat()}) ===",
        f"【総合健全性】 {health_marks[result.overall_health]} {result.overall_health.upper()}"
        f" — {result.one_line_summary}",
        f"データ出所: {result.data_source}",
        "",
    ]

    if result.delta_from_yesterday:
        delta_parts = [
            f"{k}: {v:+.1f}" for k, v in result.delta_from_yesterday.items() if v is not None
        ]
        if delta_parts:
            lines.append("【前日比】 " + " / ".join(delta_parts))
            lines.append("")

    for idx, item in enumerate(result.items, start=1):
        state_mark = {
            "attention_needed": "🟠",
            "healthy": "🟢",
            "insufficient_data": "🟡",
            "out_of_scope": "⚪",
        }[item.card_state]
        lines.append(
            f"{idx}. [{axis_labels[item.decision_axis]}] {state_mark} {item.headline}",
        )
        lines.append(f"   根拠: {item.rationale}")
        lines.append(
            f"   スコア: urg {item.urgency_score:.0f} / "
            f"imp {item.impact_score:.0f} / cf {item.confidence_score:.0f}"
            f"  →  total {item.total_score:.1f}",
        )
        lines.append(f"   推奨: {item.suggested_action}（期限: {item.deadline_label}）")
        if item.delta_from_last:
            lines.append(f"   変化: {item.delta_from_last}")
        if item.days_pending > 0:
            lines.append(f"   滞留: {item.days_pending} 日")
        if item.estimated_pnl_jpy:
            pnl_str = format_jpy(item.estimated_pnl_jpy, digits=2, with_sign=True)
            lines.append(f"   想定インパクト: 年 約 {pnl_str}")
        lines.append("")

    if result.citations:
        lines.append("【主要出典】")
        for c in result.citations[:5]:
            lines.append(f"  - {c.label} ({c.url})")

    if result.freshness_warnings:
        lines.append("")
        lines.append("【鮮度警告】")
        for w in result.freshness_warnings[:3]:
            lines.append(f"  ⚠ {w}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 既存エンジン呼出ラッパ
# ---------------------------------------------------------------------------


def _run_compliance(profile: CompanyProfile) -> ComplianceReport:
    """profile.wait_time_rows / handling_time_rows から ComplianceReport を構築する。

    periodic_report._build_compliance はサンプル中央値で固定埋めするのに対し、
    cockpit は「データに基づく判定」を優先するため、CompanyProfile に直接対応する
    フィールドが無い項目は None（not_measured）として扱う。
    こうすることで 1 日拘束時間 / 年間総拘束時間 / 連続休息のような実測必須項目が
    not_measured カードとして可視化され、計測体制整備のアクションに繋がる。
    """
    waiting_max = max(
        (w.max_minutes for w in profile.wait_time_rows),
        default=None,
    )
    handling_max = max(
        (h.max_minutes for h in profile.handling_time_rows),
        default=None,
    )
    return check_truck_driver_compliance(
        daily_working_hours_max=None,
        annual_working_hours=None,
        annual_overtime_hours=None,
        waiting_minutes_max=waiting_max,
        handling_minutes_max=handling_max,
        rest_hours_min=None,
    )


# ---------------------------------------------------------------------------
# 候補生成（b.4 マッピング）
# ---------------------------------------------------------------------------


def _collect_compliance_items(
    compliance: ComplianceReport,
    profile: CompanyProfile,
    today: date,
    prior: OperationKpiSnapshot | None,
    pending: list[DecisionRecord],
) -> list[CockpitItem]:
    """ComplianceReport を CockpitItem 候補リストに展開する（軸 A）。

    violation を最優先、borderline を次点、not_measured は計測促進カードとして配置。
    """
    items: list[CockpitItem] = []
    submission_risk = _has_submission_risk(today)

    for ci in compliance.items:
        if ci.status == "violation":
            urgency = 95.0 if submission_risk else 90.0
            impact = 90.0 if ci.name in {"荷待ち時間", "荷役等時間"} else 85.0
            action = "改善計画を即時策定し、追加措置を様式第5 Ⅲ に記載する"
            deadline_label = "即時"
            review_due = today
        elif ci.status == "borderline":
            urgency = 75.0
            impact = 65.0
            action = "閾値の 5% バッファを設けて再計測。改善余地のある運用見直し検討"
            deadline_label = "今月中"
            review_due = _add_days(today, 14)
        elif ci.status == "not_measured":
            urgency = 60.0
            impact = 55.0
            action = f"{ci.name} の計測体制を整備（計測テンプレ Excel に追加）"
            deadline_label = "計測体制整備"
            review_due = _add_days(today, 30)
        else:
            continue  # compliant は候補化しない

        confidence = _compliance_confidence(profile, ci)
        item_id = f"compl_{_slug(ci.name)}_{ci.status}_{today.strftime('%Y%m%d')}"
        days_pending = _days_pending_of(pending, item_id, today)
        delta = _delta_from_prior_compliance(ci, prior)

        rationale = (
            f"{ci.name}: 実測 {ci.measured_value}{ci.unit} / "
            f"基準 {ci.threshold}{ci.unit}（status={ci.status}）"
        )
        if ci.note:
            rationale += f" — {ci.note}"

        items.append(
            CockpitItem(
                item_id=item_id,
                decision_axis="compliance",
                card_state="attention_needed",
                headline=f"【法令】{ci.name} {_status_label(ci.status)}",
                rationale=rationale,
                urgency_score=urgency,
                impact_score=impact,
                confidence_score=confidence,
                total_score=_weighted_total(urgency, impact, confidence),
                related_compliance_item=ci.name,
                suggested_action=action,
                deadline_label=deadline_label,
                next_review_due=review_due,
                days_pending=days_pending,
                delta_from_last=delta,
                estimated_pnl_jpy=None,
                citation_keys=[improvement_standards_citation().label],
                anticipated_objections=_objections_for_compliance(ci, profile),
            )
        )

    return items


def _collect_kpi_reach_items(
    feasibility: FeasibilityResult,
    profile: CompanyProfile,
    today: date,
    prior: OperationKpiSnapshot | None,
    pending: list[DecisionRecord],
) -> list[CockpitItem]:
    """FeasibilityResult.kpi_reachability を CockpitItem 候補に展開する（軸 B）。

    green は候補化しない（プラン §b.4）。
    """
    items: list[CockpitItem] = []
    for kpi in feasibility.kpi_reachability:
        if kpi.feasibility_level == "green":
            continue

        urgency = 85.0 if kpi.feasibility_level == "red" else 65.0
        impact = 90.0 if kpi.feasibility_level == "red" else 75.0
        confidence = _kpi_confidence(profile, kpi)

        action = (
            "目標年延長または目標値見直しを経営会議に上程"
            if kpi.feasibility_level == "red"
            else "複数施策の同時実施計画を策定し、月次モニタリング体制を整備"
        )
        deadline_label = "次回経営会議" if kpi.feasibility_level == "red" else "今四半期"
        review_due = _add_days(
            today,
            7 if kpi.feasibility_level == "red" else 30,
        )
        item_id = f"kpi_{_slug(kpi.kpi_name)}_{kpi.feasibility_level}_{today.strftime('%Y%m%d')}"
        days_pending = _days_pending_of(pending, item_id, today)
        delta = _delta_from_prior_kpi(kpi, prior)

        rationale = (
            f"{kpi.kpi_name}（目標年 {kpi.target_year}）: "
            f"年間必要 {kpi.annual_required_improvement:.1f}pp vs "
            f"業界実績 {kpi.industry_typical_improvement:.1f}pp/年。{kpi.rationale}"
        )

        items.append(
            CockpitItem(
                item_id=item_id,
                decision_axis="kpi_reach",
                card_state="attention_needed",
                headline=f"【KPI】{kpi.kpi_name} {kpi.feasibility_level} 判定",
                rationale=rationale,
                urgency_score=urgency,
                impact_score=impact,
                confidence_score=confidence,
                total_score=_weighted_total(urgency, impact, confidence),
                related_kpi_name=kpi.kpi_name,
                suggested_action=action,
                deadline_label=deadline_label,
                next_review_due=review_due,
                days_pending=days_pending,
                delta_from_last=delta,
                estimated_pnl_jpy=None,
                citation_keys=[logistics_efficiency_law_citation().label],
                anticipated_objections=_objections_for_kpi(kpi, profile),
            )
        )

    return items


def _collect_measure_items(
    measure_eval: MeasureEvalResult,
    profile: CompanyProfile,
    today: date,
    pending: list[DecisionRecord],
) -> list[CockpitItem]:
    """measure_eval.top_recommendations を CockpitItem 候補に展開する（軸 C）。

    Top 3 を 3 件すべて候補化（実際の選抜は Top3 抽出時の axis 上限で絞る）。
    """
    items: list[CockpitItem] = []
    operating_profit = max(profile.operating_profit_jpy, 1)

    for rank, score in enumerate(measure_eval.top_recommendations, start=1):
        urgency = _measure_urgency(rank, score)
        impact = _measure_impact(score, operating_profit)
        confidence = _measure_confidence(profile, score)

        item_id = f"measure_{score.measure.measure_id}_{today.strftime('%Y%m%d')}"
        days_pending = _days_pending_of(pending, item_id, today)

        action = (
            (f"{score.measure.name} の実行可否を経営会議で承認（主管 {score.responsible_dept}）")
            if score.responsible_dept
            else f"{score.measure.name} の実行可否を経営会議で承認"
        )
        deadline_label = "今週金曜"
        review_due = _add_days(today, 7)

        rationale = f"Top{rank} 推薦（総合 {score.total_score:.1f}/100）: {score.selection_reason}"

        items.append(
            CockpitItem(
                item_id=item_id,
                decision_axis="measure_pick",
                card_state="attention_needed",
                headline=f"【施策】{score.measure.name} を今週決める",
                rationale=rationale,
                urgency_score=urgency,
                impact_score=impact,
                confidence_score=confidence,
                total_score=_weighted_total(urgency, impact, confidence),
                related_measure_id=score.measure.measure_id,
                suggested_action=action,
                deadline_label=deadline_label,
                next_review_due=review_due,
                days_pending=days_pending,
                delta_from_last=None,
                estimated_pnl_jpy=(
                    int(score.estimated_annual_cost_saving_jpy)
                    if score.estimated_annual_cost_saving_jpy
                    else None
                ),
                citation_keys=[logistics_efficiency_law_citation().label],
                anticipated_objections=_objections_for_measure(score, profile),
            )
        )

    return items


# ---------------------------------------------------------------------------
# スコアリング（b.5）
# ---------------------------------------------------------------------------


def _weighted_total(urgency: float, impact: float, confidence: float) -> float:
    """加重合計を 0-100 にクリップして返す。"""
    raw = urgency * _WEIGHT_URGENCY + impact * _WEIGHT_IMPACT + confidence * _WEIGHT_CONFIDENCE
    return max(0.0, min(100.0, raw))


def _measure_urgency(rank: int, score: MeasureScore) -> float:
    """軸 C のうち、難易度・補助金・Top 順位から urgency を導く。"""
    base = 70.0 - (rank - 1) * 5.0  # rank1=70 / rank2=65 / rank3=60
    if score.measure.eligible_subsidies:
        base += 5.0  # 補助金あり → 締切意識で+5
    if score.measure.implementation_difficulty <= 2:
        base += 5.0  # 短期実装可 → 早く決める意義
    return max(0.0, min(95.0, base))


def _measure_impact(score: MeasureScore, operating_profit: int) -> float:
    """軸 C のインパクトを 営業利益への寄与率 から正規化する。"""
    saving = score.estimated_annual_cost_saving_jpy or 0.0
    if saving <= 0:
        return 50.0  # 前提施策（visualization_baseline 等）
    ratio = saving / operating_profit  # 営業利益比
    if ratio >= 0.10:
        return 95.0
    if ratio >= 0.05:
        return 85.0
    if ratio >= 0.02:
        return 75.0
    if ratio >= 0.01:
        return 65.0
    return 55.0


def _measure_confidence(profile: CompanyProfile, score: MeasureScore) -> float:
    """軸 C の confidence: data_source + リソース充足度。"""
    base = _data_source_base_confidence(profile.data_source)
    if score.missing_resources:
        base -= 10.0 * min(len(score.missing_resources), 3)
    if score.estimated_payback_years and score.estimated_payback_years <= 3.0:
        base += 5.0
    return max(0.0, min(100.0, base))


def _compliance_confidence(profile: CompanyProfile, ci: ComplianceItem) -> float:
    """軸 A の confidence: data_source + 実測 wait_time_rows の有無。"""
    base = _data_source_base_confidence(profile.data_source)
    if ci.measured_value is None:
        base -= 30.0  # 計測なし → 自信度大幅減
    elif profile.wait_time_rows or profile.handling_time_rows:
        base += 10.0
    if all_warnings():
        base -= 5.0
    return max(0.0, min(100.0, base))


def _kpi_confidence(profile: CompanyProfile, kpi: TargetReachability) -> float:
    """軸 B の confidence: data_source + load_factor 実測の有無。"""
    base = _data_source_base_confidence(profile.data_source)
    if profile.load_factor_actual_pct is not None:
        base += 10.0
    if kpi.feasibility_level == "red":
        base -= 5.0  # red 判定はモデル外推の幅が広い
    return max(0.0, min(100.0, base))


def _data_source_base_confidence(data_source: DataSource) -> float:
    """data_source ごとの初期 confidence。"""
    return {
        "actual": 90.0,
        "estimated": 70.0,
        "sample": 60.0,
    }[data_source]


# ---------------------------------------------------------------------------
# Top 3 抽出（b.5）
# ---------------------------------------------------------------------------


def _select_top_three(
    candidates: list[CockpitItem],
    compliance: ComplianceReport,
    profile: CompanyProfile,
    today: date,
) -> list[CockpitItem]:
    """候補から最終 3 件を抽出する（軸 A 必須化 + 軸 C 上限 + 重複排除）。"""
    sorted_cands = sorted(candidates, key=lambda c: c.total_score, reverse=True)

    selected: list[CockpitItem] = []
    used_axes: dict[DecisionAxis, int] = {
        "compliance": 0,
        "kpi_reach": 0,
        "measure_pick": 0,
    }
    used_keys: set[str] = set()

    must_include_compliance = _must_include_compliance(compliance, today)
    if must_include_compliance:
        for c in sorted_cands:
            if c.decision_axis == "compliance":
                selected.append(c)
                used_axes["compliance"] += 1
                used_keys.add(_dedup_key(c))
                break

    for c in sorted_cands:
        if len(selected) >= 3:
            break
        if c in selected:
            continue
        if c.decision_axis == "measure_pick" and (used_axes["measure_pick"] >= _MAX_MEASURE_ITEMS):
            continue
        key = _dedup_key(c)
        if key in used_keys:
            continue
        selected.append(c)
        used_axes[c.decision_axis] += 1
        used_keys.add(key)

    while len(selected) < 3:
        selected.append(
            _make_state_card(
                existing=selected,
                profile=profile,
                today=today,
            )
        )

    selected.sort(key=_axis_order)
    return selected


def _must_include_compliance(report: ComplianceReport, today: date) -> bool:
    """軸 A を必須化するかの判定。

    重大違反（_HIGH_SEVERITY_ITEMS のいずれかが violation）または
    提出期限 30 日以内なら True。
    """
    has_severe = any(
        i.status == "violation" and i.name in _HIGH_SEVERITY_ITEMS for i in report.items
    )
    return has_severe or _has_submission_risk(today)


def _has_submission_risk(today: date) -> bool:
    """中長期計画 提出期限まで 30 日以内なら True。"""
    days_left = (CLO_SUBMISSION_DEADLINE - today).days
    return 0 <= days_left <= _SUBMISSION_RISK_DAYS


def _dedup_key(item: CockpitItem) -> str:
    """重複排除キー（同 measure_id / kpi / compliance_item を避ける）。"""
    if item.related_measure_id:
        return f"measure:{item.related_measure_id}"
    if item.related_kpi_name:
        return f"kpi:{item.related_kpi_name}"
    if item.related_compliance_item:
        return f"compl:{item.related_compliance_item}"
    return f"id:{item.item_id}"


def _axis_order(item: CockpitItem) -> int:
    """A → B → C の表示順。"""
    return {"compliance": 0, "kpi_reach": 1, "measure_pick": 2}[item.decision_axis]


def _make_state_card(
    existing: list[CockpitItem],
    profile: CompanyProfile,
    today: date,
) -> CockpitItem:
    """埋め枠カード。空き軸に対して状態を判定する。"""
    occupied = {item.decision_axis for item in existing}
    target_axis: DecisionAxis = next(
        (a for a in ("compliance", "kpi_reach", "measure_pick") if a not in occupied),
        "measure_pick",
    )

    axis_label = {
        "compliance": "法令準拠",
        "kpi_reach": "KPI達成見通し",
        "measure_pick": "施策選定",
    }[target_axis]

    state, headline, rationale = _infer_state_card_text(
        target_axis,
        profile,
        axis_label,
    )

    item_id = f"state_{target_axis}_{state}_{today.strftime('%Y%m%d')}"

    return CockpitItem(
        item_id=item_id,
        decision_axis=target_axis,
        card_state=state,
        headline=headline,
        rationale=rationale,
        urgency_score=20.0,
        impact_score=20.0,
        confidence_score=80.0 if state == "healthy" else 50.0,
        total_score=_weighted_total(20.0, 20.0, 80.0 if state == "healthy" else 50.0),
        related_measure_id=None,
        related_kpi_name=None,
        related_compliance_item=None,
        suggested_action=_state_card_action(state, axis_label),
        deadline_label="—",
        next_review_due=None,
        days_pending=0,
        delta_from_last=None,
        estimated_pnl_jpy=None,
        citation_keys=[],
        anticipated_objections=[],
    )


def _infer_state_card_text(
    axis: DecisionAxis,
    profile: CompanyProfile,
    axis_label: str,
) -> tuple[CardState, str, str]:
    """空き軸の card_state と表示文を推定する。"""
    if axis == "compliance":
        if not profile.wait_time_rows and not profile.handling_time_rows:
            return (
                "insufficient_data",
                f"【{axis_label}】計測データ未取込",
                "wait_time_rows / handling_time_rows が空のため遵守判定不能。"
                "テンプレ Excel での計測データ取込を推奨",
            )
        return (
            "healthy",
            f"【{axis_label}】告示違反なし（緑）",
            "現在の計測データでは改善基準告示の違反項目なし。継続監視中",
        )
    if axis == "kpi_reach":
        if profile.load_factor_actual_pct is None:
            return (
                "insufficient_data",
                f"【{axis_label}】積載率実測未取込",
                "load_factor_actual_pct が未設定のため業界平均（38%）で代替判定中",
            )
        return (
            "healthy",
            f"【{axis_label}】積載率目標到達見通し（緑）",
            "目標年に向けた年間必要改善幅は業界実績の範囲内",
        )
    if profile.is_chain_franchise:
        return (
            "out_of_scope",
            f"【{axis_label}】連鎖化事業者は荷役等領域が対象外",
            "様式第3「第5条関係」では荷役等時間短縮の記載は不要。"
            "施策候補は積載率向上 / 荷待ち時間短縮の 2 領域に集中",
        )
    return (
        "healthy",
        f"【{axis_label}】Top 3 推薦施策はすべて健全",
        "candidates が軸 C 上限に届かず、追加で検討すべき施策なし",
    )


def _state_card_action(state: CardState, axis_label: str) -> str:
    if state == "insufficient_data":
        return f"{axis_label} の計測データ取込を進める"
    if state == "out_of_scope":
        return "対象外領域のため当面のアクション不要"
    return "継続監視（次の異常発生まで定常運用）"


# ---------------------------------------------------------------------------
# Snapshot / Decision 永続化
# ---------------------------------------------------------------------------


def _build_snapshot(
    profile: CompanyProfile,
    today: date,
    compliance: ComplianceReport,
    feasibility: FeasibilityResult,
    open_items: list[str],
) -> OperationKpiSnapshot:
    """profile + 各 report から OperationKpiSnapshot を構築する。"""
    wait_avg = _avg_value(profile.wait_time_rows, "average_minutes")
    wait_max = _max_value(profile.wait_time_rows, "max_minutes")
    handling_avg = _avg_value(profile.handling_time_rows, "average_minutes")
    over_2h = sum(w.over_2h_count for w in profile.wait_time_rows)

    feas_level: VerdictLevel = (
        feasibility.kpi_reachability[0].feasibility_level
        if feasibility.kpi_reachability
        else "yellow"
    )

    return OperationKpiSnapshot(
        company_id=profile.company_id,
        snapshot_date=today,
        load_factor_pct=profile.load_factor_actual_pct,
        wait_time_avg_min=wait_avg,
        wait_time_max_min=wait_max,
        handling_time_avg_min=handling_avg,
        co2_intensity_g_per_tonkm=None,  # 別ロジックで計算予定
        over_2h_count_total=over_2h,
        compliance_overall=compliance.overall_status,
        feasibility_kpi_level=feas_level,
        open_items=open_items,
    )


def _persist_snapshot(snapshot: OperationKpiSnapshot) -> Path:
    """snapshot を outputs/cockpit_snapshots/<id>/<yyyymmdd>.json に保存する。"""
    base = _outputs_root() / "cockpit_snapshots" / snapshot.company_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{snapshot.snapshot_date.strftime('%Y%m%d')}.json"
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return path


def _load_prior_snapshot(
    company_id: str,
    today: date,
) -> OperationKpiSnapshot | None:
    """直近 7 日以内で today より古い snapshot を 1 件返す。

    最も新しい日付（today に近い）を採用する。
    """
    base = _outputs_root() / "cockpit_snapshots" / company_id
    if not base.is_dir():
        return None
    candidates: list[tuple[date, Path]] = []
    for p in base.glob("*.json"):
        try:
            d = datetime.strptime(p.stem, "%Y%m%d").date()
        except ValueError:
            continue
        if 0 < (today - d).days <= 7:
            candidates.append((d, p))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return OperationKpiSnapshot.model_validate_json(
        candidates[0][1].read_text(encoding="utf-8"),
    )


def _load_pending_decisions(company_id: str) -> list[DecisionRecord]:
    """outputs/decisions/<id>.jsonl から status=pending の最新レコードを返す。

    同 cockpit_item_id の中で最新（decided_at 最大）を pending と判定し、
    その値が "pending" のもののみ集約する。Append-only ログの解釈仕様。
    """
    path = _outputs_root() / "decisions" / f"{company_id}.jsonl"
    if not path.is_file():
        return []
    latest_per_item: dict[str, DecisionRecord] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = DecisionRecord.model_validate_json(line)
        except (ValueError, TypeError):
            continue  # 壊れた行はスキップ（前方互換）
        existing = latest_per_item.get(record.cockpit_item_id)
        if existing is None or record.decided_at > existing.decided_at:
            latest_per_item[record.cockpit_item_id] = record
    return [r for r in latest_per_item.values() if r.decision == "pending"]


def append_decision(record: DecisionRecord) -> Path:
    """DecisionRecord を outputs/decisions/<id>.jsonl に append する。

    Public API（b.6 で REST POST から呼ぶ）。
    """
    base = _outputs_root() / "decisions"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{record.company_id}.jsonl"
    with path.open("a", encoding="utf-8") as fp:
        fp.write(record.model_dump_json())
        fp.write("\n")
    return path


def _days_pending_of(
    pending: list[DecisionRecord],
    item_id: str,
    today: date,
) -> int:
    """pending リストから指定 item_id の滞留日数を返す。未登録なら 0。"""
    for r in pending:
        if r.cockpit_item_id == item_id:
            return max(0, (today - r.decided_at.date()).days)
    return 0


# ---------------------------------------------------------------------------
# Delta / Overall health
# ---------------------------------------------------------------------------


def _compute_delta(
    current: OperationKpiSnapshot,
    prior: OperationKpiSnapshot | None,
) -> dict[str, float | None]:
    """前日 snapshot との数値差分を返す。prior が None なら全 None。"""
    keys = (
        "load_factor_pct",
        "wait_time_avg_min",
        "wait_time_max_min",
        "handling_time_avg_min",
        "co2_intensity_g_per_tonkm",
    )
    if prior is None:
        return dict.fromkeys(keys)
    return {
        k: (
            getattr(current, k) - getattr(prior, k)
            if getattr(current, k) is not None and getattr(prior, k) is not None
            else None
        )
        for k in keys
    }


def _compute_overall_health(
    compliance: ComplianceReport,
    feasibility: FeasibilityResult,
    selected: list[CockpitItem],
) -> VerdictLevel:
    """総合健全性（緑/黄/赤）を判定する。

    - 重大違反あり → red
    - feasibility red あり or borderline → yellow
    - すべて健全（attention_needed 0 件） → green
    """
    if compliance.overall_status == "violation":
        return "red"
    if any(k.feasibility_level == "red" for k in feasibility.kpi_reachability):
        return "red"
    if compliance.overall_status == "borderline":
        return "yellow"
    if any(k.feasibility_level == "yellow" for k in feasibility.kpi_reachability):
        return "yellow"
    if all(item.card_state != "attention_needed" for item in selected):
        return "green"
    return "yellow"


def _build_one_line_summary(
    profile: CompanyProfile,
    selected: list[CockpitItem],
    overall_health: VerdictLevel,
    snapshot: OperationKpiSnapshot,
    delta: dict[str, float | None],
) -> str:
    """overall_health バナー用の 1 行サマリーを生成する。"""
    attention = [i for i in selected if i.card_state == "attention_needed"]
    lf = (
        f"積載率 {snapshot.load_factor_pct:.0f}%"
        if snapshot.load_factor_pct is not None
        else "積載率 未計測"
    )
    if delta.get("load_factor_pct") is not None:
        lf += f" ({delta['load_factor_pct']:+.1f}pp)"

    if overall_health == "red":
        return f"重大対応 {len(attention)} 件あり / {lf}"
    if overall_health == "yellow":
        return f"要注視 {len(attention)} 件 / {lf}"
    return f"全体健全 / {lf}"


# ---------------------------------------------------------------------------
# 想定反論（J4 薄版）
# ---------------------------------------------------------------------------


def _objections_for_compliance(
    ci: ComplianceItem,
    profile: CompanyProfile,
) -> list[ObjectionItem]:
    """軸 A 用の想定反論 3 件。CFO / 現場 / 取締役会 の典型反論。"""
    return [
        ObjectionItem(
            role="cfo",
            objection=(f"{ci.name} 改善のコストインパクトは？改善投資より違反継続の方が経済的では"),
            rebuttal=(
                "勧告→命令→企業名公表の段階制で長期ブランド毀損が上回る。"
                "違反継続による荷主からの取引見直しリスクが顕在化する"
            ),
            evidence_axis="brand_risk",
        ),
        ObjectionItem(
            role="operation",
            objection="現場リソースは限界、追加施策の余裕はない",
            rebuttal=(
                "VBS（バース予約）等の運用変更は追加人員不要で導入可能。"
                "段階導入とパイロット拠点で負荷を分散する"
            ),
            evidence_axis="supply",
        ),
        ObjectionItem(
            role="board",
            objection="CLO 計画書の追加措置欄まで踏み込む必要があるのか",
            rebuttal=(
                "様式第5 Ⅲ で改善基準告示違反時は追加措置記載が法令上の義務。"
                "未記載は記載漏れとして再提出指示の対象になりうる"
            ),
            evidence_axis="legal",
        ),
    ]


def _objections_for_kpi(
    kpi: TargetReachability,
    profile: CompanyProfile,
) -> list[ObjectionItem]:
    """軸 B 用の想定反論。"""
    return [
        ObjectionItem(
            role="cfo",
            objection=(f"目標値 {kpi.target_value:.0f} は本当に必要か。業界平均で十分では"),
            rebuttal=(
                "国交省「目指すべき水準」として設定された値で、"
                "未達のままでは排出量取引・カーボンクレジット経済化の機会損失が大きい"
            ),
            evidence_axis="cost",
        ),
        ObjectionItem(
            role="sales",
            objection="積載率向上は荷主側との納期交渉にしわ寄せになる",
            rebuttal=(
                "VMI / 納期分散で荷主との関係性を強化しつつ達成可能。"
                "Lead Time Review 施策で win-win を設計する"
            ),
            evidence_axis="brand_risk",
        ),
        ObjectionItem(
            role="operation",
            objection="現状業務との両立は難しい。1 年では無理",
            rebuttal=(
                f"目標年は {kpi.target_year} で残り "
                f"{kpi.target_year - kpi.current_year} 年。"
                "段階的なマイルストーン設計で年次達成"
            ),
            evidence_axis="supply",
        ),
    ]


def _objections_for_measure(
    score: MeasureScore,
    profile: CompanyProfile,
) -> list[ObjectionItem]:
    """軸 C 用の想定反論。"""
    payback = (
        f"{score.estimated_payback_years:.1f} 年"
        if score.estimated_payback_years
        else "投資回収不明"
    )
    return [
        ObjectionItem(
            role="cfo",
            objection=f"投資 {format_jpy(score.measure.typical_investment_jpy_high)}の妥当性は",
            rebuttal=(
                f"想定回収期間 {payback}。"
                + (
                    f"補助金 {score.measure.eligible_subsidies[0]} で実質投資が圧縮可能"
                    if score.measure.eligible_subsidies
                    else "ROI ベースで主要施策の中で最も高効率"
                )
            ),
            evidence_axis="cost",
        ),
        ObjectionItem(
            role="operation",
            objection="主管部門の人的リソースが足りない",
            rebuttal=(
                f"主管 {score.responsible_dept or '物流部'} で月次 KPI を握り、"
                "外注ベンダーの活用で人的負荷を抑える"
            ),
            evidence_axis="supply",
        ),
        ObjectionItem(
            role="partner",
            objection="取引先の理解が得られるか不明",
            rebuttal=(
                "失敗パターン: "
                + "; ".join(score.measure.common_pitfalls[:1] or ["先行事例ヒアリング"])
                + "。先行 7 社事例（経産省 CLO 取組事例集）で説得材料あり"
            ),
            evidence_axis="brand_risk",
        ),
    ]


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------


def _avg_value(rows: list[WaitTimeRow] | list[HandlingTimeRow], attr: str) -> float | None:
    """measured_count による加重平均を返す（行なし or 計測 0 → None）。"""
    total_count = 0
    weighted_sum = 0.0
    for r in rows:
        c = r.measured_count
        if c <= 0:
            continue
        total_count += c
        weighted_sum += getattr(r, attr) * c
    return weighted_sum / total_count if total_count > 0 else None


def _max_value(rows: list[WaitTimeRow] | list[HandlingTimeRow], attr: str) -> float | None:
    """属性の最大値（行なし → None）。"""
    values = [getattr(r, attr) for r in rows]
    return max(values) if values else None


def _add_days(today: date, days: int) -> date:
    """date に日数を加える（datetime に変換せずに date のまま）。"""
    return today + timedelta(days=days)


def _slug(name: str) -> str:
    """日本語項目名から ASCII slug を作る（item_id の安定化用）。

    既知項目はマッピングし、未知は文字列ハッシュで代用する。
    """
    mapping = {
        "1日拘束時間（原則）": "daily_working_max",
        "年間総拘束時間": "annual_working",
        "年間時間外労働": "annual_overtime",
        "荷待ち時間": "wait_max",
        "荷役等時間": "handling_max",
        "連続休息時間": "rest_min",
    }
    if name in mapping:
        return mapping[name]
    safe = "".join(c if c.isascii() and (c.isalnum() or c in "_-") else "_" for c in name)
    return safe.lower().strip("_") or f"unknown{abs(hash(name)) % 10000:04d}"


def _status_label(status: ComplianceStatus) -> str:
    return {
        "violation": "違反",
        "borderline": "要注意",
        "not_measured": "未計測",
        "compliant": "遵守",
    }[status]


def _delta_from_prior_compliance(
    ci: ComplianceItem,
    prior: OperationKpiSnapshot | None,
) -> str | None:
    """軸 A の delta_from_last 文字列を生成する。"""
    if prior is None or ci.measured_value is None:
        return None
    if ci.name == "荷待ち時間" and prior.wait_time_max_min is not None:
        diff = ci.measured_value - prior.wait_time_max_min
        if abs(diff) < 0.5:
            return None
        sign = "+" if diff > 0 else ""
        return f"前回比 {sign}{diff:.0f} 分"
    return None


def _delta_from_prior_kpi(
    kpi: TargetReachability,
    prior: OperationKpiSnapshot | None,
) -> str | None:
    """軸 B の delta_from_last 文字列を生成する。"""
    if prior is None or prior.load_factor_pct is None:
        return None
    if "積載率" in kpi.kpi_name:
        diff = kpi.current_baseline - prior.load_factor_pct
        if abs(diff) < 0.1:
            return None
        sign = "+" if diff > 0 else ""
        return f"前回比 {sign}{diff:.1f}pp"
    return None


__all__ = [
    "CardState",
    "CockpitItem",
    "CockpitResult",
    "DecisionAxis",
    "DecisionRecord",
    "DecisionStatus",
    "EvidenceAxis",
    "ObjectionItem",
    "ObjectionRole",
    "OperationKpiSnapshot",
    "VerdictLevel",
    "append_decision",
    "build_cockpit_summary",
    "build_daily_cockpit",
]
