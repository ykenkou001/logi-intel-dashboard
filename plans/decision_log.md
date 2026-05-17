# Tier S1 — DecisionLog 永続化 詳細計画

**作成日**: 2026-05-17
**ブランチ**: `docs/decision-log-store`（origin/main から派生 / worktree: `../logi-intel-dashboard.decision-log`）
**位置づけ**: [plans/phase55_update_proposal.md](./phase55_update_proposal.md) §4 Tier S1 の詳細実装計画
**運用**: CLAUDE.md §9.4「設計議論の結論は plans に残す」

---

## 0. 着手前サマリ（健一さんレビュー対象）

### 0.1 想定と現実のギャップ（重要）

セッション開始時の仕様（指示メッセージ）は「`core/io/decision_log_store.py` を**新規**作成」だったが、コード調査の結果、**既存実装の一部はすでに存在する**ことが判明した。

| 領域 | 既存実装の状況 |
|---|---|
| データモデル `DecisionRecord` | [core/analytics/operation_cockpit.py:284](../core/analytics/operation_cockpit.py#L284)（Pydantic v2 frozen）。`cockpit_item_id` 紐付きの**単発決定**用 |
| 永続化 `append_decision` / `_load_pending_decisions` | [core/analytics/operation_cockpit.py:1144-1180](../core/analytics/operation_cockpit.py#L1144-L1180)。`outputs/decisions/<id>.jsonl`（append-only jsonl） |
| REST `POST /api/v1/clo/decisions/{company_id}` | [api/routers/clo.py:789](../api/routers/clo.py#L789)。`DecisionLogRequest` 入力スキーマあり |
| Web `logDecision` ボタン | [web/app/dashboard/cockpit/page.tsx:105-114](../web/app/dashboard/cockpit/page.tsx#L105-L114)。adopt / postpone / reject の 3 ボタン稼働中 |
| MCP `logi_clo_decision_log_*` | **未実装** |
| REST GET（履歴取得） | **未実装**（読出は cockpit ビルダー側の `_load_pending_decisions` で pending のみ拾うだけ） |
| Web 履歴ペイン | **未実装**（書込ボタンのみ） |
| `core/io/decision_log_store.py` | **未存在**（永続化が `core/analytics/operation_cockpit.py` に embedded） |
| `selected_measures` / `rejected_measures` を持つスナップショット型 | **未存在**（`measure_eval` Top3 採用や `scenario_sim` baseline 採択は記録できない） |
| 様式第 5 定期報告での証跡再利用 | **未連携**（[core/analytics/standardization_score.py:276](../core/analytics/standardization_score.py#L276) に「decision_log との連動は次 PR の課題」と明記） |

### 0.2 Tier S1 の真のスコープ（再定義）

- ✅ `core/io/decision_log_store.py` を**新規**作成し、既存 `DecisionRecord` / `append_decision` / `_load_pending_decisions` を**移動 + 拡張**する（`operation_cockpit.py` には re-export で後方互換維持）
- ✅ **新スナップショット型 `DecisionLogEntry`** を追加（`measure_eval` Top3 採用一括 / `scenario_sim` baseline 採択 / `cockpit` 単発判断を統合できる上位型）
- ✅ MCP `logi_clo_decision_log_record` / `logi_clo_decision_log_query` 追加（追記のみ）
- ✅ REST `POST/GET /api/v1/clo/decision-logs/{company_id}` 追加（追記のみ・既存 `/decisions/{id}` とは別エンドポイント）
- ✅ Web `web/lib/api.ts` 型追加 + `/dashboard/cockpit` に意思決定履歴ペイン追加

### 0.3 並列セッションとの衝突回避

- **触らない**: `core/io/facility_store.py`（B）/ `core/analytics/wait_time_heatmap.py`（B）/ `core/export/ppt_writer.py`（C）/ `core/validators/submission_validator.py`（C 読出）
- **追記のみ**（既存関数編集禁止）: `mcp_server/tools/clo_tools.py` / `api/routers/clo.py` / `web/lib/api.ts`
- **編集 OK**（主担当）: `core/analytics/operation_cockpit.py`（既存 `DecisionRecord` 移動 + re-export のみ、ロジック書換は禁止）/ `web/app/dashboard/cockpit/page.tsx`（履歴ペイン追加）

---

## 1. 目的（健一さん指示の再掲）

CLO の「いつ・誰が・何を根拠に・どの施策を採用/不採用にしたか」を永続化し、
**様式第 5 定期報告の「経営判断の証跡」として再利用できる状態**を作る。

### 1.1 様式第 5 定期報告での具体的再利用シナリオ

- 様式第 5 Ⅲ「実施状況」: 施策の採用・不採用判断とその根拠を経営判断ログから引用
- 様式第 5 Ⅵ「改善基準告示遵守状況」: cockpit 軸 A 単発判断（adopt / postpone / reject）の累積を月次集計
- 経営会議資料: `decided_by` / `decided_at` / `rationale` / `sources` の 4 列で監査可能性を担保

---

## 2. データモデル設計（**Codex 二者議論の対象**）

### 2.1 既存 `DecisionRecord`（変更しない・移動のみ）

```python
class DecisionRecord(BaseModel):
    """既存。cockpit 1 枠の単発決定（adopt/postpone/reject/escalate）。"""
    model_config = ConfigDict(frozen=True)
    record_id: str           # UUID4
    company_id: str
    cockpit_item_id: str     # CockpitItem.item_id への参照
    decided_at: datetime
    decided_by: str
    decision: DecisionStatus
    rationale: str = ""
    expected_effect_jpy: int | None = None
    review_due: date | None = None
    linked_alerts: list[str] = []
```

### 2.2 新規 `DecisionLogEntry`（スナップショット型・Tier S1 の核心）

```python
DecisionType = Literal[
    "cockpit_single",          # 既存 cockpit カード 1 枠の決定（DecisionRecord ラッパ）
    "measure_eval_topbottom",  # measure_eval Top3/Bottom3 採用一括判断
    "scenario_sim_baseline",   # scenario_sim baseline + 7 ストレスの採択
    "plan_draft_freeze",       # plan_draft の確定 / 凍結
    "free_form",               # 任意のフリー判断（経営会議議事録等）
]

class DecisionLogEntry(BaseModel):
    """経営判断スナップショット 1 件。様式第 5 証跡として引用可能。"""
    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(description="UUID4")
    company_id: str
    decision_type: DecisionType
    decided_at: datetime
    decided_by: str = Field(description="決定者（CLO 名・取締役会・system）")

    # 判断の中身
    headline: str = Field(description="1 行要約（経営会議資料での表題）")
    rationale: str = Field(description="判断の根拠（複数文 OK）")
    selected_measures: list[str] = Field(
        default_factory=list,
        description="採用した measure_id（ALL_MEASURES.measure_id を参照）",
    )
    rejected_measures: list[str] = Field(
        default_factory=list,
        description="不採用とした measure_id（judgment trail 用）",
    )

    # 監査可能性
    sources: list[Citation] = Field(
        default_factory=list,
        description="判断根拠の出典（既存 Citation 型を流用）",
    )

    # コンテキスト（Codex 議論の核心）
    context_snapshot: ContextSnapshot = Field(
        description="判断時点のスナップショット（軽量埋込）",
    )

    # 関連付け
    linked_cockpit_record_id: str | None = Field(
        default=None,
        description="DecisionRecord.record_id（decision_type='cockpit_single' のとき必須）",
    )
    review_due: date | None = None
    tags: list[str] = Field(default_factory=list, description="検索用タグ")
```

### 2.3 `ContextSnapshot`（**Codex 議論の最重要トピック**）

3 案ある。Codex に判断を仰ぐ。

#### 案 A: フル埋込（重い・自己完結）

```python
class ContextSnapshot(BaseModel):
    """フル埋込: 判断時点の入力データを全部抱える。"""
    cockpit_result_dump: dict | None = None    # CockpitResult.model_dump()
    measure_eval_dump: dict | None = None      # MeasureEvalResult.model_dump()
    scenario_sim_dump: dict | None = None      # ScenarioSimResult.model_dump()
```

- 利点: 後日 cockpit/measure_eval の出力ロジックが変わっても、過去判断時点の数値が完全保存される
- 欠点: 1 件あたり数 KB〜数十 KB。jsonl ファイルが急膨張する

#### 案 B: キー数値のみ抜粋（軽量・標準）

**【Codex 議論 1 反映: 様式第 5 Ⅵ「改善基準告示遵守状況」の引用要件から、wait_time_max / handling_time / over_2h_count / compliance_overall / feasibility_kpi_level を追加。operating_profit_ratio は extra に降格】**
**【健一さんレビュー 2 反映: `compliance_overall` / `feasibility_kpi_level` は既存 Literal 型を再利用して固める】**

```python
from core.legal.improvement_check import ComplianceStatus  # Literal["compliant", "borderline", "violation"]
from core.analytics.operation_cockpit import VerdictLevel  # Literal["green", "yellow", "red"]

class ContextSnapshot(BaseModel):
    """抜粋: 経営判断に直結する数値のみ。"""
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
    compliance_overall: ComplianceStatus | None = None  # Literal 型で固定（健一レビュー 2）
    feasibility_kpi_level: VerdictLevel | None = None    # Literal 型で固定（健一レビュー 2）
    # 任意拡張（operating_profit_ratio / Top3 順位・total_score・効果額等を入れる）
    extra: dict[str, float | str | int | None] = Field(default_factory=dict)
```

**注**: `VerdictLevel` は `core/analytics/operation_cockpit.py:98` で定義済みだが、Step 1 で `decision_log_store.py` に移動はしない（並列セッション衝突回避 + 軸 B feasibility 由来の型として `operation_cockpit` に残すのが意味的に正しい）。`feasibility_check` モジュールにも同形の `VerdictLevel` があるが、import 元は `operation_cockpit` に統一する。

- 利点: 1 件数百 B〜1 KB。jsonl で運用可能 + 様式第 5 Ⅲ / Ⅵ 両方の証跡要件を満たす
- 欠点: 後日「あの時の cockpit 全画面」を再現できない（数値の単体引用のみ）

#### 案 C: 参照キー + 別ファイル（中庸・複雑）

```python
class ContextSnapshot(BaseModel):
    """参照: 別ファイル（cockpit_snapshots/<id>/<date>.json 等）を引く。"""
    snapshot_date: date
    cockpit_snapshot_path: str | None = None
    measure_eval_snapshot_path: str | None = None
    summary_metrics: dict[str, float | str | int | None] = Field(default_factory=dict)
```

- 利点: cockpit_snapshots/ 既存ファイル群（[operation_cockpit.py:17](../core/analytics/operation_cockpit.py#L17)）を再利用、jsonl は軽量
- 欠点: 参照先ファイルの整合性管理が必要（古い snapshot が消えると壊れる）

### 2.4 確定: 案 B 拡張版（Codex 議論 1 反映）

**案 B（抜粋）を基本**、`extra` フィールドで拡張余地を残す。理由:

- 案 A は「監査可能性最強」だが、`outputs/decision_logs/<id>.jsonl` が数 MB に達する見込み（CLO 1 社が 3 年間運用すると数百〜数千エントリ）
- 案 C は cockpit_snapshots/ の保管期間と decision_logs/ の保管期間を独立に決められないと整合性が崩れる
- 案 B は「経営判断に直結する数値（積載率・荷待ち・営業利益率・F2・J2）」が判断時点で何だったかさえ残れば、様式第 5 引用には十分

**Codex 議論 1 で追加された必須フィールド**: `wait_time_max_min` / `handling_time_avg_min` / `over_2h_count_total` / `compliance_overall` / `feasibility_kpi_level`（様式第 5 Ⅵ「改善基準告示遵守状況」引用に必要）。

**`extra` に入れるべき任意フィールド**（Codex 議論 5 反映）:
- `operating_profit_ratio`（scenario_sim 由来の財務指標）
- Top3/Bottom3 採用時は当時の `rank` / `total_score` / `expected_effect_jpy` を `topbottom_<measure_id>_rank` 等のキーで保存

---

## 3. ストレージ設計

### 3.1 ファイル形式

- 保存先: `outputs/decision_logs/<company_id>.jsonl`（既存 `outputs/decisions/<id>.jsonl` とは別ファイル）
- 形式: jsonl（既存 cockpit decisions と同じ append-only 方式に合わせる）
- 既存 `outputs/decisions/<id>.jsonl`（cockpit 単発記録）は**温存**し、新型は別ファイルに分離（後方互換の安全策）

### 3.2 既存 `DecisionRecord` との関係（Codex 議論対象 ②）

3 案ある。

| 案 | 内容 | 既存 jsonl への影響 |
|---|---|---|
| α | 既存を温存・並行追加。`DecisionLogEntry.linked_cockpit_record_id` で参照 | 既存ファイルそのまま |
| β | 既存を `DecisionLogEntry(decision_type="cockpit_single")` に吸収。既存 jsonl を新 jsonl へ移行 | 既存ファイル移行スクリプト必要 |
| γ | 既存を deprecate、新 jsonl のみへ集約 | 既存 jsonl は読み取り専用 |

**確定: 案 α + 統合読出ビュー（Codex 議論 2/3 反映）**

- 物理ファイルは分離（既存 `outputs/decisions/<id>.jsonl` + 新 `outputs/decision_logs/<id>.jsonl`）
- ただし新 `query_decision_log_entries()` および新 REST `GET /api/v1/clo/decision-logs/{id}` は **論理的に両方を統合して返す**:
  - 新 `outputs/decision_logs/<id>.jsonl` のエントリはそのまま
  - 既存 `outputs/decisions/<id>.jsonl` のエントリは `decision_type="cockpit_single"` の `DecisionLogEntry` に**読出時変換**（書込時の移行は不要）
  - これにより「cockpit_single が片方にしか無い」抜け漏れリスクを回避（Codex 議論 2 で指摘された懸念に対応）
- 既存 `POST /api/v1/clo/decisions/{id}` フローは温存（Web ボタンが壊れない）

理由: 後方互換ゼロコスト + 履歴ペインの完全性を両立。将来の一元化バッチは別 PR で任意実行。

### 3.3 S3 backend 対応

`measure_run_store.py` の `_maybe_publish_to_s3` / `_maybe_fetch_from_s3` パターンを踏襲する（Lambda 上の永続化）。

---

## 4. 実装計画（順序）

### Step 1: `core/io/decision_log_store.py` 新規作成

- `DecisionRecord` を `core/analytics/operation_cockpit.py` から移動
- `DecisionLogEntry` / `DecisionType` / `ContextSnapshot` を新規定義（Codex 議論確定後）
- `append_decision()` を移動（既存 jsonl パス温存）
- `append_decision_log_entry()` を新規追加（新 jsonl パス）
- `load_decisions()` / `load_pending_decisions()` を移動
- `query_decision_log_entries(company_id, *, decision_type=None, from_date=None, to_date=None, decided_by=None, include_legacy_cockpit=True)` を新規追加。**Codex 議論 2/3 反映**: `include_legacy_cockpit=True`（既定）で旧 `outputs/decisions/<id>.jsonl` を `DecisionLogEntry(decision_type="cockpit_single")` に変換して merge
- 旧 `DecisionRecord` → `DecisionLogEntry` 変換ヘルパ `_lift_legacy_record_to_entry()` を private 関数として追加
- S3 backend 対応（既存 `measure_run_store.py` パターン踏襲）

### Step 2: `core/analytics/operation_cockpit.py` の re-export 化

- `DecisionRecord` / `append_decision` / `_load_pending_decisions` を `decision_log_store` から import し直して re-export
- 既存 `__all__` を維持
- **既存ロジック（`build_daily_cockpit` 等）は一切書き換えない**（並列セッション衝突回避）

### Step 3: MCP ツール 2 件追加（`mcp_server/tools/clo_tools.py` 末尾に追記）

- `logi_clo_decision_log_record(company_id, decision_type, decided_by, headline, rationale, selected_measures=[], rejected_measures=[], sources=[], context_snapshot={}, linked_cockpit_record_id=None, review_due=None, tags=[])`
- `logi_clo_decision_log_query(company_id, *, decision_type=None, from_date=None, to_date=None, decided_by=None, limit=50)`

### Step 4: REST 2 エンドポイント追加（`api/routers/clo.py` 末尾に追記）

- `POST /api/v1/clo/decision-logs/{company_id}`: 新 `DecisionLogEntry` を append
- `GET /api/v1/clo/decision-logs/{company_id}?decision_type=...&from=...&to=...&decided_by=...`: クエリ実行

### Step 5: Web 型定義（`web/lib/api.ts` に追記のみ）

- `DecisionType` / `DecisionLogEntry` / `ContextSnapshot` 型を Pydantic と完全一致で定義
- `fetchDecisionLogEntries(companyId, opts)` / `recordDecisionLogEntry(companyId, body)` 関数

### Step 6: Web 履歴ペイン（`web/app/dashboard/cockpit/page.tsx` 編集）

- 既存 3 枠カード表示の**下部**に「過去の意思決定」ペインを追加
- ページロード時に `fetchDecisionLogEntries(companyId, { limit: 20 })` で履歴を取得
- decision_type / decided_at / decided_by / headline / selected_measures（measure 日本語名で表示）を時系列で表示
- 既存 cockpit ボタン押下後は新 jsonl ではなく既存 `/decisions/{id}` を引き続き呼ぶ（後方互換）

### Step 7: 様式第 5 連携の足場（**Codex 議論 6 で却下 → Tier S1 では入れない**）

- `core/analytics/standardization_score.py:276` の「decision_log との連動は次 PR の課題」は **Tier S1 範囲外**
- Codex 議論 6 の根拠: Tier S1 の主目的は永続化ストアと記録/照会経路。計算入力だけ先に広げると未使用フィールドを増やすだけで F2 算定の実効連携は進まない
- **対応**: `standardization_score.py:276` の TODO コメントを更新し「Tier S1（PR #X）で `core/io/decision_log_store.query_decision_log_entries()` を提供済。本 PR では未連携。F2 算定ロジック連携は別 PR で `compute_standardization_score` の入力・F2 計算・テストをまとめて変更する」と書き換えるのみ

---

## 5. テスト計画（pytest 15 件以上を目安）

| # | テスト対象 | ファイル |
|---|---|---|
| T1 | `decision_log_store.append_decision_log_entry()` の append-only 動作 | `tests/io/test_decision_log_store.py`（新規） |
| T2 | `query_decision_log_entries()` の decision_type フィルタ | 同上 |
| T3 | `query_decision_log_entries()` の from_date / to_date フィルタ | 同上 |
| T4 | `query_decision_log_entries()` の decided_by フィルタ | 同上 |
| T5 | 既存 `append_decision` 後方互換（旧 jsonl パスへの書込維持） | 同上 |
| T6 | `DecisionLogEntry.model_validate_json` で旧フォーマットを読まない（隔離保証） | 同上 |
| T7 | S3 backend で `_maybe_publish_to_s3` が呼ばれる | 同上 |
| T8 | S3 backend で `_maybe_fetch_from_s3` が空ならローカルフォールバック | 同上 |
| T9 | `linked_cockpit_record_id` 整合性（cockpit_single のみ必須） | 同上 |
| T10 | ContextSnapshot 案 B `extra` フィールドの任意キー保存 | 同上 |
| T11 | MCP `logi_clo_decision_log_record` の Pydantic 入力検証 | `tests/mcp/test_clo_decision_log_tools.py`（新規） |
| T12 | MCP `logi_clo_decision_log_query` の出力構造（ToolResponse 形状） | 同上 |
| T13 | REST `POST /decision-logs/{id}` の 201 応答 + entry_id 返却 | `tests/api/test_clo_router.py`（追記） |
| T14 | REST `GET /decision-logs/{id}` の query 文字列での絞込 | 同上 |
| T15 | REST `GET /decision-logs/{id}` で存在しない company_id → 404 | 同上 |
| T16 | E2E: cockpit 単発記録 → 履歴ペインに 1 件出現（Web シナリオ） | `tests/api/test_clo_router.py`（追記） |
| T17 | conftest cleanup fixture が `outputs/decision_logs/*.jsonl` を消去（テスト隔離） | `tests/conftest.py`（既存 fixture 拡張） |

---

## 6. 完了基準（健一さん仕様の再掲）

- ✅ pytest 全 pass（新規 15 件以上）
- ✅ MCP `logi_clo_decision_log_record` / `logi_clo_decision_log_query` が Claude Desktop で動作確認済み
- ✅ REST `POST/GET /api/v1/clo/decision-logs/{id}` が curl で動作確認済み
- ✅ Web `/dashboard/cockpit` に意思決定履歴ペインが表示される
- ✅ PR 作成（タイトル例: `feat(decision-log): Tier S1 DecisionLog 永続化`）
- ✅ マージ後、worktree を片付ける（`git worktree remove ../logi-intel-dashboard.decision-log && git worktree prune`）

---

## 7. Codex 二者議論のスコープ（独立評価依頼）

CLAUDE.md §9.4 に従い、以下 6 点を Codex に投げる。

### 議論 1: `ContextSnapshot` 設計（最重要）
案 A（フル埋込）/ 案 B（抜粋）/ 案 C（参照）のトレードオフ。Claude 推奨は案 B。様式第 5 定期報告の証跡要件から逆算した「最低限のフィールド」を Codex に評価依頼。

### 議論 2: 既存 `DecisionRecord` との関係
案 α（並行追加）/ 案 β（一元化）/ 案 γ（deprecate）。Claude 推奨は案 α。

### 議論 3: ファイル分離 vs 統合
`outputs/decisions/<id>.jsonl`（既存・cockpit 単発）と `outputs/decision_logs/<id>.jsonl`（新・スナップショット）を分離するか統合するか。

### 議論 4: `decision_type` enum の網羅性
`cockpit_single` / `measure_eval_topbottom` / `scenario_sim_baseline` / `plan_draft_freeze` / `free_form` の 5 値で十分か。`certified_match` / `feasibility_check` / `submission_validate` の判断も型化すべきか。

### 議論 5: `selected_measures` / `rejected_measures` の表現
`measure_id` の文字列リスト（軽量）vs `MeasureScore` 全埋込（重い・自己完結）。Claude 推奨は前者。

### 議論 6: 様式第 5 連携の足場（Tier S1 範囲）
`standardization_score.py:276` の遺し課題を Tier S1 で部分解消するか、別 PR に分けるか。

---

## 8. 議論経緯ログ（Codex 勧告反映）

CLAUDE.md §9.4 に従い、Codex 二者議論（2026-05-17 / gpt-5.5 想定）の結果を記録する。

| # | Codex 勧告 | Claude 判断 | 反映先 |
|---|---|---|---|
| 1 | ContextSnapshot 案 B に `wait_time_max_min` / `handling_time_avg_min` / `over_2h_count_total` / `compliance_overall` / `feasibility_kpi_level` を追加（様式第 5 Ⅵ 引用要件）。`operating_profit_ratio` は `extra` に降格 | ◎ 採用 | §2.3 案 B / §2.4 |
| 2 | Tier S1 では案 α（並行追加）で OK だが、新 `query_decision_log_entries` で旧 `outputs/decisions` を読み込む **統合読出ビュー** を用意。移行は任意バッチに分離 | ◎ 採用 | §3.2 / §4 Step 1 |
| 3 | 物理ファイルは分離、論理 API/表示は統合。新 GET は新旧両方を返す（少なくとも `cockpit_single` は旧 jsonl を変換表示） | ◎ 採用 | §3.2 / §4 Step 1 / Step 4 |
| 4 | `decision_type` 5 enum + `tags` で吸収。`certified_match` / `feasibility_check` / `submission_validate` 自体は採否判断ではなく分析ツール | ◎ 採用 | §2.2 enum 変更なし |
| 5 | `selected_measures` / `rejected_measures` は `list[str]` 維持。Top3/Bottom3 当時の `rank` / `total_score` / `expected_effect_jpy` は `context_snapshot.extra` に保存 | ◎ 採用 | §2.4 extra ガイド追記 |
| 6 | 様式第 5 連携（`standardization_score.py:276` の遺し課題）は **Tier S1 では入れない**。永続化ストアと記録/照会経路の安定化に専念 | ◎ 採用（却下→ Step 7 範囲縮小） | §4 Step 7 |

**Codex 総合所感**: 「S1 は保存境界を固め、集計連携は次 PR に分けるべき」→ Claude 全面同意。Tier S1 のスコープを「永続化レイヤ + 統合読出 + MCP/REST/Web 公開」に絞る方針で確定。

### Codex 議論で確定したスコープ縮小

- ❌ `standardization_score.py` の F2 連携実装は Tier S1 範囲外（TODO コメント書換のみ）
- ❌ 既存 `outputs/decisions/<id>.jsonl` の物理移行スクリプトは Tier S1 範囲外（任意バッチに分離）

### Codex 議論で確定したスコープ追加

- ✅ `ContextSnapshot` の必須フィールド 5 件追加（議題 1）
- ✅ `query_decision_log_entries(include_legacy_cockpit=True)` の統合読出機能（議題 2/3）
- ✅ `_lift_legacy_record_to_entry()` private ヘルパ（議題 3）
- ✅ Top3/Bottom3 当時順位・スコアの `context_snapshot.extra` 保存ガイド（議題 5）

### 議論で却下されなかったが追加で出た盲点（Claude 単独追加）

- T17 conftest cleanup fixture に `outputs/decision_logs/*.jsonl` の追加が必要（既存テスト隔離との整合）
- Web 履歴ペインで「旧 jsonl 由来エントリ」を識別表示すべきか（バッジ等）→ 健一さんレビューで判断

---

## 9. 健一さんレビュー回答（2026-05-17）

全 3 点 OK 回答済。確定事項:

| # | 内容 | 確定 | 反映先 |
|---|---|---|---|
| 1 | 「移動 + 拡張」アプローチ（既存 `DecisionRecord` を `core/io/decision_log_store.py` に移動 + `operation_cockpit.py` から re-export で後方互換） | ✅ 採用 | §4 Step 1, Step 2 |
| 2 | `ContextSnapshot.compliance_overall` / `feasibility_kpi_level` は **Pydantic Literal 型で固める**（既存 `ComplianceStatus` / `VerdictLevel` を import して再利用） | ✅ 採用 | §2.3 案 B（下記更新） |
| 3 | Web 履歴ペインで旧 `outputs/decisions/<id>.jsonl` 由来エントリには **「（旧仕様）」バッジを付ける**（透過表示しない） | ✅ 採用 | §4 Step 6, [plans/decision_log_implementation.md](./decision_log_implementation.md) |

### 確定後の進め方

1. ✅ plans/decision_log.md を **v1.0 として fix**（本ファイル）
2. ✅ 実装計画書 [plans/decision_log_implementation.md](./decision_log_implementation.md) を起こす
3. ⏳ Codex に実装計画を独立評価依頼
4. ⏳ 実装着手（§4 Step 1〜6 / Step 7 は TODO 書換のみ）
5. ⏳ pytest 全 pass → PR 作成 → マージ → worktree 片付け

---

**最終決定者**: 健一
**最終更新**: 2026-05-17（健一さん 3 点レビュー回答反映 / **v1.0 fix** / 実装計画書へ移行）
