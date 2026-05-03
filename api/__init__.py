"""FastAPI REST 層。

`core/` のビジネスロジックを HTTP エンドポイントとして公開する薄いラッパー。
MCP サーバーと同じく `core/export/response.ToolResponse` をそのまま JSON で返却し、
Web ダッシュボード（フェーズ4 Next.js）と Python 経由のクライアント双方から利用する。
"""
