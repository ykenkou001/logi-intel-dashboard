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
