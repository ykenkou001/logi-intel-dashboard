# 開発ロードマップ

**責任範囲**: フェーズ別の開発計画と進捗状況。「今どこにいるか」「次に何をするか」を把握するためのドキュメント。

> ⚠️ 全フェーズの判断基準は **CLO 支援への徹底コミット**（[CLAUDE.md §1.5](../CLAUDE.md)）。アプリの軸は **意思決定支援（Option C）**。各フェーズの完了条件は「CLO の意思決定に直接効く形で出力できること」。

## フェーズ全体像

```
フェーズ 0   準備                                                ✅ 完了
フェーズ 1   MVP — MCP サーバー初版（e-Stat）                    ✅ 完了
フェーズ 2   データソース拡張                                     ✅ 完了
フェーズ 2.5 CLO 武装データ層 + 出口整備                          ✅ 完了
フェーズ 3.0 計画書ドラフト基盤                                   ✅ 完了 (2026-05-02)
フェーズ 3.5 ★意思決定支援強化（差別化の心臓部）★              ← 今ここ
フェーズ 4.0 Web ダッシュボード + AWS 移行 + 自社データ取込
フェーズ 4.5 継続運用機能（定期報告書・進捗・法改正アラート）
フェーズ 5   公開・記事化
```

---

## 現在のフェーズ: フェーズ 3 完了（Step 1〜7 全完了・2026-05-02）→ フェーズ 3.5 着手準備中

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

## フェーズ 2.5: CLO 武装データ層 + 出口整備 ✅ 完了（2026-05-02）

**達成内容**: フェーズ3 の分析モジュールが「CLO に刺さる成果物」を出せる土台を整備。
レビューで発見した高優先 7 件を反映後、6 ステップ全完了。総コミット 6 件、テスト 138 件全パス、ruff/mypy 双方クリア。

### Step 1: e-Stat 追加クライアント ✅

- [x] `core/clients/estat_logistics.py` — 物流特化ヘルパー（既存 `EStatClient` のラッパー）
- [x] 物流必修7統計の statsCode カタログ（自動車輸送統計年報・物流センサス・港湾・鉄道・経済センサス・賃金構造・国勢調査）
- [x] `find_latest_stats_data_id` による statsDataId 動的解決（年次更新追従）

### Step 2: 静的データ層 + 鮮度管理 ✅

- [x] `core/static/_freshness.py` — 鮮度メタデータ管理（4種類のカデンス）
- [x] `core/static/co2_factors.py` — 国交省・経産省共同ガイドラインVer.3.1
- [x] `core/static/improvement_standards.py` — 改善基準告示2024年4月施行版（告示原文準拠）
- [x] `core/static/national_targets.py` — 物流分野固有CO2目標（▲23.4%）+ モーダルシフト目標
- [x] `core/static/jsic.py` — 日本標準産業分類細分類（CLO関連業種27件）
- [x] `core/static/industry_freight_coef.py` — 業種別物流原単位（売上→取扱量推計）
- [x] `core/static/sample_company.py` — サンプル3社（製造/卸売/連鎖化）
- [ ] `core/static/standard_freight.py` — 標準的運賃 2024 改定版（フェーズ3 着手時）
- [ ] `core/static/efficiency_law_certified.py` — 物流効率化法 認定事業 CSV 自動取込（フェーズ3 着手時）

### Step 3: 法令ロジック ✅

- [x] `core/legal/eligibility.py` — 3区分判定エンジン（第一種/第二種/連鎖化）
  - 取扱量未指定なら売上から推計（industry_freight_coef 利用）
  - ボーダーライン警告（基準±30%）/ override での明示指定
- [x] `core/legal/improvement_check.py` — 改善基準告示準拠チェック
  - ComplianceItem.to_form5_line() で様式第5 用表示生成

### Step 4: 国交省公式テンプレートの取込（一部完了）

- [x] **公式記載事例集** 製造業・卸売業・小売業・連鎖化事業者 × 取組進行/これから = 8 パターン + 定期報告2パターン = 10ファイル MD 化（2026-05-02）
- [ ] **様式第3別紙 中長期計画書（Word）** — 手動 DL タスク（MLIT ポータル）
- [ ] **様式第5 定期報告書（Word）** — 手動 DL タスク
- [ ] **PPT マスタスライド** — micware ブランドテンプレート入手後

### Step 5: 出口層 + MCP ツール構造統一 ✅

- [x] `core/export/citation.py` — 出典管理（テンプレート 8 種類）
- [x] `core/export/response.py` — ToolResponse 構造 + 衝突回避ファイル名命名
- [x] `core/export/ppt_writer.py` — PPT 出力（エグゼクティブサマリー2枚目固定）
- [x] `core/export/excel_writer.py` — 数値表 + 出典シート
- [x] `core/export/docx_form3_writer.py` — 様式第3別紙（第46条/第5条 自動切替）
- [x] `core/export/markdown_writer.py` — Markdown 出力
- [x] `logi_macro_overview` を ToolResponse 構造に移行 + citation 適用
- [ ] `core/export/pdf_writer.py` — PDF 変換（フェーズ3 着手時）
- [ ] estat_tools / energy_tools / weather_tools / xroad_tools / corp_number_tools の citation 遡及適用（フェーズ3）

### Step 6: 燃料価格履歴蓄積 ✅

- [x] `fuel_price_history` テーブル DDL（`core/cache.py`）
- [x] PRIMARY KEY (date, source) で日次1行制約
- [x] `EnergyClient.get_fuel_prices()` 呼出毎に履歴自動 INSERT

### 完了条件の達成状況

- [x] `logi_macro_overview("東京都")` の戻り値が `{summary, files, citations, freshness_warnings}` 構造
- [x] 静的データ鮮度警告が Claude の応答に含まれる仕組み
- [x] 様式第3別紙テンプレートに「実施措置」「計画内容」「実施時期」3項目を流し込める（テスト済）
- [ ] 燃料価格 1ヶ月分以上の履歴蓄積（運用してから自然達成・コード側の準備は完了）

### フェーズ2.5 で発見した残課題（フェーズ3 着手時に対応）

- [ ] PDF writer 実装
- [ ] 既存 MCP ツール5種への citation 遡及適用
- [ ] 様式第3 Word / 様式第5 Word / PPT マスタの公式テンプレート入手
- [ ] standard_freight.py / efficiency_law_certified.py の実装

---

## フェーズ 3: CLO 支援機能（武装データ層活用）

**前提**: フェーズ 2.5 で静的データ層・法令ロジック・出口層が揃っていること。
**ゴール**: 国交省様式に準拠した CLO 計画書ドラフトを PPT + Word + Excel で出力できる。

詳細設計 → [docs/clo_domain.md](docs/clo_domain.md)（フェーズ3実装設計セクション）

### 分析モジュール（core/analytics/）

> **命名統一**: CLO 計画策定の文脈で使うツールは `logi_clo_*` に統一（旧表記 `logi_analyze_*` は廃止）

- [x] **Step 1**: 業界ベンチマーク（`logi_clo_benchmark_position`）✅ 完了（2026-05-02）
  - 自社業種（JSIC コード）に応じた全国・地域別事業所数・業界平均比を算出
  - `core/analytics/benchmark.py` — BenchmarkResult + analyze_benchmark
  - `mcp_server/tools/clo_tools.py` — logi_clo_benchmark_position 登録
  - e-Stat 経済センサス‐基礎調査 2024（statsDataId `0004040101`、産業小分類別民営事業所数）
    + JILS物流コスト調査（静的）を組合せ
  - JSIC 細分類4桁の上3桁を `cd_cat01` に渡して **小分類で絞り込み**（東京都の 5411 → 4,851件で検証済）
  - Claude Desktop 実機確認: 完了（2026-05-02）
- [x] **Step 2**: ドライバー需給ギャップ（`logi_clo_driver_gap`）✅ 完了（2026-05-02）
  - 就業者数 × 改善基準告示削減係数（13.5%）
  - `core/analytics/driver_gap.py` — DriverGapResult + analyze_driver_gap
  - `clo_tools.py` — logi_clo_driver_gap 登録
  - e-Stat 経済センサス‐基礎調査 2024（statsDataId `0004040102`、中分類44 道路貨物運送業の従業者数）
    + 改善基準告示（厚労省告示第367号）+ 国交省2030年試算（▲34.1%）
  - 妥当性検証: 全国170万人＝物流2024年問題資料と一致、都道府県シェアも人口分布と整合
- [x] **Step 3**: 適用判定（`logi_clo_eligibility`）✅ 完了（2026-05-02）
  - 業種 × 売上 × 取扱量 → 第一種/第二種/連鎖化のどれに該当するか判定
  - `core/analytics/eligibility_analysis.py` — build_eligibility_summary
  - `clo_tools.py` — logi_clo_eligibility 登録（既存 `core/legal/eligibility.py` をラップ）
  - 取扱量未指定なら売上 × `industry_freight_coef` で推計、ボーダーライン警告（±30%）対応
  - 妥当性検証: 5ケース（該当なし/大規模/連鎖化/ボーダーライン/実測値）全て期待通り
- [x] **Step 4**: 数値目標提案（`logi_clo_target_proposal`）✅ 完了（2026-05-02）
  - 業界平均 + 物流分野固有目標（輸送量当たりCO2 ▲23.4% 等／`national_targets.py`）から逆算した目標値
  - `core/analytics/target_proposal.py` — TargetProposalResult + propose_targets
  - `clo_tools.py` — logi_clo_target_proposal 登録
  - 4目標を出力: CO2原単位（▲23.4%）/ 積載率（38→50%）/ モーダルシフト（鉄道+15.8%）/ 物流コスト比率（業界平均比 ▲0.3〜0.5pt）
  - 業界平均比200%以上の規模優位企業には ▲0.5pt 提案、それ以外は ▲0.3pt
  - 運輸業は物流コスト目標を自動除外（荷主ではないため）
  - 妥当性検証: 4ケース（卸売・製造・運輸・小売）全て期待通り、業界平均値もJILS公表値と整合
- [x] **Step 5**: 施策効果シミュレータ（`logi_clo_simulate_measures`）✅ 完了（2026-05-02）
  - モーダルシフト / 積載率向上 / 共同配送 / 中継輸送 / バース予約 の5施策を1ツールで同時試算
  - `core/analytics/simulator.py` — SimulationResult + simulate_measures
  - `clo_tools.py` — logi_clo_simulate_measures 登録
  - 各施策ごとに CO2 削減・コスト削減・ドライバー時間削減・必要投資・回収期間を出力
  - co2_factors（トラック76 vs 鉄道21 g-CO2/トンキロ）+ 業界統計の標準ファクターを使用
  - 妥当性検証: 3ケース（中堅卸/大規模製造/食肉加工）の数値が業界事例レンジと整合

### 統合ツール

- [x] **Step 6**: 認定事業マッチング（`logi_clo_certified_match`）✅ 完了（2026-05-02）
  - 物流効率化法認定事業との類似マッチング（外部補助金スクレイピングはスコープ外）
  - `core/static/efficiency_law_certified.py` — 認定事業 公表サンプル10件
  - `core/analytics/certified_match.py` — find_matches + スコアリング
  - `clo_tools.py` — logi_clo_certified_match 登録
  - 業種カテゴリ一致 +3点 / 取組タイプ一致 +2点で上位5件抽出
  - 妥当性検証: 4ケース（卸売/製造/コンビニ/運送業）全て期待通り、運送業はマッチ0件で正常表示
- [x] **Step 7**: **計画書ドラフト統合生成（`logi_clo_plan_draft`）** ✅ 完了（2026-05-02）
  - Step 1〜6 を順次呼び、**様式第3別紙（Word）+ 経営会議 PPT + Excel + Markdown** を一括出力
  - 出力先: `outputs/{ppt,docx,excel,markdown}/`
  - PPT には**エグゼクティブサマリー（2枚目固定）**を含む
  - 全数値に出典 URL 付与（12件統合・URL ベース重複排除済）
  - `core/analytics/plan_draft.py` — generate_plan_draft + build_plan_draft_summary
  - 入力: サンプル企業ID（製造業/卸売業/連鎖化）。フェーズ4 で実データ対応予定
  - 妥当性検証: 3サンプル全成功、12ファイル生成、CO2削減3,400-12,900トン/年が業界事例と整合

### フェーズ 3 完了条件

- `logi_clo_plan_draft(company_profile)` 一発で **PPT・Word（様式第3別紙）・Excel** が生成される
- **PPT 1 枚目に「経営層向けエグゼクティブサマリー」が必ず入る**（財務×戦略×競合×リスク）
- 全数値に出典が付き、経営会議で「出典は？」と聞かれて即答できる
- 国交省記載事例集と同等の粒度で「実施措置」「計画内容」「実施時期」が埋まる
- 自社データはサンプル（`core/static/sample_company.py`）で動作確認 — 本格的なアップロードはフェーズ4

---

## フェーズ 3.5: 意思決定支援強化（★ 差別化の心臓部 ★）

**ゴール**: 「データ提供」から「**施策の選択と評価**」へ — CLO が経営会議で「何をやるか・なぜやるか・いくら効くか」を即答できる意思決定支援を実現する。

**背景**: フェーズ3 完了時点では「計画書ドラフト」は出るが、「**どの施策を選ぶべきか**」の判断材料が弱い。差別化ポイントは Option C「意思決定支援特化」。

### 実装順序の推奨（即効性 + 依存関係）

下記の Step 1〜7 はドキュメント上の論理的グルーピング。**実装は以下の順序を推奨**:

| 実装順 | Step | 理由 |
|------|------|------|
| 1 | **Step 6** 提出前バリデータ | 既存資産（フェーズ3 PPT/Word/Excel）の品質保証。実装規模小・即効性高 |
| 2 | **Step 4** 財務翻訳レイヤ | 既存シミュレータに「営業利益+X億円」を後付け。経営会議の説得力激変 |
| 3 | **Step 1** 施策プレイブックライブラリ | 後続 Step 2/3/5 の基盤データ |
| 4 | **Step 2** 施策評価エンジン | プレイブック + 自社プロフィール → スコアリング |
| 5 | **Step 5** 実現可能性チェッカー | プレイブック + 評価の応用 |
| 6 | **Step 3** シナリオシミュレータ | What-if 分析（複雑度高） |
| 7 | **Step 7** 様式第5（定期報告書） | フェーズ4.5「継続運用」への橋渡し（緊急度低・2026年7月まで時間あり） |

### Step 1: 施策プレイブックライブラリ

- [ ] `core/playbook/` — 業種×取組レベル別の標準施策セット
- [ ] 公式記載事例集（既MD化済 10ファイル）+ 物流効率化法 認定事業 + 業界事例から施策タグを抽出
- [ ] 施策ごとのメタデータ: 投資コスト・期待効果・実装難易度・前提条件・適用補助金・成功事例・失敗パターン
- [ ] 業種別・規模別フィルタリング

### Step 2: 施策評価エンジン（`logi_clo_measure_eval`）

- [ ] 自社プロフィール × 施策候補 → スコアリング（投資対効果・実装可能性・法令適合度・補助金カバー率）
- [ ] 上位3施策をレコメンドし、選定根拠を出力
- [ ] CO2 削減効果（環境省係数）・コスト削減効果（自社データ × 施策効果係数）・実装難易度（1〜5）・投資回収期間を多軸スコア化

### Step 3: シナリオシミュレータ（`logi_clo_scenario_sim`）

- [ ] 複数施策の組合せシミュレーション（モーダルシフト + 共同配送 等）
- [ ] 投資総額・KPI改善幅・5年累積効果を試算
- [ ] **What-if 分析**: 燃料価格 ±20% / 運賃 ±10% / 需要 ±10% / 改善基準告示さらなる強化 シナリオでストレステスト

### Step 4: 財務翻訳レイヤ（`logi_clo_financial_translate`）

物流 KPI を P&L インパクトに換算。経営層への翻訳機能。

- [ ] 物流KPI（積載率・荷待ち時間）→ 経営指標（売上原価率・営業利益率）への換算
- [ ] 経営層が直感的に理解できる円単位での効果額提示（積載率 +5% → 営業利益 +X 億円）
- [ ] CO2 削減 → 炭素税回避額 + ESG プレミアム
- [ ] 罰則回避（不作為のコスト）試算

### Step 5: 実現可能性チェッカー（`logi_clo_feasibility_check`）

- [ ] 自社リソース（拠点数・車両数・人員）と施策要件のフィット判定
- [ ] 業界実績分布から「業界平均到達」が自社規模で 3 年で可能か判定
- [ ] 警告レベル: 緑（妥当）/ 黄（要注意）/ 赤（無理筋・罰則リスク高）
- [ ] 「この施策はあなたの会社では難しい」を明確に伝える勇気

### Step 6: 提出前バリデータ（`logi_clo_submission_validate`）

計画書の必須記載・整合性をチェック。提出前の最終ゲート。

- [ ] 様式第3記載内容の網羅性チェック（必須3項目 × 実施措置/計画内容/実施時期 = 9項目）
- [ ] 様式第5記載内容のチェック（実績データの妥当性・遵守状況）
- [ ] 数値整合性（合計値・年次推移）
- [ ] 出典欠落チェック
- [ ] 法定様式準拠率レポート

### Step 7: 定期報告書（様式第5）出力（`logi_clo_periodic_report_draft`）

毎年7月末提出の様式第5 ドラフトを生成。フェーズ3 の中長期計画書ドラフトと対をなす機能。

- [ ] 様式第5 Word ドラフト生成
- [ ] 計測データ（荷待ち時間・荷役等時間）テンプレート埋込
- [ ] 中長期計画との進捗比較セクション（計画 vs 実績ギャップ可視化）
- [ ] 既MD化済の `manufacturing_report_*.md` をテンプレートとして活用

### フェーズ 3.5 完了条件

- `logi_clo_plan_draft` の出力に「**Top 3 推薦施策 + 選定理由 + 実現可能性スコア**」が含まれる
- What-if シナリオで計画が「燃料 +20% でも黒字維持」を示せる
- 物流 KPI 改善が「営業利益 X 億円」に翻訳される
- 計画書提出前に必須項目チェック（様式第3 + 様式第5）が pass する
- `logi_clo_periodic_report_draft` で**様式第5 ドラフト**が出力される（毎年7月末提出に対応）
- ※ エグゼクティブサマリー（経営層向け1ページ要約）は **フェーズ3 で PPT 2枚目に固定実装済み**

---

## フェーズ 4.0: Web ダッシュボード + AWS 移行 + 自社データ取込

**ゴール**: 社内全員が HTTPS でアクセスできる Web ダッシュボードを AWS 上に構築し、CSV/Excel で自社データをアップロードできるようにする。

### Web ダッシュボード
- [ ] FastAPI REST 層（`api/` ディレクトリ）
- [ ] Next.js 初期化
- [ ] 主要画面: マクロ概況・業界ベンチマーク・ドライバー需給・施策ライブラリ・シミュレータ・**自社プロフィール入力フォーム**・計画書ダウンロード
- [ ] 成果物（PPT/PDF/Excel/Word）ダウンロード UI（プレサインド URL 経由）

### 自社データアップロード（フェーズ4.0 で本格対応）
- [ ] `CompanyProfile` Pydantic モデルの最終確定
- [ ] CSV / Excel / Pydantic フォーム による一括アップロード
  - 拠点リスト・配送ルート・積載率実績・荷待ち時間実績・燃料消費等
  - サンプルテンプレート（`outputs/sample_company_template.xlsx`）DL 提供
- [ ] サンプルデータ（`core/static/sample_company.py`）から実データへの移行手順

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
