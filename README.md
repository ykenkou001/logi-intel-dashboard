# logi-intel-dashboard

日本のオープンデータと自社物流データを統合し、CLO（物流統括管理者）の意思決定・中長期計画・定期報告を支援する社内向け分析基盤。

Claude Desktop/Code から MCP ツールとして呼び出せるほか、FastAPI REST API と Next.js ダッシュボードから、PPT / Word / Excel / Markdown の成果物を生成・ダウンロードできる。

**現在のフェーズ**: フェーズ 4.5 — 継続運用機能（CLO デイリーコックピット）を実装中

**開発進捗**: [docs/roadmap.md](docs/roadmap.md)

---

## 主な機能

- e-Stat / 国税庁法人番号 / xROAD / 気象庁 / 燃料価格などの物流関連データ取得
- CLO 計画策定支援: ベンチマーク、ドライバー需給、適用判定、目標提案、施策評価、シナリオ分析
- 国交省様式に沿った中長期計画書ドラフト、定期報告書ドラフト、経営会議向け PPT の生成
- Excel / CSV による自社データ取込とサンプル企業データからの差し替え
- Web ダッシュボード 8 画面 + CLO デイリーコックピット
- AWS PoC: CloudFront + S3 静的サイト + API Gateway HTTP API + Lambda + S3 出力配信

> RESAS API は 2025-03-24 に提供終了済み。このプロジェクトでは新規利用せず、e-Stat 等の現行オープンデータに寄せる。

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
| e-Stat | `ESTAT_APP_ID` | 必須。政府統計 API の appId |
| 国税庁 法人番号 | `CORP_NUMBER_APP_ID` | 取得済みなら設定。未設定時は該当機能のみエラー表示 |

### Web 環境

```bash
cd web
npm install
```

---

## ローカル起動

`uvicorn` や `npm run dev` を直接叩かず、既存プロセスの kill と環境変数固定を行うヘルパーを使う。

```powershell
pwsh scripts/dev_api.ps1            # FastAPI :8000（--reload）
pwsh scripts/dev_web.ps1            # Next.js :3000（API_BASE=localhost:8000）
```

確認先:

- FastAPI: http://localhost:8000/docs
- Web: http://localhost:3000
- Health: http://localhost:8000/health

本番 PoC は CloudFront 経由で配信中。URL と AWS 構成の詳細は [docs/roadmap.md](docs/roadmap.md) と [docs/architecture.md](docs/architecture.md) を参照。

---

## 開発コマンド

```bash
uv run pytest
uv run pytest --cov=core
uv run ruff check .
uv run ruff format .
uv run mypy core mcp_server api

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
| `core/` | ビジネスロジック、分析、静的データ、成果物生成 |
| `mcp_server/` | Claude Desktop/Code 向け FastMCP ツール層 |
| `api/` | FastAPI REST API 層 |
| `web/` | Next.js ダッシュボード |
| `lambda/` | AWS Lambda 用エントリ・依存定義 |
| `infra/` | Terraform IaC |
| `docs/` | 設計、ロードマップ、API、CLO ドメイン知識 |
| `outputs/` | ローカル実行時の生成成果物 |

---

## 主要ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [AGENTS.md](AGENTS.md) | Codex 向けプロジェクト指示 |
| [CLAUDE.md](CLAUDE.md) | Claude Code 向け指示・運用メモ |
| [docs/architecture.md](docs/architecture.md) | システム構成・技術スタック・AWS 構成 |
| [docs/roadmap.md](docs/roadmap.md) | フェーズ別進捗 |
| [docs/api_endpoints.md](docs/api_endpoints.md) | 利用 API 一覧・認証・TTL |
| [docs/clo_domain.md](docs/clo_domain.md) | CLO 業務ドメイン知識 |
| [docs/data_input_guide.md](docs/data_input_guide.md) | 自社データ入力ガイド |
| [docs/git_workflow.md](docs/git_workflow.md) | ブランチ・PR 運用 |

---

## ライセンス・帰属

本プロジェクトは以下の OSS を参考にしている。

- [japan-data-mcp](https://github.com/Izyuusya/japan-data-mcp) (Apache-2.0): e-Stat クライアント実装の参考
- [estat-mcp](https://github.com/ajtgjmdjp/estat-mcp) (Apache-2.0): MCP ツール設計の参考

利用データの取得先・制約は [docs/api_endpoints.md](docs/api_endpoints.md) を参照。
