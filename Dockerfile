# Logi-Intel Dashboard FastAPI コンテナ
#
# マルチステージビルドで uv の依存解決を分離し、最終イメージは python:3.12-slim ベース。
# AWS ECS / Lambda（コンテナ）両対応を想定。
#
# ビルド:
#   docker build -t logi-intel-api:latest .
# 起動:
#   docker run --rm -p 8000:8000 --env-file .env logi-intel-api:latest

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# uv インストール
RUN pip install --no-cache-dir uv==0.5.4

WORKDIR /app

# 依存ファイルだけ先にコピーしてキャッシュ効率化
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# アプリコードをコピーして project install
COPY core ./core
COPY mcp_server ./mcp_server
COPY api ./api
RUN uv sync --frozen --no-dev

# ─── 最終イメージ ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# 非 root ユーザーで実行
RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

# ビルダから venv とアプリだけコピー
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/core /app/core
COPY --from=builder --chown=app:app /app/mcp_server /app/mcp_server
COPY --from=builder --chown=app:app /app/api /app/api

# 成果物ディレクトリ（コンテナ内で生成。AWS では EFS or S3 マウントへ差替予定）
RUN mkdir -p /app/outputs/ppt /app/outputs/docx /app/outputs/excel /app/outputs/markdown /app/outputs/pdf /app/outputs/profiles /app/outputs/templates && chown -R app:app /app/outputs

USER app

EXPOSE 8000

# ALB / API Gateway 経由のヘルスチェックは GET /health を叩く想定
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
