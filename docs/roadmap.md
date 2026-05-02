# 開発ロードマップ

**責任範囲**: フェーズ別の開発計画と進捗状況。「今どこにいるか」「次に何をするか」を把握するためのドキュメント。

> ⚠️ 全フェーズの判断基準は **CLO 支援への徹底コミット**（[CLAUDE.md §1.5](../CLAUDE.md)）。各フェーズの完了条件は「CLO 計画書ドラフトに使える形で出力できること」。

---

## 現在のフェーズ: フェーズ 2.5 — CLO 武装データ層 + 出口整備

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

## フェーズ 2: データソース拡張 ✅ 完了

- [x] 国税庁法人番号クライアント・ツール
- [x] xROAD 交通量クライアント・ツール（リアルタイム）
- [x] 気象庁 JSON クライアント・ツール
- [x] エネ庁 石油価格クライアント・ツール
- [x] 統合ツール: 都道府県マクロ概況（logi_macro_overview）
- [x] Claude Desktop で logi_macro_overview("東京都") の動作確認（2026-05-01 完了）
  - ※ 国税庁法人番号データは applicationID 取得後に有効化（申請済み・約1ヶ月待ち）

---

## フェーズ 2.5: CLO 武装データ層 + 出口整備 ← 今ここ

**ゴール**: フェーズ3 の分析モジュールが「CLO に刺さる成果物」を出せるよう、データ層と出口層を先に厚くする。

**背景**: 現状のロードマップでは分析モジュールに直行するが、(a) データ層が薄い (b) 成果物出力経路がない、ため「Claude の会話で数字が出るが CLO の机に届かない」状態に陥る。本フェーズで土台を作る。

### Step 1: e-Stat 追加クライアント（CLO 必須統計）

- [ ] `core/clients/estat_logistics.py` — 物流特化ヘルパー（既存 `EStatClient` のラッパー）
  - [ ] **自動車輸送統計年報** アクセサ（積載率・実車率の業界平均／statsCode `00600340`）
  - [ ] **全国貨物純流動調査（物流センサス）** アクセサ（OD・モード別シェア／5年に1回・最新2021／statsCode `00600370`）
  - [ ] **港湾統計 / 内航船舶輸送統計 / 鉄道輸送統計** アクセサ（モーダルシフト先キャパ）
- [ ] **statsDataId は動的検索（`getStatsList(statsCode=...)`）+ 結果キャッシュ**で取得（年次更新に追従）

### Step 2: 静的データ層 + 鮮度管理

- [ ] `core/static/_freshness.py` — 各静的データの最終更新日と推奨更新間隔を管理、起動時に古いデータを警告
  - [ ] **トラック輸送状況実態調査の年次取込状況**もここで管理（旧 Step 6 から統合）
  - [ ] 様式第3・第5 改訂チェック（毎年4月）リマインダもここで管理
- [ ] `core/static/co2_factors.py` — 環境省 CO2 排出原単位（輸送機関別）
- [ ] `core/static/improvement_standards.py` — 改善基準告示（**正確な告示文を引用**: 1日拘束 原則13h/最大16h、年間総拘束 原則3,300h、休息継続 9h以上/努力10h、時間外 年960h 等）
- [ ] `core/static/standard_freight.py` — 標準的運賃 2024 改定版
- [ ] `core/static/efficiency_law_certified.py` — 物流効率化法 認定事業 CSV 自動取込スクリプト
- [ ] `core/static/industry_freight_coef.py` — 業種別物流原単位（売上→取扱量推計）
- [ ] `core/static/national_targets.py` — 物流分野固有の国家目標（輸送量当たりCO2排出原単位 23.4%削減 等。日本全体の▲46%とは別物）
- [ ] `core/static/jsic.py` — 日本標準産業分類（細分類4桁）マスタ（計画書「主たる事業の細分類番号」用）
- [ ] `core/static/sample_company.py` — フェーズ4までの自社プロフィール仮データ（3 社分）
  - スキーマ: `name, jsic_code, annual_freight_tons, annual_revenue_jpy, sites, is_chain_franchise, fleet_count` 等

### Step 3: 法令ロジック

- [ ] `core/legal/eligibility.py` — **3区分判定エンジン**
  - 特定第一種荷主（発荷主：年間9万トン以上）
  - 特定第二種荷主（着荷主：年間9万トン以上）
  - 特定連鎖化事業者（フランチャイズ本部：販売額基準・第65条）
- [ ] `core/legal/improvement_check.py` — 改善基準告示準拠チェック

### Step 4: 国交省公式テンプレートの取込

- [x] **公式記載事例集**（製造業・卸売業・小売業・連鎖化事業者 × 取組進行/これから = 8 パターン+定期報告2パターン = 10ファイル）を MD 化（2026-05-02 完了）
- [ ] **様式第3別紙 中長期計画書（Word）** を `core/templates/clo_plan_form3.docx` に同梱（独立タスク：MLIT ポータルから手動 DL）
- [ ] **様式第5 定期報告書（Word）** を `core/templates/clo_report_form5.docx` に同梱
- [ ] **PPT マスタスライド** `core/templates/micware_master.pptx`（micware ブランドテンプレート入手後）
- [ ] 入手元: [国交省ポータル](https://www.revised-logistics-act-portal.mlit.go.jp/planning/) / [経産省](https://www.meti.go.jp/policy/economy/distribution/butsuryu-kouritsuka.html)

### Step 5: 出口層（成果物生成）+ 既存ツールの構造統一

**ここが本フェーズの核心**。MCP ツールがファイルを返せるようにする。

- [ ] `core/export/citation.py` — 出典 URL の統一管理（statsDataId / 告示番号 / 省令番号 / 取得日時 / 公式URL）
- [ ] `core/export/ppt_writer.py` — **PPT 出力（最優先）** / `python-pptx` / micware マスタスライド
- [ ] `core/export/excel_writer.py` — Excel 出力 / `openpyxl` / 数値表 + 出典シート
- [ ] `core/export/docx_form3_writer.py` — **様式第3別紙への流し込み** / `python-docx`
- [ ] `core/export/markdown_writer.py` — Markdown 出力
- [ ] `core/export/pdf_writer.py` — PDF 変換（PPT/Word から、LibreOffice CLI or WeasyPrint）
- [ ] **MCP ツール戻り値構造の統一**: 全 MCP ツールを `{summary: str, files: dict[str,str], citations: list[Citation]}` 形式に移行
  - [ ] `logi_macro_overview` を構造化レスポンスに移行
  - [ ] estat_tools, energy_tools, weather_tools, xroad_tools, corp_number_tools 全てに citation 遡及適用
- [ ] **ファイル名衝突回避**: `outputs/{type}/{purpose}_{company_id}_{unix_ts}_{rand4}.{ext}` 命名

### Step 6: 燃料価格履歴の蓄積（フェーズ3から前倒し）

蓄積を早く始めるほど傾向分析の価値が出るため、本フェーズで先行着手。

- [ ] `fuel_price_history` テーブル DDL を `core/cache.py` に追加
- [ ] `EnergyClient.get_fuel_prices()` 呼出毎に履歴行を自動 INSERT
- [ ] 重複防止: `(date, source)` UNIQUE 制約

### 完了条件

- `logi_macro_overview("東京都")` の戻り値が `{summary, files, citations}` 構造になり、`files.ppt` と `files.excel` のパスが含まれ、開ける
- 静的データ鮮度警告が Claude の応答（citations or summary 内）に含まれる
- 様式第3別紙テンプレートに「実施措置」「計画内容」「実施時期」の3項目を流し込める
- 燃料価格 1ヶ月分以上の履歴が `fuel_price_history` に蓄積されている

### フェーズ2.5 で**忘れない**チェックリスト（中優先・実装着手時に対応）

- [ ] **問題8（9万トン基準）**: `eligibility.py` 実装時に第一種/第二種/連鎖化の3区分を実装
- [ ] **問題9（改善基準告示）**: `improvement_standards.py` 実装時に告示原文を出典付きで引用
- [ ] **問題10（業種別ベンチマーク）**: `logi_macro_overview` 拡張時に「運送業者向け」と「荷主業種別」を区別
- [ ] **問題11（JSIC）**: `static/jsic.py` 実装時にコード→名称の双方向マッピングを用意
- [ ] **問題12（CO2目標）**: `national_targets.py` 実装時に物流分野固有目標と国全体目標を分離
- [ ] **問題13（citation 遡及）**: Step 5 の MCP ツール戻り値統一と同時に既存全ツールへ適用

---

## フェーズ 3: CLO 支援機能（武装データ層活用）

**前提**: フェーズ 2.5 で静的データ層・法令ロジック・出口層が揃っていること。
**ゴール**: 国交省様式に準拠した CLO 計画書ドラフトを PPT + Word + Excel で出力できる。

詳細設計 → [docs/clo_domain.md](docs/clo_domain.md)（フェーズ3実装設計セクション）

### 分析モジュール（core/analytics/）

> **命名統一**: CLO 計画策定の文脈で使うツールは `logi_clo_*` に統一（旧表記 `logi_analyze_*` は廃止）

- [ ] **Step 1**: 業界ベンチマーク（`logi_clo_benchmark_position`）
  - 自社業種（JSIC コード）に応じた全国順位・地域順位・業界平均比を算出
- [ ] **Step 2**: ドライバー需給ギャップ（`logi_clo_driver_gap`）
  - 就業者数 × 改善基準告示削減係数
- [ ] **Step 3**: 適用判定（`logi_clo_eligibility`）
  - 業種 × 売上 × 取扱量 → 第一種/第二種/連鎖化のどれに該当するか判定
- [ ] **Step 4**: 数値目標提案（`logi_clo_target_proposal`）
  - 業界平均 + 物流分野固有目標（輸送量当たりCO2 ▲23.4% 等／`national_targets.py`）から逆算した目標値
- [ ] **Step 5**: 施策効果シミュレータ（`logi_clo_simulate_*`）
  - モーダルシフト / 積載率向上 / 共同配送 / 中継輸送 / バース予約

### 統合ツール

- [ ] **Step 6**: 認定事業マッチング（`logi_clo_certified_match`）
  - 物流効率化法認定事業との類似マッチング（外部補助金スクレイピングはスコープ外）
- [ ] **Step 7**: **計画書ドラフト統合生成（`logi_clo_plan_draft`）**
  - Step 1〜6 を順次呼び、**様式第3別紙（Word）+ 経営会議 PPT + Excel + Markdown** を一括出力
  - 出力先: `outputs/{ppt,docx,excel,markdown}/`
  - PPT には**エグゼクティブサマリー（2枚目固定）**を含む
  - 全数値に出典 URL 付与（`core/export/citation.py`）

### フェーズ 3 完了条件

- `logi_clo_plan_draft(company_profile)` 一発で **PPT・Word（様式第3別紙）・Excel** が生成される
- 全数値に出典が付き、経営会議で「出典は？」と聞かれて即答できる
- 国交省記載事例集と同等の粒度で「実施措置」「計画内容」「実施時期」が埋まる

---

## フェーズ 3.5: 意思決定支援強化（NEW）

**ゴール**: 「データ提供」から「**施策の選択と評価**」へ — CLO が経営会議で説明責任を果たせる意思決定支援を実現する。

**背景**: フェーズ3 完了時点では「計画書ドラフト」は出るが、「**どの施策を選ぶべきか**」の判断材料が弱い。差別化ポイントは Option C「意思決定支援特化」。

### Step 1: 施策プレイブックライブラリ

- [ ] `core/playbook/` — 業種×取組レベル別の標準施策セット
- [ ] 公式記載事例集（既MD化済 10ファイル）から施策タグを抽出
- [ ] 施策ごとのメタデータ: 投資コスト・期待効果・実装難易度・前提条件・出典事例

### Step 2: 施策評価エンジン（`logi_clo_measure_eval`）

- [ ] 自社プロフィール × 施策候補 → スコアリング（投資対効果・実装可能性・法令適合度）
- [ ] 上位3施策をレコメンドし、選定根拠を出力

### Step 3: シナリオシミュレータ（`logi_clo_scenario_sim`）

- [ ] 複数施策の組合せシミュレーション（モーダルシフト + 共同配送 等）
- [ ] 投資総額・KPI改善幅・5年累積効果を試算

### Step 4: 財務翻訳レイヤ（`logi_clo_financial_translate`）

- [ ] 物流KPI（積載率・荷待ち時間）→ 経営指標（売上原価率・営業利益率）への換算
- [ ] 経営層が直感的に理解できる円単位での効果額提示

### Step 5: 実現可能性チェッカー（`logi_clo_feasibility_check`）

- [ ] 自社リソース（拠点数・車両数・人員）と施策要件のフィット判定
- [ ] 「この施策はあなたの会社では難しい」を明確に伝える勇気

### Step 6: 提出前バリデータ（`logi_clo_submission_validate`）

- [ ] 様式第3記載内容の網羅性チェック（必須3項目 × 実施措置/計画内容/実施時期）
- [ ] 様式第5記載内容のチェック（実績データの妥当性・遵守状況）
- [ ] 法定様式準拠率レポート

### Step 7: 定期報告書（様式第5）出力

- [ ] `logi_clo_periodic_report_draft` — 様式第5 ドラフト生成
- [ ] 計測データ（荷待ち時間・荷役等時間）テンプレート埋込
- [ ] 中長期計画との進捗比較セクション
- [ ] 既MD化済の `manufacturing_report_*.md` をテンプレートとして活用

### フェーズ 3.5 完了条件

- `logi_clo_plan_draft` の出力に「**Top 3 推薦施策 + 選定理由 + 実現可能性スコア**」が含まれる
- 計画書 PPT 2枚目に**エグゼクティブサマリー**（経営層向け要約）が自動挿入される
- `logi_clo_periodic_report_draft` で**様式第5 ドラフト**が出力される（毎年7月末提出に対応）

---

## フェーズ 4: Web ダッシュボード + AWS 移行 + 自社データアップロード

**ゴール**: 社内全員が HTTPS でアクセスできる Web ダッシュボード + MCP サーバーを AWS 上に構築する。**サンプル自社データから実データ運用へ移行する**。

### Web ダッシュボード
- [ ] FastAPI REST 層（`api/` ディレクトリ）
- [ ] Next.js 初期化
- [ ] 主要画面実装（都道府県マクロ概況・燃料価格推移・ドライバー需給・**自社プロフィール入力フォーム**）
- [ ] 成果物（PPT/PDF/Excel/Word）ダウンロード UI（プレサインド URL 経由）

### 自社データアップロード（フェーズ4 で本格対応）
- [ ] `CompanyProfile` Pydantic モデルの最終確定
- [ ] CSV/Excel 一括アップロード対応(拠点リスト・車両リスト等)
- [ ] サンプルデータ（`core/static/sample_company.py`）から実データへの移行手順

### AWS 移行
- [ ] MCP サーバーを stdio モード → HTTP/SSE モードに切り替え（FastMCP 設定変更）
- [ ] `core/cache.py` を SQLite → Redis（ElastiCache）に差し替え
- [ ] API キーを AWS Secrets Manager に移行
- [ ] ECS または Lambda にデプロイ
- [ ] Claude Desktop 設定をローカル起動から AWS エンドポイントに変更
- [ ] VPN 内からの接続確認

詳細設計 → [docs/architecture.md](docs/architecture.md)（AWS 移行計画セクション）

---

## フェーズ 4.5: 継続運用（NEW）

**ゴール**: 「一度提出して終わり」ではなく、毎年の定期報告・KPI 追跡・法令変更対応を継続できる仕組み。

- [ ] **KPI 連続トラッキング** — 月次/四半期で荷待ち・積載率の実績を蓄積
- [ ] **定期報告自動ドラフト** — 様式第5 を年次自動生成（前年データから）
- [ ] **法令変更アラート** — 改善基準告示・物流効率化法の改正をリマインド
- [ ] **計画 vs 実績ギャップ通知** — 中長期計画の数値目標から乖離した場合のアラート

---

## フェーズ 5: 公開・記事化

- [ ] README 整備
- [ ] Zenn 記事執筆
- [ ] 社内デモ
- [ ] （任意）Public 化、PyPI 公開

---

## 全体フェーズ俯瞰図

```
フェーズ0 (準備) ──→ フェーズ1 (MVP/MCP) ──→ フェーズ2 (データソース拡張)
                                                      ↓
フェーズ2.5 (武装データ層+出口) ──→ フェーズ3 (CLO計画書ドラフト)
                                                      ↓
フェーズ3.5 (意思決定支援強化+様式第5) ──→ フェーズ4 (Web+AWS+自社データ)
                                                      ↓
                            フェーズ4.5 (継続運用) ──→ フェーズ5 (公開)
```

**法的マイルストーン**:
- 2026-04: CLO 選任義務化施行
- 2026-10末: **初回中長期計画提出** ← フェーズ3完了が間に合うべき
- 毎年7月末: **定期報告書提出** ← フェーズ3.5 が間に合うべき

---

## Zenn 記事素材メモ

フェーズ完了ごとに `docs/zenn_drafts/` に実装ポイント・スクリーンショット・コードスニペットを蓄積する。
