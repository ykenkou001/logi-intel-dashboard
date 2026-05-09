"""AWS Lambda エントリポイント。

Mangum を使って FastAPI（ASGI）を Lambda Function URL のイベント形式に
ブリッジする。lifespan は無効化（Lambda はリクエストごとにライフサイクルが
完結し、startup/shutdown フックが意味を成さないため）。

Lambda 関数設定:
    Runtime: Python 3.12
    Handler: api.lambda_handler.handler
    Memory:  1024 MB（python-pptx + openpyxl の作業領域として推奨）
    Timeout: 300 秒（plan_draft は外部 API + 4 種類のファイル生成で最大 1〜2 分）

環境変数:
    LOGI_STORAGE_BACKEND=s3
    LOGI_S3_BUCKET=<outputs バケット名>
    LOGI_S3_PREFIX=outputs/
    LOGI_OUTPUTS_DIR=/tmp/outputs
    LOGI_SECRETS_BACKEND=ssm
    LOGI_SSM_PREFIX=/logi-intel/dev
    LOGI_API_CORS_ORIGINS=https://<cloudfront-domain>
    （+ シークレットは SSM Parameter Store 経由で取得するため env 直接は不要）
"""

from __future__ import annotations

from mangum import Mangum

from api.main import app

# lifespan="off": Lambda 上では startup/shutdown を呼ばない（コンテナ再利用時に二重実行を避ける）
handler = Mangum(app, lifespan="off")
