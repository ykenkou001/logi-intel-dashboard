# 開発ロードマップ

**責任範囲**: フェーズ別の開発計画と進捗状況。「今どこにいるか」「次に何をするか」を把握するためのドキュメント。

---

## 現在のフェーズ: フェーズ 2 — データソース拡張

---

## フェーズ 0: 準備

- [x] リポジトリ作成: `logi-intel-dashboard` (Private)
- [x] uv で初期化、pyproject.toml 作成
- [ ] API キー取得: e-Stat, 国税庁法人番号（健一が手動で実施）
  - ※ RESAS API は 2025-03-24 提供終了のため対象外
- [x] `.env.example` 作成

---

## フェーズ 1: MVP — MCP サーバー初版 ✅ 完了

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

- [x] 国税庁法人番号クライアント・ツール
- [x] xROAD 交通量クライアント・ツール（リアルタイム）
- [x] 気象庁 JSON クライアント・ツール
- [x] エネ庁 石油価格クライアント・ツール
- [x] 統合ツール: 都道府県マクロ概況（logi_macro_overview）
- [x] Claude Desktop で logi_macro_overview("東京都") の動作確認（2026-05-01 完了・国税庁APIキー取得後に完全動作）

---

## フェーズ 3: CLO 支援機能

- [ ] 業界ベンチマーク分析
- [ ] ドライバー需給ギャップ推計
- [ ] 中長期計画ドラフト生成プロンプト
- [ ] 燃料価格動向と補助金影響分析

---

## フェーズ 4: Web ダッシュボード + AWS 移行

**ゴール**: 社内全員が HTTPS でアクセスできる Web ダッシュボード + MCP サーバーを AWS 上に構築する

### Web ダッシュボード
- [ ] FastAPI REST 層（`api/` ディレクトリ）
- [ ] Next.js 初期化
- [ ] 主要画面実装（都道府県マクロ概況・燃料価格推移・ドライバー需給）

### AWS 移行
- [ ] MCP サーバーを stdio モード → HTTP/SSE モードに切り替え（FastMCP 設定変更）
- [ ] `core/cache.py` を SQLite → Redis（ElastiCache）に差し替え
- [ ] API キーを AWS Secrets Manager に移行
- [ ] ECS または Lambda にデプロイ
- [ ] Claude Desktop 設定をローカル起動から AWS エンドポイントに変更
- [ ] VPN 内からの接続確認

詳細設計 → [docs/architecture.md](docs/architecture.md)（AWS 移行計画セクション）

---

## フェーズ 5: 公開・記事化

- [ ] README 整備
- [ ] Zenn 記事執筆
- [ ] 社内デモ
- [ ] （任意）Public 化、PyPI 公開

---

## Zenn 記事素材メモ

フェーズ完了ごとに `docs/zenn_drafts/` に実装ポイント・スクリーンショット・コードスニペットを蓄積する。
