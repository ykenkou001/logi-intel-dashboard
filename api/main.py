"""FastAPI エントリポイント。

起動方法:
    uv run uvicorn api.main:app --reload --port 8000

OpenAPI ドキュメント:
    http://localhost:8000/docs       (Swagger UI)
    http://localhost:8000/redoc      (ReDoc)

設計方針:
    - REST API は `core/` のビジネスロジックを呼び出す薄いラッパー
    - 戻り値は MCP ツールと同じ ToolResponse 構造
      （summary/files/citations/freshness_warnings/data_source）
    - 成果物ファイルは `/api/v1/files/{path}` 経由でダウンロード
      （フェーズ4.5 で S3 プレサインド URL に置換予定）
    - CORS は開発時はワイルドカード、本番（AWS 移行時）は社内ドメインのみ許可
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import analytics, check, clo, company, files, macro

load_dotenv()

app = FastAPI(
    title="Logi-Intel Dashboard API",
    description=(
        "物流業界向け日本オープンデータ統合基盤の REST API 層。\n\n"
        "MCP サーバー（Claude Desktop/Code 用）と同じ `core/` ビジネスロジックを"
        "HTTP エンドポイントとして公開し、Web ダッシュボードから利用する。"
    ),
    version="0.1.0",
    contact={"name": "logi-intel-dashboard"},
)

# 開発時は全 origin 許可。AWS 移行時に社内 VPN ドメインのみへ絞り込む。
# `LOGI_API_CORS_ORIGINS=""`（空文字）が `.env` に残っていると split で [""] になり
# 全 origin が弾かれてしまうため、空要素を除去してから空なら ["*"] にフォールバックする。
_raw_cors = os.environ.get("LOGI_API_CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _raw_cors.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(macro.router)
app.include_router(clo.router)
app.include_router(company.router)
app.include_router(files.router)
app.include_router(check.router)
app.include_router(analytics.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """ヘルスチェックエンドポイント。AWS ALB のヘルスチェックに利用。"""
    return {"status": "ok", "service": "logi-intel-dashboard-api"}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    """ルートエンドポイント。OpenAPI ドキュメントへの誘導のみ。"""
    return {
        "service": "logi-intel-dashboard-api",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }
