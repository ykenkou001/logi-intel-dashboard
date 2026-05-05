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
フェーズ 3.5 ★意思決定支援強化（差別化の心臓部）★              ✅ 完了 (2026-05-03)
フェーズ 4.0 Web ダッシュボード + AWS 移行 + 自社データ取込      ✅ 完了 (2026-05-05)
フェーズ 4.1 段階 a 小改修（基盤整備 a.1〜a.5）                   ✅ 完了 (2026-05-05)
フェーズ 4.5 段階 b J3 デイリーコックピット + B 用途別テンプレ    ✅ 完了 (2026-05-06)
フェーズ 5.0 段階 c 業種別 CLO 標準パッケージ + F2/J2 スコア   ← 進行中（c.7 着手前）
             └ c.1-c.3 IndustryPackage 基盤 + Override 4 分類     ✅ 完了 (2026-05-06)
             └ c.4 既存資産接続検証                              ✅ 完了 (2026-05-06)
             └ c.5/c.6 F2 標準化スコア + J2 罠スコア              ✅ 完了 (2026-05-06)
             └ c.7 MCP/REST 3 ツール公開                         ⏳ 次セッション着手
             └ c.8 連鎖化特有処理 / c.9 統合テスト + Web 2 画面  ⏳ 未着手
フェーズ 5.5 公開・記事化（旧フェーズ5）                          ⏳ 未着手
```

> 段階 a/b/c の詳細設計は `~/.claude/plans/b-c-flickering-pixel.md`（健一の global plans）参照。
> Codex の二者議論で確定した 7 件の修正点を反映済。

---

## 現在のフェーズ: フェーズ 5.0 進行中 — c.1-c.6 完了 / c.7 MCP/REST 公開フェーズ着手前

> **状況（2026-05-06 時点）**: 段階 c の中核（IndustryPackage 基盤 + F2 標準化スコア + J2 罠スコア）まで main 取込済。次は c.7 で `logi_clo_*` ツール 3 件 + REST 3 エンドポイント公開。引継ぎ詳細は [HANDOFF_NEXT_SESSION.md](../HANDOFF_NEXT_SESSION.md) 参照。

### 完了 PR（フェーズ4.5+5.0 関連）

| PR | 内容 | 主要新規ファイル |
|---|---|---|
| #6 | フェーズ4.1 段階 a（a.1-a.5） | `core/analytics/wait_time_heatmap.py` / `core/static/standard_freight.py` / NotebookLM 7 社事例 / sample_retail_01 / 3 スライド経営会議要約 PPT |
| #7 | b.2-b.6 デイリーコックピット中核 + Codex 協業ルール（CLAUDE.md §9） | `core/analytics/operation_cockpit.py`（990 行）/ MCP `logi_clo_today_decisions` / REST `/today-decisions/{id}` `/decisions/{id}` |
| #8 | b.7 コックピット Web 画面 | `web/app/dashboard/cockpit/page.tsx`（380 行）+ `web/lib/api.ts` 拡張 |
| #9 | b.9 シナリオテスト + 12 fixtures | `tests/core/test_analytics_operation_cockpit_scenarios.py`（120 アサーション）+ `tests/fixtures/cockpit_summaries/*.txt` × 12 |
| #10 | フェーズ4.5 B 用途別テンプレ（daily/monthly/annual） | `core/io/template_writer.py` 拡張 + `logi_clo_generate_template` purpose 引数 |
| #11 | c.1-c.3 業種別 CLO 標準パッケージ基盤（Codex KPI レビュー反映済） | `core/playbook/industry_packages.py`（770 行）+ `core/io/override_store.py` |
| #12 | HANDOFF を c.4-c.6 向けに刷新 | `HANDOFF_NEXT_SESSION.md` |
| #13 | c.4 既存資産接続検証 + c.5/c.6 F2 標準化スコア + J2 罠スコア | `core/analytics/standardization_score.py` + `core/analytics/waste_trap.py` + テスト 73 件追加（pytest 783 件全 pass） |

### Codex 協業実績（CLAUDE.md §9 適用例）

- **段階 b/c 詳細実装計画の二者議論**（2026-05-05）: Codex 勧告 7 件を `plans/b-c-flickering-pixel.md` に反映
- **c.1 業種別 KPI 数値妥当性レビュー**（2026-05-06）: 着手前に Codex に独立レビュー依頼 → 3 件 critical 修正を全反映
  - 積載率: 旧案 manufacturing 55% / wholesale 52% を取下げ → 国の 2028 年度全体目標 **44%** に統一
  - 在庫回転数 / 共配率 / 配送便数削減等は `target_value=None`（標準値の根拠が国・JILS 未確認）
  - Codex 単独提案 2 件追加: 「荷待ち+荷役等 ≤60 分/回」「物流コスト売上高比率 baseline」

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
- [x] **PPT デザイン基盤** — Logi-Intel CLO Report（コード生成型デザイントークン）採用（2026-05-03）。詳細 → [docs/ppt_design.md](ppt_design.md) / [DESIGN.md](../DESIGN.md)
  - ⏳ micware ブランドへの差し替えは将来検討（公式ブランドガイドライン入手後）

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
| 6 | **Step 3** シナリオシミュレータ ✅ 完了（2026-05-03） | What-if 分析 + 保守/標準/上振れ 3 区分（複雑度高・Codex レビュー 3 を吸収） |
| 7 | **Step 7** 様式第5（定期報告書） + 提出実務チェックリスト ✅ 完了（2026-05-03） | フェーズ4.5「継続運用」への橋渡し（Codex レビュー 1 を吸収） |

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

### Step 3: シナリオシミュレータ（`logi_clo_scenario_sim`）✅ 完了（2026-05-03）

> **Codex レビュー 3 取込済**: 「5施策合算が強く見えすぎる」問題への対応として、各施策効果に **保守 / 標準 / 上振れ の 3 区分** を持たせ、重複・前提・信頼度を明示。CFO 質問（実装費・運用費・税効果・減価償却・サービスレベル低下リスク）に答える形に拡張済。

- [x] 複数施策の組合せシミュレーション（同 form3_section 重複 0.7 倍ダンピング適用）
- [x] 投資総額・営業利益増・5年累積 NPV を試算（NPV は割引率 3% / 5 年累積）
- [x] **What-if 分析**: baseline + 7 ストレス（燃料±20% / 運賃±10% / 需要±10% / 改善基準強化）
- [x] **3 区分シナリオ（Codex 3 取込）**: 各シナリオに `conservative 0.6 / standard 1.0 / upside 1.3` を直交させ ThreeBandValue で持つ
- [x] **重複ダンピング × 3 区分の組合せ**: 同 form3_section 重複 0.7 倍と 3 区分を直交し、CFO に「最低でも保守シナリオで X 億円」と説明できる出力形
- [x] **堅牢性判定**: ストレス standard 営業利益増 / baseline standard で 🟢 70%以上 / 🟡 50-70% / 🔴 50%未満
- [x] **入力施策**: `selected_measure_ids` 引数指定 OR None で Step 2 Top 3 自動採用
- [x] `core/analytics/scenario_sim.py` 新規（396 行）+ テスト 24 件全パス
- [x] /verify-clo-step --tool scenario_sim: 3/3 PASS（全サンプルで燃料 +20% で 🟢 維持）

**サンプル別 baseline 営業利益増（標準値・年）**:
| サンプル | 営業利益増 | 燃料 +20% | 改善基準強化 |
|----------|-----------|----------|------------|
| 製造業 | 2.64 億円 | 🟢 | 🟢 |
| 卸売業 | 3.95 億円 | 🟢 | 🟢 |
| コンビニ | 16.14 億円 | 🟢 | 🟢 |

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

- [x] 様式第5 Word ドラフト生成（`core/export/docx_form5_writer.py`・Ⅰ〜Ⅵ セクション・連鎖化荷役等項目自動省略）
- [x] 計測データ（荷待ち時間・荷役等時間）テンプレート埋込（`_WAIT_TIME_TEMPLATES` / `_HANDLING_TIME_TEMPLATES`）
- [x] 中長期計画との進捗比較セクション（数値目標 4 つ + 主要施策 3 件 = 7 行・初年度 △ 継続対応 中心）
- [x] 既MD化済の `manufacturing_report_*.md` をテンプレートとして活用（数値レンジを参考）
- [x] **提出実務チェックリスト（Codex 1 取込）**: `core/export/submission_checklist.py` 新規 + `logi_clo_plan_draft` および `logi_clo_periodic_report_draft` の出力末尾に「提出準備」セクション統合
  - 提出経路: e-Gov / GビズID プライム or メンバー（固定）
  - 指定通知書番号 / 法人番号 / 代表者情報 / 作成担当者連絡先（auto / placeholder 切替）
  - 様式第3 / 様式第4 / 様式第5 の使い分けと提出頻度（form_usage_notes）
- [x] `core/analytics/periodic_report.py` 新規（370 行）+ テスト 12 件 + verify_periodic_report 統合
- [x] `core/export/submission_checklist.py` 新規（160 行）+ テスト 8 件
- [x] /verify-clo-step --tool periodic_report: 3/3 PASS（必須 Ⅰ〜Ⅵ セクション + チェックリスト + 連鎖化対応）

### フェーズ 3.5 完了条件 ✅ すべて達成（2026-05-03）

- [x] `logi_clo_plan_draft` の出力に「**Top 3 推薦施策 + 選定理由 + 実現可能性スコア**」が含まれる（Step 2 measure_eval）
- [x] What-if シナリオで計画が「燃料 +20% でも黒字維持」を示せる（Step 3 scenario_sim・全サンプルで 🟢）
- [x] 物流 KPI 改善が「営業利益 X 億円」に翻訳される（Step 4 financial_translate）
- [x] 計画書提出前に必須項目チェック（様式第3 + 様式第5）が pass する（Step 6 submission_validator）
- [x] `logi_clo_periodic_report_draft` で**様式第5 ドラフト**が出力される（Step 7・毎年7月末提出に対応）
- [x] エグゼクティブサマリー（経営層向け1ページ要約）は **フェーズ3 で PPT 2枚目に固定実装済み**
- [x] **提出実務チェックリスト**が plan_draft / periodic_report 双方の出力末尾に統合される（Codex 1 取込）

---

## フェーズ 4.0: Web ダッシュボード + AWS 移行 + 自社データ取込

**ゴール**: 社内全員が HTTPS でアクセスできる Web ダッシュボードを AWS 上に構築し、CSV/Excel で自社データをアップロードできるようにする。

### Web ダッシュボード
- [x] **FastAPI REST 層**（`api/` ディレクトリ）— ✅ 完了（2026-05-03）
  - 21 エンドポイント公開（CLO 12 / macro 1 / company 3 / files 1 / meta 4）
  - MCP ツールと同じ ToolResponse 構造を JSON で返却（フロントは MCP/REST 同一パーサで処理可能）
  - OpenAPI / Swagger UI / ReDoc を `/docs` `/redoc` で公開
  - `outputs/` 配下のダウンロード経路（パストラバーサル防止）
  - FastAPI テスト 27 件（tests/api/）全 pass・全 421 テスト regression なし
  - 起動: `uv run uvicorn api.main:app --reload --port 8000`
- [x] **Next.js 15 初期化**（`web/` ディレクトリ）— ✅ 完了（2026-05-03）
  - App Router + TypeScript + Tailwind + Recharts（依存予約）
  - Logi-Intel CLO Report のデザイントークンを Tailwind に反映（primary / accent / muted）
  - 型付き API クライアント `web/lib/api.ts`（`ToolResponse` を Pydantic と一致させる）
  - 起動: `cd web && npm install && npm run dev`
- [x] **ダッシュボード全 8 画面実装** — ✅ 完了（2026-05-04）
  - `/` トップ / `/dashboard/macro` / `/dashboard/benchmark` / `/dashboard/driver-gap`
  - `/dashboard/playbook` / `/dashboard/measure-eval` / `/dashboard/scenario-sim`
  - `/dashboard/company`（テンプレ DL + Excel アップロード）/ `/dashboard/plan-draft`
  - 共通化: `components/ToolResponseDisplay.tsx`（summary / files / citations / freshness / data_source 統一表示）+ `lib/constants.ts`（都道府県・JSIC プリセット等）
  - `npm run build` 成功（12 ページ全静的生成、First Load JS 102-106KB）
- [x] **成果物ダウンロード UI** — ✅ 完了（2026-05-04）
  - `lib/api.ts:fileDownloadUrl` で `outputs/...` 相対パスを `/api/v1/files/...` URL に変換（Windows バックスラッシュも吸収）
  - 全画面の `ToolResponseDisplay` が `files` 一覧をリンク表示（PPT/Word/Excel/Markdown/PDF/テンプレ Excel/プロフィール JSON）

### 自社データアップロード（Codex 4 フル版・✅ 完了 2026-05-03）
- [x] `CompanyProfile` Pydantic モデルの拡張（積載率実績・荷待ち時間・荷役等時間・燃料消費・KPI 履歴）
- [x] **Excel 1 ファイル + マルチシート**による一括アップロード（profile / sites / wait_time / handling_time / kpi_history / _jsic_reference）
- [x] CSV ディレクトリ経路（補助）
- [x] サンプルテンプレート生成 `logi_clo_generate_template` MCP ツール
- [x] 取込ツール `logi_clo_load_company`（`outputs/profiles/<company_id>.json` に永続化）
- [x] `get_sample(company_id)` の ID 解決優先順位: 実データ JSON > サンプル3社
- [x] サンプルデータ（`core/static/sample_company.py`）から実データへの移行手順 → `docs/data_input_guide.md`
- [x] 実装ファイル: `core/io/template_writer.py` / `core/io/company_loader.py` / `core/io/company_store.py` + テスト 24 件
- [x] periodic_report.py の `_WAIT_TIME_TEMPLATES` を CompanyProfile.wait_time_rows に一本化（既存挙動互換）

> 残作業（フェーズ4.5 で対応）: plan_draft の docx 文章テンプレート化（公式記載見本集 MD 10 ファイルの取込）/ KPI 計測フレーム / CLO スタイル別重み付け

### AWS 移行（PoC 最安構成・✅ デプロイ完了 2026-05-05）

> 旧 ECS Fargate + ALB + ElastiCache 案は廃案。PoC のため Lambda + S3 + CloudFront の月額 $1〜$3 構成。
> 詳細 → [docs/aws_migration_plan.md](aws_migration_plan.md)

**社内レビュー用 URL**: https://d1zei8qivkf3cr.cloudfront.net/
**API Gateway 直接 URL**: https://fgwicoog66.execute-api.ap-northeast-1.amazonaws.com
**AWS アカウント**: 538099532416（健一個人・AdministratorAccess）

**完了済 コード改修**:
- [x] `core/storage.py` 新規（LOGI_STORAGE_BACKEND={local|s3} 切替）
- [x] `core/secrets.py` 新規（LOGI_SECRETS_BACKEND={env|ssm} 切替）
- [x] `core/io/company_store.py` の自社プロフィール JSON を S3 切替対応
- [x] `api/routers/files.py` を S3 プレサインド URL リダイレクト（302）に
- [x] `api/lambda_handler.py` Mangum で FastAPI を Lambda 化
- [x] Next.js を `output: "export"` で 12 ページ静的化
- [x] `core/macro/sources.py` 切り出し（fastmcp 依存を api/ から除去 → Lambda zip サイズ削減）
- [x] `lambda/requirements-lambda.txt` (Lambda 専用最小依存リスト・43MB zip)

**完了済 デプロイ**:
- [x] SSM Parameter Store に ESTAT_APP_ID 投入（CORP_NUMBER_APP_ID は未取得・ダミー不要・該当機能エラー表示で代替）
- [x] Terraform で IaC apply（S3 + Lambda + API Gateway HTTP API + CloudFront + IAM）
- [x] Lambda zip デプロイ（45MB / Python 3.12 / 1024MB / timeout 300s / /tmp 1GB）
- [x] Next.js 静的を S3 同期（73 ファイル / 約 1MB）
- [x] CloudFront URL 動作確認（/health 200 / /api/v1/clo/plan-draft 200 / S3 プレサインド DL 動作）

**設計上の決定（トラブル対応の記録）**:
- ❌ Lambda Function URL（NONE auth）→ 403。Block Public Access 系の挙動と推測
- ❌ Lambda Function URL（AWS_IAM auth）+ CloudFront OAC → 403（OAC 経由の sigv4 が通らず原因特定困難）
- ✅ 結論: API Gateway HTTP API + Lambda Proxy Integration が最も確実。コスト差は <$0.01/月なので PoC では妥協

**MCP モード切替（後続・必要時）**:
- [ ] MCP サーバーを HTTP/SSE モードに切替（FastMCP 設定変更）
- [ ] Claude Desktop 設定をローカル起動から AWS エンドポイントに変更

**残課題（次セッション）**:
- [ ] e-Stat API キーが Lambda 上で正しく読めるか実動作確認（macro / benchmark / driver-gap）
- [ ] サンプル sample_chain_01 / sample_wholesale_01 での plan-draft 動作確認（製造業のみ実機確認済）
- [ ] Codex 指摘の **PPT 視覚化強化**（charts/tables/pictures = 0 状態を脱却・施策ポートフォリオ図 等）

### 自社データ取込（本格実装）
- [ ] Pydantic `CompanyDataset` モデル（拠点・ルート・KPI 履歴）
- [ ] CSV / Excel パーサー
- [ ] アップロードデータの社内 PostgreSQL 保管（マルチテナント前提）
- [ ] フェーズ3 で使ったサンプルデータからの差し替え

---

## フェーズ 4.1: 段階 a 小改修（基盤整備）✅ 完了（2026-05-05）

**ゴール**: 段階 b（J3 デイリーコックピット）の前提となる静的データ・サンプル・出力テンプレを揃える。
詳細設計 → `~/.claude/plans/b-c-flickering-pixel.md` §段階 a。

- [x] **a.1 拠点別待機時間ヒートマップ** — `core/analytics/wait_time_heatmap.py`（拠点 × 時間帯 4 区分）/ `web/app/dashboard/wait-heatmap/page.tsx` / MCP `logi_clo_wait_heatmap` / REST `/wait-heatmap`
- [x] **a.2 NotebookLM 7 社事例の構造化取込（Codex 担当）** — `core/static/efficiency_law_certified.py` の `CertifiedCase` を before/after・投資レンジ・回収月数で拡張、経産省 CLO 取組事例集 7 社を追加
- [x] **a.3 経営会議向け 3 スライド要約 PPT** — `core/export/ppt_writer.write_clo_executive_brief()` / MCP `logi_clo_executive_brief` / REST `/executive-brief/{id}`
- [x] **a.4 標準的運賃 2024 改定版 + WaitTimeStandard** — `core/static/standard_freight.py` / `core/static/improvement_standards.WaitTimeStandard`（threshold=120 / avg_target=30）
- [x] **a.5 sample_retail_01 fixture** — 4 業種テストの基盤（地域 DC × 大型店 × 中型店の 3 構成 + 拠点別待機時間 fixtures）

### フェーズ 4.1 完了条件 ✅ すべて達成

- [x] sample_retail_01 で 3 拠点 × 4 時間帯 = 12 セルのヒートマップが生成される
- [x] 段階 b で参照する `WaitTimeStandard` / `STANDARD_FREIGHT_RATES` / `CertifiedCase` 拡張がすべて確定
- [x] 既存テスト 422 件 → 475 件全 pass

---

## フェーズ 4.5: 段階 b J3 デイリーコックピット + B 用途別テンプレ ✅ 完了（2026-05-06）

**ゴール**: CLO が朝 1 回開けば「未達 KPI ／ 放置リスク ／ 今週決める施策」が 3 件だけ並ぶ意思決定支援ビューを完成させる（J3）。+ 自社データ入力テンプレを用途別（日次/月次/年次）に分割（B 軸）。

詳細設計 → `~/.claude/plans/b-c-flickering-pixel.md` §段階 b。

### 段階 b: J3 デイリーコックピット（PR #7 / #8 / #9）

- [x] **b.2 データモデル**（Pydantic v2）— `CockpitItem` / `ObjectionItem` / `OperationKpiSnapshot` / `DecisionRecord` / `CockpitResult`
- [x] **b.3 統合エンジン**（`build_daily_cockpit`）— improvement_check + feasibility_check + measure_eval を 3 軸（compliance / kpi_reach / measure_pick）にマッピング
- [x] **b.4 既存判定関数の統合** — ComplianceReport.items[].status → urgency/impact 派生 / FeasibilityResult.kpi_reachability → 候補化 / MeasureScore Top3 → 軸 C
- [x] **b.5 「3 判断」抽出アルゴリズム** — urgency × impact × confidence の加重合計（0.4/0.4/0.2）+ 軸 A 必須化（重大違反 OR 提出期限 30 日以内）+ 軸 C 上限 2 + 重複排除 + state card 4 分類補填
- [x] **b.6 MCP/REST ツール** — `logi_clo_today_decisions` / GET `/today-decisions/{id}` / POST `/decisions/{id}`（I2 ログ append-only）
- [x] **b.7 Web 画面** — `web/app/dashboard/cockpit/page.tsx`（overall_health バナー + 3 軸カード + J4 薄版折りたたみ + 採用/保留/却下ボタン）
- [x] **b.8 永続化層** — `outputs/cockpit_snapshots/<id>/<yyyymmdd>.json` + `outputs/decisions/<id>.jsonl`
- [x] **b.9 シナリオテスト** — 4 サンプル × 3 シナリオ（baseline / violation_added / measurements_cleared）= 12 ケーススナップショット + 120 アサーション

### J4 薄版（b に組込・本格 J4 は段階 c で別実装）

- [x] 各 attention_needed `CockpitItem` に `anticipated_objections: list[ObjectionItem]` 3 件付き（CFO / 現場 / Partner|Board ロール × cost/legal/supply/brand_risk 軸）
- [x] Codex 勧告: 「3 件だけ」が「昨日と同じ」化リスク → 前回差分・未決 aging・次レビュー期日を主表示

### B 軸: 用途別テンプレ（PR #10）

- [x] `template_purpose: Literal["daily","monthly","annual"]` を `write_company_template` / `logi_clo_generate_template` / `/api/v1/company/template` / Web UI へ通す
- [x] daily   = 日次運用入力用（profile / sites + 簡易 wait_time）
- [x] monthly = 月次集計用（profile / sites + wait_time + handling_time + kpi_history）
- [x] annual  = 計画策定用（現行 6 シート完全互換、デフォルト）

### フェーズ 4.5 完了条件 ✅ すべて達成

- [x] `logi_clo_today_decisions("sample_*")` で 3 件の意思決定カードが返る（4 サンプルで動作確認済）
- [x] Web `/dashboard/cockpit` で overall_health バナー + 3 軸カード + 採用/保留/却下ボタンが動作
- [x] 12 ケーススナップショット fixture が CI で守られる（pytest 624+ 件全 pass）
- [x] 用途別テンプレ DL が Web から動作（3 用途とも Excel 生成可能）

### 旧フェーズ4.5（継続運用機能）の扱い

旧計画「定期報告書 + KPI トラッキング + 法改正監視」は J3 コックピットへ統合 or 段階 c 以降に再配置。

- 定期報告書ドラフト生成（製造業以外） → 段階 c.7 連鎖化特有処理 で対応予定
- KPI トラッキング dashboard → J3 コックピット `delta_from_yesterday` で部分達成
- 進捗 alert → コックピット H1 アラート（将来実装）
- 法改正監視 → スコープ外（フェーズ 5.5 検討）
- 計画改定サポート → コックピットの DecisionRecord ログから差分生成（将来実装）

---

## フェーズ 5.0: 段階 c 業種別 CLO 標準パッケージ + F2/J2 スコア（進行中・c.7 着手前）

**ゴール**: 「コンサル代行」の代替として、業種別の標準パッケージ（KPI / 施策 / 会議体 / レポート / データ項目）を SaaS 商品化。個社差分を Override 4 分類で別管理し、F2 標準化スコアと J2 罠スコアで継続改善を支援する。

詳細設計 → `~/.claude/plans/b-c-flickering-pixel.md` §段階 c。

### c.1-c.3: 業種別パッケージ基盤 ✅ 完了（PR #11・2026-05-06）

- [x] **c.1 4業種 × 5要素マトリクス** — manufacturing / wholesale / retail / chain_franchise × KPI / 施策 / 会議体 / レポート / データ項目 = 20 セル充填
- [x] **c.2 データモデル** — `StandardKpiDef` / `StandardMeetingDef` / `StandardReportDef` / `StandardDataItemDef` / `IndustryPackage` / `OverrideEntry` / `CompanyPackageOverride` + Override 4 分類（unmanaged_deviation / approved_better_practice / required_localization / temporary_exception）
- [x] **c.3 公開関数** — `get_package` / `list_packages` / `resolve_company_package`（base + override 合成・期限制御付）+ `core/io/override_store.py`（save/load Override JSON）
- [x] テスト 48 件 + 7 件 = 55 件全 pass / `core/playbook/industry_packages.py` 約 770 行

**Codex 業種別 KPI レビュー反映**:
- 積載率全業種: 旧案 manufacturing 55% / wholesale 52% を取下げ → **国の 2028 年度全体目標 44%** に統一
- 在庫回転数 / 共配率 / 配送便数削減 / SKU 当たり物流コスト等は `target_value=None`（推測排除）
- Codex 単独提案 2 件: 「荷待ち+荷役等 ≤60 分/回」（物流効率化法ポータル判断基準）/ 「物流コスト売上高比率 baseline」（JILS 2021）

### c.4 既存資産接続検証 ✅ 完了（PR #13・2026-05-06）

- [x] `measure_ids` ↔ `ALL_MEASURES.applicable_industries` 整合性検証（chain_franchise が loading セクション施策を除外していること等）
- [x] `LOGISTICS_COST_RATIO[industry]` × `IndustryPackage.kpis.logistics_cost_revenue_ratio_pct.baseline_value` 接続
- [x] `tests/core/test_playbook_industry_packages.py` 拡張（17 件追加）

### c.5 / c.6 F2 標準化スコア + J2 罠スコア ✅ 完了（PR #13・2026-05-06）

- [x] **c.6 F2 標準化スコア** — `core/analytics/standardization_score.py`（unmanaged_deviation のみ減点で単調性確保 / approved_better_practice は減点なし bonus 候補 / 必須 KPI 全実装で +10 / approved_better_practice ≥2 で +5）/ テスト 22 件
- [x] **c.6 J2 罠スコア** — `core/analytics/waste_trap.py` + 6 軸セーフガード（立ち上げ期間 / データ欠損 / サンプル数 / 季節性 / 外部要因 / 投資回収前）で誤検知抑止 / 9 種 root cause 分類 / テスト 34 件
- [x] pytest 783 件全 pass / ruff クリーン / 新規テスト 73 件追加（c.4: 17 / F2: 22 / J2: 34）

#### 持ち越し課題（c.7 後の改善 PR で対応予定）

1. **J2 罠スコアの decision_log 連動** — 現状は `plan` 入力に閉じている。`outputs/decisions/<id>.jsonl` 連動で「pending のまま X ヶ月」検出を強化
2. **actual_effect_jpy の逆算** — `kpi_history` の改善幅（積載率 ▲pp / 物流コスト/売上比率 ▲%）から自動算出
3. **F2 bonus 拡張** — 「必須 KPI 全実装 + 月次会議定着」判定ロジックの追加（現状は実装ベース判定のみ）

### c.7-c.9 ⏳ 未着手

- [ ] **c.7 MCP/REST 3 ツール公開**（次セッション） — `logi_clo_industry_package_get` / `logi_clo_standardization_score` / `logi_clo_waste_trap_detect` + 対応 REST エンドポイント
- [ ] **c.8 連鎖化事業者特有処理** — `chain_franchise` パッケージ強制（`metric_id` プレフィックス `handling_*` 禁止 / `form3_section == "loading"` 除外 / `legal_basis="第65条"` 明記）
- [ ] **c.9 統合テスト + Web 画面 2 件** — `web/app/dashboard/industry-package/page.tsx`（4 業種タブ + 5 要素表）/ `web/app/dashboard/standardization/page.tsx`（自社 F2 + 差分テーブル）

### フェーズ 5.0 完了条件

- [x] `compute_standardization_score(profile, override)` で coverage_pct + score (0-100) が返り、approved_better_practice の追加では減点されない（単調性確保）— PR #13
- [x] `detect_waste_traps` の 6 軸セーフガードで `months_since_start=0` 時に trap_severity="low" 固定 — PR #13
- [x] 4 業種すべてで `get_package(category)` が StandardKpiDef リストを返す — PR #11
- [x] 連鎖化サンプルで荷役等セクション施策が混入しないことが CI で守られる — PR #11 + PR #13 で強化
- [ ] **c.7 MCP/REST 公開**: 上記 core/ 関数を `logi_clo_*` ツール経由で呼べる状態（次セッション着手）
- [ ] Web 2 画面が `npm run build` 成功・実機動作確認済（c.9）

---

## フェーズ 5.5: 公開・記事化 ⏳ 未着手

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
フェーズ3.5 (意思決定支援強化+様式第5) ──→ フェーズ4.0 (Web+AWS+自社データ)
                                                      ↓
                          フェーズ4.1 (段階 a 基盤整備) ──→ フェーズ4.5 (段階 b J3 コックピット + B 用途別テンプレ)
                                                      ↓
                        フェーズ5.0 (段階 c 業種別 SaaS パッケージ + F2/J2) ──→ フェーズ5.5 (公開)
```

**法的マイルストーン**:
- 2026-04: CLO 選任義務化施行 ✅ 経過
- 2026-10末: **初回中長期計画提出** ← フェーズ3 で計画書ドラフト完成、フェーズ4.5 で日次運用支援、フェーズ5.0 で業種別パッケージ
- 毎年7月末: **定期報告書提出** ← フェーズ3.5 Step 7 で対応済

---

## Zenn 記事素材メモ

フェーズ完了ごとに `docs/zenn_drafts/` に実装ポイント・スクリーンショット・コードスニペットを蓄積する。
