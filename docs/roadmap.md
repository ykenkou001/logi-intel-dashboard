# 開発ロードマップ

**責任範囲**: フェーズ別の開発計画と進捗状況。「今どこにいるか」「次に何をするか」を把握するためのドキュメント。

---

## 現在のフェーズ: フェーズ 2 — データソース拡張

---

## フェーズ 0: 準備

- [x] リポジトリ作成: `logi-intel-dashboard` (Private)
- [x] uv で初期化、pyproject.toml 作成
- [ ] API キー取得: e-Stat, RESAS, 国税庁法人番号（健一が手動で実施）
- [x] `.env.example` 作成

---

## フェーズ 1: MVP — MCP サーバー初版 ★現在ここ★

**ゴール**: Claude Desktop から「東京都の運輸業事業所数」が返ってくる

- [x] `core/clients/base.py`（共通 HTTP クライアント基底クラス）
- [x] `core/clients/estat.py`（e-Stat 統計表検索 + データ取得）
- [x] `core/cache.py`（SQLite キャッシュ）
- [x] `mcp_server/server.py`（FastMCP エントリ）
- [x] `mcp_server/tools/estat_tools.py`（統計表検索ツール、データ取得ツール、メタデータ取得ツール）
- [x] Claude Desktop 設定登録手順を README に記載
- [x] Claude Desktop で動作確認（2026-05-01 logi_estat_search 成功確認）

---

## フェーズ 2: データソース拡張

- [ ] 国税庁法人番号クライアント・ツール
- [ ] xROAD 交通量クライアント・ツール（リアルタイム）
- [ ] 気象庁 JSON クライアント・ツール
- [ ] エネ庁 石油価格クライアント・ツール
- [ ] 統合ツール: 都道府県マクロ概況（複数 API 横断）

---

## フェーズ 3: CLO 支援機能

- [ ] 業界ベンチマーク分析
- [ ] ドライバー需給ギャップ推計
- [ ] 中長期計画ドラフト生成プロンプト
- [ ] 燃料価格動向と補助金影響分析

---

## フェーズ 4: Web ダッシュボード

- [ ] FastAPI REST 層
- [ ] Next.js 初期化
- [ ] 主要画面実装
- [ ] デプロイ

---

## フェーズ 5: 公開・記事化

- [ ] README 整備
- [ ] Zenn 記事執筆
- [ ] 社内デモ
- [ ] （任意）Public 化、PyPI 公開

---

## Zenn 記事素材メモ

フェーズ完了ごとに `docs/zenn_drafts/` に実装ポイント・スクリーンショット・コードスニペットを蓄積する。
