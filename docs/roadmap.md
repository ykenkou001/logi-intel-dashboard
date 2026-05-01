# 開発ロードマップ

**責任範囲**: フェーズ別の開発計画と進捗状況。「今どこにいるか」「次に何をするか」を把握するためのドキュメント。

> ⚠️ 全フェーズの判断基準は **CLO 支援への徹底コミット**（[CLAUDE.md §1.5](../CLAUDE.md)）。各フェーズの完了条件は「CLO 計画書ドラフトに使える形で出力できること」。

---

## 現在のフェーズ: フェーズ 2 — データソース拡張

---

## フェーズ 0: 準備

- [x] リポジトリ作成: `logi-intel-dashboard` (Private)
- [x] uv で初期化、pyproject.toml 作成
- [x] API キー取得: e-Stat（取得済み）
  - ※ RESAS API は 2025-03-24 提供終了のため対象外
  - ※ 国税庁法人番号 applicationID は 2026-05-01 申請済み・取得まで約1ヶ月かかるためスキップ
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
- [x] Claude Desktop で logi_macro_overview("東京都") の動作確認（2026-05-01 完了）
  - ※ 国税庁法人番号データは applicationID 取得後に有効化（申請済み・約1ヶ月待ち）

---

## フェーズ 2.5: CLO 武装データ層 + 出口整備（NEW）

**ゴール**: フェーズ3 の分析モジュールが「CLO に刺さる成果物」を出せるよう、データ層と出口層を先に厚くする。

**背景**: 現状のロードマップでは分析モジュールに直行するが、(a) データ層が薄い (b) 成果物出力経路がない、ため「Claude の会話で数字が出るが CLO の机に届かない」状態に陥る。本フェーズで土台を作る。

### Step 1: e-Stat 追加クライアント（CLO 必須統計）

- [ ] **自動車輸送統計年報** クライアント（積載率・実車率の業界平均）
- [ ] **全国貨物純流動調査（物流センサス）** クライアント（OD・モード別シェア／5年に1回・最新2021）
- [ ] **港湾統計 / 内航船舶輸送統計 / 鉄道輸送統計** クライアント（モーダルシフト先キャパ）

### Step 2: 静的データ層 + 鮮度管理

- [ ] `core/static/_freshness.py` — 各静的データの最終更新日と推奨更新間隔を管理、起動時に古いデータを警告
- [ ] `core/static/co2_factors.py` — 環境省 CO2 排出原単位（輸送機関別）
- [ ] `core/static/improvement_standards.py` — 改善基準告示（拘束時間13h/日、休息11h、年960h 等）
- [ ] `core/static/standard_freight.py` — 標準的運賃 2024 改定版
- [ ] `core/static/efficiency_law_certified.py` — 物流効率化法 認定事業 CSV 自動取込スクリプト
- [ ] `core/static/industry_freight_coef.py` — 業種別物流原単位（売上→取扱量推計）

### Step 3: 法令ロジック

- [ ] `core/legal/eligibility.py` — 9万トン基準による特定荷主判定エンジン
- [ ] `core/legal/improvement_check.py` — 改善基準告示準拠チェック

### Step 4: 国交省公式テンプレートの取込

- [ ] **様式第3別紙 中長期計画書（Word）** を `core/templates/clo_plan_form3.docx` に同梱
- [ ] **公式記載事例集**（製造業・卸売業・小売業・連鎖化事業者 × 取組進行/これから = 8 パターン）を MD 化して `core/templates/clo_plan_examples/` に同梱
- [ ] 入手元: [国交省ポータル](https://www.revised-logistics-act-portal.mlit.go.jp/planning/) / [経産省](https://www.meti.go.jp/policy/economy/distribution/butsuryu-kouritsuka.html)
- [ ] 年1回（毎年4月）の様式改訂チェックリマインダを `_freshness.py` に登録

### Step 5: 出口層（成果物生成）

**ここが本フェーズの核心**。MCP ツールがファイルを返せるようにする。

- [ ] `core/export/citation.py` — 出典 URL の統一管理
- [ ] `core/export/ppt_writer.py` — **PPT 出力（最優先）** / `python-pptx` / micware マスタスライド
- [ ] `core/export/excel_writer.py` — Excel 出力 / `openpyxl` / 数値表 + 出典シート
- [ ] `core/export/docx_form3_writer.py` — **様式第3別紙への流し込み** / `python-docx`
- [ ] `core/export/markdown_writer.py` — Markdown 出力
- [ ] `core/export/pdf_writer.py` — PDF 変換（PPT/Word から、LibreOffice CLI or WeasyPrint）

### Step 6: PDF 取込ハーネス + リマインダ

- [ ] `scripts/import_truck_survey.py` — トラック輸送状況実態調査の年次取込（手動）
- [ ] 起動時/MCP 呼出時に「実態調査が古い」を Claude に見せる仕組み

### 完了条件

- `logi_macro_overview("東京都")` の戻り値に `files.ppt` と `files.excel` のパスが含まれ、開ける
- 静的データ鮮度警告が Claude の応答に含まれる
- 様式第3別紙テンプレートに「実施措置」「計画内容」「実施時期」の3項目を流し込める

---

## フェーズ 3: CLO 支援機能（武装データ層活用）

**前提**: フェーズ 2.5 で静的データ層・法令ロジック・出口層が揃っていること。
**ゴール**: 国交省様式に準拠した CLO 計画書ドラフトを PPT + Word + Excel で出力できる。

詳細設計 → [docs/clo_domain.md](docs/clo_domain.md)（フェーズ3実装設計セクション）

### 分析モジュール（core/analytics/）

- [ ] **Step 1**: 業界ベンチマーク（`logi_clo_benchmark_position`）
  - 全国順位・地域順位・業界平均比を算出
- [ ] **Step 2**: ドライバー需給ギャップ（`logi_clo_driver_gap`）
  - 就業者数 × 改善基準告示削減係数
- [ ] **Step 3**: 適用判定（`logi_clo_eligibility`）
  - 業種 × 売上 → 9万トン超過判定（`core/legal/eligibility.py` 利用）
- [ ] **Step 4**: 数値目標提案（`logi_clo_target_proposal`）
  - 業界平均 + 国家目標（CO2 ▲46%）から逆算した目標値
- [ ] **Step 5**: 施策効果シミュレータ（`logi_clo_simulate_*`）
  - モーダルシフト / 積載率向上 / 共同配送 / 中継輸送 / バース予約

### 統合ツール

- [ ] **Step 6**: 補助金マッチング（`logi_clo_subsidy_match`）
  - 物流効率化法認定 + 公募中補助金とのマッチング
- [ ] **Step 7**: **計画書ドラフト統合生成（`logi_clo_plan_draft`）**
  - Step 1〜6 を順次呼び、**様式第3別紙（Word）+ 経営会議 PPT + Excel + Markdown** を一括出力
  - 出力先: `outputs/{ppt,docx,excel,markdown}/`
  - 全数値に出典 URL 付与（`core/export/citation.py`）

### 燃料価格履歴（独立タスク）

- [ ] **Step 8**: 燃料価格履歴蓄積（`fuel_price_history` テーブル）
- [ ] ~~燃料価格動向と補助金影響分析~~ → Step 8 の数ヶ月蓄積後に実装

### フェーズ 3 完了条件

- `logi_clo_plan_draft(company_profile)` 一発で **PPT・Word（様式第3別紙）・Excel** が生成される
- 全数値に出典が付き、経営会議で「出典は？」と聞かれて即答できる
- 国交省記載事例集と同等の粒度で「実施措置」「計画内容」「実施時期」が埋まる

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
