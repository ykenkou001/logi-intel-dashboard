# 開発ロードマップ

**責任範囲**: フェーズ別の開発計画と進捗状況。「今どこにいるか」「次に何をするか」を把握するためのドキュメント。

> ⚠️ 全フェーズの判断基準は **CLO 支援への徹底コミット**（[CLAUDE.md §1.5](../CLAUDE.md)）。アプリの軸は **意思決定支援（Option C）**。各フェーズの完了条件は「CLO の意思決定に直接効く形で出力できること」。

## フェーズ全体像

```
フェーズ 0   準備
フェーズ 1   MVP — MCP サーバー初版（e-Stat）                    ✅ 完了
フェーズ 2   データソース拡張                                     ✅ 完了
フェーズ 2.5 CLO 武装データ層 + 出口整備                          ← 今ここ
フェーズ 3.0 計画書ドラフト基盤
フェーズ 3.5 ★意思決定支援強化（差別化の心臓部）★
フェーズ 4.0 Web ダッシュボード + AWS 移行 + 自社データ取込
フェーズ 4.5 継続運用機能（定期報告書・進捗・法改正アラート）
フェーズ 5   公開・記事化
```

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
- **PPT 1 枚目に「経営層向けエグゼクティブサマリー」が必ず入る**（財務×戦略×競合×リスク）
- 全数値に出典が付き、経営会議で「出典は？」と聞かれて即答できる
- 国交省記載事例集と同等の粒度で「実施措置」「計画内容」「実施時期」が埋まる
- 自社データはサンプル（`core/static/sample_company.py`）で動作確認 — 本格的なアップロードはフェーズ4

---

## フェーズ 3.5: 意思決定支援強化（★ 差別化の心臓部 ★）

**ゴール**: CLO が経営会議で「**何をやるか・なぜやるか・いくら効くか**」を即答できるツール群を提供する。

**背景**: フェーズ3 までは「データ集約 + 計画書ドラフト」止まり。それは "最低限の CLO 対応ツール"。本フェーズで「**意思決定支援パートナー**」へ昇格させる。

### Step 1: 施策ライブラリ（`core/playbook/`）

物流効率化法 認定事業 + 国交省記載事例集 + 業界事例から抽出した、具体施策のデータベース。

- [ ] `core/playbook/measures.py` — 施策マスタ（モーダルシフト、共同配送、中継輸送、バース予約、AI配車、パレット標準化 等）
- [ ] 各施策に: 想定効果（積載率/CO2/コスト）、実装期間、必要投資、リスク、適用補助金、成功事例、失敗パターン
- [ ] 業種別・規模別フィルタリング
- [ ] **MCP ツール**: `logi_clo_playbook_search(industry, scale, kpi_target)`

### Step 2: 施策評価エンジン（`core/analytics/measure_eval.py`）

複数施策を多軸で評価・スコアリング。

- [ ] CO2 削減効果（環境省係数を使用）
- [ ] コスト削減効果（自社データ × 施策効果係数）
- [ ] 実装難易度スコア（1〜5）
- [ ] 補助金カバー率
- [ ] 投資回収期間
- [ ] **MCP ツール**: `logi_clo_evaluate_measures(measure_ids[], company_profile)`

### Step 3: シナリオシミュレータ（`core/simulator/`）

What-if 分析で計画のストレステストを行う。

- [ ] 燃料価格 ±20% シナリオ
- [ ] 運賃 ±10% シナリオ
- [ ] 需要 ±10% シナリオ
- [ ] 改善基準告示 さらなる強化シナリオ
- [ ] 複数シナリオ重ね合わせ
- [ ] **MCP ツール**: `logi_clo_simulate_scenario(plan_id, scenarios[])`

### Step 4: 財務翻訳エンジン（`core/finance/translate.py`）

物流 KPI を P&L インパクトに換算。経営層への翻訳機能。

- [ ] 積載率 +5% → 営業利益 +X 億円
- [ ] CO2 削減 → 炭素税回避額 + ESG プレミアム
- [ ] 罰則回避（不作為のコスト）試算
- [ ] **MCP ツール**: `logi_clo_translate_to_financial(measures[], company_profile)`

### Step 5: 達成可能性チェッカー（`core/validator/feasibility.py`）

提案目標の現実性を業界実績分布から判定。

- [ ] 「業界平均到達」が自社規模で 3 年で可能か
- [ ] 過去の同業他社の改善速度との比較
- [ ] 警告レベル: 緑（妥当）/ 黄（要注意）/ 赤（無理筋・罰則リスク高）
- [ ] **MCP ツール**: `logi_clo_check_feasibility(plan_id)`

### Step 6: pre-submission Validator（`core/validator/plan_check.py`）

計画書の必須記載・整合性をチェック。提出前の最終ゲート。

- [ ] 必須記載 3 項目（貨物重量・荷待ち・荷役）× 3 軸（実施措置・計画内容・実施時期）= 9 項目チェック
- [ ] 数値整合性（合計値・年次推移）
- [ ] 出典欠落チェック
- [ ] **MCP ツール**: `logi_clo_validate_plan(plan_path)`

### Step 7: エグゼクティブサマリー（`core/export/exec_summary.py`）

取締役会用 1 ページ PPT を独立生成。

- [ ] 1 ページに財務×戦略×競合×リスクを集約
- [ ] フェーズ3 の `logi_clo_plan_draft` から自動呼び出し（必須出力）
- [ ] **MCP ツール**: `logi_clo_executive_summary(company_profile)`

### フェーズ 3.5 完了条件

- 施策を入力すると、CO2 / コスト / 補助金 / 達成可能性が一覧で評価される
- What-if シナリオで計画が「燃料 +20% でも黒字維持」を示せる
- 物流 KPI 改善が「営業利益 X 億円」に翻訳される
- 計画書提出前に必須項目チェックが pass する
- 取締役会用 1 ページ PPT が独立して生成できる

---

## フェーズ 4.0: Web ダッシュボード + AWS 移行 + 自社データ取込

**ゴール**: 社内全員が HTTPS でアクセスできる Web ダッシュボードを AWS 上に構築し、CSV/Excel で自社データをアップロードできるようにする。

### Web ダッシュボード
- [ ] FastAPI REST 層（`api/` ディレクトリ）
- [ ] Next.js 初期化
- [ ] 主要画面: マクロ概況・業界ベンチマーク・施策ライブラリ・シミュレータ・計画書ダウンロード
- [ ] **自社データアップロード画面**（CSV / Excel / Pydantic フォーム）
  - 拠点リスト・配送ルート・積載率実績・荷待ち時間実績・燃料消費等
  - サンプルテンプレート（`outputs/sample_company_template.xlsx`）DL 提供

### AWS 移行
- [ ] MCP サーバーを stdio モード → HTTP/SSE モードに切り替え（FastMCP 設定変更）
- [ ] `core/cache.py` を SQLite → Redis（ElastiCache）に差し替え
- [ ] API キーを AWS Secrets Manager に移行
- [ ] ECS または Lambda にデプロイ
- [ ] Claude Desktop 設定をローカル起動から AWS エンドポイントに変更
- [ ] VPN 内からの接続確認

詳細設計 → [docs/architecture.md](docs/architecture.md)（AWS 移行計画セクション）

### 自社データ取込（本格実装）
- [ ] Pydantic `CompanyDataset` モデル（拠点・ルート・KPI 履歴）
- [ ] CSV / Excel パーサー
- [ ] アップロードデータの社内 PostgreSQL 保管（マルチテナント前提）
- [ ] フェーズ3 で使ったサンプルデータからの差し替え

---

## フェーズ 4.5: 継続運用機能

**ゴール**: 計画策定 → 実行 → 報告 → 改定の年次サイクルをアプリ内で回せる。

- [ ] **定期報告書ドラフト生成**（様式第5）— 製造業以外も対応
- [ ] **KPI トラッキング dashboard** — 計画 vs 実績の可視化
- [ ] **進捗 alert** — 目標未達リスクの早期警告
- [ ] **法改正監視** — 改善基準告示・物流効率化法 政省令の改訂を検出してアラート
- [ ] **計画改定サポート** — 過去計画と新環境の差分分析

### フェーズ 4.5 完了条件

- 計画提出 → 1 年後に「実績入力 → 達成率分析 → 報告書ドラフト生成」が完結する
- 法改正があったら Claude が起動時に通知する

---

## フェーズ 5: 公開・記事化

- [ ] README 整備
- [ ] Zenn 記事執筆
- [ ] 社内デモ
- [ ] （任意）Public 化、PyPI 公開

---

## Zenn 記事素材メモ

フェーズ完了ごとに `docs/zenn_drafts/` に実装ポイント・スクリーンショット・コードスニペットを蓄積する。
