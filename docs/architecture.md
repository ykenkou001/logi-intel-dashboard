# アーキテクチャ・技術スタック・ディレクトリ構造

**責任範囲**: システム全体の設計方針、採用技術、ファイル配置のルール。「なぜこの構成か」の根拠を含む。

---

## システム構成（3層）

```
                                 ┌─→ [FastAPI REST] → [Next.js ダッシュボード] (フェーズ4以降)
                                 │
[各オープンデータ API] → [core モジュール]
                                 │
                                 └─→ [FastMCP サーバー] → [Claude Desktop / Code]
```

### 各層の責務

| 層 | パス | 責務 |
|----|------|------|
| core モジュール | `core/` | API クライアント、キャッシュ、データ正規化、複合分析ロジック。外部依存なしで単体テスト可能 |
| MCP サーバー層 | `mcp_server/` | core を呼び出す薄いラッパー。Claude が叩くツール定義のみ |
| REST API 層 | `api/` | core を呼び出す薄いラッパー。Web フロントが叩く（フェーズ4） |

**重要**: ビジネスロジックは必ず core に置く。MCP・REST 層には書かない。

---

## 技術スタック

| カテゴリ | 採用技術 | 備考 |
|---------|---------|------|
| 言語 | Python 3.12+ | |
| パッケージ管理 | uv | requirements.txt ではなく pyproject.toml |
| MCP フレームワーク | FastMCP | https://github.com/jlowin/fastmcp |
| HTTP クライアント | httpx (async) | requests は使わない |
| データ検証 | Pydantic v2 | |
| キャッシュ DB | SQLite | API レスポンスキャッシュ用 |
| 分析 DB | DuckDB | 集計クエリ用、SQLite から読み込み可 |
| Lint / Format | Ruff | flake8 / black は使わない |
| 型チェック | mypy (strict) | |
| テスト | pytest, pytest-asyncio | |
| フロント (フェーズ4) | Next.js 15, Recharts, deck.gl | |

### 依存関係追加時のルール

- 新しい依存を追加する前に、本当に必要か確認する
- 軽量な代替があればそちらを優先（例: requests より httpx）
- 追加したら `pyproject.toml` の依存セクションを整理する

---

## ディレクトリ構造

```
logi-intel-dashboard/
├── CLAUDE.md                      # Claude Code 指示書
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .env                           # gitignore 対象
├── .gitignore
├── core/                          # 共通コアモジュール
│   ├── __init__.py
│   ├── clients/                   # 各 API クライアント
│   │   ├── __init__.py
│   │   ├── base.py                # 共通基底クラス（リトライ、レート制限）
│   │   ├── estat.py               # e-Stat API
│   │   ├── corp_number.py         # 国税庁法人番号 API
│   │   ├── xroad.py               # 国交省 xROAD 交通量 API
│   │   ├── weather.py             # 気象庁 bosai JSON
│   │   └── energy.py              # gogo.gs 燃料価格（GoGoGsClient）
│   │   # ※ RESAS API は 2025-03-24 提供終了のため含まない
│   │   # ※ enecho.meti.go.jp は Akamai ブロックで接続不可（2026-05-01 確認）
│   ├── cache.py                   # SQLite キャッシュ層
│   ├── exceptions.py              # カスタム例外定義
│   ├── models/                    # Pydantic モデル
│   │   ├── __init__.py
│   │   ├── estat.py
│   │   └── ...
│   └── analytics/                 # 複合分析ロジック
│       ├── __init__.py
│       ├── benchmark.py           # 業界ベンチマーク
│       ├── driver_gap.py          # ドライバー需給ギャップ
│       └── clo_planning.py        # CLO 中長期計画支援
├── mcp_server/                    # MCP サーバー層
│   ├── __init__.py
│   ├── server.py                  # FastMCP エントリポイント
│   ├── tools/                     # ツール定義
│   │   ├── __init__.py
│   │   ├── estat_tools.py
│   │   └── ...                    # ※ resas_tools.py は作成しない（API 終了）
│   └── prompts/                   # MCP プロンプト
│       └── clo_plan_draft.py
├── api/                           # REST API 層（フェーズ4）
│   └── main.py
├── web/                           # フロント（フェーズ4）
├── tests/
│   ├── core/
│   ├── mcp_server/
│   └── fixtures/                  # API レスポンスサンプル
├── docs/                          # ドキュメント群
│   ├── architecture.md            # このファイル
│   ├── roadmap.md                 # 開発フェーズ・進捗
│   ├── coding_standards.md        # コーディング規約
│   ├── api_endpoints.md           # 利用 API 一覧と認証方法・キャッシュ戦略
│   ├── mcp_tools.md               # MCP ツール命名規則・設計指針
│   ├── clo_domain.md              # CLO 業務ドメイン知識
│   ├── oss_reference.md           # 参考 OSS の方針
│   ├── testing.md                 # テスト方針
│   ├── git_workflow.md            # Git 運用・ブランチ戦略
│   ├── notes.md                   # 重要注意点（API 規約、セキュリティ等）
│   └── licenses.md                # 各 API の利用規約と商用利用可否
└── scripts/
    └── setup_db.py                # 初期 DB 構築
```

---

## キャッシュ戦略

### SQLite キャッシュテーブル設計

```sql
CREATE TABLE api_cache (
    cache_key TEXT PRIMARY KEY,    -- {api}:{endpoint}:{params_hash}
    response_json TEXT NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    ttl_seconds INTEGER NOT NULL
);
CREATE INDEX idx_fetched_at ON api_cache(fetched_at);
```

### TTL 基準

| API | TTL |
|-----|-----|
| e-Stat | 24 時間（統計表は更新頻度低い） |
| 国税庁法人番号 | 30 日 |
| xROAD 交通量 | 1 分（5 分値データ） |
| 気象庁 | 30 分 |
| gogo.gs 燃料価格 | 24 時間（前日更新） |

### 環境変数

- `LOGI_CACHE_BYPASS=1` で強制バイパス可（開発時）

---

## AWS 移行計画（フェーズ4）

現在はローカル稼働（Claude Desktop が stdio で子プロセスとして起動）。
フェーズ4 で AWS 上に常駐サーバーとして移行し、社内全員が接続可能にする。

### ローカル vs AWS の差分

| 項目 | ローカル（現在） | AWS（フェーズ4） |
|------|----------------|----------------|
| 起動方式 | Claude Desktop が stdio で子プロセス起動 | ECS/Lambda 上で常駐 |
| 通信方式 | stdio（標準入出力） | HTTP / SSE |
| キャッシュ | ローカル SQLite | ElastiCache（Redis）または RDS |
| API キー管理 | `.env` ファイル | AWS Secrets Manager |
| 接続元 | 開発者 PC のみ | 社内全員（VPN 内） |

### 移行時の主な変更点

1. **`mcp_server/server.py`** — `mcp.run()` を stdio モードから HTTP/SSE モードに切り替え（FastMCP が対応済み）
2. **`core/cache.py`** — SQLite → Redis クライアントに差し替え（インターフェースは共通化しておく）
3. **`.env`** — Secrets Manager から環境変数を注入する仕組みに変更
4. **Claude Desktop 設定** — `localhost` から AWS エンドポイント URL に変更

### 設計上の注意

- `core/` 層はローカル・AWS どちらでも動くように、外部ストレージへの依存をキャッシュ層に閉じ込める
- HTTP モードでは認証（API キー or Cognito）を MCP サーバー層に追加する必要がある
