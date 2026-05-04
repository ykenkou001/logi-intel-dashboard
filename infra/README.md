# Terraform IaC（PoC）

Logi-Intel Dashboard PoC 用の AWS インフラを単一ファイルで定義する。

## 前提

- AWS CLI が設定済み (`aws configure`)
- リージョン: ap-northeast-1
- 個人アカウント（AdministratorAccess 推奨）
- Terraform 1.5+ インストール済み
- Lambda zip パッケージ作成済み（`lambda/function.zip`）

## デプロイ手順

### 1. SSM Parameter Store にシークレット投入（**Terraform 適用前に必須**）

```powershell
$env:AWS_REGION = "ap-northeast-1"

aws ssm put-parameter `
    --name "/logi-intel/dev/ESTAT_APP_ID" `
    --value "<実際のキー>" `
    --type "SecureString"

aws ssm put-parameter `
    --name "/logi-intel/dev/CORP_NUMBER_APP_ID" `
    --value "<実際のキー>" `
    --type "SecureString"
```

### 2. Lambda zip パッケージ作成

```powershell
# プロジェクトルートで
uv export --no-hashes --no-dev --no-emit-project > lambda/requirements.txt

Remove-Item -Recurse -Force lambda/build -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force lambda/build | Out-Null

pip install -r lambda/requirements.txt `
    --target lambda/build `
    --platform manylinux2014_x86_64 `
    --python-version 3.12 `
    --only-binary=:all:

Copy-Item -Recurse -Force core lambda/build/
Copy-Item -Recurse -Force api lambda/build/
Copy-Item -Recurse -Force mcp_server lambda/build/

Compress-Archive -Path lambda/build/* -DestinationPath lambda/function.zip -Force
```

### 3. Terraform apply

```powershell
cd infra
terraform init
terraform plan -var="env=dev"
terraform apply -var="env=dev"
```

### 4. Next.js を S3 にアップロード

```powershell
cd ../web

# 同一 origin で API を叩くため API_BASE を空に
$env:NEXT_PUBLIC_API_BASE_URL = ""
npm run build

# Terraform 出力からバケット名取得
$bucket = terraform -chdir=../infra output -raw s3_bucket
aws s3 sync out/ "s3://$bucket/web/" --delete --region ap-northeast-1

# CloudFront キャッシュ無効化
$dist = terraform -chdir=../infra output -raw cloudfront_url
$distId = (aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='$($dist -replace 'https://','')'].Id | [0]" --output text)
aws cloudfront create-invalidation --distribution-id $distId --paths "/*"
```

### 5. 動作確認

```powershell
$cfUrl = terraform -chdir=infra output -raw cloudfront_url
curl "$cfUrl/health"
# → {"status": "ok", "service": "logi-intel-dashboard-api"}

# ブラウザで $cfUrl を開く → ダッシュボード表示
```

## 構成リソース

| リソース | 用途 |
|---------|------|
| S3 バケット (1 個) | `web/`・`outputs/`・`profiles/` を prefix で分離 |
| Lambda 関数 | FastAPI + Mangum、Python 3.12、1024MB / 5min タイムアウト |
| Lambda Function URL | CloudFront のオリジン（直接叩くことも可） |
| CloudFront ディストリビューション | `/` → S3 web、`/api/*` `/health` `/docs` `/openapi.json` → Lambda |
| IAM ロール | Lambda が S3 RW + SSM Read + CloudWatch Logs |
| CloudWatch Logs | 7 日保管 |

## 削除（PoC 終了時）

```powershell
cd infra
terraform destroy -var="env=dev"
```

S3 バケットは `force_destroy=true` でオブジェクトもまとめて削除される。

## コスト

CloudWatch Logs Insights オフ・WAF なし・Route53 なしで、月額目安 **$1〜$5**（Lambda は無料枠 100 万リクエスト内に収まる想定）。
