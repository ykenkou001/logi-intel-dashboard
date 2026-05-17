"""経営意思決定ログの永続化（outputs/decision_logs/<id>.jsonl + 旧 outputs/decisions/ 統合読出）。

設計方針 (Tier S1 / フェーズ 5.5):
    - 既存 cockpit 単発 DecisionRecord は outputs/decisions/<id>.jsonl に温存（後方互換）
    - 新 DecisionLogEntry スナップショット型は outputs/decision_logs/<id>.jsonl に append
    - query_decision_log_entries() は両ファイルを論理統合して返す
      （include_legacy_cockpit=True 既定）
    - 旧 DecisionRecord → DecisionLogEntry 変換は _lift_legacy_record_to_entry() で実施
    - LOGI_STORAGE_BACKEND=s3 のとき S3 への複製・取得（measure_run_store.py パターン踏襲）

設計判断ログは plans/decision_log.md v1.0 / plans/decision_log_implementation.md v1.1 を参照。
"""

from __future__ import annotations

import contextlib
import os
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.analytics.feasibility_check import VerdictLevel
from core.export.citation import Citation
from core.legal.improvement_check import ComplianceStatus

# ---------------------------------------------------------------------------
# 型エイリアス（operation_cockpit.py から移動 / 単一ソース確立）
# ---------------------------------------------------------------------------
# VerdictLevel は feasibility_check.py が既存 single source。
# operation_cockpit.py:98 にも同形 Literal が並存しているが本 PR では触らない。

DecisionStatus = Literal["pending", "adopt", "postpone", "reject", "escalate"]

DecisionType = Literal[
    "cockpit_single",
    "measure_eval_topbottom",
    "scenario_sim_baseline",
    "plan_draft_freeze",
    "free_form",
]


# ---------------------------------------------------------------------------
# データモデル
# ---------------------------------------------------------------------------


class DecisionRecord(BaseModel):
    """I2 意思決定ログの 1 行（既存仕様・operation_cockpit.py から移動）。

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


class ContextSnapshot(BaseModel):
    """判断時点の数値スナップショット（案 B 拡張版）。

    様式第 5 定期報告の Ⅲ「実施状況」+ Ⅵ「改善基準告示遵守状況」引用要件を満たす。
    """

    model_config = ConfigDict(frozen=True)

    snapshot_date: date
    # 様式第5 Ⅲ「実施状況」引用に必要
    load_factor_pct: float | None = Field(default=None, ge=0, le=100)
    co2_intensity_g_per_tonkm: float | None = Field(default=None, ge=0)
    f2_score: float | None = Field(default=None, ge=0, le=100)
    j2_trap_count_high: int | None = Field(default=None, ge=0)
    related_kpi_name: str | None = None
    # 様式第5 Ⅵ「改善基準告示遵守状況」引用に必要
    wait_time_avg_min: float | None = Field(default=None, ge=0)
    wait_time_max_min: float | None = Field(default=None, ge=0)
    handling_time_avg_min: float | None = Field(default=None, ge=0)
    over_2h_count_total: int | None = Field(default=None, ge=0)
    compliance_overall: ComplianceStatus | None = None
    feasibility_kpi_level: VerdictLevel | None = None
    # 任意拡張
    extra: dict[str, float | str | int | list[str] | None] = Field(default_factory=dict)


class DecisionLogEntry(BaseModel):
    """経営判断スナップショット 1 件。様式第 5 証跡として引用可能。"""

    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(description="UUID4。呼出側で生成して渡す")
    company_id: str
    decision_type: DecisionType
    decided_at: datetime
    decided_by: str = Field(description="決定者（CLO 名・取締役会・system）")

    headline: str = Field(description="1 行要約（経営会議資料での表題）")
    rationale: str = Field(default="", description="判断の根拠（複数文 OK）")
    selected_measures: list[str] = Field(
        default_factory=list,
        description="採用した measure_id（ALL_MEASURES.measure_id を参照）",
    )
    rejected_measures: list[str] = Field(
        default_factory=list,
        description="不採用とした measure_id（judgment trail 用）",
    )
    sources: list[Citation] = Field(
        default_factory=list,
        description="判断根拠の出典",
    )
    context_snapshot: ContextSnapshot = Field(
        description="判断時点のスナップショット（軽量埋込）",
    )

    linked_cockpit_record_id: str | None = Field(
        default=None,
        description="DecisionRecord.record_id（cockpit_single 連携時のみ設定）",
    )
    review_due: date | None = None
    tags: list[str] = Field(default_factory=list, description="検索用タグ")

    legacy_source: bool = Field(
        default=False,
        description=(
            "True なら旧 outputs/decisions/<id>.jsonl からの読出変換結果。"
            "write 時は常に False（Web で「（旧仕様）」バッジ表示用）"
        ),
    )


# ---------------------------------------------------------------------------
# パス解決
# ---------------------------------------------------------------------------


def _outputs_root() -> Path:
    """LOGI_OUTPUTS_DIR を実行時に解決する（pytest tmp_path への差替対応）。"""
    return Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs"))


def _legacy_decisions_path(company_id: str) -> Path:
    """既存 cockpit 単発 DecisionRecord 用 jsonl（後方互換維持）。"""
    return _outputs_root() / "decisions" / f"{company_id}.jsonl"


def _new_decision_logs_path(company_id: str) -> Path:
    """新 DecisionLogEntry スナップショット用 jsonl。"""
    return _outputs_root() / "decision_logs" / f"{company_id}.jsonl"


# ---------------------------------------------------------------------------
# Public API: 既存（operation_cockpit.py から移動・後方互換維持）
# ---------------------------------------------------------------------------


def append_decision(record: DecisionRecord) -> Path:
    """既存 cockpit 単発 DecisionRecord を旧 jsonl に append（仕様完全維持）。

    Public API（cockpit ボタン → REST POST /decisions/{id} から呼ばれる）。
    S3 backend 利用時は append 前に既存 jsonl を S3 から取り込んでローカルに反映し、
    その上で新行を追加してから publish する（Lambda コールドスタート対策・Codex 指摘 1）。
    """
    path = _legacy_decisions_path(record.company_id)
    _sync_local_from_s3_if_needed(path, s3_key=f"decisions/{record.company_id}.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(record.model_dump_json())
        fp.write("\n")
    _maybe_publish_to_s3(path, key=f"decisions/{record.company_id}.jsonl")
    return path


def load_pending_decisions(company_id: str) -> list[DecisionRecord]:
    """旧 jsonl から status='pending' の最新レコードを返す（cockpit aging 計算用）。

    同 cockpit_item_id の中で最新（decided_at 最大）を判定し、その値が "pending" の
    もののみ集約する。Append-only ログの解釈仕様。
    """
    raw = _read_jsonl_text(
        _legacy_decisions_path(company_id),
        s3_key=f"decisions/{company_id}.jsonl",
    )
    if raw is None:
        return []
    latest_per_item: dict[str, DecisionRecord] = {}
    for line in raw.splitlines():
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


# ---------------------------------------------------------------------------
# Public API: 新規（Tier S1）
# ---------------------------------------------------------------------------


def append_decision_log_entry(entry: DecisionLogEntry) -> Path:
    """新スナップショット型を outputs/decision_logs/<id>.jsonl に append。

    Codex 論点 1: entry_id は呼出側で `str(uuid.uuid4())` で生成して渡すこと。
    frozen=True のため store 側で書き換えはできない。entry_id が空文字なら ValueError。

    Codex 最終レビュー指摘 1: S3 backend 利用時は append 前に既存 jsonl を S3 から
    ローカルに取り込み、その上で新行を追加して publish する。これにより Lambda
    コールドスタート（ローカル /tmp が空）で append しても S3 既存ログを失わない。
    """
    if not entry.entry_id:
        raise ValueError("entry_id is required (caller must generate uuid4 before calling)")
    if entry.legacy_source:
        raise ValueError("legacy_source=True records must not be appended (read-only flag)")

    path = _new_decision_logs_path(entry.company_id)
    _sync_local_from_s3_if_needed(path, s3_key=f"decision_logs/{entry.company_id}.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(entry.model_dump_json())
        fp.write("\n")
    _maybe_publish_to_s3(path, key=f"decision_logs/{entry.company_id}.jsonl")
    return path


def query_decision_log_entries(
    company_id: str,
    *,
    decision_type: DecisionType | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    decided_by: str | None = None,
    include_legacy_cockpit: bool = True,
    limit: int | None = None,
) -> list[DecisionLogEntry]:
    """新旧両 jsonl を論理統合して返す。decided_at 降順 + limit 切り出し。

    Args:
        company_id: 対象企業 ID
        decision_type: フィルタ（None なら全種）
        from_date / to_date: decided_at の日付範囲フィルタ（両端含む）
        decided_by: 決定者フィルタ（完全一致）
        include_legacy_cockpit: True なら旧 outputs/decisions/<id>.jsonl を
            _lift_legacy_record_to_entry() で変換して merge（既定 True）
        limit: 件数上限（None 無制限）
    """
    entries: list[DecisionLogEntry] = []

    # 1. 新 jsonl からロード
    new_raw = _read_jsonl_text(
        _new_decision_logs_path(company_id),
        s3_key=f"decision_logs/{company_id}.jsonl",
    )
    if new_raw is not None:
        for line in new_raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(DecisionLogEntry.model_validate_json(line))
            except (ValueError, TypeError):
                continue

    # 2. 旧 jsonl からロード（変換）
    if include_legacy_cockpit:
        legacy_raw = _read_jsonl_text(
            _legacy_decisions_path(company_id),
            s3_key=f"decisions/{company_id}.jsonl",
        )
        if legacy_raw is not None:
            for line in legacy_raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = DecisionRecord.model_validate_json(line)
                except (ValueError, TypeError):
                    continue
                entries.append(_lift_legacy_record_to_entry(record))

    # 3. フィルタ適用
    def _matches(e: DecisionLogEntry) -> bool:
        if decision_type is not None and e.decision_type != decision_type:
            return False
        if decided_by is not None and e.decided_by != decided_by:
            return False
        if from_date is not None and e.decided_at.date() < from_date:
            return False
        return not (to_date is not None and e.decided_at.date() > to_date)

    filtered = [e for e in entries if _matches(e)]

    # 4. decided_at 降順ソート
    filtered.sort(key=lambda e: e.decided_at, reverse=True)

    # 5. limit
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _lift_legacy_record_to_entry(record: DecisionRecord) -> DecisionLogEntry:
    """旧 DecisionRecord を DecisionLogEntry(decision_type='cockpit_single') に変換。

    変換ルール:
        - entry_id = record.record_id（UUID4 として再利用、ID 衝突なし）
        - headline = f"[{record.decision}] {record.cockpit_item_id}"
        - rationale = record.rationale
        - selected_measures / rejected_measures = []（cockpit 単発は施策 ID 持たない）
        - sources = []（既存にはない）
        - context_snapshot = snapshot_date のみ + extra に linked_alerts / expected_effect_jpy
        - linked_cockpit_record_id = record.record_id
        - review_due = record.review_due
        - tags = [f"decision:{record.decision}"]
        - legacy_source = True ← Web バッジ表示用
    """
    extra: dict[str, float | str | int | list[str] | None] = {}
    if record.expected_effect_jpy is not None:
        extra["expected_effect_jpy"] = record.expected_effect_jpy
    if record.linked_alerts:
        extra["linked_alerts"] = list(record.linked_alerts)

    snapshot = ContextSnapshot(
        snapshot_date=record.decided_at.date(),
        extra=extra,
    )
    return DecisionLogEntry(
        entry_id=record.record_id,
        company_id=record.company_id,
        decision_type="cockpit_single",
        decided_at=record.decided_at,
        decided_by=record.decided_by,
        headline=f"[{record.decision}] {record.cockpit_item_id}",
        rationale=record.rationale,
        selected_measures=[],
        rejected_measures=[],
        sources=[],
        context_snapshot=snapshot,
        linked_cockpit_record_id=record.record_id,
        review_due=record.review_due,
        tags=[f"decision:{record.decision}"],
        legacy_source=True,
    )


def _read_jsonl_text(path: Path, *, s3_key: str) -> str | None:
    """jsonl ファイルのテキストを返す（S3 backend 利用時は S3 を優先）。"""
    s3_data = _maybe_fetch_from_s3(s3_key)
    if s3_data is not None:
        return s3_data
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _sync_local_from_s3_if_needed(path: Path, *, s3_key: str) -> None:
    """append 前に S3 既存 jsonl をローカルに同期する（Lambda コールドスタート対策）。

    S3 backend 利用時のみ動作。S3 から取得した内容で local file を上書きする
    （local が空 or 古い場合）。ローカルに既に内容があっても、S3 が信頼源として
    優先される（append-only ログのデータ消失を防ぐ）。
    """
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    remote = _maybe_fetch_from_s3(s3_key)
    if remote is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # S3 に既存内容があれば local を S3 で上書き（信頼源は S3）
    path.write_text(remote, encoding="utf-8")


def _maybe_publish_to_s3(path: Path, *, key: str) -> None:
    """S3 backend 利用時はローカル書出後に複製。それ以外は no-op。

    measure_run_store.py のパターンを踏襲。`key` は S3 上のキー（例 "decision_logs/<id>.jsonl"）。
    既存 `get_storage().publish(path)` はローカルパスから S3 キーを自動生成する想定なので、
    `key` 引数は将来の互換性のため受けるが現状は不使用。
    """
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    from core.storage import get_storage

    with contextlib.suppress(Exception):
        get_storage().publish(path)


def _maybe_fetch_from_s3(key: str) -> str | None:
    """S3 backend 利用時は指定キーから取得。それ以外は None。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return None
    from core.storage import get_storage

    storage = get_storage()
    data = storage.read_bytes(key)
    return data.decode("utf-8") if data is not None else None


__all__ = [
    "ComplianceStatus",
    "ContextSnapshot",
    "DecisionLogEntry",
    "DecisionRecord",
    "DecisionStatus",
    "DecisionType",
    "VerdictLevel",
    "append_decision",
    "append_decision_log_entry",
    "load_pending_decisions",
    "query_decision_log_entries",
]
