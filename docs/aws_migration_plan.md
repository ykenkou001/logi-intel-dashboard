# AWS 移行計画（PoC 版・最安構成）

**責任範囲**: ローカル稼働 → AWS 上の社内レビュー用 PoC への移行手順とコスト管理。
コードレベルの設計詳細は [docs/architecture.md](architecture.md) を参照。

> ⚠️ AWS 移行は**コストと運用負担を伴う実環境への変更**である。
> 健一の明示的な承認なしに `terraform apply` / `aws lambda update-function-code` 等は実行しない。

---

## 1. 背景と目的

PoC 段階。利用想定は不明（おそらく社内 数人〜数十人のスポット利用）。
目的は次の 3 つ：

1. 自宅 PC ではなく社内 URL で動作確認できるようにする（GW 明けの社内レビュー用）
2. 月額コストを **$5〜$10 以内** に抑える
3. Zenn 記事化（Lambda Web Adapter で FastAPI を無改修デプロイする構成）

> **明示的にやらないこと**: Docker / ECS / ALB / ElastiCache / Cognito。
> 過去のドラフトでは ECS Fargate 想定で Dockerfile を準備したが、PoC には過剰なため廃案。

---

## 2. 構成図

```
[社内ユーザー] ─HTTPS─→ [CloudFront]
                             │
                             ├─ /            ─→ [S3: Next.js 静的ビルド]
                             │
                             └─ /api/*       ─→ [Lambda Function URL]
                                                  │
                                                  ├─ Lambda Web Adapter
                                                  │   で FastAPI 無改修起動
                                                  │
                                                  ├─ outputs/      ─→ [S3 outputs]
                                                  ├─ profiles/     ─→ [S3 profiles]
                                                  ├─ secrets       ─→ [SSM Parameter Store]
                                                  └─ logs          ─→ [CloudWatch Logs (7d)]
```

**API Gateway 不採用の理由**: HTTP API でも $1/M リクエストかかる。
PoC では Lambda Function URL（呼び出しコスト 0）で十分。

---

## 3. 月額コスト試算

| 項目 | 用途 | PoC 月額 |
|------|------|---------|
| CloudFront | Web 配信 + Lambda へのルーティング | ~$0〜$1（無料枠 1TB） |
| S3 (web)   | Next.js 静的ビルド | ~$0（5GB 無料枠） |
| S3 (outputs / profiles) | 成果物 + プロフィール JSON | ~$0〜$1 |
| Lambda     | FastAPI（実行時間ぶんだけ） | ~$0〜$2（100万リクエスト無料枠） |
| Function URL | Lambda 呼出口 | $0（呼出料金なし） |
| SSM Parameter Store | API キー（SecureString） | $0（標準 Parameter は無料） |
| CloudWatch Logs | 7 日保管・Insights オフ | ~$1 |
| Route 53 / ACM | ドメイン使う場合のみ | ~$0.5（オプション） |
| **合計** | | **$1〜$5** |

> Secrets Manager は使わない（$0.40/secret/月）。SSM Parameter Store SecureString
> は無料枠で十分。

---

## 4. 必要なコード改修（デプロイ前提）

| 改修 | ファイル | 規模 | 目的 |
|------|---------|------|------|
| outputs を S3 切替対応 | `core/export/response.py` | 〜半日 | Lambda は `/tmp` 以外読み書き不可。S3 に切替 |
| 自社プロフィール永続化を S3 切替対応 | `core/io/company_store.py` | 〜半日 | 同上 |
| ファイル DL を S3 プレサインド URL に | `api/routers/files.py` | 1 時間 | Lambda 配信よりプレサインド URL のほうが速い・安い |
| Next.js を `output: "export"` 化 | `web/next.config.ts` | 1 時間 | S3 配信のため静的化 |
| Lambda Web Adapter エントリスクリプト | `lambda/run.sh` 新規 | 30 分 | FastAPI を無改修で起動 |
| Lambda パッケージング | `pyproject.toml` + Makefile | 1 時間 | zip 形式（依存量しだいで container 化検討） |
| Terraform IaC | `infra/main.tf` 1 ファイル | 半日 | S3 / Lambda / CloudFront / SSM をコード化 |

**合計: 1〜2 日**。

---

## 5. デプロイ手順（健一・健一権限の AWS 個人アカウント）

### 5.1 AWS CLI 準備

```powershell
# 既に完了済み（ユーザー報告: 2026-05-04）
aws configure
# - Region: ap-northeast-1
# - Output: json
```

### 5.2 IAM 権限

個人アカウントなので、**運用は AdministratorAccess で進める**。
権限を絞り込むのは社内移管時の宿題（`docs/aws_migration_plan.md` 改訂タスク）。

### 5.3 SSM Parameter Store にシークレット投入

```powershell
aws ssm put-parameter `
  --name "/logi-intel/dev/ESTAT_APP_ID" `
  --value "<実際のキー>" `
  --type "SecureString"

aws ssm put-parameter `
  --name "/logi-intel/dev/CORP_NUMBER_APP_ID" `
  --value "<実際のキー>" `
  --type "SecureString"
```

### 5.4 Terraform 初期化と適用

```powershell
cd infra
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

実行内容（予定）:
- S3 バケット作成（web / outputs / profiles）
- Lambda 関数作成（zip / Web Adapter Layer 添付）
- Lambda Function URL 発行
- CloudFront ディストリビューション作成（S3 origin + Lambda Function URL origin）
- IAM ロール（Lambda → S3 Read/Write、SSM Read）

### 5.5 Lambda 関数コードのアップロード

```powershell
# zip パッケージ作成
uv export --no-hashes --no-dev > lambda/requirements.txt
pip install -r lambda/requirements.txt -t lambda/build/
cp -r core api lambda/build/
cd lambda/build && Compress-Archive -Path * -DestinationPath ../function.zip -Force

# Lambda デプロイ
aws lambda update-function-code `
  --function-name logi-intel-api-dev `
  --zip-file fileb://lambda/function.zip
```

### 5.6 Next.js ビルド + S3 アップロード

```powershell
cd web
npm run build     # output: "export" で out/ に静的ファイル生成
aws s3 sync out/ s3://logi-intel-web-dev-<アカウントID>/ --delete
aws cloudfront create-invalidation `
  --distribution-id <CloudFront ID> `
  --paths "/*"
```

### 5.7 動作確認

```powershell
# CloudFront URL に curl
curl https://<distribution-id>.cloudfront.net/health
# → {"status": "ok", "service": "logi-intel-dashboard-api"}

# 計画書ドラフト生成（重い処理。Lambda タイムアウト 5 分を確認）
curl -X POST https://<distribution-id>.cloudfront.net/api/v1/clo/plan-draft/sample_mfg_01
```

---

## 6. 認証（PoC では未実装）

社内レビューでは CloudFront のデフォルト URL（`*.cloudfront.net`）を共有する程度で
十分とする。以下は将来検討:

- IP allowlist（社内固定 IP がわかれば AWS WAF or CloudFront Functions で）
- Basic 認証（CloudFront Functions で実装可・無料枠あり）
- Cognito（社内 SSO 連携・MAU 50,000 まで無料）

---

## 7. 段階的カットオーバー

1. 健一個人 AWS で dev 環境を 1 週間運用
2. 営業 1 名に β 参加してもらい URL を共有
3. フィードバック反映後、社内全展開
4. 利用が定着したら社内 AWS アカウントへ Terraform で移行

---

## 8. 「やらないこと」リスト（PoC 制約）

- ❌ ECS Fargate（コスト過剰）
- ❌ ALB（$18/月の固定費・PoC 不要）
- ❌ ElastiCache Redis（$13/月・SQLite で十分・PoC ではキャッシュ無くても可）
- ❌ Secrets Manager（Parameter Store SecureString で代替）
- ❌ API Gateway（Lambda Function URL で代替）
- ❌ Cognito（PoC では認証なし）
- ❌ マルチテナント設計（健一個人 + micware 社内のみ）
- ❌ Public 公開（社内レビュー用 URL 共有のみ）

---

## 9. 進捗状況

| Step | 内容 | 状態 |
|------|------|------|
| 1 | コード改修（S3 切替・Lambda Web Adapter エントリ） | ⏳ 未着手 |
| 2 | Terraform IaC 整備 | ⏳ 未着手 |
| 3 | SSM Parameter Store にシークレット投入 | ⏳ 健一作業 |
| 4 | `terraform apply` 実行 | ⏳ 未着手 |
| 5 | Lambda zip デプロイ + S3 同期 | ⏳ 未着手 |
| 6 | CloudFront URL での動作確認 | ⏳ 未着手 |

---

## 10. 参考資料

- [AWS Lambda Web Adapter（GitHub）](https://github.com/awslabs/aws-lambda-web-adapter)
- [Lambda Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html)
- [Next.js 静的エクスポート](https://nextjs.org/docs/app/building-your-application/deploying/static-exports)
- [SSM Parameter Store SecureString](https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-secure-strings.html)
