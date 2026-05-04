# 次セッションへの引継ぎ（2026-05-05 時点）

## ⚠️ 0. 最初に確認 — apply 待ちの差分があるか

直前セッション末で **CloudFront Function（directory URL → index.html 書換）** を追加したが、
健一の側で `terraform apply` が実行されたかどうか確認すること。

```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard\infra
terraform plan -var="env=dev"
# "No changes" ならapply済。差分が出たら未apply。
```

未 apply の場合は次を実行：
```powershell
terraform apply plan.tfplan
# 5〜10 分（CloudFront 配信反映）
```

apply 後の動作確認:
```powershell
curl -s -o NUL -w "HTTP=%%{http_code}`n" "https://d1zei8qivkf3cr.cloudfront.net/dashboard/macro/"
# HTTP=200 が期待値（apply 前は AccessDenied XML が返る）
```

### 直前セッションで発見・対応した 2 件のバグ（記録）

1. **`Failed to construct 'URL': Invalid URL`** （フロントエンド）
   - 原因: `new URL("/api/v1/...")` は base なし相対パスを受け付けない。`NEXT_PUBLIC_API_BASE_URL=""` の本番ビルドで全 fetch 失敗
   - 対応: `web/lib/api.ts` の `request()` を文字列結合 + URLSearchParams に変更（コミット `854efdf`）。デプロイ済（S3 同期 + CloudFront 無効化済）

2. **`/dashboard/<page>/` で AccessDenied XML**（インフラ）
   - 原因: S3 はディレクトリ概念がないため `web/dashboard/macro/` の GetObject が失敗。実体は `web/dashboard/macro/index.html`
   - 対応: CloudFront Function `rewrite-index` を追加（コミット `e6d3574`）。**未 apply の可能性あり** — 上記手順で確認

---

## 1. 現在地

**フェーズ 4.0 完了** — AWS PoC デプロイ稼働中。社内レビューに使える状態。

| 項目 | 値 |
|------|----|
| 社内レビュー URL | https://d1zei8qivkf3cr.cloudfront.net/ |
| API Gateway 直叩き | https://fgwicoog66.execute-api.ap-northeast-1.amazonaws.com |
| AWS アカウント | 538099532416（健一個人・AdministratorAccess） |
| Region | ap-northeast-1 |
| Lambda 関数名 | `logi-intel-dev-api` |
| CloudFront ID | `E3F7LKFZVFU04Q` |
| API Gateway ID | `fgwicoog66` |
| S3 バケット | `logi-intel-dev-7m2lqc` |
| Terraform state | `infra/terraform.tfstate`（ローカル・gitignored） |

## 2. 動作確認済み

| 経路 | 結果 |
|------|------|
| `GET /` （Web トップ） | 200 / 全 8 画面リンク表示 |
| `GET /health` | 200 `{"status":"ok"}` |
| `GET /api/v1/company/samples` | 200 / サンプル3社 JSON |
| `GET /api/v1/clo/playbook` | 200 / 標準10施策 |
| `POST /api/v1/clo/plan-draft/sample_mfg_01` | 200 / PPT/Word/Excel/Markdown 生成（30〜60秒）|
| `GET /api/v1/files/markdown/...` | 302 → S3 プレサインド URL → 19KB DL OK |

## 3. 残課題（優先度順）

### 🔴 必須（次セッション最優先）

#### 3.1 e-Stat API キーが Lambda 上で読めるか確認
- SSM Parameter Store: `/logi-intel/dev/ESTAT_APP_ID` に投入済
- Lambda 環境変数: `LOGI_SECRETS_BACKEND=ssm` + `LOGI_SSM_PREFIX=/logi-intel/dev`
- `core/secrets.py` の `get_secret("ESTAT_APP_ID")` が SSM から取得して `os.environ` に反映する仕組み
- **未検証**: macro / benchmark / driver-gap のいずれも e-Stat 呼出が動作するか

検証手順：
```powershell
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/macro/overview?prefecture=東京都"
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/benchmark?jsic_code=5411&prefecture=東京都&revenue_jpy=5000000000"
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/driver-gap?prefecture=東京都"
```

`{"detail":"e-Stat API error..."}` が返れば **`core/clients/estat.py` のクライアント初期化が `os.environ.get("ESTAT_APP_ID")` を直接読んでいる**箇所が原因。`core.secrets.get_secret()` 経由に書き換える必要あり。

CloudWatch Logs 確認：
```powershell
aws logs tail /aws/lambda/logi-intel-dev-api --follow --region ap-northeast-1
```

#### 3.2 sample_chain_01 / sample_wholesale_01 の plan-draft 動作確認

```powershell
curl.exe -X POST "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/plan-draft/sample_chain_01"
curl.exe -X POST "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/plan-draft/sample_wholesale_01"
```

連鎖化事業者（chain_01）は荷役等項目が省略されるなど挙動が異なるため、念のため動作確認。

### 🟡 高優先（社内デモ前）

#### 3.3 Codex 指摘の PPT 視覚化強化
PoC は数字が出るが PPT は **charts/tables/pictures = 0** で「文章を整えたスライド」状態。社内デモで「資料っぽさ」を出すには：

優先 3 枚（推定 1〜2 日）：
1. **施策ポートフォリオ図**（横軸 営業利益インパクト × 縦軸 CO2 削減 × バブル投資額・色 難易度）
2. **重複控除後ウォーターフォール**（合算最大 → 重複控除 → 標準シナリオ → 保守シナリオ）
3. **2030 年 KPI ロードマップ**（積載率 38→50% / CO2 ▲23.4% の四半期マイルストーン）

実装ファイル：`core/export/ppt_writer.py` に追加（python-pptx で matplotlib 画像を埋込）

### 🟢 中優先

#### 3.4 ホーム画面のローカル開発手順を AWS 経路にも対応
[web/app/page.tsx](web/app/page.tsx) のフッター部分が「`uv run uvicorn ... --port 8000`」のままなので、本番デプロイ表示と整合性取る（簡易タスク）。

#### 3.5 認証導入（PoC 卒業後）
- 現状: 認証なし（CloudFront URL を知ってる人なら誰でもアクセス可）
- 案: CloudFront Functions で Basic 認証 / Cognito User Pool / IP allowlist
- PoC 段階では不要だが社内全展開前に必要

### ⚪ 低優先（フェーズ 4.5）

- 計画書ドラフト docx の文章テンプレート化（公式記載見本集 MD 10 ファイル取込）
- 実 KPI 計測フレーム（計画策定時の測定方法・頻度・閾値埋込）
- CLO スタイル別重み付け（攻め / 守り / 環境重視 / 効率重視）

## 4. アーキテクチャ概要（記事化用素材）

```
[ブラウザ] ─HTTPS─→ [CloudFront]
                       │
                       ├─ /            ──→ [S3: web/ プレフィックス] (Next.js 静的)
                       │                       OAC で署名
                       │
                       └─ /api/* /health /docs /openapi.json
                                          ──→ [API Gateway HTTP API]
                                                 │ AWS_PROXY 統合
                                                 ↓
                                           [Lambda: Python 3.12 + Mangum + FastAPI]
                                                 │
                                                 ├─ /tmp/outputs ──→ [S3: outputs/ プレフィックス] (PPT/Word/Excel/Markdown)
                                                 ├─ /tmp/profiles → [S3: profiles/ プレフィックス] (CompanyProfile JSON)
                                                 └─ secrets        ──→ [SSM Parameter Store SecureString]
                                                                          /logi-intel/dev/ESTAT_APP_ID
```

### Zenn 記事ネタ
1. **「FastAPI を Mangum で Lambda に載せて API Gateway HTTP API でフロント、月 $3 で社内 PoC」**（実話そのまま）
2. **「Lambda OAC 採用を試みて 403 沼にハマった話」**（途中の試行錯誤・最終的に API Gateway HTTP API に逃げた経緯）
3. **「MCP × REST 同じビジネスロジックで 2 経路 — `core/` を Claude Desktop と Web ダッシュボードで共有」**（差別化ポイント）
4. **「物流効率化法 CLO 業務 × LLM ツール — 法令準拠ドラフト生成のドメイン設計」**（業界向け）

## 5. 次セッション開始時の手順

```powershell
# 1. プロジェクト確認
cd c:\Users\ykenk\repos\logi-intel-dashboard
git log --oneline -5
git status

# 2. ローカル環境確認
uv run pytest --tb=short -q       # 422 件 pass を確認
cd web && npm run type-check      # type-check pass を確認

# 3. 残課題 3.1 から着手
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/macro/overview?prefecture=東京都"
# 失敗するなら CloudWatch Logs を見る
aws logs tail /aws/lambda/logi-intel-dev-api --since 5m --region ap-northeast-1
```

## 6. AWS リソース管理

### Lambda zip 再ビルド & 再デプロイ
```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard

# 1. lambda/build/ にコード再配置
Remove-Item -Recurse -Force lambda\build\api, lambda\build\core -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force core lambda\build\
Copy-Item -Recurse -Force api lambda\build\
Get-ChildItem lambda\build -Recurse -Directory -Force | Where-Object { $_.Name -eq "__pycache__" -or $_.Name -like "*.dist-info" } | Remove-Item -Recurse -Force

# 2. zip 圧縮
Remove-Item lambda\function.zip -ErrorAction SilentlyContinue
Compress-Archive -Path lambda\build\* -DestinationPath lambda\function.zip -CompressionLevel Optimal

# 3. アップロード
aws lambda update-function-code --function-name logi-intel-dev-api --zip-file fileb://lambda/function.zip --region ap-northeast-1
```

### Next.js 再ビルド & S3 再同期
```powershell
cd web
$env:NEXT_PUBLIC_API_BASE_URL = ""
npm run build
aws s3 sync out/ s3://logi-intel-dev-7m2lqc/web/ --delete --region ap-northeast-1
aws cloudfront create-invalidation --distribution-id E3F7LKFZVFU04Q --paths "/*" --region ap-northeast-1
```

### AWS リソース全削除（PoC 終了時）
```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard\infra
terraform destroy -var="env=dev"

# SSM パラメータも個別に削除（terraform 管理外のため）
aws ssm delete-parameter --name /logi-intel/dev/ESTAT_APP_ID --region ap-northeast-1
```

## 7. 設計上の決定（記録）

### Lambda Function URL → API Gateway HTTP API へ転換
PoC で次の 2 つを試したが両方 403：
1. Function URL（NONE auth）+ public resource policy
2. Function URL（AWS_IAM auth）+ CloudFront OAC + sigv4 署名

**結論**: API Gateway HTTP API + Lambda Proxy 統合に切替。コスト差 <$0.01/月で許容。
原因は AWS の Block Public Access 系か OAC の sigv4 経路の問題と推測されるが、PoC 期限優先で深追いせず。

### Docker は不要と判断
- 当初 ECS Fargate 想定で Dockerfile を準備したが、Lambda zip で十分（45MB）。
- Dockerfile / docker-compose.yml / .dockerignore は撤去済（コミット 9d52337）。

### `core/storage.py` + `core/secrets.py` の抽象化
- ローカル開発（既存挙動）を完全互換のまま AWS 切替対応
- 環境変数 `LOGI_STORAGE_BACKEND={local|s3}` / `LOGI_SECRETS_BACKEND={env|ssm}` で切替
- Lambda は両方 S3/SSM、ローカルは local/env のまま

## 8. 主要ファイルマップ

```
infra/
├── main.tf                       # Terraform IaC（S3+Lambda+API GW+CloudFront+IAM）
├── README.md                     # デプロイ手順
└── terraform.tfstate             # ローカル state（gitignored）

lambda/
├── README.md                     # zip ビルド手順
├── requirements-lambda.txt       # Lambda 専用最小依存リスト
└── function.zip                  # ビルド成果物（gitignored・43MB）

scripts/
└── put-ssm-secrets.ps1           # .env から SSM Parameter Store へ投入

core/
├── storage.py                    # LocalStorage / S3Storage 抽象（新規）
├── secrets.py                    # env / SSM 抽象（新規）
└── macro/
    └── sources.py                # macro fetch ヘルパー切り出し（fastmcp 非依存）

api/
└── lambda_handler.py             # Mangum で FastAPI を Lambda 化

docs/
├── aws_migration_plan.md         # AWS 移行計画書（PoC 最安構成）
└── roadmap.md                    # フェーズ全体（フェーズ4.0 完了マーク済）
```

---

最終更新: 2026-05-05（PoC デプロイ完了直後）
