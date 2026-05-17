# Tier S1 — DecisionLog 永続化 実装計画書

**作成日**: 2026-05-17
**ブランチ**: `docs/decision-log-store`（worktree: `../logi-intel-dashboard.decision-log`）
**親計画**: [plans/decision_log.md](./decision_log.md) v1.0（健一さん 3 点レビュー回答 + Codex 二者議論反映済）
**位置づけ**: 親計画 §4 を「ファイル別の具体的差分・関数シグネチャ・テスト本数・PR チェックリスト」まで詳細化したもの

---

## 0. ファイル別変更サマリ（一覧）

| # | パス | 種別 | 行数（目安） | 衝突回避 |
|---|---|---|---|---|
| 1 | `core/io/decision_log_store.py` | **新規** | 約 290 | A 主担当 |
| 2 | `core/analytics/operation_cockpit.py` | **編集**（re-export のみ） | -45 / +20 | A 主担当（既存ロジック改変なし） |
| 3 | `mcp_server/tools/clo_tools.py` | **追記のみ** | +85 | 共通領域（末尾追記、既存関数改変なし） |
| 4 | `api/routers/clo.py` | **追記のみ** | +110 | 共通領域（末尾追記、既存関数改変なし） |
| 5 | `web/lib/api.ts` | **追記のみ** | +95 | 共通領域（末尾追記、既存関数改変なし） |
| 6 | `web/app/dashboard/cockpit/page.tsx` | **編集**（履歴ペイン追加） | +130 | A 主担当（既存カード表示改変なし） |
| 7 | `core/analytics/standardization_score.py` | **コメント書換のみ**（line 276 付近） | +5 / -3 | A 主担当（ロジック改変なし） |
| 8 | `tests/io/test_decision_log_store.py` | **新規** | 約 320 | A 主担当 |
| 9 | `tests/mcp/test_clo_decision_log_tools.py` | **新規** | 約 140 | A 主担当 |
| 10 | `tests/api/test_clo_router.py` | **追記のみ** | +160 | A 主担当 |
| 11 | `tests/conftest.py` | **編集**（fixture 追加） | +12 | A 主担当 |

**変更行数合計**: 約 1,360 行（テスト含む）。Tier S1 規模感: 中。

---

## 1. Step 1: `core/io/decision_log_store.py` 新規作成（最重要・約 290 行）

### 1.1 完全な関数シグネチャ

```python
"""経営意思決定ログの永続化（outputs/decision_logs/<id>.jsonl + 旧 outputs/decisions/ 統合読出）。

設計方針:
    - 既存 cockpit 単発 DecisionRecord は outputs/decisions/<id>.jsonl に温存（後方互換）
    - 新 DecisionLogEntry スナップショット型は outputs/decision_logs/<id>.jsonl に append
    - query_decision_log_entries() は両ファイルを論理統合して返す（include_legacy_cockpit=True 既定）
    - 旧 DecisionRecord → DecisionLogEntry 変換は _lift_legacy_record_to_entry() で実施
    - LOGI_STORAGE_BACKEND=s3 のとき S3 への複製・取得（measure_run_store.py パターン踏襲）
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.analytics.feasibility_check import VerdictLevel  # 既存 single source（Codex 論点 8 反映）
from core.export.citation import Citation
from core.legal.improvement_check import ComplianceStatus  # Literal["compliant", "borderline", "violation"]

# ---------------------------------------------------------------------------
# 型エイリアス（operation_cockpit.py から移動）
# ---------------------------------------------------------------------------
# 注 (Codex 論点 8 反映): VerdictLevel は feasibility_check.py:38 が既存 single source。
# operation_cockpit.py:98 にも同形 Literal が並存しているが本 PR では触らない（並列セッション衝突回避）。
# 本ファイルでは feasibility_check 経由で import し、operation_cockpit.py 側の重複は次 PR で解消。

DecisionStatus = Literal["pending", "adopt", "postpone", "reject", "escalate"]
"""既存 DecisionRecord のステータス。append-only で履歴保持。"""

DecisionType = Literal[
    "cockpit_single",          # cockpit 1 枠の単発判断（既存 DecisionRecord 由来 / 新規も可）
    "measure_eval_topbottom",  # measure_eval Top3/Bottom3 採用一括判断
    "scenario_sim_baseline",   # scenario_sim baseline + ストレス採択
    "plan_draft_freeze",       # plan_draft 確定/凍結
    "free_form",               # 任意のフリー判断（経営会議議事録等）
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
    decided_by: str
    decision: DecisionStatus
    rationale: str = ""
    expected_effect_jpy: int | None = None
    review_due: date | None = None
    linked_alerts: list[str] = Field(default_factory=list)


class ContextSnapshot(BaseModel):
    """判断時点の数値スナップショット（案 B 拡張版・健一レビュー 2 反映）。"""
    model_config = ConfigDict(frozen=True)

    snapshot_date: date
    # 様式第5 Ⅲ「実施状況」引用に必要
    load_factor_pct: float | None = Field(default=None, ge=0, le=100)
    co2_intensity_g_per_tonkm: float | None = Field(default=None, ge=0)
    f2_score: float | None = Field(default=None, ge=0, le=100)
    j2_trap_count_high: int | None = Field(default=None, ge=0)
    related_kpi_name: str | None = None
    # 様式第5 Ⅵ「改善基準告示遵守状況」引用に必要（Codex 議論 1 で追加）
    wait_time_avg_min: float | None = Field(default=None, ge=0)
    wait_time_max_min: float | None = Field(default=None, ge=0)
    handling_time_avg_min: float | None = Field(default=None, ge=0)
    over_2h_count_total: int | None = Field(default=None, ge=0)
    compliance_overall: ComplianceStatus | None = None
    feasibility_kpi_level: VerdictLevel | None = None
    # 任意拡張（Codex 論点 1 反映: list[str] も許容して linked_alerts を入れられるように）
    extra: dict[str, float | str | int | list[str] | None] = Field(default_factory=dict)


class DecisionLogEntry(BaseModel):
    """経営判断スナップショット 1 件。様式第 5 証跡として引用可能。"""
    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(description="UUID4")
    company_id: str
    decision_type: DecisionType
    decided_at: datetime
    decided_by: str = Field(description="決定者（CLO 名・取締役会・system）")

    headline: str = Field(description="1 行要約")
    rationale: str = Field(default="", description="判断の根拠（複数文 OK）")
    selected_measures: list[str] = Field(default_factory=list)
    rejected_measures: list[str] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    context_snapshot: ContextSnapshot

    linked_cockpit_record_id: str | None = Field(
        default=None,
        description="DecisionRecord.record_id（decision_type='cockpit_single' のとき設定可）",
    )
    review_due: date | None = None
    tags: list[str] = Field(default_factory=list)

    # 旧 jsonl 由来の識別フラグ（Web で「（旧仕様）」バッジ表示用・健一レビュー 3）
    legacy_source: bool = Field(
        default=False,
        description="True なら旧 outputs/decisions/<id>.jsonl からの読出変換結果。write 時は常に False",
    )


# ---------------------------------------------------------------------------
# パス解決
# ---------------------------------------------------------------------------

def _outputs_root() -> Path:
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
    """既存 cockpit 単発 DecisionRecord を旧 jsonl に append（仕様完全維持）。"""

def load_pending_decisions(company_id: str) -> list[DecisionRecord]:
    """旧 jsonl から status=pending の最新レコードを返す（_load_pending_decisions を public 名で公開）。"""


# ---------------------------------------------------------------------------
# Public API: 新規（Tier S1）
# ---------------------------------------------------------------------------

def append_decision_log_entry(entry: DecisionLogEntry) -> Path:
    """新スナップショット型を outputs/decision_logs/<id>.jsonl に append。

    **Codex 論点 1 反映**: entry_id は呼出側（REST / MCP）で `str(uuid.uuid4())` で生成して
    渡すこと。frozen=True のため store 側で書き換えはできない。entry が空文字の entry_id を
    持っている場合は ValueError を返す（防御的検証）。
    """

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
    """新旧両 jsonl を論理統合して返す（Codex 議論 2/3 反映）。

    Args:
        company_id: 対象企業 ID
        decision_type: フィルタ（None なら全種）
        from_date / to_date: decided_at の日付範囲フィルタ
        decided_by: 決定者フィルタ（完全一致）
        include_legacy_cockpit: True なら旧 outputs/decisions/<id>.jsonl も
            _lift_legacy_record_to_entry() で変換して merge（既定 True）
        limit: 件数上限（None 無制限）。decided_at 降順でソート後に切り出し

    Returns:
        decided_at 降順の DecisionLogEntry リスト
    """


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _lift_legacy_record_to_entry(record: DecisionRecord) -> DecisionLogEntry:
    """旧 DecisionRecord を DecisionLogEntry(decision_type='cockpit_single') に変換。

    - entry_id = record.record_id（UUID4 として再利用、ID 衝突なし）
    - headline = f"[{record.decision}] {record.cockpit_item_id}"
    - rationale = record.rationale
    - selected_measures = []（cockpit 単発は施策 ID 持たない）
    - rejected_measures = []
    - sources = []（既存にはない）
    - context_snapshot = ContextSnapshot(snapshot_date=record.decided_at.date())
      （他フィールド全 None / extra={"linked_alerts": record.linked_alerts, "expected_effect_jpy": record.expected_effect_jpy} で軽量保持）
    - linked_cockpit_record_id = record.record_id
    - review_due = record.review_due
    - tags = [f"decision:{record.decision}"]
    - legacy_source = True ← Web バッジ表示用
    """

def _read_jsonl_lines(path: Path) -> list[str]:
    """jsonl を 1 行ずつ str リストで返す。存在しないなら []。壊れた行はスキップ。"""

def _maybe_publish_to_s3(path: Path) -> None:
    """measure_run_store.py と同パターン。S3 backend のみ複製。"""

def _maybe_fetch_from_s3(key: str) -> str | None:
    """measure_run_store.py と同パターン。S3 backend のみ取得。"""


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
```

### 1.2 既存 jsonl レイアウトの互換性

- 旧 `outputs/decisions/<id>.jsonl` の各行は `DecisionRecord.model_dump_json()` フォーマット → 変更しない
- 新 `outputs/decision_logs/<id>.jsonl` の各行は `DecisionLogEntry.model_dump_json()` フォーマット → 新規ファイル
- 統合読出は jsonl 単位で分離読み、Python 内 list で merge してから sort

---

## 2. Step 2: `core/analytics/operation_cockpit.py` の re-export 化（行数差 -45 / +20）

### 2.1 削除

- L284-L312 の `class DecisionRecord` 定義丸ごと（28 行）
- L1144-L1180 の `_load_pending_decisions` + `append_decision` 関数丸ごと（37 行 → 削除総計 65 行のうち、移動 + import 行で実質差し引き -45）

### 2.2 追加

```python
# operation_cockpit.py の冒頭 import 部分に追加
from core.io.decision_log_store import (
    DecisionRecord,          # 後方互換 re-export
    DecisionStatus,          # 後方互換 re-export
    append_decision,         # 後方互換 re-export
    load_pending_decisions as _load_pending_decisions,  # 内部利用名を維持
)
```

### 2.3 `__all__` 維持

```python
# 既存 __all__ をそのまま残す（DecisionRecord / DecisionStatus / append_decision が re-export で引き続き利用可能）
__all__ = [
    "CardState",
    "CockpitItem",
    "CockpitResult",
    "DecisionAxis",
    "DecisionRecord",      # ← re-export 経由
    "DecisionStatus",      # ← re-export 経由
    "EvidenceAxis",
    "ObjectionItem",
    "ObjectionRole",
    "OperationKpiSnapshot",
    "VerdictLevel",        # ← operation_cockpit.py 側で独自定義のまま残す（衝突なし）
    "append_decision",     # ← re-export 経由
    "build_cockpit_summary",
    "build_daily_cockpit",
]
```

### 2.4 衝突回避ガード（**Codex 論点 3 反映: 行番号を実コードに修正**）

- `build_daily_cockpit` / `_objections_for_*` / `OperationKpiSnapshot` / `CockpitItem` / `CockpitResult` 等は**一切変更しない**
- `_load_pending_decisions` を呼んでいる実コード箇所は **L405 のみ**（`build_daily_cockpit` 内）。import エイリアスで吸収して既存呼出を維持
- `from .` 形式の import を新規追加せず、`from core.io.decision_log_store import ...` に統一（既存パターン踏襲）

### 2.5 リグレッション必須 CI ゲート（Codex 論点 3 追加）

- `tests/core/test_analytics_operation_cockpit.py` 全件 pass
- `tests/api/test_clo_router.py` 既存 `POST /decisions/{id}` テスト全件 pass
- 上記が落ちたら **re-export 失敗** とみなして PR は merge 不可

### 2.5 並列セッション衝突確認

- セッション B（facility_store / wait_time_heatmap）は operation_cockpit.py を Read のみ。書き換えない。
- セッション C（ppt_writer / submission_validator）は operation_cockpit.py に依存していない。
- → 本 Step は衝突なし。

---

## 3. Step 3: MCP ツール 2 件追加（`mcp_server/tools/clo_tools.py` 末尾追記・+85 行）

### 3.1 配置（**Codex 論点 4 反映: マーカ + import 集約**）

ファイル末尾の `__all__` 直前に **セクションマーカ `# ─── Tier S1: DecisionLog 永続化 ─────`** を挟んで追記。既存ツールの import / 関数定義は一切変更しない。

import 追加は **マーカ直後にブロックとして集約**:

```python
# ─── Tier S1: DecisionLog 永続化 ─────────────────────────────────────────
# Tier S1 PR でのみ追加。並列セッション B/C は本セクションをスキップして良い。

from core.io.decision_log_store import (
    ContextSnapshot,
    DecisionLogEntry,
    DecisionType,
    append_decision_log_entry,
    query_decision_log_entries,
)
```

ファイル冒頭への import 追加は**しない**（セクション内に閉じる → rebase 競合最小化）。

### 3.2 追加コード雛形

```python
# ─── Tier S1: DecisionLog 永続化 ───────────────────────────────────────────

@mcp.tool()
async def logi_clo_decision_log_record(
    company_id: str,
    decision_type: str,  # cockpit_single / measure_eval_topbottom / scenario_sim_baseline / plan_draft_freeze / free_form
    decided_by: str,
    headline: str,
    rationale: str = "",
    selected_measures: list[str] | None = None,
    rejected_measures: list[str] | None = None,
    snapshot_date: str | None = None,  # ISO date
    snapshot_load_factor_pct: float | None = None,
    snapshot_wait_time_avg_min: float | None = None,
    snapshot_wait_time_max_min: float | None = None,
    snapshot_co2_intensity_g_per_tonkm: float | None = None,
    snapshot_compliance_overall: str | None = None,
    snapshot_feasibility_kpi_level: str | None = None,
    snapshot_extra: dict | None = None,
    linked_cockpit_record_id: str | None = None,
    review_due: str | None = None,
    tags: list[str] | None = None,
) -> ToolResponse:
    """経営意思決定 1 件を outputs/decision_logs/<id>.jsonl に append し、entry_id を返す。

    様式第 5 定期報告の証跡として後日 logi_clo_decision_log_query で引用可能。
    """

@mcp.tool()
async def logi_clo_decision_log_query(
    company_id: str,
    decision_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    decided_by: str | None = None,
    include_legacy_cockpit: bool = True,
    limit: int = 50,
) -> ToolResponse:
    """意思決定履歴を取得（新旧両 jsonl を統合）。decided_at 降順。

    様式第 5 Ⅲ「実施状況」/ Ⅵ「改善基準告示遵守状況」執筆時の引用に使う。
    """
```

### 3.3 ToolResponse 構造

- `summary`: 「N 件の意思決定を記録/取得しました（decision_type=..., decided_by=...）」
- `citations`: 取得したエントリの `sources` の和集合（重複排除）
- `metadata`: `{"entries": [DecisionLogEntry.model_dump(mode='json'), ...]}` 形式
- `freshness_warnings`: 通常空。include_legacy_cockpit=True で旧 jsonl から `legacy_source=True` エントリが含まれる時は 1 件のみ「凡例: 旧仕様（cockpit 単発判断）由来の N 件を含みます」を返す

---

## 4. Step 4: REST 2 エンドポイント追加（`api/routers/clo.py` 末尾追記・+110 行）

### 4.1 配置（**Codex 論点 4 反映: マーカ + import 集約**）

ファイル末尾（既存 `/industry-package/{id}` 等の後）に **セクションマーカ `# ─── Tier S1: DecisionLog 永続化 ─────`** を挟んで追記。既存 `POST /decisions/{id}` は**温存**。

import 追加もマーカ直後に集約（ファイル冒頭には追加しない）:

```python
# ─── Tier S1: DecisionLog 永続化 ─────────────────────────────────────────

from core.io.decision_log_store import (
    ContextSnapshot,
    DecisionLogEntry,
    DecisionType,
    append_decision_log_entry,
    query_decision_log_entries,
)
# 既存 import 部に ComplianceStatus / VerdictLevel が無ければ:
from core.analytics.feasibility_check import VerdictLevel  # noqa: F401 (Pydantic Literal フィールドで使用)
from core.legal.improvement_check import ComplianceStatus  # noqa: F401
```

### 4.2 追加コード雛形（**Codex 論点 5 反映: ContextSnapshotRequest 削除**）

POST 入力は `ContextSnapshot` を直接使う（YAGNI / 1 クラス削減）:

```python
class DecisionLogEntryRequest(BaseModel):
    """POST /decision-logs 入力スキーマ。entry_id / decided_at はサーバー側生成。"""
    decision_type: DecisionType
    decided_by: str
    headline: str
    rationale: str = ""
    selected_measures: list[str] = Field(default_factory=list)
    rejected_measures: list[str] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    context_snapshot: ContextSnapshot  # Codex 論点 5: ContextSnapshot を直接利用
    linked_cockpit_record_id: str | None = None
    review_due: date | None = None
    tags: list[str] = Field(default_factory=list)


@router.post("/decision-logs/{company_id}", status_code=201)
async def decision_log_record(
    company_id: str,
    body: Annotated[DecisionLogEntryRequest, Body()],
) -> dict[str, str]:
    """新 DecisionLogEntry を outputs/decision_logs/<id>.jsonl に append。"""
    _resolve_profile_or_404(company_id)
    entry = DecisionLogEntry(
        entry_id=str(uuid.uuid4()),  # Codex 論点 1: 呼出側で生成
        company_id=company_id,
        decision_type=body.decision_type,
        decided_at=datetime.now(UTC),
        decided_by=body.decided_by,
        headline=body.headline,
        rationale=body.rationale,
        selected_measures=list(body.selected_measures),
        rejected_measures=list(body.rejected_measures),
        sources=list(body.sources),
        context_snapshot=body.context_snapshot,  # 変換不要（直接利用）
        linked_cockpit_record_id=body.linked_cockpit_record_id,
        review_due=body.review_due,
        tags=list(body.tags),
        legacy_source=False,  # write は常に False
    )
    try:
        path = append_decision_log_entry(entry)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"jsonl append 失敗: {exc}") from exc
    return {
        "entry_id": entry.entry_id,
        "company_id": company_id,
        "decision_type": entry.decision_type,
        "log_path": str(path),
    }


@router.get("/decision-logs/{company_id}")
async def decision_log_query(
    company_id: str,
    decision_type: DecisionType | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    decided_by: str | None = Query(default=None),
    include_legacy_cockpit: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    """新旧両 jsonl を統合した意思決定履歴を返す。"""
    _resolve_profile_or_404(company_id)
    entries = query_decision_log_entries(
        company_id,
        decision_type=decision_type,
        from_date=from_date,
        to_date=to_date,
        decided_by=decided_by,
        include_legacy_cockpit=include_legacy_cockpit,
        limit=limit,
    )
    return {
        "company_id": company_id,
        "count": len(entries),
        "entries": [e.model_dump(mode="json") for e in entries],
    }
```

### 4.3 import 追加方針（Codex 論点 4 反映）

§4.1 で示した通り、import 追加は**セクションマーカ直後のブロックに集約**する。ファイル冒頭に追加しない。

---

## 5. Step 5: Web 型定義（`web/lib/api.ts` 末尾追記・+95 行）

**Codex 論点 4 反映**: 同一マーカ `// ─── Tier S1: DecisionLog 永続化 ─────` で区切り、import / 型定義 / 関数を 1 セクションに集約する（rebase 競合最小化）。

### 5.1 追加型（Pydantic 完全一致）

```typescript
// ─── Tier S1: DecisionLog 永続化 ─────────────────────────────────────────

export type DecisionType =
  | "cockpit_single"
  | "measure_eval_topbottom"
  | "scenario_sim_baseline"
  | "plan_draft_freeze"
  | "free_form";

export type ComplianceStatusValue = "compliant" | "borderline" | "violation";

export interface ContextSnapshotPayload {
  snapshot_date: string; // ISO date YYYY-MM-DD
  load_factor_pct: number | null;
  wait_time_avg_min: number | null;
  wait_time_max_min: number | null;
  handling_time_avg_min: number | null;
  over_2h_count_total: number | null;
  co2_intensity_g_per_tonkm: number | null;
  f2_score: number | null;
  j2_trap_count_high: number | null;
  related_kpi_name: string | null;
  compliance_overall: ComplianceStatusValue | null;
  feasibility_kpi_level: VerdictLevel | null;
  extra: Record<string, number | string | null>;
}

export interface DecisionLogEntry {
  entry_id: string;
  company_id: string;
  decision_type: DecisionType;
  decided_at: string; // ISO datetime
  decided_by: string;
  headline: string;
  rationale: string;
  selected_measures: string[];
  rejected_measures: string[];
  sources: Citation[];
  context_snapshot: ContextSnapshotPayload;
  linked_cockpit_record_id: string | null;
  review_due: string | null; // ISO date
  tags: string[];
  legacy_source: boolean; // true なら旧 jsonl 由来（Web で「（旧仕様）」バッジ表示・健一レビュー 3）
}

export interface DecisionLogQueryResponse {
  company_id: string;
  count: number;
  entries: DecisionLogEntry[];
}

export interface DecisionLogRecordRequest {
  decision_type: DecisionType;
  decided_by: string;
  headline: string;
  rationale?: string;
  selected_measures?: string[];
  rejected_measures?: string[];
  sources?: Citation[];
  context_snapshot: ContextSnapshotPayload;
  linked_cockpit_record_id?: string | null;
  review_due?: string | null;
  tags?: string[];
}

export async function fetchDecisionLogEntries(
  companyId: string,
  opts: {
    decisionType?: DecisionType;
    fromDate?: string;
    toDate?: string;
    decidedBy?: string;
    includeLegacyCockpit?: boolean;
    limit?: number;
  } = {},
): Promise<DecisionLogQueryResponse> {
  const qs = new URLSearchParams();
  if (opts.decisionType) qs.set("decision_type", opts.decisionType);
  if (opts.fromDate) qs.set("from_date", opts.fromDate);
  if (opts.toDate) qs.set("to_date", opts.toDate);
  if (opts.decidedBy) qs.set("decided_by", opts.decidedBy);
  if (opts.includeLegacyCockpit === false) qs.set("include_legacy_cockpit", "false");
  if (opts.limit) qs.set("limit", String(opts.limit));
  return request<DecisionLogQueryResponse>(
    `/api/v1/clo/decision-logs/${encodeURIComponent(companyId)}?${qs.toString()}`,
  );
}

export async function recordDecisionLogEntry(
  companyId: string,
  body: DecisionLogRecordRequest,
): Promise<{ entry_id: string; company_id: string; decision_type: DecisionType; log_path: string }> {
  return request(
    `/api/v1/clo/decision-logs/${encodeURIComponent(companyId)}`,
    { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } },
  );
}
```

### 5.2 既存 `DecisionStatus` / `DecisionLogRequest` / `logDecision` は**温存**（cockpit 単発ボタン用）

---

## 6. Step 6: Web 履歴ペイン（`web/app/dashboard/cockpit/page.tsx` 編集・+130 行）

### 6.1 追加領域（既存 3 枠カード下部）

```tsx
// ファイル末尾の <main> 内、既存カード描画の直後に追加
<DecisionHistoryPane companyId={companyId} />

// 同ファイル内に新規コンポーネント定義
function DecisionHistoryPane({ companyId }: { companyId: string }) {
  const [data, setData] = useState<DecisionLogQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchDecisionLogEntries(companyId, { limit: 20 })
      .then((res) => { if (!cancelled) setData(res); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [companyId]);

  if (loading) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data || data.entries.length === 0) {
    return (
      <section className="mt-8 p-4 rounded-lg border border-gray-200 bg-white">
        <h2 className="text-base font-semibold mb-2">過去の意思決定</h2>
        <p className="text-sm text-gray-500">まだ記録された意思決定はありません。</p>
      </section>
    );
  }
  return (
    <section className="mt-8 p-4 rounded-lg border border-gray-200 bg-white">
      <h2 className="text-base font-semibold mb-3">過去の意思決定（最新 {data.count} 件）</h2>
      <ul className="space-y-2">
        {data.entries.map((entry) => (
          <li
            key={entry.entry_id}
            className="border border-gray-100 rounded-md p-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-start justify-between gap-2 text-xs text-gray-600 mb-1">
              <span>{new Date(entry.decided_at).toLocaleString("ja-JP")}</span>
              <span className="flex items-center gap-1">
                <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {DECISION_TYPE_LABEL[entry.decision_type]}
                </span>
                {entry.legacy_source && (
                  <span
                    title="旧 outputs/decisions/*.jsonl 由来の cockpit 単発判断"
                    className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200"
                  >
                    （旧仕様）
                  </span>
                )}
                <span className="text-gray-500">by {entry.decided_by}</span>
              </span>
            </div>
            <div className="text-sm font-medium text-gray-900">{entry.headline}</div>
            {entry.rationale && (
              <p className="text-xs text-gray-600 mt-1 line-clamp-2">{entry.rationale}</p>
            )}
            {entry.selected_measures.length > 0 && (
              <div className="mt-1 text-[11px] text-emerald-700">
                採用: {entry.selected_measures.map((m) => measureLabel(m)).join(" / ")}
              </div>
            )}
            {entry.rejected_measures.length > 0 && (
              <div className="text-[11px] text-rose-700">
                不採用: {entry.rejected_measures.map((m) => measureLabel(m)).join(" / ")}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

const DECISION_TYPE_LABEL: Record<DecisionType, string> = {
  cockpit_single: "コックピット判断",
  measure_eval_topbottom: "施策 Top/Bottom 採択",
  scenario_sim_baseline: "シナリオ baseline 採択",
  plan_draft_freeze: "計画書凍結",
  free_form: "自由記述",
};

function measureLabel(measureId: string): string {
  // web/lib/labels.ts の MEASURE_LABEL 既存マップを引く（無ければ measureId そのまま）
  return MEASURE_LABEL[measureId] ?? measureId;
}
```

### 6.2 既存 `logDecision` 呼出 / カード描画は**一切変更しない**

- 既存 cockpit 単発ボタンは `POST /decisions/{id}` を引き続き呼ぶ（後方互換）
- 履歴ペインは別 useEffect で `GET /decision-logs/{id}` を呼び、両系統が混在表示される（`legacy_source` バッジで区別）

### 6.3 履歴ペイン即時更新（**Codex 論点 6 反映: Tier S1 範囲に含める**）

`onDecisionLogged` コールバック内で履歴ペインの **refresh counter** を更新し、`useEffect` 依存に含めて即時再フェッチする:

```tsx
// page.tsx 上位コンポーネント内
const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

// 既存カード側に渡す
onDecisionLogged={() => {
  setHistoryRefreshKey((k) => k + 1);  // Tier S1: ボタン押下後の即時更新
}}

// 履歴ペインコンポーネント
<DecisionHistoryPane companyId={companyId} refreshKey={historyRefreshKey} />

// useEffect 依存配列
useEffect(() => {
  // fetch...
}, [companyId, refreshKey]);
```

### 6.4 `MEASURE_LABEL` fallback（**Codex 論点 6 反映: 現行 labels.ts に無いため**）

現状 `web/lib/labels.ts` に `MEASURE_LABEL` は存在しない。本 PR で:

- 案 1: `labels.ts` に `MEASURE_LABEL: Record<string, string>` を**追加**（並列セッション衝突リスクあり）
- 案 2: 履歴ペイン内に **local fallback 関数** を定義し、id を **そのまま raw 表示**

**確定: 案 2**（並列セッション衝突回避優先）。fallback 関数:

```tsx
function measureLabel(measureId: string): string {
  // labels.ts に MEASURE_LABEL が将来追加されたら import に切替
  return measureId;  // Tier S1 は raw id 表示。日本語化は別 PR
}
```

---

## 7. Step 7: `standardization_score.py` のコメント書換のみ（+5 / -3）

### 7.1 変更箇所

[core/analytics/standardization_score.py:276](../core/analytics/standardization_score.py#L276) 付近の TODO コメントを更新:

```python
# 変更前:
# decision_log との連動は次 PR の課題（DecisionRecord に measure_id が無い）。

# 変更後:
# Tier S1（PR #X）で core/io/decision_log_store.query_decision_log_entries() を提供済。
# 本モジュールでは未連携。F2 算定ロジック側で decision_log_entries を入力に取って
# selected_measures / rejected_measures から bonus / penalty を算出するのは別 PR。
```

### 7.2 ロジック変更なし。テスト変更なし。

---

## 8. テスト計画詳細（pytest **21 件** - Codex 論点 7 反映: +4 件）

### 8.1 `tests/io/test_decision_log_store.py`（新規・10 件）

```python
"""decision_log_store の永続化・統合読出テスト。"""

def test_T1_append_decision_log_entry_creates_jsonl(tmp_path, monkeypatch):
    """新スナップショット型 1 件を append すると jsonl が 1 行 + 改行で作成される。"""

def test_T2_query_filters_by_decision_type(tmp_path, monkeypatch):
    """decision_type フィルタが効く（measure_eval_topbottom のみ取得）。"""

def test_T3_query_filters_by_date_range(tmp_path, monkeypatch):
    """from_date / to_date フィルタが効く。"""

def test_T4_query_filters_by_decided_by(tmp_path, monkeypatch):
    """decided_by 完全一致フィルタが効く。"""

def test_T5_legacy_append_decision_backward_compat(tmp_path, monkeypatch):
    """旧 append_decision() で outputs/decisions/<id>.jsonl が引き続き書ける。"""

def test_T6_decision_log_entry_skips_invalid_lines(tmp_path, monkeypatch):
    """壊れた jsonl 行はスキップして他の行は読める（前方互換）。"""

def test_T7_query_merges_legacy_when_include_legacy_cockpit_true(tmp_path, monkeypatch):
    """旧 jsonl のレコードが decision_type='cockpit_single' で merge される。
    legacy_source=True フラグが立つ。"""

def test_T8_query_excludes_legacy_when_include_legacy_cockpit_false(tmp_path, monkeypatch):
    """include_legacy_cockpit=False で旧 jsonl が無視される。"""

def test_T9_query_sorts_by_decided_at_desc_and_applies_limit(tmp_path, monkeypatch):
    """decided_at 降順 + limit 切り出しが正しい。"""

def test_T10_context_snapshot_extra_preserves_arbitrary_keys(tmp_path, monkeypatch):
    """ContextSnapshot.extra に任意キー保存 → 再読時も同値で復元（list[str] 含む）。"""

# ─── Codex 論点 7 反映で追加（+4 件） ────────────────────────────────────

def test_T18_s3_backend_publishes_after_append(monkeypatch, mock_s3_storage):
    """LOGI_STORAGE_BACKEND=s3 のとき append_decision_log_entry 後に
    _maybe_publish_to_s3 が呼ばれる（moto / unittest.mock で storage を mock）。"""

def test_T19_s3_backend_falls_back_to_local_when_s3_empty(monkeypatch, mock_s3_storage):
    """LOGI_STORAGE_BACKEND=s3 で S3 上にファイルが無いとき、ローカル jsonl にフォールバックして読める。"""

def test_T20_validation_error_on_invalid_compliance_overall():
    """ContextSnapshot.compliance_overall に 'unknown' 等 Literal 範囲外値で ValidationError。"""

def test_T21_linked_cockpit_record_id_is_optional_for_all_decision_types():
    """linked_cockpit_record_id は全 decision_type で optional（cockpit_single でも必須化しない）。
    クライアントが明示連携したい時のみ設定する仕様確認テスト。"""
```

### 8.2 `tests/mcp/test_clo_decision_log_tools.py`（新規・2 件）

```python
def test_T11_mcp_decision_log_record_returns_entry_id(...):
    """MCP logi_clo_decision_log_record が ToolResponse + entry_id を返す。"""

def test_T12_mcp_decision_log_query_returns_metadata_entries(...):
    """MCP logi_clo_decision_log_query の metadata.entries が降順 list で返る。"""
```

### 8.3 `tests/api/test_clo_router.py` 追記（4 件）

```python
def test_T13_post_decision_logs_returns_201_and_entry_id(client, tmp_path):
    """POST /decision-logs/{id} が 201 + entry_id を返す。"""

def test_T14_get_decision_logs_applies_query_filters(client, tmp_path):
    """GET /decision-logs/{id}?decision_type=... が絞込される。"""

def test_T15_get_decision_logs_unknown_company_404(client):
    """存在しない company_id → 404。"""

def test_T16_e2e_cockpit_then_decision_log_pane_merges(client, tmp_path):
    """E2E: 旧 POST /decisions/{id} で 1 件 + 新 POST /decision-logs/{id} で 1 件 →
    GET /decision-logs/{id} で 2 件返り、legacy_source=True が 1 件含まれる。"""
```

### 8.4 `tests/conftest.py` 編集（1 件・fixture 拡張）

```python
import shutil
from pathlib import Path

import pytest

_MEASURE_RUNS_DIR = Path("outputs/measure_runs")
_DECISIONS_DIR = Path("outputs/decisions")          # 既存 cockpit 単発 jsonl
_DECISION_LOGS_DIR = Path("outputs/decision_logs")  # 新 Tier S1 jsonl


@pytest.fixture(autouse=True)
def cleanup_runtime_dirs() -> None:
    """各テスト後に outputs/measure_runs/ + outputs/decisions/ + outputs/decision_logs/ をリセット。"""
    yield
    for d in (_MEASURE_RUNS_DIR, _DECISIONS_DIR, _DECISION_LOGS_DIR):
        if d.is_dir():
            shutil.rmtree(d)
```

### 8.5 既存テストへの影響（リグレッション確認）

- `tests/core/test_analytics_operation_cockpit.py` で `DecisionRecord` / `append_decision` を import している箇所 → re-export で動くはずだが、import パス変更なしでも動くか実機で確認
- `tests/api/test_clo_router.py` の既存 `POST /decisions/{id}` テスト → 仕様完全維持で pass するはず

---

## 9. 実装順序とブロッカ依存

```
Step 1 (decision_log_store.py 新規)
   ↓
Step 2 (operation_cockpit.py re-export 化)  ← Step 1 完了が前提
   ↓
T1〜T6 / T10 (decision_log_store 単体テスト)  ← Step 1 完了が前提
   ↓
T5 後方互換 + 既存テスト全 pass 確認         ← Step 2 完了が前提
   ↓
Step 3 (MCP)  + Step 4 (REST)  + Step 7 (TODO コメント)  ← 並列可
   ↓
T7〜T9 / T11〜T16 (統合・API テスト)         ← Step 3-4 完了が前提
   ↓
Step 5 (web/lib/api.ts) + Step 6 (cockpit/page.tsx)
   ↓
最終確認: pytest 全 pass + Next.js build + Claude Desktop / curl 実機確認
   ↓
PR 作成
```

---

## 10. 検証チェックリスト（PR 前に全部 ✅）

### 10.1 静的解析
- [ ] `uv run ruff check` 全 pass
- [ ] `uv run ruff format --check` 全 pass
- [ ] `uv run mypy` 全 pass
- [ ] Next.js `npm run lint` 全 pass

### 10.2 テスト
- [ ] `uv run pytest --tb=short -q` 既存全 pass + 新規 17 件全 pass
- [ ] `tests/core/test_analytics_operation_cockpit.py` リグレッションなし
- [ ] `tests/api/test_clo_router.py` 既存 `/decisions/{id}` テスト pass

### 10.3 ビルド
- [ ] `cd web && npm run build` 全 16 ページ build pass
- [ ] cockpit ページが build エラーなく型解決される

### 10.4 実機（CLAUDE.md §7 準拠）
- [ ] `pwsh scripts/dev_api.ps1` で FastAPI 起動 → `curl POST /api/v1/clo/decision-logs/sample_wholesale_01` で 201 + entry_id 確認
- [ ] `curl GET /api/v1/clo/decision-logs/sample_wholesale_01?limit=5` で entries 取得
- [ ] `pwsh scripts/dev_web.ps1` で Next.js 起動 → `/dashboard/cockpit` で履歴ペインが表示
- [ ] Claude Desktop 再起動後 `logi_clo_decision_log_record` / `logi_clo_decision_log_query` が呼び出せる
- [ ] 旧 cockpit 単発ボタン（adopt / postpone / reject）が引き続き動作

### 10.5 数値妥当性（CLAUDE.md §7 経営会議で説明できる数字か）
- [ ] context_snapshot に積載率 / 荷待ち時間を入れて記録 → query で同値で復元
- [ ] decided_at が UTC で保存され、Web で JST に変換表示される
- [ ] 旧 jsonl 由来エントリに「（旧仕様）」バッジが表示される

---

## 11. PR タイトル + ボディ案

### タイトル
```
feat(decision-log): Tier S1 DecisionLog 永続化 (#XX)
```

### ボディ概要

```
## 目的
CLO の「いつ・誰が・何を根拠に・どの施策を採用/不採用にしたか」を永続化し、様式第 5 定期報告の「経営判断の証跡」として再利用できる状態を作る。フェーズ 5.5 Tier S1。

## 主な変更
- core/io/decision_log_store.py 新規（DecisionRecord / DecisionLogEntry / ContextSnapshot + append_decision / append_decision_log_entry / query_decision_log_entries / load_pending_decisions）
- core/analytics/operation_cockpit.py: 既存 DecisionRecord / append_decision を移動 + re-export（後方互換維持）
- mcp_server/tools/clo_tools.py: logi_clo_decision_log_record / logi_clo_decision_log_query 2 件追加
- api/routers/clo.py: POST/GET /api/v1/clo/decision-logs/{id} 2 件追加
- web/lib/api.ts: 型 + fetchDecisionLogEntries / recordDecisionLogEntry 追加
- web/app/dashboard/cockpit/page.tsx: 履歴ペイン追加（旧 jsonl 由来は「（旧仕様）」バッジ表示）
- core/analytics/standardization_score.py:276 TODO コメント書換のみ
- tests: 新規 17 件追加（pytest XXX 件全 pass）

## 設計判断ログ
- plans/decision_log.md v1.0（健一さん 3 点レビュー + Codex 二者議論反映済）
- plans/decision_log_implementation.md（実装計画書）

## Codex 二者議論で確定した範囲縮小
- 様式第 5 連携実装（standardization_score F2 算定）は Tier S1 範囲外（別 PR）
- 既存 outputs/decisions/<id>.jsonl の物理移行スクリプトは Tier S1 範囲外（任意バッチに分離）

## Closes
plans/phase55_update_proposal.md §4 Tier S1
```

---

## 12. 並列セッションへの通知事項（マージ後）

- 共通領域 `mcp_server/tools/clo_tools.py` / `api/routers/clo.py` / `web/lib/api.ts` に 末尾追記済
- セッション B / C が同じファイルを編集中なら rebase で吸収必要
- `tests/conftest.py` の cleanup fixture を `outputs/decisions/` + `outputs/decision_logs/` まで拡張 → 他セッションのテストにも好影響（クロス汚染防止）
- 既存 `DecisionRecord` の import パスは `core.analytics.operation_cockpit` のままで動く（re-export）

---

## 13. 変更履歴

| Version | 日付 | 内容 |
|---|---|---|
| v1.0 | 2026-05-17 | 初稿（Codex レビュー前） |
| v1.1 | 2026-05-17 | **Codex 7 件指摘反映**: 論点 1 (entry_id 呼出側生成 + extra 型拡張) / 論点 3 (行番号修正 + リグレッション CI ゲート明記) / 論点 4 (3 ファイルへセクションマーカ + import 集約) / 論点 5 (ContextSnapshotRequest 削除) / 論点 6 (履歴ペイン refresh counter + MEASURE_LABEL raw fallback) / 論点 7 (テスト +4 件 → 21 件) / 論点 8 (VerdictLevel は feasibility_check.py を single source として import) |

**最終更新**: 2026-05-17（v1.1 / Codex 全 7 件反映 / 実装着手 GO 待ち）
