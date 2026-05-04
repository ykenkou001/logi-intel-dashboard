# Logi-Intel Dashboard PoC AWS infrastructure
#
# 目的: 月額 $1〜$5 の最安構成で社内レビュー用 PoC を稼働させる。
# 構成: 単一 S3 バケット（web / outputs / profiles を prefix で分離）+ Lambda(Python+Mangum)
#       + Lambda Function URL + CloudFront（web は S3、/api/* は Lambda にルーティング）
#
# 適用前提:
#   - 健一個人 AWS アカウント (AdministratorAccess)
#   - Region: ap-northeast-1
#   - SSM Parameter Store にシークレットを事前投入
#       /logi-intel/<env>/ESTAT_APP_ID
#       /logi-intel/<env>/CORP_NUMBER_APP_ID
#       /logi-intel/<env>/EDMC_APP_ID
#
# 適用手順:
#   cd infra
#   terraform init
#   terraform plan -var="env=dev"
#   terraform apply -var="env=dev"
#
# 削除（PoC 終了時）:
#   terraform destroy -var="env=dev"
#   ※ S3 バケット削除前にオブジェクト全削除が必要なため、force_destroy=true を設定済み

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.region
}

# CloudFront 用 ACM 証明書を扱うサブプロバイダー（CloudFront は us-east-1 必須）
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# ─── 変数 ────────────────────────────────────────────────────────────

variable "env" {
  type        = string
  description = "環境識別子（dev / staging / prod）"
  default     = "dev"
}

variable "region" {
  type        = string
  description = "AWS リージョン"
  default     = "ap-northeast-1"
}

variable "project" {
  type        = string
  description = "リソース名プレフィックス"
  default     = "logi-intel"
}

variable "lambda_zip_path" {
  type        = string
  description = "Lambda zip パッケージのパス"
  default     = "../lambda/function.zip"
}

variable "lambda_memory_mb" {
  type        = number
  description = "Lambda メモリ（MB）。python-pptx + openpyxl で 1024 推奨"
  default     = 1024
}

variable "lambda_timeout_sec" {
  type        = number
  description = "Lambda タイムアウト（秒）。plan_draft は 1〜2 分かかる"
  default     = 300
}

# 一意なリソース名のためにアカウント ID を取得
data "aws_caller_identity" "current" {}

# ランダムサフィックス（S3 バケット名のグローバル一意性確保）
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  name_prefix = "${var.project}-${var.env}"
  bucket_name = "${local.name_prefix}-${random_string.suffix.result}"
  common_tags = {
    Project = var.project
    Env     = var.env
    Stack   = "poc"
    ManagedBy = "terraform"
  }
}

# ─── S3 バケット（web / outputs / profiles を prefix で分離） ─────────

resource "aws_s3_bucket" "main" {
  bucket        = local.bucket_name
  force_destroy = true # PoC 終了時に terraform destroy で空にできるよう
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket                  = aws_s3_bucket.main.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    id     = "cleanup-old-outputs"
    status = "Enabled"
    filter {
      prefix = "outputs/"
    }
    expiration {
      days = 30 # PoC 用: 30 日で自動削除
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }

  rule {
    id     = "expire-noncurrent-profiles"
    status = "Enabled"
    filter {
      prefix = "profiles/"
    }
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ─── Lambda 用 IAM ロール ─────────────────────────────────────────

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name_prefix}-api-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "basic_logging" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_inline" {
  # outputs/ profiles/ への RW
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.main.arn}/outputs/*",
      "${aws_s3_bucket.main.arn}/profiles/*",
    ]
  }
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.main.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["outputs/*", "profiles/*"]
    }
  }
  # SSM Parameter Store SecureString の取得
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/${var.env}/*",
    ]
  }
  # SecureString の復号
  statement {
    actions   = ["kms:Decrypt"]
    resources = ["arn:aws:kms:${var.region}:${data.aws_caller_identity.current.account_id}:key/*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "lambda_inline" {
  name   = "${local.name_prefix}-api-inline"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_inline.json
}

# ─── Lambda 関数 ─────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name_prefix}-api"
  retention_in_days = 7 # PoC 用: 7 日のみ保管（コスト最小化）
  tags              = local.common_tags
}

resource "aws_lambda_function" "api" {
  function_name    = "${local.name_prefix}-api"
  role             = aws_iam_role.lambda.arn
  handler          = "api.lambda_handler.handler"
  runtime          = "python3.12"
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  memory_size      = var.lambda_memory_mb
  timeout          = var.lambda_timeout_sec
  ephemeral_storage {
    size = 1024 # /tmp を outputs に使うため
  }

  environment {
    variables = {
      LOGI_STORAGE_BACKEND     = "s3"
      LOGI_S3_BUCKET           = aws_s3_bucket.main.id
      LOGI_S3_PREFIX           = "outputs/"
      LOGI_OUTPUTS_DIR         = "/tmp/outputs"
      LOGI_SECRETS_BACKEND     = "ssm"
      LOGI_SSM_PREFIX          = "/${var.project}/${var.env}"
      LOGI_API_CORS_ORIGINS    = "*"
      PYTHONPATH               = "/var/task"
    }
  }

  tags = local.common_tags

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda_inline,
  ]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
  invoke_mode        = "BUFFERED" # 通常レスポンスサイズ制限 6MB（PPT/Excel もこれ以下）

  # AWS Lambda Function URL の cors.allow_methods は GET/POST/PUT/DELETE/HEAD/* のみ許容。
  # OPTIONS は preflight として Lambda 側で自動応答するため列挙不要。
  # ここではワイルドカード "*" を使い、現実の制限は CloudFront 側 origin policy で行う。
  cors {
    allow_origins = ["*"]
    allow_methods = ["*"]
    allow_headers = ["*"]
    max_age       = 86400
  }
}

# ─── CloudFront ───────────────────────────────────────────────────

# S3 への OAC（Origin Access Control）
resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${local.name_prefix}-s3-oac"
  description                       = "OAC for ${aws_s3_bucket.main.id}/web"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.name_prefix} PoC"
  default_root_object = "index.html"
  price_class         = "PriceClass_200" # 日本含む最低料金クラス

  # S3 オリジン: web/ プレフィックスを配信
  origin {
    domain_name              = aws_s3_bucket.main.bucket_regional_domain_name
    origin_id                = "s3-web"
    origin_path              = "/web"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  # Lambda Function URL オリジン
  origin {
    domain_name = replace(replace(aws_lambda_function_url.api.function_url, "https://", ""), "/", "")
    origin_id   = "lambda-api"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "s3-web"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
    response_headers_policy_id = "67f7725c-6f97-4210-82d7-5512b31e9d03" # SecurityHeadersPolicy
  }

  # /api/* と /health は Lambda へ
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "lambda-api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # CachingDisabled
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # AllViewerExceptHostHeader
  }

  ordered_cache_behavior {
    path_pattern           = "/health"
    target_origin_id       = "lambda-api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]

    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # CachingDisabled
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # AllViewerExceptHostHeader
  }

  ordered_cache_behavior {
    path_pattern           = "/docs"
    target_origin_id       = "lambda-api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]

    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }

  ordered_cache_behavior {
    path_pattern           = "/openapi.json"
    target_origin_id       = "lambda-api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]

    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["JP"] # 日本国内のみ（社内利用想定）
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.common_tags
}

# CloudFront から S3 への読取権限
data "aws_iam_policy_document" "s3_cf" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.main.arn}/web/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.main.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "main" {
  bucket = aws_s3_bucket.main.id
  policy = data.aws_iam_policy_document.s3_cf.json
}

# ─── 出力 ────────────────────────────────────────────────────────

output "cloudfront_url" {
  description = "社内レビュー用の入口 URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "lambda_function_name" {
  description = "Lambda 関数名（zip 更新時に使用）"
  value       = aws_lambda_function.api.function_name
}

output "lambda_function_url" {
  description = "Lambda Function URL（CloudFront を介さず直接叩く場合）"
  value       = aws_lambda_function_url.api.function_url
}

output "s3_bucket" {
  description = "S3 バケット名"
  value       = aws_s3_bucket.main.id
}

output "s3_web_prefix" {
  description = "Next.js 静的ファイルの同期先"
  value       = "s3://${aws_s3_bucket.main.id}/web/"
}
