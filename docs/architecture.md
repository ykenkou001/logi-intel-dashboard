# アーキテクチャ・技術スタック・ディレクトリ構造

**責任範囲**: システム全体の設計方針、採用技術、ファイル配置のルール。「なぜこの構成か」の根拠を含む。

> ⚠️ 本アプリの存在意義は **CLO 支援への徹底コミット**（[CLAUDE.md §1.5](../CLAUDE.md)）。MCP サーバー / REST API / Web は手段であり、本体は `core/` と `core/export/`（成果物生成）にある。

---

## システム構成（core + 多出口）

```
                                              ┌─→ [FastMCP サーバー] → Claude Desktop/Code
                                              │     （社内パワーユーザー・営業向け）
[各オープンデータ API] → [core モジュール] ───┤
       ↑                       │              ├─→ [FastAPI REST] → [Next.js ダッシュボード]
       │                       │              │     （CLO担当者・経営層向け、フェーズ4）
[静的データ                    ↓              │
 (CO2係数・告示等)]    [core/export/]         └─→ [ファイル出力]
                          ↓                         ・PPT（最優先）
                       成果物生成                   ・PDF
                          ↓                         ・Excel
                  [outputs/ ディレクトリ]            ・Word（様式第3別紙）
                          ↓                         ・Markdown
                  [Web ダウンロード or 直接配布]
```

### 各層の責務

| 層 | パス | 責務 |
|----|------|------|
| core モジュール | `core/` | API クライアント、キャッシュ、データ正規化、複合分析ロジック、**法令ロジック**、**成果物生成**。外部依存なしで単体テスト可能 |
| 静的データ層 | `core/static/` | CO2 排出原単位・改善基準告示・標準的運賃等、API 不要のデータ。鮮度メタデータで更新リマインド |
| 出口層（成果物） | `core/export/` | PPT / PDF / Excel / Word / Markdown 出力。**ここが CLO に届く価値の最終地点** |
| MCP サーバー層 | `mcp_server/` | core を呼び出す薄いラッパー。Claude が叩くツール定義のみ。**戻り値はファイルパスを含む** |
| REST API 層 | `api/` | core を呼び出す薄いラッパー。Web フロントが叩く（フェーズ4）。成果物ファイルをダウンロード配信。**フェーズ4.0 で実装完了（21 エンドポイント・FastAPI）** |

**重要原則**:
- ビジネスロジックは必ず `core/` に置く。MCP・REST 層には書かない
- **MCP ツールは「Claude の会話画面に文字列を返す」だけで終わらせない**。必ず `core/export/` を呼び、ファイルパスを成果物として返す
- 全成果物に出典 URL を付与（`core/export/citation.py` 経由）

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
| **PPT 出力** | **python-pptx** | **CLO 計画書プレゼン資料生成（最優先）** |
| **Excel 出力** | **openpyxl** | **数値表・出典シート** |
| **Word 出力** | **python-docx** | **様式第3別紙（e-Gov 提出用）への流し込み** |
| **PDF 出力** | **WeasyPrint or LibreOffice CLI** | **PPT/Word からの変換** |
| Lint / Format | Ruff | flake8 / black は使わない |
| 型チェック | mypy (strict) | |
| テスト | pytest, pytest-asyncio | |
| フロント (フェーズ4) | Next.js 15, Recharts, deck.gl | 成果物ダウンロード UI 含む |

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
│   │   ├── company_profile.py     # CLO ツールの自社情報入力モデル
│   │   └── ...
│   ├── static/                    # 静的データ（API 不要・コード同梱）
│   │   ├── __init__.py
│   │   ├── _freshness.py          # 鮮度メタデータ + 更新リマインダ
│   │   ├── co2_factors.py         # 環境省 CO2 排出原単位
│   │   ├── improvement_standards.py  # 改善基準告示（拘束時間等）
│   │   ├── standard_freight.py    # 標準的運賃 2024
│   │   ├── efficiency_law_certified.py  # 物流効率化法 認定事業
│   │   └── industry_freight_coef.py  # 業種別物流原単位
│   ├── legal/                     # 法令ロジック
│   │   ├── __init__.py
│   │   ├── eligibility.py         # 9万トン基準の特定荷主判定
│   │   └── improvement_check.py   # 改善基準告示準拠チェック
│   ├── analytics/                 # 複合分析ロジック
│   │   ├── __init__.py
│   │   ├── benchmark.py           # 業界ベンチマーク
│   │   ├── driver_gap.py          # ドライバー需給ギャップ
│   │   ├── modal_shift.py         # モーダルシフト試算
│   │   ├── load_factor.py         # 積載率改善 → CO2 削減
│   │   ├── target_proposal.py     # 数値目標提案
│   │   └── clo_planning.py        # CLO 中長期計画支援
│   ├── export/                    # ★成果物生成（CLO に届く出口）★
│   │   ├── __init__.py
│   │   ├── citation.py            # 出典 URL の統一管理
│   │   ├── ppt_writer.py          # PPT 出力（最優先）
│   │   ├── pdf_writer.py          # PDF 出力
│   │   ├── excel_writer.py        # Excel 出力
│   │   ├── docx_form3_writer.py   # 様式第3別紙への流し込み
│   │   └── markdown_writer.py     # Markdown 出力
│   └── templates/                 # 成果物テンプレート
│       ├── clo_plan_form3.docx    # 国交省様式第3別紙（公式）
│       └── clo_plan_examples/     # 公式記載事例（業種別 MD 化）
│   # PPT デザインは Logi-Intel CLO Report（コード生成型・マスタファイル不使用）
│   # → docs/ppt_design.md / DESIGN.md
│   # ※ micware ブランドへの差し替えは将来検討（公式ガイドライン入手後）
├── mcp_server/                    # MCP サーバー層
│   ├── __init__.py
│   ├── server.py                  # FastMCP エントリポイント
│   ├── tools/                     # ツール定義
│   │   ├── __init__.py
│   │   ├── estat_tools.py
│   │   └── ...                    # ※ resas_tools.py は作成しない（API 終了）
│   └── prompts/                   # MCP プロンプト
│       └── clo_plan_draft.py
├── api/                           # REST API 層（フェーズ4.0 ✅ 実装済）
│   ├── __init__.py
│   ├── main.py                    # FastAPI エントリ + ヘルスチェック + CORS
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── clo.py                 # /api/v1/clo/* (12 エンドポイント)
│   │   ├── macro.py               # /api/v1/macro/overview
│   │   ├── company.py             # /api/v1/company/{template,load,samples}
│   │   └── files.py               # /api/v1/files/{path} ダウンロード
│   └── schemas/
│       ├── __init__.py
│       └── responses.py           # ToolResponseModel / CitationModel (Pydantic)
├── web/                           # フロント（フェーズ4 Next.js）
├── outputs/                       # 成果物の出力先（gitignore 対象）
│   ├── ppt/
│   ├── pdf/
│   ├── excel/
│   ├── docx/
│   └── markdown/
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

## ローカル開発と本番の切り分け

| 観点 | ローカル開発 | 本番（AWS PoC） |
|------|------------|----------------|
| FastAPI 起動 | `pwsh scripts/dev_api.ps1` で `uvicorn --reload`（port 8000） | Lambda + API Gateway HTTP API |
| Web 配信 | `pwsh scripts/dev_web.ps1` で `next dev`（port 3000） | S3 静的エクスポート + CloudFront |
| API_BASE_URL | `dev_web.ps1` が `http://localhost:8000` を環境変数で注入 | `""`（同一 origin / CloudFront 経由） |
| ストレージ | ローカル `outputs/` ディレクトリ | S3 `outputs/` prefix |
| シークレット | `.env` | SSM Parameter Store SecureString |
| キャッシュ | `./.logi_cache.db`（SQLite） | `/tmp/.logi_cache.db`（Lambda 揮発） |

### ローカル開発時の注意点（必読）

**`uvicorn` や `npm run dev` を直接叩いてはいけない。** 必ず以下を使う:

```powershell
pwsh scripts/dev_api.ps1            # FastAPI :8000（既存 uvicorn を kill + --reload）
pwsh scripts/dev_web.ps1            # Next.js :3000（既存 next dev を kill + API_BASE 固定）
```

#### 経緯（2026-05-05 の事故）

「本番 Lambda に修正をデプロイしたのに、ブラウザのフロントが古い localhost:8000 を
叩き続けて修正反映が確認できない」事故が発生。原因は次の 2 点:

1. **`--reload` なしの古い uvicorn が `core/` をメモリにロードしたまま生存**
   多重起動で port 8000 / 8765 を同時 listen していた。
2. **`web/lib/api.ts` のデフォルト API_BASE が `http://localhost:8000`**
   `NEXT_PUBLIC_API_BASE_URL` 未設定の本番ビルドでも、ブラウザが意図せずローカルを叩く構造だった。

#### 恒久対策（実施済）

- `web/lib/api.ts` のデフォルト API_BASE を `""`（同一 origin）に変更
- `scripts/dev_api.ps1` / `scripts/dev_web.ps1` に **既存プロセスの自動 kill** を組み込み
- 詳細経緯は [CLAUDE.md §6.5](../CLAUDE.md) 参照

#### 自己診断手順

「コード直したのに本番フロントの動作が変わらない」と感じたら:

1. ブラウザ DevTools の Network タブで API 先が `localhost` か CloudFront か確認
2. `Get-Process uvicorn,node` で残存プロセスを点検
3. 古いプロセスを Stop → `dev_api.ps1` で再起動

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

---

## 成果物配信戦略（CLO に届く最終地点）

本アプリの設計上の最終アウトプットは「分析結果の文字列」ではなく「**経営会議で配れるファイル**」。配信経路は2段構成。

### フェーズ 2.5〜3（ローカル）: ファイルパス返却方式

```
Claude Desktop
     ↓ logi_clo_plan_draft(company_profile)
mcp_server/tools/clo_tools.py
     ↓ core/analytics/clo_planning.py で分析
     ↓ core/export/ppt_writer.py で生成
     ↓
outputs/ppt/clo_plan_<company>_<timestamp>.pptx
     ↓
ファイルパスを Claude に返す → ユーザーが直接開く / 共有
```

MCP ツールの戻り値:
```python
{
    "summary": "...",                                # 概要テキスト
    "files": {
        "ppt": "outputs/ppt/clo_plan_xxx.pptx",
        "pdf": "outputs/pdf/clo_plan_xxx.pdf",
        "excel": "outputs/excel/clo_plan_xxx.xlsx",
        "docx_form3": "outputs/docx/form3_xxx.docx"  # 国交省様式第3別紙
    },
    "citations": [...]                               # 出典 URL リスト
}
```

### フェーズ 4（AWS + Web）: HTTPS ダウンロード方式

```
Next.js ダッシュボード
     ↓ 入力フォーム（自社情報 → CompanyProfile）
     ↓ POST /api/v1/clo/plan/draft
FastAPI
     ↓ core/analytics → core/export
     ↓
S3 に成果物アップロード
     ↓
プレサインド URL を返却
     ↓
ブラウザから PPT/PDF/Excel/DOCX をダウンロード
```

**非エンジニアの CLO 担当者が、エンジニアの介在なしに成果物を入手できることがゴール**。

### 出力フォーマットの優先順位（健一さんとの合意事項）

1. **PPT**（最優先）— 経営会議の必須フォーマット
2. **PDF** — 顧客提案・印刷配布
3. **Excel** — 数値表・社内 BI 取込
4. **Word（様式第3別紙）** — e-Gov 提出用
5. **Markdown** — Claude → 人間レビュー用
