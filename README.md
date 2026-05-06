# logi-intel-dashboard

日本のオープンデータ（e-Stat / 国税庁法人番号 / xROAD / 気象庁 / 燃料価格）と自社物流データを統合し、**CLO（物流統括管理者）の意思決定・中長期計画・定期報告を徹底的に支援する**分析基盤。

Claude Desktop/Code から MCP ツール（32 本）として呼び出せるほか、FastAPI REST API と Next.js ダッシュボード（13 画面）から、PPT / Word / Excel / Markdown の成果物ファイルを生成・ダウンロードできる。

**現在のフェーズ**: フェーズ 5.5 — 公開・記事化（MeasureExecutionRecord 永続化 + AWS 運用ハーデニング 完了済）

**開発進捗**: [docs/roadmap.md](docs/roadmap.md)

---

## なぜ作ったか

2026 年 4 月に「流通業務の総合化及び効率化の促進に関する法律（物流効率化法）」が施行され、一定規模以上の荷主企業・物流事業者に **CLO（物流統括管理者）の選任と中長期計画書の提出（2026 年 10 月末期限）** が義務付けられた。

しかし CLO 担当者の最大の悩みは「**何をやれば一番効くか**」。コンサルは高く遅い。既存の物流 DX ツールは運用特化で計画策定機能が弱い。

本アプリは **CLO の意思決定パートナーとして机に常駐する**ことを目的とし、「データを提供するだけ」では終わらず「どの施策を選ぶべきか」まで踏み込む。

---

## 主な機能

### データ取得（オープンデータ統合）

- e-Stat 統計表検索・データ取得（物流特化 7 統計カタログ付き）
- 国税庁法人番号 API による企業情報検索
- xROAD リアルタイム / バウンディングボックス交通量
- 気象庁 JSON 予報・警報
- 燃料価格（軽油・ガソリン）

### CLO 計画策定支援

- **業種別 CLO 標準パッケージ**（製造業 / 卸売業 / 小売業 / 連鎖化事業者）— 推奨 KPI・施策・月次会議議題・定期報告データ項目・Override 4 分類
- ベンチマーク位置分析（業種・規模別の業界平均比）
- ドライバー需給ギャップ分析（都道府県別）
- CLO 適用判定（第一種 / 第二種 / 連鎖化の 3 区分）
- 施策目標値の自動提案（改善基準告示・国目標値準拠）
- 施策プレイブック検索（投資レンジ・補助金・失敗パターン付き）
- 施策 4 軸スコアリング + Top 3 推薦（`logi_clo_measure_eval`）
- 施策実行可否チェック（緑 / 黄 / 赤判定 + 積載率 KPI 到達可能性）
- シナリオシミュレーション（燃料 +20% 等 7 ストレス × 3 区分）

### 意思決定支援（差別化の核心）

- **F2 標準化スコア** — 自社の CLO 標準への準拠度を 0–100 で定量化
- **J2 罠スコア** — 施策効果の誤検知を 6 軸セーフガードで抑止（立ち上げ期間 / データ欠損 / サンプル数 / 季節性 / 外部要因 / 投資回収前）
- **J3 デイリーコックピット** — CLO の「今日の 3 判断」を意思決定軸 A/B/C で提示、想定反論 3 件付き
- 経営会議向け財務翻訳（施策別 P&L 影響 / 炭素回避レンジ / 5 年 NPV）

### 成果物出力（CLO が経営会議に持ち込めるもの）

- 国交省様式第 3 別紙 中長期計画書ドラフト（Word + Markdown）
- 様式第 5 定期報告書ドラフト（Word）
- 経営会議向け PPT（python-pptx、エグゼクティブサマリー付き）
- Excel 数値表（出典シート付き）
- 法令根拠付き Markdown — 全数値に出典 URL（e-Stat 統計表 ID / 告示番号 / 省令番号）

### 自社データ取込

- Excel / CSV テンプレ記入 → `logi_clo_load_company` で取込
- サンプル 3 社（製造業 / 卸売業 / 連鎖化）で即試用可能

---

## MCP ツール一覧（Claude Desktop / Code から使用）

### オープンデータ系（10 本）

| ツール | 概要 |
|--------|------|
| `logi_estat_search` | e-Stat 統計表キーワード検索 |
| `logi_estat_get_data` | e-Stat 統計表データ取得 |
| `logi_estat_get_meta` | e-Stat 統計表メタデータ取得 |
| `logi_corp_search` | 国税庁法人番号 API 企業検索 |
| `logi_traffic_realtime` | xROAD リアルタイム交通量 |
| `logi_traffic_by_bbox` | xROAD バウンディングボックス交通量 |
| `logi_weather_forecast` | 気象庁 天気予報 |
| `logi_weather_warning` | 気象庁 警報・注意報 |
| `logi_fuel_price` | 燃料価格（軽油・ガソリン） |
| `logi_macro_overview` | 都道府県 物流マクロ概況（上記を統合） |

### CLO 支援系（22 本）

| ツール | 概要 |
|--------|------|
| `logi_clo_load_company` | 自社データ（Excel/CSV）取込 |
| `logi_clo_generate_template` | 入力テンプレ生成（daily / monthly / annual） |
| `logi_clo_eligibility` | CLO 適用判定（3 区分） |
| `logi_clo_benchmark_position` | 業界平均比ベンチマーク |
| `logi_clo_driver_gap` | ドライバー需給ギャップ分析 |
| `logi_clo_target_proposal` | 施策目標値の自動提案 |
| `logi_clo_playbook_search` | 施策プレイブック検索 |
| `logi_clo_measure_eval` | 施策 4 軸スコアリング + Top 3 推薦 |
| `logi_clo_simulate_measures` | 施策効果シミュレーション |
| `logi_clo_feasibility_check` | 施策実行可否チェック |
| `logi_clo_scenario_sim` | シナリオ分析（燃料高騰等 7 ストレス） |
| `logi_clo_financial_translate` | 施策別財務翻訳（P&L / NPV） |
| `logi_clo_plan_draft` | 中長期計画書ドラフト生成 |
| `logi_clo_submission_validate` | 計画書提出前バリデーション |
| `logi_clo_periodic_report_draft` | 様式第 5 定期報告書ドラフト生成 |
| `logi_clo_certified_match` | 物流効率化法 認定事業者マッチング |
| `logi_clo_executive_brief` | 経営会議向けエグゼクティブブリーフ |
| `logi_clo_today_decisions` | デイリーコックピット（今日の 3 判断） |
| `logi_clo_wait_heatmap` | 荷待ち・荷役時間ヒートマップ |
| `logi_clo_industry_package` | 業種別 CLO 標準パッケージ |
| `logi_clo_standardization_score` | F2 標準化スコア |
| `logi_clo_waste_traps` | J2 罠スコア（施策効果の誤検知抑止） |

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

各画面（13 機能）の入力・出力・読み方・推奨利用順は **[docs/dashboard_feature_guide.md](docs/dashboard_feature_guide.md)** にまとめている。
本番ダッシュボード（CloudFront）からも、トップページの「機能別利用ガイド」リンクおよびアプリ内 `/guide` で同じ内容を参照できる。

初見ユーザーは次の順で確認すると全体像を掴みやすい:

1. ホーム（`/`） — 機能一覧
2. 業種別 CLO 標準パッケージ（`/dashboard/industry-package`）
3. F2 標準化スコア（`/dashboard/standardization`）
4. 施策評価（`/dashboard/measure-eval`）
5. 計画書生成（`/dashboard/plan-draft`）

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
uv run pytest                        # テスト全実行（現在 835 件）
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
| `core/export/` | PPT / Word / Excel / Markdown 出力（CLO に届く価値の最終地点） |
| `core/playbook/` | 業種別 CLO 標準パッケージ・施策プレイブック |
| `core/static/` | CO2 係数・改善基準告示・標準運賃等の静的データ（鮮度管理付き） |
| `mcp_server/` | Claude Desktop/Code 向け FastMCP ツール層 |
| `api/` | FastAPI REST API 層（21 エンドポイント） |
| `web/` | Next.js ダッシュボード（13 画面） |
| `lambda/` | AWS Lambda 用エントリ・依存定義 |
| `infra/` | Terraform IaC |
| `docs/` | 設計、ロードマップ、API、CLO ドメイン知識 |
| `outputs/` | ローカル実行時の生成成果物（PPT / Word / Excel / Markdown） |

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
