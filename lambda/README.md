# Lambda パッケージング

FastAPI を Mangum でラップして Lambda Function URL でホストする。

## 構成

```
api.lambda_handler.handler  ←  Lambda Handler
   └─ Mangum(app)
       └─ api.main.app  (FastAPI)
           └─ core/  (ビジネスロジック)
```

## Lambda 関数設定（Terraform で自動化済み・参考値）

| 項目 | 値 |
|------|----|
| Runtime | Python 3.12 |
| Handler | `api.lambda_handler.handler` |
| Memory | 1024 MB |
| Ephemeral storage | 1024 MB（`/tmp` を outputs に使う） |
| Timeout | 300 秒 |
| Architecture | x86_64（boto3 / pandas を含むため arm64 はパッケージ容量で 250MB 上限を超える可能性） |

## ビルド手順（Windows / PowerShell）

```powershell
# 1. 依存関係を export
uv export --no-hashes --no-dev --no-emit-project > lambda/requirements.txt

# 2. クリーンビルド
Remove-Item -Recurse -Force lambda/build -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force lambda/build | Out-Null

# 3. Linux 向け wheel で依存をインストール（pandas/openpyxl が arm64 でなく x86_64 でビルドされるよう platform 指定）
pip install -r lambda/requirements.txt `
    --target lambda/build `
    --platform manylinux2014_x86_64 `
    --python-version 3.12 `
    --only-binary=:all:

# 4. アプリコードをコピー
Copy-Item -Recurse -Force core lambda/build/
Copy-Item -Recurse -Force api lambda/build/
Copy-Item -Recurse -Force mcp_server lambda/build/

# 5. zip 圧縮
Compress-Archive -Path lambda/build/* -DestinationPath lambda/function.zip -Force
```

## デプロイ

```powershell
aws lambda update-function-code `
    --function-name logi-intel-api-dev `
    --zip-file fileb://lambda/function.zip `
    --region ap-northeast-1
```

## 動作確認

```powershell
# Lambda Function URL に curl
$url = aws lambda get-function-url-config `
    --function-name logi-intel-api-dev `
    --region ap-northeast-1 `
    --query FunctionUrl --output text

curl "$url/health"
# → {"status": "ok", "service": "logi-intel-dashboard-api"}
```

## ローカル統合確認（Mangum なしでも可）

`uv run uvicorn api.main:app --reload` で従来通りローカル起動できる。
Mangum は Lambda 環境のみで動作し、ローカル開発には影響しない。
