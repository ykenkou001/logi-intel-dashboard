# lessons.md — 学習記録

タスク完了時に得た知見を記録する。フォーマット: `[YYYY-MM-DD] [ドメイン] 問題 → 解決策`

---

## 2026-05-09 — `refactor/codebase-cleanup-202605`（whole-repo リファクタ PR）

- **[2026-05-09] [リファクタ運用] スナップショットテストが多い領域では「基盤関数の追加」と「callsites 置換」を別 PR に分ける**
  - 問題: `core/export/formatter.py:format_jpy()` を追加してすぐ 51 callsites 置換に着手しかけたが、`tests/fixtures/cockpit_summaries/*.txt` 12 件と PPT/Excel 出力テストが既存文字列に密結合しており、置換 + スナップショット更新を 1 コミットでやると差分が膨大化してレビュー困難になることが判明
  - 解決策: 基盤関数 + 単体テストだけ先行コミット → 次 PR で callsites 置換 + スナップショット更新を分離。Step 5 の延期判断を `tasks/tasklist.md` に明示
  - 適用: 既存スナップショット fixtures が多い領域では同じパターンを採用すること

- **[2026-05-09] [Subagent 戦略] whole-repo 品質分析は 3〜4 領域に分割した Explore agent を並列起動する**
  - 問題: 18,659 行の core/ + 1,445 行の api/ + 1,979 行の mcp_server/ + 4,473 行の web/ を 1 agent で見ると視野が散漫になり高優先度問題を見逃す
  - 解決策: 領域別に 3 agent を並列起動（core / api+mcp / web）し、各 agent に共通の評価軸（重複ロジック・不要な抽象化・型安全性・エラーハンドリング・デッドコード）を渡す。出力フォーマットを統一して後段でマージ容易にする
  - 適用: 1 万行を超える調査で常用

- **[2026-05-09] [Python 規約] ruff N818 — Exception クラスは `Error` 接尾辞**
  - 問題: `class ProfileNotFound(Exception)` で N818 エラー
  - 解決策: `class ProfileNotFoundError(Exception)` にリネーム。CPython 標準（FileNotFoundError, ValueError, KeyError 等）も同じ規約

- **[2026-05-09] [api 構造] cross-router import (`from api.routers.clo import _publish_files`) は code smell**
  - 問題: company.py が clo.py からヘルパーをインポート → ルーター間結合が暗黙的
  - 解決策: `api/routers/_helpers.py` に共通ヘルパーを移し、各ルーターは横並びで `_helpers` を参照する。`_` プレフィックスはモジュール内部用と認識される慣習に従う

- **[2026-05-09] [web フック設計] dual-fetch ページは単一 fetcher の useFetchTool に直接マッチしない**
  - 問題: `standardization/page.tsx` `industry-package/page.tsx` `wait-heatmap/page.tsx` は `Promise.all([fetchA, fetchB])` で 2 つの ToolResponse を組み立てる構造
  - 解決策: 本 PR では simple 4 ページ（benchmark / driver-gap / playbook / macro）のみ移行。dual-fetch 対応は次 PR で `useFetchTool<{a, b}>(combinedFetcher)` の形か、`useFetchTool` を multi-fetch 拡張するか個別判断
  - 適用: フック導入は「最も単純な形に当てはまるケースから漸進的に」

- **[2026-05-09] [snapshot test 連動] retail サンプル ID の固定リスト漏れバグ**
  - 問題: `mcp_server/tools/clo_tools.py` の 6 箇所のエラーメッセージが `sample_mfg_01 / sample_wholesale_01 / sample_chain_01` の 3 ID 固定で、4 番目の `sample_retail_01` が抜けていた
  - 解決策: `core/static/sample_company.py` に `format_sample_ids()` を新設して単一情報源化。ID 追加時はサンプル辞書 `ALL_SAMPLES` だけ更新すれば全エラー文言が追随する
  - 適用: enum 的な「全件列挙」が必要な場面では必ず単一情報源化を試みる

- **[2026-05-09] [Codex 並行作業] 別セッションが同じ作業ツリーでブランチを切り替える**
  - 問題: 別セッションが `feature/phase-5.5-alpha-upgrade` にチェックアウトして作業を始めたため、本セッションの `refactor/codebase-cleanup-202605` から外れた状態で再開した
  - 解決策: セッション再開時は必ず `git branch --show-current` で確認 → 想定外のブランチにいたら `git checkout <自分のブランチ>` で復帰。`tasks/` 等の untracked ファイルはブランチ切替で残るため失われない
  - 適用: 並行セッション運用では「再開時のブランチ確認」を初動チェックに固定する
