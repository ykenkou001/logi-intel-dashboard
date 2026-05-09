# タスクリスト — refactor/codebase-cleanup-202605

各 Step 完了時に `- [ ]` → `- [x]` 更新。pytest 835 / ruff clean / Next.js build を逐次確認。

## Step 1: F0 — ruff format 全適用
- [ ] `uv run ruff format core/ api/ mcp_server/` 実行
- [ ] `uv run ruff check` / `ruff format --check` 確認
- [ ] `uv run pytest --tb=short -q`（835 pass）
- [ ] `git commit -m "style: apply ruff format to all python sources"`

## Step 2: H5 — `_VALID_SAMPLE_IDS` 動的化
- [ ] `core/static/sample_company.py` で `ALL_SAMPLES` をエクスポート確認
- [ ] `api/routers/clo.py:79-84` を `tuple(ALL_SAMPLES.keys())` 化
- [ ] `mcp_server/tools/clo_tools.py:188-196` の固定列挙文言も同経路で
- [ ] `wait_heatmap("sample_retail_01")` が 200 を返すテスト追加
- [ ] `pytest -q`
- [ ] `git commit -m "fix(api): include sample_retail_01 in valid sample ids"`

## Step 3: H3+H4 — プロフィール解決と ValueError 一貫化
- [ ] `core/io/profile_resolver.py` 新設（`resolve_profile` / `ProfileNotFound`）
- [ ] `api/routers/clo.py` の `_resolve_profile_or_404` を置換
- [ ] `mcp_server/tools/clo_tools.py` で `ProfileNotFound` を `ToolResponse` ラップ
- [ ] REST 404 / MCP 200+error メッセージ の挙動維持
- [ ] `pytest -q`
- [ ] `git commit -m "refactor(api,mcp): unify profile resolution and ValueError handling"`

## Step 4: M4 — `_publish_files` / `_to_model` 共通化
- [ ] `api/routers/_helpers.py` 新設
- [ ] `clo.py` / `company.py` / `macro.py` から重複削除
- [ ] `pytest -q`
- [ ] `git commit -m "refactor(api): extract _publish_files and _to_model helpers"`

## Step 5: H2 — `format_jpy` 新設 + 段階置換
- [ ] `core/export/formatter.py` 新設（`format_jpy(amount, unit, digits)`）
- [ ] 単体テスト追加（億/百万/万、小数桁、None 安全性）
- [ ] `core/analytics/plan_draft.py` の高頻度 `/ 1e8` を置換
- [ ] `simulator.py` / `target_proposal.py` / `feasibility_check.py` も置換
- [ ] `api/routers/clo.py` の現場置換
- [ ] PPT/Excel/Markdown 出力テストの文字列一致確認
- [ ] `pytest -q`
- [ ] `git commit -m "feat(core/export): add format_jpy and migrate hot paths"`

## Step 6: H1 — `SummaryResult` dataclass 化
- [ ] `core/analytics/_summary.py` 新設（dataclass + `to_str()` + `__str__`）
- [ ] 単体テスト追加（`str(SummaryResult(...))` が期待文字列を返す）
- [ ] `build_*_summary` 15 ファイルの内部書換（戻り値型注釈は `SummaryResult`、`__str__` で旧 str 互換）
- [ ] `plan_draft.py:_build_body_slides` を `result.body` 直接参照に変更
- [ ] 全 Summary テストの文字列一致確認
- [ ] `pytest -q`
- [ ] `git commit -m "refactor(core/analytics): introduce SummaryResult while preserving str compat"`

## Step 7: H6 — `useFetchTool` カスタムフック導入（先行 4 ページ）
- [ ] `web/lib/useFetchTool.ts` 新設（`<T>(fetcher) -> {data, loading, error, run}`）
- [ ] benchmark / driver-gap / playbook / standardization の 4 ページを移行
- [ ] `cd web && npm run build`（16 ページ全 pass）
- [ ] `git commit -m "feat(web): add useFetchTool hook and migrate simple pages"`

## Step 8: H7 — ラベル統合
- [ ] `web/lib/labels.ts` に AXIS_LABEL / SEVERITY_LABEL / INDUSTRY_LABEL / OVERRIDE_LABEL を追加
- [ ] cockpit / wait-heatmap / industry-package / standardization の 4 ページから重複削除
- [ ] `npm run build`
- [ ] `git commit -m "refactor(web): consolidate label maps into labels.ts"`

## Step 9: H8 — `window.alert` 撤廃 + 残り 7 ページのフック移行
- [ ] cockpit / industry-package / wait-heatmap / scenario-sim / plan-draft / measure-eval / macro / company の 8 ページを useFetchTool 化
- [ ] `cockpit/page.tsx:126` の `window.alert` を `ErrorBanner` に置換
- [ ] `npm run build`
- [ ] cockpit エラー banner の表示確認（手動）
- [ ] `git commit -m "refactor(web): replace window.alert with ErrorBanner and finish hook migration"`

## 最終
- [ ] `git diff main..HEAD --stat` 確認
- [ ] PR 作成（`gh pr create`）
