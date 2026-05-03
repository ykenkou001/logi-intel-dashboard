# Logi-Intel Dashboard — Claude Code 指示書

このファイルは Claude Code がこのプロジェクトで作業する際の指示書。
作業前に必ず最初に読み込むこと。

---

## 1. プロジェクト概要

日本のオープンデータ（e-Stat, 国税庁法人番号, xROAD, 気象庁等）を統合し、物流業界の分析データを提供する基盤。
※ RESAS API は 2025-03-24 に提供終了。e-Stat（経済センサス・国勢調査等）で代替する。

**主用途**:
- 営業・提案資料の根拠データ提供
- 2026年4月義務化の CLO（物流統括管理者）の中長期計画策定支援
- Claude Desktop/Code から自然言語でデータ問い合わせ

**ターゲットユーザー**: micware 社内の営業・企画・経営層、CLO 候補者

詳細 → [docs/architecture.md](docs/architecture.md) | [docs/clo_domain.md](docs/clo_domain.md)

---

## 1.5 ミッション宣言（必読・最優先）

**このプロジェクトの存在意義は「CLO（物流統括管理者）の中長期計画策定と運用を、本気で・徹底的に支援すること」である。**

### アプリの軸: 意思決定支援に特化（Option C）

CLO の最大の悩みは「**何をやれば一番効くか**」。データ提供や計画書代行は手段にすぎない。
本アプリの差別化は **施策の選択と評価（Decision Support）** に絞る。

```
コンサル ──→ 高い・遅い・属人的
既存物流DXツール ──→ 運用特化、計画策定は弱い
本アプリ ──→ CLO の意思決定パートナーとして机に常駐
```

### 必達 7 本柱

| # | 柱 | フェーズ |
|---|------|--------|
| 1 | **Decision Support**（施策の選択と評価） | 3.5（核心） |
| 2 | **Compliance Assurance**（法令準拠保証） | 2.5 / 3.5 |
| 3 | **Continuous Operation**（継続運用サイクル） | 4.5 |
| 4 | **Stakeholder Integration**（取引先連携） | スコープ外 |
| 5 | **Executive Communication**（経営層への翻訳） | 3.0 / 3.5 |
| 6 | **Knowledge Base**（事例・知見蓄積） | 3.5 |
| 7 | **Defensibility**（説明責任の担保） | 2.5 / 3.5 |

MCP サーバー / REST API / Web ダッシュボードはすべて手段であり、目的ではない。
あらゆる実装判断は「**それは CLO の中長期計画提出（2026年10月末）と継続運用に直接効くか？**」を基準に決定する。

### 徹底するコミットメント

1. **法定様式に沿うこと** — 国交省・経産省が公開する「様式第3別紙 中長期計画書」テンプレートに準拠した出力を生成できること
2. **法的根拠を明示すること** — 提供する全数値に出典 URL（e-Stat 統計表 ID、告示番号、省令番号等）を付与すること
3. **経営会議で使える成果物を出すこと** — 会話画面で完結させない。**PPT（最優先）/ PDF / Excel / Markdown** をファイルとして出力できること
4. **業界平均との比較を必ず提供すること** — 「自社の数字単独」ではなく「業界平均比 ▲X%」「全国順位 X 位」の形で出すこと
5. **改善基準告示・物流効率化法に整合すること** — 提案する数値目標は告示で定められた数値（拘束時間 13h/日、年 960h 等）に整合していること
6. **判断に迷ったら CLO 側に立つこと** — 実装が楽な方ではなく、CLO 担当者が経営会議で説明責任を果たせる方を選ぶ

### 「やらないこと」リスト（誘惑への防波堤）

- ❌ MCP ツールを増やすこと自体を目標にしない（CLO に効かないツールは作らない）
- ❌ Claude の会話画面で「すごい数字が出た」で完結させない（必ず成果物ファイルまで出す）
- ❌ 「動いた」を完了とせず「CLO 計画書ドラフトに使える形で出た」を完了とする
- ❌ データソースを増やすこと自体を目標にしない（CLO 業務に紐付かないデータは取らない）
- ❌ **「データを提供するだけ」で止めない**（必ず「どの施策を選ぶべきか」まで踏み込む）
- ⏳ **取引先（運送事業者）連携機能・配車最適化 AI 統合は将来検討**（フェーズ4.5 以降。当面は荷主側 CLO 支援に集中）

詳細 → [docs/clo_domain.md](docs/clo_domain.md)

---

## 2. ドキュメント索引

| ドキュメント | 内容 |
|-------------|------|
| [docs/architecture.md](docs/architecture.md) | 3 層アーキテクチャ・技術スタック・ディレクトリ構造・キャッシュ設計 |
| [docs/roadmap.md](docs/roadmap.md) | 開発フェーズ・進捗状況（今どこにいるか） |
| [docs/coding_standards.md](docs/coding_standards.md) | 言語・命名・設計・Lint 規約 |
| [docs/api_endpoints.md](docs/api_endpoints.md) | 利用 API 一覧・認証・TTL・制約 |
| [docs/mcp_tools.md](docs/mcp_tools.md) | MCP ツール命名規則・実装方針 |
| [docs/clo_domain.md](docs/clo_domain.md) | CLO 業務ドメイン知識・法的定義 |
| [docs/data_input_guide.md](docs/data_input_guide.md) | 自社データ入力ガイド（Excel/CSV テンプレ記入と取込手順） |
| [docs/ppt_design.md](docs/ppt_design.md) | PPT デザイン方針（Logi-Intel CLO Report）・スライドファミリー定義 |
| [docs/aws_migration_plan.md](docs/aws_migration_plan.md) | AWS 移行計画（フェーズ4.0 後半・8 Step 手順書） |
| [docs/oss_reference.md](docs/oss_reference.md) | 参考 OSS の方針・Attribution |
| [docs/testing.md](docs/testing.md) | テストレベル・モック方針・カバレッジ目標 |
| [docs/git_workflow.md](docs/git_workflow.md) | ブランチ戦略・コミットメッセージ規則 |
| [docs/notes.md](docs/notes.md) | API 利用規約・シークレット管理・パフォーマンス制約 |
| [docs/licenses.md](docs/licenses.md) | 各 API の利用規約と商用利用可否（要作成） |

---

## 3. 現在のフェーズ

**フェーズ 4.0 進行中 — 自社データ取込 + FastAPI + Next.js 初期化 + AWS 移行コード準備 ✅ 完了（2026-05-03）**

**フェーズ 4.0 サブステップ**:
- ✅ 自社データ取込（Codex 4 フル版）— Excel/CSV → CompanyProfile + JSON 永続化 + サンプル3社 ID 解決の統合
- ✅ FastAPI REST 層 — 21 エンドポイント公開（CLO 12 / macro 1 / company 3 / files 1 / meta 4）。MCP と同じ ToolResponse 構造で JSON 返却・tests/api/ 27 件全 pass
- ✅ Next.js 15 初期化（web/）— App Router + TypeScript + Tailwind + Recharts。型付き API クライアント・3 画面（トップ・マクロ概況・計画書ドラフト）。`npm run build` 成功
- ✅ AWS 移行 コード準備 — Dockerfile + docker-compose + 8 Step 移行計画書（docs/aws_migration_plan.md）
- ⏳ AWS 実環境展開（健一の承認後）— Terraform IaC・ECS Fargate・ElastiCache・Secrets Manager・S3

**新規 MCP ツール（フェーズ4.0 で追加）**:
- `logi_clo_generate_template`: 自社プロフィール入力テンプレ Excel を生成
- `logi_clo_load_company`: 記入済み Excel/CSV から CompanyProfile を構築・JSON 永続化

詳細 → [docs/roadmap.md](docs/roadmap.md) §フェーズ4.0 / [docs/data_input_guide.md](docs/data_input_guide.md)

---

## 4. 重要原則（必ず守ること）

- **CLO 業務に効かない実装はしない** — 1.5 のミッション宣言を最優先
- **ビジネスロジックは必ず `core/` に置く** — MCP・REST 層には書かない
- **成果物は必ずファイル出力できるようにする** — PPT / PDF / Excel / Markdown
- **全数値に出典を付与する** — `core/export/citation.py` を経由
- **過剰アクセス禁止** — キャッシュ必須、リトライにバックオフ必須
- **API キーをログに出力しない** — `core/clients/base.py` でマスク処理
- **ロジックを先に読む** — 推測で実装しない

---

## 5. 作業開始時のチェックリスト

1. このファイル（CLAUDE.md）を読み込んだか
2. 現在のフェーズを [docs/roadmap.md](docs/roadmap.md) で確認したか
3. 直近の git log を見て、どこまで進んでいるか確認したか（`git log --oneline -20`）
4. 作業前に `uv sync` で依存関係を最新化したか

---

## 6. 判断に迷ったら

優先順位:
1. このファイルの記載内容を最優先
2. `docs/` 配下の該当ドキュメント
3. 既存実装のパターンに合わせる
4. 健一（開発者）に確認

判断に迷う実装は、まず簡単な版で動かしてから、健一に確認する。**完璧主義より MVP 思考**。

---

## 7. フェーズ3 Step 単位の検証ルール（必須）

各 Step の実装完了後、**必ず以下の検証を行ってから次の Step に進むこと**。
「コードが書けた」を完了とせず「Claude Desktop で動いた」を完了とする。

### 検証手順
1. `uv run ruff check` + `uv run mypy` で静的チェックをパスさせる
2. `uv run pytest --tb=short -q` で既存テスト全件パスを確認する
3. **Claude Desktop を再起動**（MCP サーバーを再読み込みさせる）
4. Claude Desktop で当該 Step のツールを実際に呼び出し、**出力値の妥当性まで確認する**
   - エラーなく ToolResponse 構造（summary/citations/freshness_warnings）が返るか
   - **数値が現実的な範囲か**（桁が合っているか・単位が正しいか）
   - **業界知識に照らして整合的か**（例: 全国ドライバー数が数百万のオーダーか・全国事業所数が業種規模に妥当か）
   - **出典 URL を1〜2件踏んで一次情報と数値が合っているか**（経営会議で「出典は？」即答用）
   - **計算ロジックの矛盾がないか**（例: 全国シェア合計が100%に収まるか・マイナス値が出ていないか）
   - 鮮度警告が想定通り表示されるか
5. 「動いた」だけで完了とせず、**「経営会議で説明できる数字か」を判定基準にする**
6. 問題があれば修正 → 2 に戻る。問題なければ roadmap.md を ✅ に更新して次の Step へ

### 妥当性チェックの基本姿勢
- 数値が出たら、**まず常識と照らす**（例: 東京都のドライバー数が1万人未満や1000万人なら異常）
- 業界統計の公表値（国交省「物流2024年問題」資料、JILS物流コスト調査等）と桁を比較する
- ユーザー（健一）に報告する際は **「確認した妥当性のチェック項目」も列挙する**（数値だけ貼らない）

### Step ごとの最低限のテスト呼び出し例
| Step | ツール | 確認用呼び出し |
|------|--------|--------------|
| 1 | `logi_clo_benchmark_position` | `jsic_code="5411", prefecture="東京都", revenue_jpy=5_000_000_000` |
| 2 | `logi_clo_driver_gap` | `prefecture="東京都"` |
| 3 | `logi_clo_eligibility` | `jsic_code="5411", revenue_jpy=5_000_000_000` |
| 4 | `logi_clo_target_proposal` | `jsic_code="5411", prefecture="東京都", revenue_jpy=5_000_000_000` |
| 7 | `logi_clo_plan_draft` | サンプル会社プロフィールで一括生成（エグゼクサマリーに財務インパクト含む） |
| 3.5/6 | `logi_clo_submission_validate` | サンプル ID で計画書を生成→検査（PASS/準拠率/エラー警告） |
| 3.5/4 | `logi_clo_financial_translate` | サンプル ID で施策別 P&L 翻訳（営業利益+X億・炭素回避レンジ・5年NPV） |
| 3.5/1 | `logi_clo_playbook_search` | 業種・規模・難易度で標準10施策を絞込（投資レンジ・補助金・失敗パターン提示） |
| 3.5/2 | `logi_clo_measure_eval` | 自社プロフィール × 10施策 → 4軸スコアリング → Top 3 推薦 + 選定根拠 |
| 3.5/5 | `logi_clo_feasibility_check` | 施策の実行可否を 緑/黄/赤 で判定 + 積載率 KPI 到達可能性 |
| 3.5/3 | `logi_clo_scenario_sim` | サンプル ID で baseline + 7 ストレス × 3 区分（保守/標準/上振れ）試算（燃料+20% 黒字維持判定） |
| 3.5/7 | `logi_clo_periodic_report_draft` | サンプル ID で様式第5 Word を生成（Ⅰ〜Ⅵ セクション + 提出実務チェックリスト + 改善基準告示遵守判定） |

---

## 8. Subagent 活用方針

複雑なタスクは subagent に分割して委譲する。

| 役割 | 担当タスク |
|------|-----------|
| `estat-explorer` | e-Stat の統計表 ID・コード体系の探索 |
| `api-spec-reader` | API 仕様書を読んでクライアント実装を提案 |
| `test-writer` | 既存実装に対するテストを書く |
| `doc-writer` | docstring・README を整備する |

**起動の判断基準**: 単一ファイル修正 → 直接編集 / 複数ファイル横断調査 → subagent

---

最終更新: 2026-05-03（フェーズ4.0 進行中：自社データ取込 Codex 4 フル版・FastAPI REST 層・Next.js 15 初期化・AWS 移行コード準備が完了。FastAPI 21 エンドポイント／tests 421 件全 pass・Next.js `npm run build` 成功（6 ページ静的生成、First Load JS 102KB）・Dockerfile + docker-compose + docs/aws_migration_plan.md 整備。次セッションは AWS 実環境展開の方針確認 + Next.js の残り画面（ベンチマーク・ドライバー需給・施策ライブラリ・シミュレータ・自社プロフィール入力フォーム）実装）
