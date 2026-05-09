# リファクタリング計画 — refactor/codebase-cleanup-202605

**作成日**: 2026-05-09
**入力**: `tasks/review-report.md`
**目標**: pytest 835 件 / Next.js build 16 ページの維持を絶対条件に、効率化とロジック強化を 9 Step で段階実施

---

## リファクタリング方針

- **KISS**: 各ステップ単機能・単目的。F0 は純フォーマットで独立、論理変更を含まない。dataclass 化や共通化は **「今ある形を整える」** のみで責務分割（M3）には踏み込まない。
- **YAGNI**: TypedDict (M2)、metadata Pydantic 化 (M5)、巨大モジュール分割 (M3) は次回 PR。今回は「現に痛みが出ている重複・バグ・スタイル乱れ」のみ。
- **Minimal Impact**: `build_*_summary()` のシグネチャは `str` を返したまま維持（dataclass の `__str__` で透過）、`format_jpy` は新規 `core/export/formatter.py` に集約し既存式は段階置換、Codex 領域 `core/static/efficiency_law_certified.py` は触らない。
- **テストファースト**: 各 Step 末で `uv run pytest --tb=short -q` を必ず実行、835 件 pass を逐次確認。

---

## 実装順序の根拠

1. **F0（フォーマット）を最優先** — 全体に大きな空白差分を発生させるため、論理変更ステップと混ぜると差分レビューが破綻する。先に独立コミットして以降のステップ差分を意味的差分のみに絞る。
2. **H5 → H3+H4 → M4** — api 層内の独立改修。H5 は単純バグ修正で他に影響しない。続いて H3+H4 で `core/io/profile_resolver.py` ヘルパーを新設、M4 でルーター間共通化。api 層を先に固めてから core 層の大改修に入る。
3. **H2 → H1** — H2 で `format_jpy` を core/export に新設し plan_draft.py / executive_brief 等の現場で `/ 1e8` を置換。H1 の `SummaryResult` 化で内部行を組み立てる際、既に `format_jpy` が使えるとコード品質が一段上がる。**逆順だと SummaryResult 内で再度マジックナンバーが残る**。
4. **H1 を core 最後** — 影響範囲が 15 ファイル超で最大。前 3 ステップの安定が前提。`to_str()` 後方互換が肝。
5. **H6 → H7 → H8** — web 側。H6 で `useFetchTool` を作りフック導入、H7 で labels 集約、H8 で `window.alert` を `ErrorBanner` に置換（H6 の error 状態を借用）。H8 が最後なのは H6 の error チャネルに乗せられるから。
6. **バックアウト容易性**: 各ステップ独立コミット、最悪 `git revert <sha>` で前ステップに戻せる粒度。

---

## タスクリスト

### Step 1: F0 — `ruff format` 全適用
- **目的**: フォーマット差分を全消去し、以降のステップが論理差分のみになる状態を作る。
- **対象**: `core/`, `api/`, `mcp_server/` の Python 73 ファイル（既 15 ファイルのみ適用済）。
- **手順**: `uv run ruff format core/ api/ mcp_server/` → `uv run ruff check` / `ruff format --check` で確認。
- **検証**: `uv run pytest --tb=short -q`（835 件 pass）。
- **コミット**: `style: apply ruff format to all python sources`
- **想定 LOC**: ±数千行（純空白・改行）
- **ロールバック**: `git revert HEAD`

### Step 2: H5 — `_VALID_SAMPLE_IDS` 動的化（バグ修正）
- **目的**: `sample_retail_01` 未列挙バグを解消し、ID 真実の単一情報源を `core/static/sample_company.ALL_SAMPLES` に統一。
- **対象**: `api/routers/clo.py:79-84`、`mcp_server/tools/clo_tools.py:188-196`
- **手順**: `_VALID_SAMPLE_IDS = tuple(ALL_SAMPLES.keys())` に変更（インポート追加）。
- **検証**: `wait_heatmap("sample_retail_01")` が 200 を返すことを確認。`pytest -q`。
- **コミット**: `fix(api): include sample_retail_01 in valid sample ids`
- **想定 LOC**: ±15 行

### Step 3: H3+H4 — プロフィール解決と ValueError ハンドリングの REST/MCP 一貫化
- **目的**: REST/MCP で重複している「企業プロフィール解決 + 不明時メッセージ + ValueError ラップ」を共通化。
- **対象**: 新規 `core/io/profile_resolver.py`（`resolve_profile(company_id) -> CompanyProfile` / `ProfileNotFound` 例外）、`api/routers/clo.py`、`mcp_server/tools/clo_tools.py`
- **検証**: REST が引き続き 404、MCP が引き続き 200 でエラーメッセージ表示。`pytest -q`。
- **コミット**: `refactor(api,mcp): unify profile resolution and ValueError handling`
- **想定 LOC**: +60 / -50

### Step 4: M4 — `_publish_files` / `_to_model` 共通化
- **目的**: clo / company / macro 3 ルーターの重複実装を `api/routers/_helpers.py` に集約。
- **対象**: `api/routers/_helpers.py`（新設）、`clo.py` / `company.py` / `macro.py`
- **検証**: 全ルーター応答互換、`files` キー正規化が変わらないこと。
- **コミット**: `refactor(api): extract _publish_files and _to_model helpers`
- **想定 LOC**: +40 / -60

### Step 5: H2 — `core/export/formatter.py` 新設、`format_jpy` 段階置換
- **目的**: `revenue / 1e8`, `/ 1e6`, `/ 1e4` の散在 51 箇所を統一関数に置換。
- **対象**: `core/export/formatter.py`（新規）、`core/analytics/plan_draft.py` / `simulator.py` / `target_proposal.py` / `feasibility_check.py` / `api/routers/clo.py` の高頻度箇所から先行置換。
- **検証**: PPT/Excel/Markdown 出力テストの文字列スナップショットが一致。
- **コミット**: `feat(core/export): add format_jpy and migrate hot paths`
- **想定 LOC**: +60 / -90

### Step 6: H1 — `SummaryResult` dataclass 化（後方互換）
- **目的**: `build_*_summary` の戻り値を `SummaryResult(title, body)` に統一し `plan_draft.py:448-479` の `.split("\n")[2:]` 脆弱コードを `result.body` 直接参照へ。
- **対象**: `core/analytics/_summary.py`（新規 dataclass + `to_str()` + `__str__` 委譲）、`core/analytics/*.py` 15 ファイルの `build_*_summary` 内部書き換え、`plan_draft.py:_build_body_slides` の参照書換。
- **検証**: 全 Summary テストの文字列一致。
- **コミット**: `refactor(core/analytics): introduce SummaryResult while preserving str compat`
- **想定 LOC**: +120 / -80

### Step 7: H6 — `web/lib/useFetchTool.ts` カスタムフック導入
- **目的**: 11 ダッシュボードの `result/loading/error` 三点セット重複を 1 フックで吸収。
- **対象**: `web/lib/useFetchTool.ts`（新設・generic）、単純な 4 ページ（benchmark / driver-gap / playbook / standardization）から先行移行。
- **検証**: `npm run build`（Next.js 16 ページ全 pass）。
- **コミット**: `feat(web): add useFetchTool hook and migrate simple pages`
- **想定 LOC**: +80 / -120

### Step 8: H7 — ラベル定義 4 ページ分を `web/lib/labels.ts` に統合
- **目的**: AXIS_LABEL / SEVERITY_LABEL / INDUSTRY_LABEL / OVERRIDE_LABEL を `labels.ts` 単一ソース化。
- **対象**: `web/lib/labels.ts`（追記）、`cockpit/page.tsx` / `wait-heatmap/page.tsx` / `industry-package/page.tsx` / `standardization/page.tsx`
- **検証**: `npm run build`、ラベル表示が変わらないこと（目視）。
- **コミット**: `refactor(web): consolidate label maps into labels.ts`
- **想定 LOC**: +80 / -100

### Step 9: H8 — `cockpit/page.tsx` の `window.alert` を `ErrorBanner` に置換 + 残り 7 ページの useFetchTool 化
- **目的**: `cockpit/page.tsx:126` の `window.alert` 撤廃 + Step 7 の適用範囲を残り 7 ページに拡張。
- **対象**: cockpit, industry-package, wait-heatmap, scenario-sim, plan-draft, measure-eval, macro, company
- **検証**: `npm run build`、cockpit のエラー banner が出る挙動確認。
- **コミット**: `refactor(web): replace window.alert with ErrorBanner and finish hook migration`
- **想定 LOC**: +60 / -90

---

## 横断的な検証項目

- `uv run pytest --tb=short -q` — **各ステップ末で必須**（835 件 pass 維持）
- `uv run ruff check core/ api/ mcp_server/` / `ruff format --check` — Step 1 以降は常時 clean
- `cd web && npm run build` — Step 7-9 各々で実施（Next.js 16 ページ全 pass）
- `git diff main..HEAD --stat` で各 Step が想定 LOC 内に収まっていることを確認

---

## バックアウト戦略

- **Step 1 (F0) で問題発生** — revert HEAD。本 PR 全体を中止し別アプローチ検討。
- **Step 2-4 (api 層) で問題** — 該当ステップのみ revert。後続 (H2, H1, web) は独立で継続可能。
- **Step 5 (H2) で出力スナップショット崩壊** — revert して H1 だけ先行する代替経路へ切替。
- **Step 6 (H1) で広範な失敗** — revert で 15 ファイル戻す。`to_str()` 単体テストを先に追加して再挑戦。
- **Step 7-9 (web) で build 失敗** — 該当ステップのみ revert。core/api 層は無傷で PR は core 部分のみで成立。
- **ワースト基準点**: F0 + H5 + H3+H4 + M4 までで一旦 PR を切り、H1/H2/web は次 PR に回す（最低限のバグ修正と api 共通化は確保）。

---

## Critical Files

- `api/routers/clo.py`
- `core/analytics/plan_draft.py`
- `core/static/sample_company.py`
- `mcp_server/tools/clo_tools.py`
- `web/app/dashboard/cockpit/page.tsx`
