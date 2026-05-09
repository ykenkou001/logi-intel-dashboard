# タスクリスト — refactor/codebase-cleanup-202605

各 Step 完了時に `- [ ]` → `- [x]` 更新。pytest 845+ / ruff clean / Next.js build を逐次確認。

> **本 PR の最終ベースライン**: pytest 860 件 pass（+15 新規 / 元 845）/ Next.js build 16 ページ pass / ruff clean

## Step 1: F0 — ruff format 全適用 ✅
- [x] `uv run ruff format core/ api/ mcp_server/` 実行（73 ファイル整形）
- [x] `uv run ruff check` / `ruff format --check` 確認
- [x] `uv run pytest --tb=short -q`（845 pass）
- [x] `git commit -m "style: apply ruff format to all python sources"` (`9229422`)

## Step 2: H5 — `_VALID_SAMPLE_IDS` 動的化 ✅
- [x] `core/static/sample_company.py` に `list_sample_ids()` / `format_sample_ids()` を追加
- [x] `api/routers/clo.py` の `_VALID_SAMPLE_IDS` 廃止
- [x] `mcp_server/tools/clo_tools.py` の 6 箇所固定文字列を動的化
- [x] `core/analytics/plan_draft.py` / `periodic_report.py` の固定文字列を動的化
- [x] `pytest -q`（845 pass）
- [x] `git commit -m "fix(api,mcp,core): unify sample id error messages"` (`b30416b`)

## Step 3: H3+H4 — プロフィール解決と ValueError 一貫化 ✅
- [x] `core/io/profile_resolver.py` 新設（`resolve_profile` / `ProfileNotFoundError`）
- [x] `api/routers/clo.py` の `_resolve_profile_or_404` を置換
- [x] `mcp_server/tools/clo_tools.py` の 11 箇所を `try/except ProfileNotFoundError` に統一
- [x] REST 404 / MCP 200+error メッセージ の挙動維持
- [x] `pytest -q`（845 pass）
- [x] `git commit -m "refactor(api,mcp): unify profile resolution"` (`a9de8d7`)

## Step 4: M4 — `_publish_files` / `_to_model` 共通化 ✅
- [x] `api/routers/_helpers.py` 新設
- [x] `clo.py` / `company.py` の重複削除（cross-import 解消）
- [x] `pytest -q`（845 pass）
- [x] `git commit -m "refactor(api): extract publish_files / to_model"` (`a0a8002`)

## Step 5: H2 — `format_jpy` 新設（callsites 置換は次 PR） ⚠️
- [x] `core/export/formatter.py` 新設（`format_jpy(amount, unit, digits)`）
- [x] 単体テスト 15 件追加（億/百万/万/円、小数桁、None 安全性）
- [ ] ~~`core/analytics/plan_draft.py` の高頻度 `/ 1e8` を置換~~ → **次 PR へ延期**
- [ ] ~~`simulator.py` / `target_proposal.py` / `feasibility_check.py` も置換~~ → **次 PR へ延期**
- [ ] ~~`api/routers/clo.py` の現場置換~~ → **次 PR へ延期**
- [x] `pytest -q`（860 pass = 845 + 15 新規）
- [x] `git commit -m "feat(core/export): add format_jpy"` (`ef61a6a`)

**延期理由**: `tests/fixtures/cockpit_summaries/*.txt` 12 件のスナップショットテストが既存出力文字列に密結合しており、callsites 置換と同時にスナップショット更新が必要。本 PR では基盤関数 + 単体テストのみを先行コミットし、callsites 置換は次 PR に分離してリスクを限定する。

## Step 6: H1 — `SummaryResult` dataclass 化 → **本 PR では延期** ❌
- 影響範囲: `core/analytics/*.py` 15 ファイル + 32 利用箇所（テスト含む）
- リスク: スナップショット fixtures 12 件 + ToolResponse.summary 互換性
- **本 PR では未着手**。`tasks/plan.md` の「次回 PR 候補」に該当。次 PR では `SummaryResult` を `__str__` で文字列互換にする方針で再挑戦する。

## Step 7: H6 — `useFetchTool` カスタムフック導入（先行 4 ページ）✅
- [x] `web/lib/useFetchTool.ts` 新設（`<T>(fetcher) -> {data, loading, error, run, reset}`）
- [x] benchmark / driver-gap / playbook / macro の 4 ページを移行
- [x] `cd web && npm run build`（16 ページ pass）
- [x] `git commit -m "feat(web): add useFetchTool hook"` (`5c0d6b7`)

## Step 8: H7 — ラベル統合 ✅
- [x] `web/lib/labels.ts` に INDUSTRY_LABEL / OVERRIDE_CATEGORY_LABEL / DECISION_AXIS_LABEL / VERDICT_LEVEL_LABEL / SEVERITY_EMOJI を追加
- [x] cockpit / wait-heatmap / industry-package / standardization の 4 ページから重複削除
- [x] `npm run build`（16 ページ pass）
- [x] `git commit -m "refactor(web): consolidate label maps"` (`2ff8eb8`)

## Step 9: H8 — `window.alert` 撤廃 + cockpit のフック移行 ⚠️ 部分完了
- [x] cockpit/page.tsx を useFetchTool 化
- [x] `cockpit/page.tsx:115` の `window.alert` を `ErrorBanner` に置換（`onError` callback で親に伝搬）
- [x] `npm run build`
- [x] `git commit -m "refactor(web): replace window.alert"` (`b95ca3f`)
- [ ] ~~industry-package / wait-heatmap / scenario-sim / plan-draft / measure-eval / company の useFetchTool 化~~ → **次 PR へ延期**

**延期理由**: industry-package / standardization / wait-heatmap は dual-fetch（score + package を Promise.all）パターンで `useFetchTool<T>` の単一 fetcher 設計に直接マッチしない。残り 6 ページは Step 9 のスコープから外し、次 PR で `useFetchTool` を multi-fetch 対応に拡張するか個別判断する。

## 最終
- [x] `git diff main..HEAD --stat` 確認 — 9 機能コミット + 1 docs コミット
- [ ] PR 作成（`gh pr create`） ← 次のステップで実施
