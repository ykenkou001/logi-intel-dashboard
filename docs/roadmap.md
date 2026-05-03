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

## 現在のフェーズ: フェーズ 3.5 着手中（Step 6 + 4 + 1 + 2 + 5 + 改善タスク短期 4 件 完了・2026-05-03）

> **次セッションへの引継**: Step 3 → Step 7 の順で進める。詳細は本書 §フェーズ3.5 と memory `project_phase35_status.md`（Step 3 実装計画同梱）参照。
>
> **改善タスク短期 4 件 完了状態（2026-05-03）**:
> - ✅ 短期 1（業界平均比 1000% 超信頼性警告）— f096cf7
> - ✅ 短期 2（業界感覚レンジコード化 + data_source フラグ）— 59b1388
> - ✅ 短期 3（judgment trail + 実行カード簡易版）— c9a2ca7
> - ✅ 短期 4（法令区分の文言整合性監査）— 5b609f1
>
> **Codex 外部レビュー反映状態**:
> - ✅ Codex 2 軽量取込 → 短期3（実行カード簡易版）/ ✅ Codex 4 軽量取込 → 短期2（data_source）/ ✅ Codex 5 → 短期4（法令区分監査）
> - ⏳ Codex 1（提出実務チェックリスト）→ Step 7 で対応 / ⏳ Codex 3（保守/標準/上振れ）→ Step 3 で対応
> - 残り: Codex 2 フル版 → フェーズ4.5 / Codex 4 フル版 → フェーズ4.0

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
- [x] `core/static/co2_factors.py` — 経産省・国交省共同ガイドライン Ver.3.2（2023年6月発行・2026-05-02 表記更新）
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
| 1 | **Step 6** 提出前バリデータ ✅ 完了（2026-05-02） | 既存資産（フェーズ3 PPT/Word/Excel）の品質保証。実装規模小・即効性高 |
| 2 | **Step 4** 財務翻訳レイヤ ✅ 完了（2026-05-03） | 既存シミュレータに「営業利益+X億円」を後付け。経営会議の説得力激変 |
| 3 | **Step 1** 施策プレイブックライブラリ ✅ 完了（2026-05-03） | 後続 Step 2/3/5 の基盤データ |
| 4 | **Step 2** 施策評価エンジン ✅ 完了（2026-05-03） | プレイブック + 自社プロフィール → スコアリング |
| 5 | **Step 5** 実現可能性チェッカー ✅ 完了（2026-05-03） | プレイブック + 評価の応用 |
| 5.5 | **改善タスク**（短期 4 件） ✅ 完了（2026-05-03） | 基盤信頼性向上 + Codex レビュー 2/4/5 軽量取込（業界平均比警告 / 業界感覚レンジ + data_source / judgment trail + 実行カード簡易版 / 法令区分監査） |
| 6 | **Step 3** シナリオシミュレータ | What-if 分析 + 保守/標準/上振れ 3 区分（複雑度高・Codex レビュー 3 を吸収） |
| 7 | **Step 7** 様式第5（定期報告書） + 提出実務チェックリスト | フェーズ4.5「継続運用」への橋渡し（緊急度低・2026年7月まで時間あり／Codex レビュー 1 を吸収） |

### 改善タスク（短期 4 件 ✅ 完了・2026-05-03）

CLO 視点で全機能を見直したときに発見された欠点 + Codex 外部レビュー 5 点を統合した defensibility 強化タスク群。
すべて 2026-05-03 セッションで完了し、累積 322 件のテスト・ruff/mypy・/verify-clo-step 36/36 PASS。

「やる/やらない」の判定基準は **「2026-10 末の初回中長期計画提出に直接効くか」**。提出物の defensibility に直結するもの（短期1〜4）は前倒し、運用フェーズの機能（実行カードフル版・実績取込）はフェーズ4.0/4.5 に残す。

#### ✅ 短期 1: 業界平均比の桁外れ警告（30 分・コミット f096cf7）

- **症状**: スマートマート（コンビニ本部・売上 3,200 億）で「業界平均売上比 64,000%」と表示される
- **原因**: benchmark.py の業界平均が小規模事業所の中央値で、大企業を比較すると桁外れになる
- **対応**:
  - benchmark.py に「業界平均比 1000% 超は信頼性低下」警告フィールド追加
  - submission_validator に「業界平均比が極端な値」の数値整合性チェック追加
  - build_plan_draft_summary から業界平均比の単純表示を削除（既にエグゼクサマリーからは削除済）

#### ✅ 短期 2: 業界感覚レンジを `core/static/industry_benchmarks.py` として文書化（1〜1.5 時間・コミット 59b1388）

- **症状**: verify-clo-step スキルで「業界感覚に照らした妥当性判定」を Claude が暗黙にやっているが、その根拠がコード化されていない
- **リスク**: バリデータがロジックでチェックできない / セッション間で判定軸がブレる
- **対応**:
  - memory の `reference_industry_sense_ranges.md` の内容をデータ層化（営業利益率・物流コスト比率・積載率改善幅 等）
  - submission_validator に業界感覚レンジ検証を追加
  - verify-clo-step スキルもこの定数を参照する形に変更
  - **追加（Codex 4 軽量取込）**: ToolResponse / PlanDraftResult に `data_source: Literal["estimated", "actual"]` フラグを導入し、推計値と実測値の区別を出力に明示する（現状はサンプル3社=推計のみ。実データ取込本体はフェーズ4.0）

#### ✅ 短期 3: judgment trail（判断のトレース）+ 実行カード簡易版（2〜2.5 時間・コミット c9a2ca7）

- **症状**: Step 2 で Top 3 が出るが、「なぜこれを選んだか」「他の選択肢はなぜダメか」の比較理由がない
- **リスク**: 経営会議で「load_factor_tms ではダメだった理由は？」と聞かれた時に答えられない
- **対応**:
  - measure_eval.py に「Bottom 3」も出力（不採用理由含む）
  - Top 3 と Bottom 3 の対比表を build_eval_summary に追加
  - 各推薦に「他施策との比較ポイント」を追加（"X より ROI が高い" 等）
  - **追加（Codex 2 軽量取込）**: 各 Top 3 推薦に下記 3 フィールドを 1 行ずつ付与（フル版の「実行計画カード」はフェーズ4.5）
    - `responsible_dept`: 主管部門の例示（例: "物流部 / 情報システム部"）
    - `monthly_kpi`: 想定月次 KPI（例: "積載率 月次平均 +0.5pp"）
    - `dependencies`: 前提となる施策・データ（例: "可視化基盤の整備が前提"）

#### ✅ 短期 4: 法令区分の文言整合性監査（1〜2 時間・Codex 5 取込・コミット 5b609f1）

- **症状**: 連鎖化事業者の出力に荷主向けの第46条引用が混在する可能性。会社区分（特定第一種荷主／第二種荷主／連鎖化事業者）と引用条文の対応が PPT・Word 本文・引用テキストで一貫しているか未検証
- **リスク**: 提出物が法令区分と整合しない → CLO の defensibility 致命的損傷（Compliance Assurance 直撃）
- **法令区分と条文対応**:
  - 特定第一種荷主／第二種荷主: 物流効率化法 第46条（中長期計画作成義務）
  - 連鎖化事業者: 物流効率化法 第65条（中長期計画作成義務・領域 2 区分）
  - CLO 選任: 物流効率化法 第66条
- **対応**:
  - submission_validator.py に「会社区分 × 引用条文の整合性」検査を追加（既存の form3 必須セクション検査の延長）
  - core/export/citation.py の引用テンプレートを区分別に分岐（連鎖化用テンプレートを新設または既存ラベル切替）
  - PPT / Word / Markdown 全出力で会社区分が判別できる箇所（会社プロフィール・法的根拠セクション）の文言を区分依存に
  - 単体テスト: 連鎖化 1社 + 荷主 2社 のサンプルで条文引用が区分通りに切り替わることを検証

#### 中期（フェーズ4.0 で対応・要記録）

- **plan_draft の docx 文章テンプレート化**: 公式記載見本集 MD 10 ファイルを文体テンプレートとして取り込み（現状の汎用文を脱却）
- **実データ入力フォーム（Codex 4 本体）**: CSV / Excel から CompanyProfile を構築（サンプル3社からの脱却・推計/実測データ粒度の確保）
- **KPI 計測フレーム**: 計画策定時に KPI 定義（測定方法・頻度・閾値）を埋め込む
- **CLO スタイル別重み付け**: 4 軸の重みプリセット（攻め / 守り / 環境重視 / 効率重視）

#### フェーズ4.5 で対応（要記録）

- **実行責任カード フル版（Codex 2 本体）**: 施策ごとに `主管部門 / 関係部門 / 外部関係者 / 決裁事項 / 月次KPI / リスク / 依存関係` の完全版カードを生成。短期3 で導入する 3 フィールド版を拡張する形

#### 長期

- **競合差別化の定量提示**: 「コンサル ¥X 億円相当を 3 ヶ月で代替」を成果物に明記する機能
- **計画書ドラフトの章立て深化**: 公式記載見本集の「Ⅰ事業者の名称等」「Ⅴ参考情報」等にも対応

### Step 1: 施策プレイブックライブラリ ✅ 完了（2026-05-03）

- [x] `core/playbook/` — 業種×取組レベル別の標準施策セット（10 件）
- [x] 公式記載事例集（既MD化済 10ファイル）+ 物流効率化法 認定事業 + 業界事例から施策タグを抽出
- [x] 施策ごとのメタデータ: 投資コスト・期待効果・実装難易度・前提条件・適用補助金・成功事例・失敗パターン
- [x] 業種別・規模別フィルタリング（PlaybookFilter / filter_playbook）
- [x] `core/playbook/measures.py` — PlaybookMeasure dataclass + ALL_MEASURES（10件）
- [x] `core/playbook/filters.py` — PlaybookFilter + filter_playbook + build_search_summary
- [x] `clo_tools.py` — logi_clo_playbook_search 登録（業種・規模・難易度・セクション・取組タイプで絞込）
- [x] efficiency_law_certified.case_id への参照（成功事例引用可）
- [x] 単体テスト 23 件全パス（measures 10 / filters 13）

**収録施策一覧（10件）**:
| section | measure_id | 名称 |
|---------|-----------|------|
| load    | modal_shift_to_rail | 鉄道貨物へのモーダルシフト |
| load    | load_factor_tms | 積載率向上（TMS 配車最適化） |
| load    | joint_delivery_competitor | 同業他社との共同配送 |
| load    | pallet_standardization | パレット標準化（T11／T12） |
| load    | visualization_baseline | 物流実態の把握・可視化（前提施策） |
| load    | lead_time_review | 発注頻度・リードタイム見直し（着荷主側） |
| wait    | berth_booking_vbs | バース予約受付システム（VBS） |
| wait    | delivery_time_distribution | 納入時間帯の分散・拡大 |
| loading | relay_transport | 中継輸送（長距離運行の分割） |
| loading | warehouse_dx_wms | WMS 導入による倉庫オペレーション DX |

### Step 2: 施策評価エンジン（`logi_clo_measure_eval`）✅ 完了（2026-05-03）

- [x] 自社プロフィール × 施策候補 → スコアリング（投資対効果・実装可能性・法令適合度・補助金カバー率）
- [x] 上位3施策をレコメンドし、選定根拠を出力
- [x] CO2 削減効果・コスト削減効果（業界平均物流コスト比率 × addressable_share × 削減率）・実装難易度（1〜5）・投資回収期間を多軸スコア化
- [x] `core/analytics/measure_eval.py` — MeasureScore + evaluate_measures + 4軸スコアリング
- [x] `clo_tools.py` — logi_clo_measure_eval 登録
- [x] `scripts/verify_clo_step.py` に measure_eval 検証を統合
- [x] 単体テスト 25 件全パス（4軸スコア / リソース推定 / Top 3 / 連鎖化事業者特例）

**スコアリング設計**:
- ROI（35%）: 期待コスト削減 / 投資中央値の比率を 5 段階で評価
- 実装可能性（30%）: 難易度（1→100, 5→20）+ リソース欠如ペナルティ（-20/件）
- 法令適合度（25%）: 様式第3 必須セクション該当 +80 / 法令条文紐付き +20
- 補助金カバー率（10%）: 0件→0 / 1件→50 / 2件以上→100
- 連鎖化事業者は荷役等セクション（loading）の compliance スコアを 30 に減点

**自社リソース自動推定**: 拠点数≥2 → multi_site / 自社車両>0 → fleet_owned / dc系拠点 → warehouse_management / 都道府県跨ぎ≥3 → long_distance_transport

### Step 3: シナリオシミュレータ（`logi_clo_scenario_sim`）

> **実装計画は 2026-05-03 セッションで合意済**（下記 詳細設計を参照）
> **Codex レビュー 3 取込（2026-05-03）**: 「5施策合算が強く見えすぎる」問題への対応として、各施策効果に **保守 / 標準 / 上振れ の 3 区分** を持たせ、重複・前提・信頼度を明示する。CFO 質問（実装費・運用費・税効果・減価償却・サービスレベル低下リスク）に答える形に拡張する。

- [ ] 複数施策の組合せシミュレーション（モーダルシフト + 共同配送 等）
- [ ] 投資総額・KPI改善幅・5年累積効果を試算
- [ ] **What-if 分析**: 燃料価格 ±20% / 運賃 ±10% / 需要 ±10% / 改善基準告示さらなる強化 シナリオでストレステスト
- [ ] **3 区分シナリオ（Codex 3 取込）**: 各施策の期待効果（コスト削減・CO2 削減・営業利益増）を `conservative / standard / upside` の 3 値で持つ。`upside` は楽観前提、`conservative` は実装費・運用費・サービスレベル低下リスクを織り込んだ下振れ
- [ ] **重複ダンピング × 3 区分の組合せ**: 同 form3_section 重複 0.7 倍と 3 区分を直交させ、CFO に「最低でも保守シナリオで X 億円」と説明できる出力形にする

#### 詳細設計（合意済・2026-05-03）

**1. 施策組合せの重複処理（シナジー倍率方式）**
- 同 form3_section に 2 施策以上 → 合算効果に **0.7 を乗じる**（重複考慮ダンピング）
- セクション跨ぎ → 倍率 1.0
- 経営層への説明: 「同領域施策の組合せは効果重複を 30% ディスカウント」

**2. What-if シナリオ（プリセット 8 種）**

| シナリオ | コスト削減倍率 | 投資倍率 | CO2 倍率 |
|---------|--------------|---------|---------|
| baseline | 1.00 | 1.00 | 1.00 |
| 燃料 +20% | 1.05 | 1.00 | 1.00 |
| 燃料 -20% | 0.95 | 1.00 | 1.00 |
| 運賃 +10% | 1.10 | 1.00 | 1.00 |
| 運賃 -10% | 0.90 | 1.00 | 1.00 |
| 需要 +10% | 1.10 | 1.00 | 1.10 |
| 需要 -10% | 0.90 | 1.00 | 0.90 |
| 改善基準強化 | 0.80 | 1.30 | 1.00 |

**3. 堅牢性判定（緑/黄/赤）**
- 🟢 baseline 営業利益増の 70% 以上を維持
- 🟡 50-70%
- 🔴 50% 未満（投資判断却下リスク）
- 「**燃料 +20% でも黒字維持**」（フェーズ3.5 完了条件）を明示判定

**4. 入力施策**
- 引数明示 OR 省略時は Step 2 Top 3 自動採用

**5. 実装ファイル**
- `core/analytics/scenario_sim.py` (~350 行): ScenarioParameters / ScenarioResult / ScenarioSimResult / simulate_scenarios / build_scenario_summary
- `mcp_server/tools/clo_tools.py` (+50 行): `logi_clo_scenario_sim(company_id, selected_measure_ids=None)` 登録
- `tests/core/test_analytics_scenario_sim.py` (~250 行): 15-20 テスト
- `scripts/verify_clo_step.py` (+50 行): verify_scenario_sim 統合

**6. データ構造（合意済）**
```python
@dataclass(frozen=True)
class ScenarioParameters:
    name: str
    cost_saving_multiplier: float
    investment_multiplier: float
    co2_multiplier: float
    description: str

@dataclass(frozen=True)
class ScenarioResult:
    scenario: ScenarioParameters
    annual_co2_reduction_kg: float
    annual_cost_saving_jpy: float
    annual_operating_profit_increase_jpy: float
    total_investment_jpy: float
    five_year_npv_jpy: float
    robustness_level: Literal["green", "yellow", "red"]
    robustness_message: str

@dataclass
class ScenarioSimResult:
    company_id / company_name / industry
    selected_measures: list[PlaybookMeasure]
    synergy_multiplier: float
    baseline: ScenarioResult
    stress_scenarios: list[ScenarioResult]
    summary_message: str
    citations / freshness_warnings
```

### Step 4: 財務翻訳レイヤ（`logi_clo_financial_translate`）✅ 完了（2026-05-03）

物流 KPI を P&L インパクトに換算。経営層への翻訳機能。

- [x] 物流KPI（コスト削減）→ 経営指標（営業利益増・利益率改善 pp）への換算
- [x] 経営層が直感的に理解できる円単位での効果額提示（営業利益 +X 億円・5年 NPV）
- [x] CO2 削減 → 炭素価格回避額（J-クレジット 〜 GX-ETS の min/max レンジ）
- [x] ESG プレミアム → 定性記述（資本コスト改善の数値化は研究段階のため見送り）
- [x] 罰則回避（不作為コスト）→ 罰則金額 + ブランド毀損リスクの定性記述
- [x] 5 年累積 NPV（割引率 3%）算出
- [x] `core/static/financial_factors.py` — CarbonPriceRange / PenaltyAmounts / NpvParameters
- [x] `core/static/sample_company.py` — operating_profit_jpy / cost_of_goods_sold_jpy 追加
- [x] `core/analytics/financial_translate.py` — FinancialImpact + translate_to_pnl_impact
- [x] `clo_tools.py` — logi_clo_financial_translate 登録
- [x] `core/analytics/plan_draft.py` — エグゼクサマリーに財務インパクト統合
- [x] 単体テスト 12 件全パス（NPV 算出・炭素レンジ・合算・定性記述）

### Step 5: 実現可能性チェッカー（`logi_clo_feasibility_check`）✅ 完了（2026-05-03）

- [x] 自社リソース（拠点数・車両数・人員）と施策要件のフィット判定
- [x] 業界実績分布から「業界平均到達」が自社規模で目標年に可能か判定（積載率 38→50%）
- [x] 警告レベル: 🟢 緑（妥当）/ 🟡 黄（要注意）/ 🔴 赤（無理筋・罰則リスク高）
- [x] 「この施策はあなたの会社では難しい」を明確に伝える勇気
- [x] `core/analytics/feasibility_check.py` — FeasibilityVerdict / TargetReachability / check_feasibility
- [x] `clo_tools.py` — logi_clo_feasibility_check 登録
- [x] `scripts/verify_clo_step.py` に統合
- [x] 単体テスト 21 件全パス

**判定基準**:
- 🟢 green: リソース充足 + 規模適合 + 難易度 ≤3
- 🟡 yellow: リソース 1-2件不足 OR ボーダーライン規模 OR 難易度 4
- 🔴 red: リソース ≥3件不足 OR 規模未達 OR 難易度 5+不足 OR 連鎖化×荷役等
- red 理由を「業種非適合 / 売上未達 / 取扱量未達」に分類して誤誘導防止

**KPI 到達可能性**: 積載率 38→50% を業界実績 1.5pp/年と比較（残り年数で必要改善幅算定）

**サンプル別 verdict 内訳**:
| サンプル | 🟢 | 🟡 | 🔴 |
|----------|-----|-----|-----|
| 製造業    | 7  | 2  | 1  |
| 卸売業    | 7  | 2  | 1  |
| コンビニ  | 3  | 1  | 6  | （業種非適合4 + 連鎖化×荷役等2）

### Step 6: 提出前バリデータ（`logi_clo_submission_validate`）✅ 完了（2026-05-02）

計画書の必須記載・整合性をチェック。提出前の最終ゲート。

- [x] 様式第3記載内容の網羅性チェック（必須3項目 × 実施措置/計画内容/実施時期 = 9項目／連鎖化は 6項目）
- [ ] 様式第5記載内容のチェック（実績データの妥当性・遵守状況）— Step 7 実装後に追加
- [x] 数値整合性（CO2/コスト/投資/回収期間が非負・桁妥当範囲）
- [x] 出典欠落チェック（CO2ガイドライン・物流効率化法・URL 妥当性）
- [x] 告示・国家目標との整合（積載率 ≤100%、CO2 目標 ▲23.4% 整合）
- [x] 法定様式準拠率レポート（error -10pt / warning -3pt / 下限 0%）
- [x] `core/validators/submission_validator.py` — ValidationIssue + ValidationReport + validate_submission
- [x] `clo_tools.py` — logi_clo_submission_validate 登録
- [x] 単体テスト 18 件全パス（form3 完全性 5 / 数値 3 / 出典 3 / 告示 2 / score 3 / summary 2）

### Step 7: 定期報告書（様式第5）出力 + 提出実務チェックリスト（`logi_clo_periodic_report_draft`）

毎年7月末提出の様式第5 ドラフトを生成。フェーズ3 の中長期計画書ドラフトと対をなす機能。
**Codex レビュー 1 取込（2026-05-03）**: 提出実務（オンライン提出 / GビズID / 指定通知）のチェックリストを `logi_clo_plan_draft` 出力の最終ページにも 1 セクション追加し、2026-10末提出時の defensibility を担保する。

- [ ] 様式第5 Word ドラフト生成
- [ ] 計測データ（荷待ち時間・荷役等時間）テンプレート埋込
- [ ] 中長期計画との進捗比較セクション（計画 vs 実績ギャップ可視化）
- [ ] 既MD化済の `manufacturing_report_*.md` をテンプレートとして活用
- [ ] **提出実務チェックリスト（Codex 1 取込）**: 下記項目を `core/export/submission_checklist.py` として実装し、`logi_clo_plan_draft` および `logi_clo_periodic_report_draft` の出力末尾に「提出準備」セクションとして組込
  - 提出経路: e-Gov / GビズID プライム or メンバー
  - 指定通知書番号（特定事業者指定の証跡）
  - 法人番号（13 桁・国税庁法人番号公表サイト整合）
  - 代表者情報（氏名・役職）
  - 作成担当者連絡先（CLO 本人 or 委任先）
  - 様式第3 / 様式第4 / 様式第5 の使い分けと提出頻度

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
