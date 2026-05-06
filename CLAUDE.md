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

**フェーズ 5.0 進行中 — 業種別 CLO 標準パッケージ（c.7 MCP/REST 公開完了 / c.8-c.9 着手前）— 2026-05-06 時点**

| フェーズ | 状態 | 主な PR |
|---|---|---|
| 4.0 Web + AWS + 自社データ取込 | ✅ 完了（2026-05-05） | #1〜#5 |
| 4.1 段階 a 小改修（a.1〜a.5） | ✅ 完了（2026-05-05） | #6 |
| 4.5 段階 b J3 コックピット + B 用途別テンプレ | ✅ 完了（2026-05-06） | #7 / #8 / #9 / #10 |
| **5.0 段階 c 業種別パッケージ + F2/J2 スコア** | 🔄 **c.1-c.7 完了 / c.8-c.9 着手前（2026-05-06）** | **#11 / #12 / #13 / #14 / #15(本 PR)** |
| 5.5 公開・記事化 | ⏳ 未着手 | — |

**社内レビュー URL**: https://d1zei8qivkf3cr.cloudfront.net/

### フェーズ 5.0 段階 c の進捗（2026-05-06）

- ✅ **c.1-c.3 IndustryPackage 基盤**（PR #11）— `core/playbook/industry_packages.py`（770 行）/ `core/io/override_store.py` / Override 4 分類（Codex KPI レビュー反映済）
- ✅ **c.4 既存資産接続検証**（PR #13）— `measure_ids ↔ ALL_MEASURES.applicable_industries` 整合性 / `LOGISTICS_COST_RATIO` baseline 接続
- ✅ **c.5/c.6 F2 標準化スコア + J2 罠スコア**（PR #13）— `core/analytics/standardization_score.py` / `core/analytics/waste_trap.py`。J2 は 6 軸セーフガード（立ち上げ期間 / データ欠損 / サンプル数 / 季節性 / 外部要因 / 投資回収前）で誤検知抑止。F2 は unmanaged_deviation のみ減点で単調性確保
- ✅ **c.7 MCP/REST 3 ツール公開**（本 PR）— `logi_clo_industry_package` / `logi_clo_standardization_score` / `logi_clo_waste_traps` の MCP ツール 3 件、`/api/v1/clo/industry-package/{id}` / `/standardization-score/{id}` / `/waste-traps/{id}` の REST エンドポイント 3 件を追加。REST は metadata に Pydantic model_dump を載せ Web フロントが型安全に消費可能。pytest 804 件全 pass（新規 21 件）。
- ⏳ **c.8 連鎖化特有処理 / c.9 統合テスト + Web 2 画面** — 未着手

### c.5/c.6 + c.7 持ち越し課題（c.8 以降の改善 PR で対応予定）

1. J2 罠スコアの `decision_log` 連動（現状は `plan` 入力に閉じている）
2. `actual_effect_jpy` の逆算（kpi_history からの自動算出）
3. F2 bonus 拡張（必須 KPI 全実装 + 月次会議定着の判定ロジック追加）
4. （c.7 由来）`MeasureExecutionRecord` の永続化レイヤ — 現状は POST body / MCP 引数で都度受け取る。`outputs/measure_runs/<company_id>.json` に保存する `measure_run_store.py` を c.8 と同時に整備する候補

### 直近の主要成果物（フェーズ4.5 + 5.0）

- **J3 デイリーコックピット**（PR #7）— `logi_clo_today_decisions` MCP / `/today-decisions/{id}` REST / `/dashboard/cockpit` Web。CLO の「今日の3判断」を意思決定軸 A/B/C で 3 件提示・想定反論 3 件（J4 薄版）付き
- **業種別 CLO 標準パッケージ**（PR #11）— 4 業種 × 5 要素マトリクス + Override 4 分類 + Codex 業種別 KPI 数値妥当性レビュー反映済（積載率は国の 2028 目標 44% に統一、推測値は target_value=None で残す方針）
- **用途別 入力テンプレ**（PR #10）— `logi_clo_generate_template(purpose="daily|monthly|annual")`
- **F2 標準化スコア + J2 罠スコア**（PR #13）— pytest 783 件全 pass / 新規テスト 73 件追加
- **c.7 業種別パッケージ + F2/J2 の MCP/REST 公開**（本 PR）— Claude Desktop / Web ダッシュボード双方から呼び出し可能に。pytest 804 件全 pass / 新規 21 件追加

### Codex 協業実績（CLAUDE.md §9 適用例）

- **2026-05-05**: 段階 b/c 詳細実装計画の二者議論 → Codex 勧告 7 件を `~/.claude/plans/b-c-flickering-pixel.md` に反映
- **2026-05-06**: c.1 業種別 KPI 数値妥当性レビュー依頼 → 3 件 critical 修正（積載率 / 推測排除 / 公的根拠 KPI 2 件追加）を全反映

詳細 → [docs/roadmap.md](docs/roadmap.md) §フェーズ4.5 §フェーズ5.0 / [HANDOFF_NEXT_SESSION.md](HANDOFF_NEXT_SESSION.md)

---

## 4. 重要原則（必ず守ること）

- **CLO 業務に効かない実装はしない** — 1.5 のミッション宣言を最優先
- **ビジネスロジックは必ず `core/` に置く** — MCP・REST 層には書かない
- **成果物は必ずファイル出力できるようにする** — PPT / PDF / Excel / Markdown
- **全数値に出典を付与する** — `core/export/citation.py` を経由
- **過剰アクセス禁止** — キャッシュ必須、リトライにバックオフ必須
- **API キーをログに出力しない** — `core/clients/base.py` でマスク処理
- **ロジックを先に読む** — 推測で実装しない
- **`main` への直接 push は禁止** — branch protection で hook reject される。必ず feature ブランチ（`feature/...` `fix/...` `docs/...` `ci/...`）を切って PR 経由でマージする。詳細 → [docs/git_workflow.md](docs/git_workflow.md) §main ブランチ運用ルール

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

## 6.5 ローカル開発サーバー起動ルール（必須）

ローカル FastAPI / Next.js を立てる際は **必ず `scripts/dev_api.ps1` / `scripts/dev_web.ps1` を使うこと**。
`uvicorn ...` を直接叩いたり `npm run dev` を素で起動してはいけない。

### 経緯（2026-05-05 の不具合）
旧 uvicorn が `core/` をメモリにロードしたまま動き続け、本番に修正をデプロイしても
ブラウザフロントが localhost を叩き続けて修正反映が確認できない事故が発生した。

原因:
1. uvicorn を `--reload` なしで起動した古いプロセスが多重に残存
2. `web/lib/api.ts` のデフォルト API_BASE が `http://localhost:8000` で、`NEXT_PUBLIC_API_BASE_URL`
   未設定の本番ビルドでもローカルを叩く構造だった

恒久対策（実施済）:
- `scripts/dev_api.ps1` に **既存 uvicorn の自動 kill + `--reload` 起動** を組み込み
- `scripts/dev_web.ps1` に **既存 next dev の自動 kill + API_BASE 環境変数固定** を組み込み
- `web/lib/api.ts` のデフォルト API_BASE を `""`（同一 origin）に変更

### 起動コマンド
```powershell
pwsh scripts/dev_api.ps1            # FastAPI (port 8000, --reload)
pwsh scripts/dev_web.ps1            # Next.js (port 3000, API_BASE=localhost:8000)
```

### 不具合の症状（同種の事故が再発した時の見分け方）
- 「コードを直してデプロイしたのに本番のフロントから動作が変わらない」
- ブラウザ DevTools の Network タブで API リクエスト先が `localhost` になっている
- → `Get-Process uvicorn,node` で残存プロセスを確認 → `dev_api.ps1` で再起動

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

## 9. Codex との協業方針（必須）

このプロジェクトは **Claude（Opus / 設計・統合）と Codex（GPT-5.x / 並行実装・別視点レビュー）の二者協業** で進める。「片方が全部やる」前提では運用しない。Codex は Subagent ではなく **対等な協業相手**として扱う。

### 9.1 Codex に相談・助言を求めるべき場面

Claude 単独で抱えず、**積極的に Codex に意見を求める**こと。判断を 1 モデル分の盲点に委ねないことが目的。

| 場面 | Codex 活用方法 |
|------|---------------|
| 設計判断に迷う（複数の妥当な選択肢） | `/codex` または `codex:rescue` で **二者議論を持ちかける**（例: 段階 b/c 計画の二者議論で 6 件の修正点を抽出した実績あり） |
| 実装が詰まった・別の切り口が欲しい | `codex:rescue` を呼び、症状・試したこと・期待結果を渡してセカンドオピニオンを取る |
| Claude の計画書・PR を独立レビューさせたい | Codex に「フラットに評価してくれ」と渡し、レビュー結果を **取り込み or 反論** する形で議論する |
| Claude が書いた数値ロジック・閾値の妥当性確認 | 業界感覚レンジ表や CLO 業務知見を Codex の知識で交差検証する |
| NotebookLM 取込・PPT 生成・Word/Excel 改善 | **Codex 単独**で完結する（Claude は触らない・9.2 参照） |

**起動方法**: スラッシュコマンド `/rescue` または `codex:rescue` agent。事前に `/codex setup` で疎通確認する。

### 9.2 役割分担の固定ルール（衝突回避）

同じファイルに同時に手を入れると merge 衝突 + 仕様の食い違いが発生する。**着手前に担当を固定する**こと。

| 領域 | 担当 | 理由 |
|------|------|------|
| 中核アーキテクチャ・統合スコアリング・データモデル設計 | **Claude** | Opus の設計力を活かす（例: `core/analytics/operation_cockpit.py` の 3 軸統合エンジン） |
| 静的データ取込（NotebookLM 由来事例・告示数値・運賃表） | **Codex** | 一括構造化に向く（例: `core/static/efficiency_law_certified.py` の 7 社事例取込） |
| サンプルデータ生成（fixture 追加） | **Codex** | データ構築は Codex 効率的（例: `sample_retail_01` 4 業種カバー追加） |
| Word / Excel / PPT 生成物の改善 | **Codex** | 過去実績あり。Claude は触らない |
| Web 画面（Next.js / Tailwind / Recharts） | **Codex 優先**、Claude が API 設計後に委譲 | Tailwind CSS Grid のカスタム実装等は Codex が早い |
| 中核ビジネスロジックの単体テスト | **Claude スモーク + Codex 拡張テスト**の二段構え | Claude が「壊れていないこと」のガード、Codex が網羅性（例: 4社×3シナリオ=12ケース） |
| CI/CD パイプライン・インフラ（IaC） | **Claude** | AWS/Terraform 知見を Claude 側に蓄積している |
| MCP / REST エンドポイント定義 | **Claude** | 既存パターンに合わせる定型作業 |

### 9.3 並行作業時の禁止事項

- **新セッション開始時に必ず HANDOFF_NEXT_SESSION.md と memory `feedback_codex_parallel_collaboration.md` を確認**する
- 「Codex が並行作業中」と明示されている領域のファイルを Read してはいけない（Edit / Write は当然禁止）
- 不明な領域に手を入れる前に、健一に「これは Codex 領域では？」と確認する
- `pyproject.toml` の dependencies は両者が触りうる共有領域。先に触る側が他方に通知する想定で、健一に都度確認する
- **`main` 直接 push は禁止**。Codex も Claude も別ブランチ + PR 経由（branch protection で hook reject される）

### 9.4 Codex の助言を取り込む際の作法

1. **Codex の指摘を額面通り受け入れない**。妥当性を Claude 側で評価し、「採用」「修正のうえ採用」「却下」を明示する
2. 設計議論の結論は **plan ファイル（plans/*.md）** にバージョンを切って残す。「Codex 勧告 ① ② ③」のように番号付けする運用を踏襲する（例: [plans/b-c-flickering-pixel.md](https://github.com/ykenkou001/logi-intel-dashboard/blob/main/plans/b-c-flickering-pixel.md)）
3. **未確定値を Codex が「不明」と返したら、推測で埋めない**。`None` または空文字で残し、健一の判断を仰ぐ（NotebookLM 取込での運用ルール）
4. PR 説明文に「Codex 議論で確定した修正点」と「Claude 単独判断」を区別して書く

### 9.5 Codex 議論の歴史的経緯

| 日付 | 議題 | 結論 |
|------|------|------|
| 2026-05-05 | 段階 b/c 詳細実装計画 | Codex 勧告で 7 件の修正点を反映（plans/b-c-flickering-pixel.md §段階 a/b/c） |
| 2026-05-05 | フェーズ4.0 PR #1 マージ後の Word/Excel 改善分担 | Codex 単独実施で確定 |
| 2026-05-05 | フェーズ4.5 着手時の領域分担 | b.7 Web / b.9 拡張テストを Codex 委譲、b 中核を Claude |

「Codex に聞こうか迷ったら聞く」が初動。Claude 単独で進めて後から「Codex に聞けばよかった」となる方が高コスト。

詳細 → memory `feedback_codex_parallel_collaboration.md`（並行作業の境界線）

---

最終更新: 2026-05-06（フェーズ5.0 c.1-c.7 完了 / c.8-c.9 着手前。本 PR で c.7 MCP/REST 3 ツール公開 — `logi_clo_industry_package` / `logi_clo_standardization_score` / `logi_clo_waste_traps` の MCP ツール 3 件 + REST エンドポイント 3 件を追加。pytest 804 件全 pass / 新規テスト 21 件追加。次は c.8 連鎖化特有処理 / c.9 統合テスト + Web 2 画面 — 詳細は HANDOFF_NEXT_SESSION.md / docs/roadmap.md §フェーズ5.0 / `~/.claude/plans/b-c-flickering-pixel.md` 参照）
