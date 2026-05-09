# コードレビュー結果 — フェーズ5.0 完了直後の whole-repo リファクタリング

**作成日**: 2026-05-09
**ブランチ**: `refactor/codebase-cleanup-202605`
**目的**: 効率的な実装への改善とロジック強化（CLAUDE.md §1.5 ミッション準拠）
**前提**: pytest 835 件全 pass / Next.js build 16 ページ全 pass を維持

---

## Phase 1: 静的解析サマリ

| 項目 | 結果 |
|---|---|
| `ruff check core/ api/ mcp_server/` | ✅ All checks passed |
| `ruff format --check ...` | ❌ **73 ファイルがフォーマット未適用**（15 ファイルのみ既適用） |

→ Phase 4 の最初に `ruff format` を全 Python に一括適用する（差分が大きいため独立コミット推奨）。

---

## Phase 2: 領域別品質分析

### 1. core/（68 ファイル / 18,659 行）

#### 強み
- 例外チェーン（HttpClientError → カスタム例外）が一貫
- `core/static/_freshness.py` で鮮度管理を一元化
- `Citation` モデルが多形態出力対応（dict / footnote / markdown）
- `core/analytics/waste_trap.py` のセーフガード閾値が定数化

#### 高優先度の問題

**[H1] Summary 関数の同一パターン反復** — `core/analytics/*.py` 15+ ファイル
- 問題: 各 analytics モジュールが `def build_*_summary(result) -> str` を持ち、内部で `lines = []` → `lines.append(...)` → `"\n".join(lines)` を繰り返す
- `core/analytics/plan_draft.py:448-479` で戻り値を `.split("\n")[2:]` `[1:]` でスライスしており、見出し形式の差異に脆弱
- 推奨: Summary 関数の戻り値を `SummaryResult(title: str, body: list[str])` 型に変更、または見出し位置を共通化
- リスク: 中（テンプレート化したセクション分割の検証が必須）

**[H2] 通貨換算マジックナンバーの分散** — 51 箇所（grep `/ 1e8`, `/ 1e6`, `/ 1e4`）
- 問題: `revenue_jpy / 1e8` → "億円", `/ 1e6` → "百万円", `/ 1e4` → "万円" が出力ロジックに散在。`:.1f` `:.2f` `,.0f` 桁丸めも混在
- 推奨: `core/export/formatter.py` を新設し `format_jpy(amount, unit="oku" | "million" | "man") -> str` を提供
- 影響範囲: PPT / Excel / Markdown / Word の全成果物
- リスク: 中（既存テンプレート文字列内の埋め込みロジック抽出に検証必須）

#### 中優先度の問題

**[M1] `type: ignore` の根拠不明** — `certified_match.py:101`, `plan_draft.py:165, 180, 182`
- 推奨: `cast()` 利用または `MeasureType` を `Literal["modal_shift", ...]` に厳密化

**[M2] `Any` の無制限使用** — `cache.py`, `clients/*.py` 等で 30+ 箇所
- 推奨: TypedDict（`CacheEntry`, `FuelPrice`, `EstStatData`）を段階導入

**[M3] 巨大モジュール** — `ppt_writer.py:1560行`, `operation_cockpit.py:1453行`
- 推奨: 各々 3 ファイルに分割（`ppt_writer.py` → `{layout, chart_builder, slide_builder}.py`、`operation_cockpit.py` → `{cockpit_builder, snapshot_store, decision_log}.py`）
- リスク: 高（インポート再配線と pytest 影響範囲の両立検証が必要） → 今回スコープ外（次回 PR 候補）

#### 低優先度
- L1: `sample_company.py` ハードコード ID 列挙（テストデータ管理）
- L2: None 安全性 guard clause の形式不統一
- L3: `plan_draft.py:345-346` で `0.7 × 0.6 = 0.42` 等の重複計算を中間値化

---

### 2. api/（10 ファイル / 1,445 行） + mcp_server/（10 ファイル / 1,979 行）

#### 強み
- FastAPI と MCP の二系統を薄く保てている
- ToolResponse 構造（summary / citations / freshness_warnings）はおおむね統一

#### 高優先度の問題

**[H3] プロフィール取得のエラーハンドリング非対称** — `api/routers/clo.py:87-98` vs `mcp_server/tools/clo_tools.py:188-196`
- REST: `HTTPException(404)` で即座に失敗
- MCP: `ToolResponse(summary="見つかりません")` で 200 OK を返却
- 推奨: 共通の `resolve_profile()` ヘルパーを `core/io/` に置き、REST はそのまま 404、MCP は呼び出し側でラップ

**[H4] バリデーション例外の一貫性欠落** — `api/routers/clo.py:135-150` 他
- 推奨: `ValueError` → `HTTPException(400)` を rotuer ミドルウェアで一括ハンドル

**[H5] `_VALID_SAMPLE_IDS` に sample_retail_01 が未反映** — `api/routers/clo.py:79`
- 影響: `wait_heatmap` 等 retail 依存エンドポイントが 404 を返す可能性（**機能バグ**）
- 推奨: `core/static/sample_company.py` から動的列挙

#### 中優先度の問題

**[M4] `_publish_files()` + `_to_model()` の重複定義** — clo / company / macro 3 ルーターで同一実装
- 推奨: `api/routers/_helpers.py` に共通化

**[M5] ToolResponse metadata 構築の詳細度ばらつき** — `clo.py:296-320`（wait_heatmap）vs `clo.py:644-701`（cockpit）
- 推奨: metadata Pydantic スキーマで型安全化（今回スコープ外、別 PR）

#### 低優先度
- L4: `# type: ignore[no-untyped-def]` が `_resolve_profile_or_404()` に残存
- L5: `citations` の URL ベース重複排除ロジックが executive_brief とそれ以外で異なる → `Citation.__hash__` 定義で統一

---

### 3. web/（19 ファイル / 4,473 行）

#### 強み
- API_BASE 設定は適切（デフォルト `""` で同一 origin、ローカルは `.env.development.local`）
- Pydantic 互換型 18 個が `web/lib/api.ts` に集約済み
- `labels.ts` 共通表示層が PR #17 で導入済み

#### 高優先度の問題

**[H6] fetch + loading + error 三点セット重複** — 11 ダッシュボード全ページ
- 全ページで `const [result, setResult] = useState(null)` / `const [loading, setLoading] = useState(false)` / `const [error, setError] = useState(null)` が複製
- 推奨: `web/lib/useFetchTool.ts` カスタムフックで吸収（loading/error/result + auto error handling）
- 効果: ボイラープレート ▲30%、エラー通知の一貫性 UP

**[H7] ラベル定義の重複（4 ページ）** — `cockpit/page.tsx:23-89` / `wait-heatmap:18-38` / `industry-package:31-52` / `standardization:24-49`
- AXIS_LABEL / SEVERITY_LABEL / INDUSTRY_LABEL / OVERRIDE_LABEL がページ内に定義（labels.ts 共通化方針に違反）
- 推奨: 全列を `web/lib/labels.ts` に集約

**[H8] エラー通知の不整合** — `cockpit/page.tsx:126` のみ `window.alert()` 使用
- 推奨: `ErrorBanner` コンポーネントに統一（H6 の useFetchTool 化と合わせて吸収）

#### 中優先度
- M6: `industry-package/page.tsx` 520 行 — H7 反映で簡素化可能
- M7: `useMemo` 活用が部分的（3/11 ページ）— 計算量小の箇所が多いため優先度低

#### 低優先度
- L6: `wait-heatmap` の TIME_SLOT_LABEL_JP を `constants.ts` に移動
- L7: `runScenarioSim` / `loadCompanyProfile` が `buildUrl()` を経由していない

---

## Phase 2 総括

| 領域 | 高 | 中 | 低 |
|---|---|---|---|
| core/ | 2 | 3 | 3 |
| api/ + mcp_server/ | 3 | 2 | 2 |
| web/ | 3 | 2 | 2 |
| **合計** | **8** | **7** | **7** |

加えて Phase 1 で **`ruff format` 未適用 73 ファイル** を検出。

---

## CLO ミッション適合チェック

✅ **すべての改修候補が CLO 業務に直結**
- Summary 統一 / 通貨フォーマッタ → 計画書・経営会議資料の堅牢性
- プロフィール解決の一貫化 / sample_retail_01 反映 → MCP・REST 双方の信頼性
- web の DRY 化 → 機能追加時の作業量と回帰リスク削減

❌ CLO 業務に効かない改修候補: なし

---

## 推奨スコープ（Phase 3 に渡す入力）

**今回 PR で実施**（pytest 835 維持を優先、リスク低〜中のみ）:
- F0: `ruff format` 全 Python に適用（純フォーマット）
- H5: `_VALID_SAMPLE_IDS` の動的化 + sample_retail_01 修正（バグ）
- H3 + H4: プロフィール解決と ValueError ハンドリングの REST/MCP 一貫化
- M4: `_publish_files` / `_to_model` 共通化
- H2: `core/export/formatter.py` 新設して `format_jpy` 統一（高頻度から段階的に）
- H1: `SummaryResult` dataclass 化（plan_draft.py の split 依存解消）
- H6: web 側 `useFetchTool` フック導入
- H7: web 側ラベル統合
- H8: web 側 `window.alert` 撤廃

**次回 PR 候補（リスク高または範囲広）**:
- M3: 巨大モジュール分割（ppt_writer / operation_cockpit）
- M2: TypedDict 段階的導入
- M5: ToolResponse metadata Pydantic 化

---

## 次フェーズ (Phase 3) への申し送り

上記推奨スコープを起点に、依存関係と安全な実装順序を Plan agent で詳細化する。
