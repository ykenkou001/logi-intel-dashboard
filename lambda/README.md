# Lambda パッケージング

FastAPI を Mangum でラップして Lambda + API Gateway HTTP API でホストする。
**通常の更新は GitHub Actions（`.github/workflows/deploy-api.yml`）で自動化されている**。
本書は緊急時の手動再デプロイ・トラブル時の参照用。

## 構成

```
api.lambda_handler.handler  ←  Lambda Handler
   └─ Mangum(app)
       └─ api.main.app  (FastAPI)
           └─ core/  (ビジネスロジック)
```

`mcp_server/` は Lambda zip に含めない（Web/REST 経路から参照されないため）。

## Lambda 関数設定（Terraform で自動化済み・参考値）

| 項目 | 値 |
|------|----|
| Runtime | Python 3.12 |
| Handler | `api.lambda_handler.handler` |
| Memory | 1024 MB |
| Ephemeral storage | 1024 MB（`/tmp` を outputs に使う） |
| Timeout | 300 秒 |
| Architecture | x86_64（manylinux2014_x86_64 wheel） |

## デプロイ経路

| 経路 | 上限 | 採用理由 |
|------|------|----------|
| `update-function-code --zip-file`（API 直アップロード） | ~70 MB | × 2026-05-05 に CI で超過 |
| **`update-function-code --s3-bucket --s3-key`（S3 経由）** | 250 MB | ✅ 現行採用 |

GitHub Actions 経由のデプロイは `s3://logi-intel-dev-7m2lqc/lambda-deploy/function-<sha>.zip` に
アップロード後、`update-function-code --s3-bucket ... --s3-key ...` で取り込む。
古い zip は S3 ライフサイクル（7 日）で自動削除される。

## zip サイズ削減ポリシー

- `boto3 / botocore / boto3-stubs / botocore-stubs / s3transfer / jmespath` は **Lambda Python ランタイム同梱**のため除外
- `mcp_server/` は除外（Lambda 経路から参照なし）
- `pip install --no-compile`（`.pyc` を生成しない）
- `__pycache__` `*.pyc` `*.pyo` を削除
- `*.dist-info/{RECORD,REQUESTED,INSTALLER,WHEEL}` を削除
- パッケージ内の `tests/ test/ examples/ docs/` を削除

詳細は `.github/workflows/deploy-api.yml` のビルドステップを参照。

## 緊急時のローカルビルド手順（Windows / PowerShell）

CI が動かない時の最後の手段。基本は CI に任せる。

```powershell
# 1. 依存関係を export（boto3 系は Lambda ランタイム同梱のため除外）
uv export --no-hashes --no-dev --no-emit-project --output-file lambda/requirements.full.txt
Get-Content lambda/requirements.full.txt | Where-Object {
    $_ -notmatch '^(boto3|botocore|boto3-stubs|botocore-stubs|s3transfer|jmespath)([=<>!~ ]|$)'
} | Set-Content lambda/requirements.txt

# 2. クリーンビルド
Remove-Item -Recurse -Force lambda/build -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force lambda/build | Out-Null

# 3. Linux 向け wheel で依存をインストール
pip install -r lambda/requirements.txt `
    --target lambda/build `
    --platform manylinux2014_x86_64 `
    --python-version 3.12 `
    --only-binary=:all: `
    --no-compile

# 4. アプリコードをコピー（mcp_server は含めない）
Copy-Item -Recurse -Force core lambda/build/
Copy-Item -Recurse -Force api lambda/build/

# 5. 不要ファイル削除
Get-ChildItem lambda/build -Recurse -Directory -Force |
    Where-Object { $_.Name -eq '__pycache__' } |
    Remove-Item -Recurse -Force
Get-ChildItem lambda/build -Recurse -File -Force -Include *.pyc, *.pyo |
    Remove-Item -Force

# 6. zip 圧縮
Remove-Item lambda/function.zip -ErrorAction SilentlyContinue
Compress-Archive -Path lambda/build/* -DestinationPath lambda/function.zip -CompressionLevel Optimal
"{0:N1} MB" -f ((Get-Item lambda/function.zip).Length / 1MB)
```

## 緊急時の手動デプロイ（S3 経由）

```powershell
$sha = git rev-parse HEAD
$key = "lambda-deploy/function-$sha-manual.zip"

aws s3 cp lambda/function.zip "s3://logi-intel-dev-7m2lqc/$key" `
    --region ap-northeast-1

aws lambda update-function-code `
    --function-name logi-intel-dev-api `
    --s3-bucket logi-intel-dev-7m2lqc `
    --s3-key $key `
    --region ap-northeast-1
```

## 動作確認

```powershell
curl https://d1zei8qivkf3cr.cloudfront.net/health
# → {"status":"ok"}
```

## ローカル統合確認（Mangum なしでも可）

`pwsh scripts/dev_api.ps1` で従来通りローカル起動できる。
Mangum は Lambda 環境のみで動作し、ローカル開発には影響しない。
