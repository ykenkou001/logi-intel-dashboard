# logi-intel-dashboard

日本のオープンデータ（e-Stat / 国税庁法人番号 / xROAD / 気象庁 / 燃料価格）と自社物流データを統合し、**CLO（物流統括管理者）の意思決定・中長期計画・定期報告を徹底的に支援する**分析基盤。

Claude Desktop/Code から MCP ツール（38 本）として呼び出せるほか、FastAPI REST API と Next.js ダッシュボード（14 画面）+ `/check` 対象企業判定画面から、PPT / Word / Excel / HTML / Markdown の成果物ファイルを生成・ダウンロードできる。

**現在のフェーズ**: フェーズ 5.5 — Tier S 5 件すべて完了（DecisionLog 永続化 / KPI 月次推移 + 物流コスト比率 / Facility 管理 / 罰則 PPT / README 再編集）。残るは記事化 + AWS terraform apply。

**開発進捗**: [docs/roadmap.md](docs/roadmap.md)

<p align="center">
  <img src="docs/promo/logi-intel-promo-15s.gif" alt="Logi-Intel 15 秒紹介動画（デイリーコックピット / 施策評価 / 成果物ダウンロード）" width="720">
</p>

<p align="center">
  🎬 紹介動画: <a href="docs/promo/logi-intel-promo-15s.mp4">15 秒版（mp4）</a> ／ <a href="docs/promo/logi-intel-promo-30s-dynamic.mp4">30 秒テロップ解説版（mp4）</a>
  <br><sub>画面はサンプル企業のデータ。生成ソースは <a href="docs/promo/">docs/promo/</a></sub>
</p>

---

## なぜ作ったか

2026 年 4 月に「流通業務の総合化及び効率化の促進に関する法律（物流効率化法）」が施行され、一定規模以上の荷主企業・物流事業者に **CLO（物流統括管理者）の選任と中長期計画書の提出（2026 年 10 月末期限）** が義務付けられた。

しかし CLO 担当者の最大の悩みは「**何をやれば一番効くか**」。コンサルは高く遅い。既存の物流 DX ツールは運用特化で計画策定機能が弱い。

本アプリは **CLO の意思決定パートナーとして机に常駐する**ことを目的とし、「データを提供するだけ」では終わらず「どの施策を選ぶべきか」まで踏み込む。

---

## CLO の意思決定フロー（このアプリの主な使い方）

本アプリは **CLO の中長期計画策定と継続運用** を、5 ステップの意思決定フローで支援する。各ステップで「何が問われるか」「使うツール」「成果物」を業務フロー順に並べた。

### Step 1: 対象判定 — あなたの会社は CLO 義務対象か（30 秒）

> **問い**: 自社は特定第一種荷主・特定連鎖化事業者・特定倉庫業者・特定貨物自動車運送事業者等のどれに該当するか

| 項目 | 内容 |
|---|---|
| MCP ツール | `logi_clo_eligibility` |
| Web 画面 | `/check`（30 秒判定）/ `/dashboard/driver-gap` |
| 入力 | 業種・売上・年間取扱貨物量・保有車両数・倉庫保管量 |
| 出力 | 該当区分判定 / CLO 選任義務有無 / 中長期計画提出義務有無 |

### Step 2: 業界比較 — 自社の位置を知る

> **問い**: 自社の物流 KPI（積載率・荷待ち時間・物流コスト比率）は業界平均と比べてどうか。業種別 CLO 標準パッケージへの準拠度はどの程度か

| 項目 | 内容 |
|---|---|
| MCP ツール | `logi_clo_benchmark_position` / `logi_clo_driver_gap` / `logi_clo_industry_package` / `logi_clo_standardization_score` / `logi_macro_overview` |
| Web 画面 | `/dashboard/benchmark` / `/dashboard/macro` / `/dashboard/industry-package` / `/dashboard/standardization` |
| 入力 | 業種（JSIC コード）・地域・自社プロフィール |
| 出力 | 全国・地域別シェア / 業界平均比 / F2 標準化スコア（0–100）/ ドライバー需給ギャップ |

### Step 3: 施策評価 — 何をやれば一番効くか（差別化の核心）

> **問い**: 10〜30 ある施策候補のうち、自社にとって今やるべき Top 3 はどれか。なぜ他の施策を選ばなかったか（**選外理由まで説明できる状態**）

| 項目 | 内容 |
|---|---|
| MCP ツール | `logi_clo_playbook_search` / `logi_clo_measure_eval` / `logi_clo_feasibility_check` / `logi_clo_target_proposal` / `logi_clo_simulate_measures` / `logi_clo_scenario_sim` / `logi_clo_waste_traps` |
| Web 画面 | `/dashboard/playbook` / `/dashboard/measure-eval` / `/dashboard/scenario-sim` / `/dashboard/waste-traps` |
| 入力 | 自社プロフィール（Step 1〜2 で確定）+ 業種別 CLO 標準パッケージ |
| 出力 | Top 3 推薦 + ROI / 実装可能性 / 法令適合度 / 補助金マッチ / **不採用理由**（Bottom 3）/ 罠スコア（誤検知抑止）/ 燃料高騰等 7 ストレス × 3 区分シミュ |

### Step 4: 計画書ドラフト — 経営会議で説明する

> **問い**: 国交省様式に準拠した中長期計画書ドラフトを、PPT / Word / Excel で出力できるか。準拠率は何 % か

| 項目 | 内容 |
|---|---|
| MCP ツール | `logi_clo_financial_translate` / `logi_clo_plan_draft` / `logi_clo_executive_brief` / `logi_clo_submission_validate` |
| Web 画面 | `/dashboard/plan-draft` |
| 入力 | Step 3 で確定した施策セット |
| 出力 | 様式第 3 別紙 Word / 経営会議用 PPT（エグゼクティブサマリー付き）/ 詳細データ Excel / 提出前準拠率レポート / 法令根拠付き Markdown |

### Step 5: 継続運用 — 翌年度報告まで支える

> **問い**: 2026-10-31 提出後、毎年度 7 月末日の定期報告でどう品質を維持するか。経営会議で「なぜこの施策？」「なぜ選ばなかった？」に毎回答えられるか

| 項目 | 内容 |
|---|---|
| MCP ツール | `logi_clo_today_decisions` / `logi_clo_kpi_timeseries` / `logi_clo_record_monthly_snapshot` / `logi_clo_periodic_report_draft` / `logi_clo_wait_heatmap` / `logi_clo_certified_match` / `logi_clo_load_company` / `logi_clo_generate_template` |
| Web 画面 | `/dashboard/cockpit` / `/dashboard/kpi-timeseries` / `/dashboard/wait-heatmap` / `/dashboard/company` |
| 入力 | 月次 KPI 実績 / 施策実行記録 / 当月の物流コスト実績 |
| 出力 | デイリーコックピット（今日の 3 判断 + 想定反論 3 件）/ KPI 月次推移（24 ヶ月折れ線 + 業界平均 ReferenceLine + 悪化アラート）/ 様式第 5 定期報告書 Word / 荷待ち・荷役時間ヒートマップ |

### 出口層（Step 4〜5 共通）

5 ステップのどこからでも、以下の成果物形式で出力できる。**全数値に出典 URL**（e-Stat 統計表 ID / 告示番号 / 省令番号）を付与する。

- **PPT**（経営会議向け、最優先）— python-pptx、エグゼクティブサマリースライド固定配置
- **Word** — 様式第 3 別紙 / 様式第 5 法定様式に準拠
- **Excel** — サマリーシート + 詳細表 + 出典シートの 3 層構造
- **HTML** — self-contained、印刷・社内ポータル掲載向け
- **Markdown** — 社内 Wiki / レビュー / PR 貼り付け向け

---

## 機能カバレッジ（参考）

| カテゴリ | 内容 |
|---|---|
| **オープンデータ統合** | e-Stat（物流特化 7 統計カタログ）/ 国税庁法人番号 / xROAD（交通量）/ 気象庁（予報・警報）/ 燃料価格 |
| **MCP ツール** | 計 38 本（オープンデータ系 10 / CLO 支援系 28） |
| **REST API** | FastAPI、34 エンドポイント |
| **Web ダッシュボード** | Next.js、14 機能画面 + `/check` 対象判定 + `/guide` 利用ガイド |
| **業種別パッケージ** | 製造業 / 卸売業 / 小売業 / 連鎖化事業者（連鎖化は `第 65 条` 強制ガード付き） |
| **法令ロジック** | 改正物流効率化法（第 5 条 / 第 46 条 / 第 65 条）/ 改善基準告示 2024-04 / 標準的運賃 2024-03 改定版 |
| **意思決定支援の核** | F2 標準化スコア（0–100）/ J2 罠スコア（6 軸セーフガード）/ J3 デイリーコックピット（今日の 3 判断）/ KPI 月次推移（業界平均 ReferenceLine + 悪化アラート）/ 経営会議向け財務翻訳（P&L / NPV） |
| **継続運用** | DecisionLog 永続化（様式第 5 証跡引用可）/ KPI 時系列スナップショット（jsonl + S3 backend）/ 報告単位 Facility 管理 / 罰則・社名公表リスク PPT |
| **自社データ取込** | Excel / CSV テンプレ → `logi_clo_load_company` / サンプル 3 社（製造 / 卸売 / 連鎖化）で即試用可能 |

MCP ツールと REST エンドポイントの完全な一覧は [docs/api_endpoints.md](docs/api_endpoints.md) と [docs/mcp_tools.md](docs/mcp_tools.md) を参照。

---

## セットアップ

### 前提条件

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js / npm（Web ダッシュボードを動かす場合）

```bash
# uv のインストール（未導入の場合）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Python 環境

```bash
uv python install 3.12
uv sync
cp .env.example .env
```

`.env` に必要な API キーを設定する。

| API | 環境変数 | 備考 |
|-----|----------|------|
| e-Stat | `ESTAT_APP_ID` | 必須。[政府統計の総合窓口](https://www.e-stat.go.jp/api/) から取得 |
| 国税庁法人番号 | `CORP_NUMBER_APP_ID` | 任意。未設定時は該当機能のみエラー表示 |

### Web 環境

```bash
cd web
npm install
```

---

## Web ダッシュボードの使い方

各ダッシュボード画面（13 機能）の入力・出力・読み方・推奨利用順は **[docs/dashboard_feature_guide.md](docs/dashboard_feature_guide.md)** にまとめている。
本番ダッシュボード（CloudFront）からも、トップページの「機能別利用ガイド」リンクおよびアプリ内 `/guide` で同じ内容を参照できる。

初見ユーザーは「CLO の意思決定フロー」5 ステップの順で触ると全体像を掴みやすい:

1. 対象企業判定（`/check`） — Step 1
2. 業種別 CLO 標準パッケージ（`/dashboard/industry-package`） — Step 2
3. F2 標準化スコア（`/dashboard/standardization`） — Step 2
4. 施策評価（`/dashboard/measure-eval`） — Step 3
5. 計画書生成（`/dashboard/plan-draft`） — Step 4
6. デイリーコックピット（`/dashboard/cockpit`） — Step 5

---

## ローカル起動

`uvicorn` や `npm run dev` を直接叩かず、既存プロセスの kill と環境変数固定を行うヘルパーを使う。

```powershell
pwsh scripts/dev_api.ps1            # FastAPI :8000（--reload）
pwsh scripts/dev_web.ps1            # Next.js :3000（API_BASE=localhost:8000）
```

確認先:

- FastAPI Swagger: http://localhost:8000/docs
- Web ダッシュボード: http://localhost:3000
- ヘルスチェック: http://localhost:8000/health

### Claude Desktop への登録

`claude_desktop_config.json` に以下を追加する。

```json
{
  "mcpServers": {
    "logi-intel": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server.server"],
      "cwd": "/path/to/logi-intel-dashboard",
      "env": {
        "ESTAT_APP_ID": "<your_app_id>"
      }
    }
  }
}
```

---

## 開発コマンド

```bash
uv run pytest                        # テスト全実行（現在 915 件）
uv run pytest --cov=core             # カバレッジ付き
uv run ruff check .                  # Lint
uv run ruff format .                 # フォーマット
uv run mypy core mcp_server api      # 型チェック

cd web
npm run lint
npm run build
```

CLO 機能単位の検証:

```bash
uv run python scripts/verify_clo_step.py --tool all
```

---

## CI / CD

GitHub Actions で PR と `main` へのマージ後デプロイを管理する。

| Workflow | トリガー | 内容 |
|----------|---------|------|
| `.github/workflows/ci.yml` | PR / main push | ruff + pytest + Next.js lint / type-check / build |
| `.github/workflows/deploy-api.yml` | main push（Python/API/Lambda 関連変更時） | Lambda zip ビルド + S3 経由デプロイ + ヘルスチェック |
| `.github/workflows/deploy-web.yml` | main push（`web/` 変更時） | `npm run build` + S3 sync + CloudFront invalidate |

`main` への直接 push は禁止。必ず `feature/...` `fix/...` `docs/...` `ci/...` ブランチで作業し、Pull Request 経由で取り込む。詳細は [docs/git_workflow.md](docs/git_workflow.md) を参照。

---

## ディレクトリ概要

| パス | 役割 |
|------|------|
| `core/` | ビジネスロジック、分析、静的データ、成果物生成（CLO 支援の本体） |
| `core/analytics/` | ベンチマーク・シナリオ・スコアリング等の分析モジュール |
| `core/export/` | PPT / Word / Excel / HTML / Markdown 出力（CLO に届く価値の最終地点） |
| `core/playbook/` | 業種別 CLO 標準パッケージ・施策プレイブック |
| `core/static/` | CO2 係数・改善基準告示・標準運賃等の静的データ（鮮度管理付き） |
| `mcp_server/` | Claude Desktop/Code 向け FastMCP ツール層 |
| `api/` | FastAPI REST API 層（34 エンドポイント） |
| `web/` | Next.js ダッシュボード（14 画面）+ `/check` 対象企業判定 |
| `lambda/` | AWS Lambda 用エントリ・依存定義 |
| `infra/` | Terraform IaC |
| `docs/` | 設計、ロードマップ、API、CLO ドメイン知識 |
| `outputs/` | ローカル実行時の生成成果物（PPT / Word / Excel / HTML / Markdown） |

---

## 主要ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [AGENTS.md](AGENTS.md) | Codex 向けプロジェクト指示 |
| [CLAUDE.md](CLAUDE.md) | Claude Code 向け指示・ミッション宣言 |
| [docs/architecture.md](docs/architecture.md) | システム構成・技術スタック・AWS 構成 |
| [docs/roadmap.md](docs/roadmap.md) | フェーズ別進捗（今どこにいるか） |
| [docs/clo_domain.md](docs/clo_domain.md) | CLO 業務ドメイン知識・法的定義 |
| [docs/api_endpoints.md](docs/api_endpoints.md) | 利用 API 一覧・認証・TTL・制約 |
| [docs/dashboard_feature_guide.md](docs/dashboard_feature_guide.md) | Web ダッシュボード機能別利用ガイド（初見ユーザー向け／アプリ内 `/guide` で参照可能） |
| [docs/data_input_guide.md](docs/data_input_guide.md) | 自社データ入力ガイド（Excel/CSV） |
| [docs/ppt_design.md](docs/ppt_design.md) | PPT デザイン方針・スライドファミリー定義 |
| [docs/git_workflow.md](docs/git_workflow.md) | ブランチ・PR 運用 |
| [docs/testing.md](docs/testing.md) | テストレベル・モック方針・カバレッジ目標 |
| [plans/phase55_update_proposal.md](plans/phase55_update_proposal.md) | フェーズ 5.5 アップデート案（Codex 二者議論で確定した束ね直し方針） |

---

## 技術スタック

| カテゴリ | 採用技術 |
|---------|---------|
| 言語 | Python 3.12+ |
| パッケージ管理 | uv |
| MCP フレームワーク | FastMCP |
| HTTP クライアント | httpx (async) |
| データ検証 | Pydantic v2 |
| キャッシュ | SQLite |
| Lint / Format | Ruff |
| 型チェック | mypy (strict) |
| テスト | pytest, pytest-asyncio |
| PPT 出力 | python-pptx |
| Excel 出力 | openpyxl |
| Word 出力 | python-docx |
| フロント | Next.js 15, Recharts, Tailwind CSS |
| インフラ | AWS（CloudFront + S3 + API Gateway + Lambda）, Terraform |

> RESAS API は 2025-03-24 に提供終了済み。このプロジェクトでは新規利用せず、e-Stat 等の現行オープンデータで代替している。

---

## ライセンス・帰属

本プロジェクトは以下の OSS を参考にしている。

- [japan-data-mcp](https://github.com/Izyuusya/japan-data-mcp) (Apache-2.0): e-Stat クライアント実装の参考
- [estat-mcp](https://github.com/ajtgjmdjp/estat-mcp) (Apache-2.0): MCP ツール設計の参考

利用データの取得先・制約は [docs/api_endpoints.md](docs/api_endpoints.md) を参照。
