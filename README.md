# logi-intel-dashboard

日本のオープンデータを統合し、物流業界のマーケット動向・地域特性を分析する基盤。  
Claude Desktop/Code から自然言語でデータを問い合わせたり、Web ダッシュボードで可視化したりできることを目指す。

**現在のフェーズ**: フェーズ1 — MVP MCP サーバー初版  
**開発進捗**: [docs/roadmap.md](docs/roadmap.md)

---

## セットアップ

### 前提条件

- [uv](https://docs.astral.sh/uv/) がインストール済みであること

```bash
# uv のインストール（未導入の場合）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 環境構築

```bash
# 1. Python 3.12 を導入（初回のみ）
uv python install 3.12

# 2. 依存関係インストール（.venv/ が自動作成される）
uv sync

# 3. API キーを設定
cp .env.example .env
# .env を開いて各 API キーを貼り付ける
```

### API キー取得方法

| API | 取得先 | 備考 |
|-----|--------|------|
| e-Stat（政府統計） | https://www.e-stat.go.jp/api/ | 利用登録で appId 取得、無料 |
| RESAS（地域経済） | https://opendata.resas-portal.go.jp/ | ユーザー登録で API キー取得、無料 |
| 国税庁 法人番号 | https://www.houjin-bangou.nta.go.jp/webapi/ | 利用申込で applicationID 取得、無料 |

---

## 開発コマンド

```bash
uv run pytest                  # テスト実行
uv run pytest --cov=core       # カバレッジ付きテスト
uv run ruff check .            # Lint チェック
uv run ruff format .           # コード整形
uv run mypy core mcp_server    # 型チェック
```

---

## CI / CD

GitHub Actions で main への push を検知し、本番 AWS PoC へ自動デプロイ。

| Workflow | トリガー | 内容 |
|----------|---------|------|
| `.github/workflows/ci.yml` | PR 作成 / main push | ruff + pytest + Next.js lint / type-check / build |
| `.github/workflows/deploy-api.yml` | main push（`core/`, `api/`, `lambda/`, `pyproject.toml` 変更時） | Lambda zip ビルド + `lambda update-function-code` + ヘルスチェック |
| `.github/workflows/deploy-web.yml` | main push（`web/` 変更時） | `npm run build` + S3 sync + CloudFront invalidate + 疎通確認 |

**Terraform は CI から除外** — インフラ変更（`infra/`）は手動 `terraform apply` を維持。

### 認証（OIDC）

GitHub Actions は AWS への長期 access key を持たず、OIDC で IAM ロール `logi-intel-dev-github-actions`
を引き受ける。`token.actions.githubusercontent.com:sub = repo:<owner>/<repo>:ref:refs/heads/main` の
condition で **main ブランチからの実行のみ許可**。

### 初回セットアップ手順

1. `cd infra && terraform plan -var "env=dev" -out plan.tfplan && terraform apply plan.tfplan`
   → `github_actions_role_arn` が output される
2. GitHub リポジトリの Settings → Secrets and variables → Actions
   → **`AWS_GITHUB_ACTIONS_ROLE_ARN`** を Secret として登録（値は output の ARN）
3. （推奨）Settings → Branches → main の保護ルール:
   - "Require status checks to pass before merging" → `CI / Python` `CI / Web` を必須化
   - "Require branches to be up to date before merging"

### ロールバック

問題のある main commit を revert → push すれば自動的に再デプロイされる。
緊急時は GitHub Actions の "Re-run jobs" で過去の green コミットを再実行可。

詳細経緯は [CLAUDE.md §6.5](CLAUDE.md) と [docs/architecture.md](docs/architecture.md) を参照。

---

## ローカル開発サーバー起動（必読）

**`uvicorn` や `npm run dev` を直接叩かず、必ず以下のヘルパースクリプトを使う。**

```powershell
pwsh scripts/dev_api.ps1            # FastAPI :8000（既存プロセス自動 kill + --reload）
pwsh scripts/dev_web.ps1            # Next.js :3000（API_BASE=localhost:8000 を環境変数固定）
```

### なぜ必要か

2026-05-05 に「本番 Lambda に修正をデプロイしたのに、ブラウザのフロントが
古い localhost を叩き続けて修正反映が確認できない」事故が発生した。原因は:

1. `--reload` なしで起動した古い uvicorn が `core/` をメモリにロードしたまま生存
2. `web/lib/api.ts` のデフォルト API_BASE が `http://localhost:8000` で、
   ブラウザが意図せずローカルを叩く構造だった

両ヘルパースクリプトは **既存プロセスを起動時に必ず kill** + **`--reload` で
コード変更を即時反映** するため、多重起動・コード古残存の両方を根絶する。

### 症状で気付くポイント

「コード直したのに本番フロントの動作が変わらない」と感じたら:

1. ブラウザ DevTools の Network タブで API リクエスト先が `localhost` か確認
2. `Get-Process uvicorn,node` で残存プロセスを点検
3. 該当プロセスを stop → `dev_api.ps1` で再起動

詳細経緯は [CLAUDE.md §6.5](CLAUDE.md) を参照。

---

## ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [CLAUDE.md](CLAUDE.md) | Claude Code 向け指示書・クイックリファレンス |
| [docs/architecture.md](docs/architecture.md) | システム構成・技術スタック・ディレクトリ構造 |
| [docs/roadmap.md](docs/roadmap.md) | 開発フェーズ・進捗状況 |
| [docs/api_endpoints.md](docs/api_endpoints.md) | 利用 API 一覧・認証・TTL |
| [docs/clo_domain.md](docs/clo_domain.md) | CLO 業務ドメイン知識 |
| [docs/coding_standards.md](docs/coding_standards.md) | コーディング規約 |

---

## ライセンス・帰属

本プロジェクトは以下の OSS を参考にしています:

- [japan-data-mcp](https://github.com/Izyuusya/japan-data-mcp) (Apache-2.0): e-Stat クライアント実装の参考
- [estat-mcp](https://github.com/ajtgjmdjp/estat-mcp) (Apache-2.0): MCP ツール設計の参考

利用データのライセンスは [docs/licenses.md](docs/licenses.md) を参照。
