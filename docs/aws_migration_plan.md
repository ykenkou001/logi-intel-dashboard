# AWS 移行計画（フェーズ4.0 後半）

**責任範囲**: ローカル稼働 → AWS 上常駐サーバへの移行手順とリスク管理。
コードレベルの設計詳細は [docs/architecture.md](architecture.md) を参照。

> ⚠️ AWS 移行は**コストと運用負担を伴う実環境への変更**である。
> 健一の明示的な承認なしに `terraform apply` / `aws ecs update-service` 等の
> 実行はしない。本ドキュメントは計画と前準備に留める。

---

## 1. 移行の背景

ローカル稼働（Claude Desktop が stdio で子プロセスとして起動）は開発者本人しか
使えない。社内全員（営業・企画・経営層）が CLO 計画策定支援を使うには、
HTTPS 経由でアクセスできる常駐サーバが必要。

**達成したいゴール**:
- 営業・企画担当が VPN 内から URL 一発でアクセスできる
- 自社プロフィール Excel をブラウザからアップロードして計画書 4 種を生成・DL できる
- 社内 SSO（Cognito か Microsoft Entra ID）で利用者を認証できる
- API キーや個社データを Secrets Manager / KMS で適切に保護できる

---

## 2. ローカル ↔ AWS の差分（再掲）

| 項目 | ローカル（現在） | AWS（移行後） |
|------|----------------|----------------|
| 起動方式 | stdio MCP / `uv run uvicorn` | ECS Fargate（タスク常駐） |
| 通信方式 | stdio / HTTP localhost | HTTPS via CloudFront → ALB |
| キャッシュ | `core/cache.py` SQLite | ElastiCache (Redis 7) |
| API キー管理 | `.env` ファイル | AWS Secrets Manager |
| 自社データ JSON | `outputs/profiles/` ローカル | S3 バケット（個社用 prefix 分離） |
| 成果物配信 | ファイルパス返却 | プレサインド URL（5分有効） |
| 接続元 | 開発者 PC | 社内 VPN / Cognito 認証 |

---

## 3. 移行ステップ（推奨順）

### Step 1: コンテナ化 — ✅ 着手済み（2026-05-03）

- [x] `Dockerfile`（マルチステージ・非 root 実行・healthcheck 統合）
- [x] `.dockerignore`（venv / node_modules / outputs / .env を除外）
- [x] `docker-compose.yml`（Redis サービス含むローカル統合検証用）
- [ ] `docker build` 動作確認（健一の Docker Desktop で実行予定）
- [ ] `docker compose up` で API + Redis が起動し `/health` が 200 を返すことを確認
- [ ] x86_64 / linux ビルド確認（ECS Fargate は arm64 か x86_64 を選択）

### Step 2: キャッシュ層の差替準備（コードのみ・AWS 接続なし）

`core/cache.py` を Backend 抽象化して SQLite / Redis を切替可能にする。

- [ ] `core/cache_backend.py` 新設 — `CacheBackend` プロトコル（get / store / get_stale）
- [ ] `core/cache_sqlite.py` — 既存実装をクラス化
- [ ] `core/cache_redis.py` — `redis-py` で同インターフェースを実装
- [ ] `core/cache.py` — 環境変数 `LOGI_CACHE_BACKEND={sqlite|redis}` でディスパッチ
- [ ] `LOGI_REDIS_URL` 必須化（redis 選択時）
- [ ] テスト: `tests/core/test_cache_redis.py`（fakeredis でユニットテスト）

> 設計原則: 現行の関数 API（`get/store/get_stale/insert_fuel_price_record/get_fuel_price_history`）は維持する。
> 既存の MCP / FastAPI からの import 経路は無変更で済むこと。

### Step 3: シークレット管理の差替準備

- [ ] `core/secrets.py` 新設 — env / Secrets Manager から取得する薄いラッパー
- [ ] `core/clients/base.py` 等で `os.environ.get` を直接読まず `secrets.get(name)` 経由
- [ ] `LOGI_SECRETS_BACKEND={env|aws}` で切替

### Step 4: 自社プロフィール永続化の S3 化

- [ ] `core/io/company_store.py` を S3 化
- [ ] `LOGI_COMPANY_STORE_BACKEND={local|s3}` でディスパッチ
- [ ] バケット命名: `logi-intel-{env}-profiles`、prefix で個社分離（`<company_id>/profile.json`）
- [ ] サーバサイド暗号化（SSE-S3 か KMS）必須

### Step 5: Infrastructure as Code（IaC）

選択肢:
- **Terraform**（推奨。社内 SRE 標準があれば従う）
- AWS CDK（TypeScript）
- AWS SAM / Serverless Framework

最低限必要なリソース:
- VPC（2 AZ・private subnet）
- ECR リポジトリ（`logi-intel-api`）
- ECS Fargate サービス（task: api / web / 必要なら mcp）
- ALB（社内 VPN 接続のみ許可するセキュリティグループ）
- ElastiCache Redis（cluster mode disabled・1 シャード・dev は cache.t4g.micro）
- S3 バケット（プロファイル / 成果物・バージョニング有効・ライフサイクル設定）
- Secrets Manager（API キー・データベース認証）
- CloudWatch Logs（FastAPI / Next.js 両方）
- Cognito User Pool（社内 SSO 連携）

> 推定運用コスト（dev 環境・月）:
> ECS Fargate (0.25 vCPU / 0.5GB × 1 task): ~$10
> ElastiCache cache.t4g.micro: ~$13
> ALB: ~$18
> S3 / CloudWatch: ~$5
> **合計: 約 $50/月（本番環境はこの 2-3 倍想定）**

### Step 6: フロントエンドのデプロイ

選択肢:
- **CloudFront + S3 静的エクスポート**（軽量・SSR 不要なら推奨）
  - `next build && next export` で静的化
  - S3 にアップロード、CloudFront から配信
- AWS Lambda + Lambda@Edge（SSR 必要時）
- Vercel（社外サービス。社内データの安全性確認が必要）

現状の Next.js は静的化可能な構成（API 呼び出しは全てクライアントサイド `fetch`）。
**CloudFront + S3 を第一候補とする**。

### Step 7: MCP サーバーの HTTP/SSE モード化

- [ ] `mcp_server/server.py` で `mcp.run()` を HTTP/SSE モードに変更（FastMCP 対応済み）
- [ ] 認証層追加（API Key / Cognito JWT）
- [ ] Claude Desktop 設定のサンプル更新（`localhost` → AWS エンドポイント）

### Step 8: 段階的カットオーバー

1. 開発者本人で AWS dev 環境を 1 週間運用
2. 営業 1 名にβ参加してもらう
3. フィードバック反映後、社内全展開

---

## 4. 移行前のセキュリティ・コンプライアンス確認

- [ ] 個社データを S3 に置くことの社内承認（情シス・法務）
- [ ] Cognito or Entra ID 連携の認証フロー設計
- [ ] CloudFront / ALB の WAF ルール（OWASP Top 10）
- [ ] バックアップ / DR 方針（プロファイル JSON の世代管理）
- [ ] ログ保管ポリシー（CloudWatch Logs Insights / S3 アーカイブ）
- [ ] e-Stat / 国税庁 API の **AWS からの呼び出し可否を再確認**（IP 制限の有無）

---

## 5. 「やらないこと」リスト

- ❌ マルチテナント設計（当面は micware 社内専用）
- ❌ Public 公開（社内 VPN 内のみ）
- ❌ 実運用前の terraform apply（AWS リソース課金開始の意思決定は健一）
- ❌ 個社プロフィール JSON のリージョン跨ぎレプリケーション（要件外）

---

## 6. 進捗状況

| Step | 内容 | 状態 |
|------|------|------|
| 1 | Dockerfile + docker-compose | ✅ 着手済み（2026-05-03） |
| 2 | キャッシュ層 Backend 抽象化 | ⏳ 未着手 |
| 3 | シークレット管理ラッパー | ⏳ 未着手 |
| 4 | 自社プロフィール S3 化 | ⏳ 未着手 |
| 5 | IaC（Terraform）整備 | ⏳ 未着手 |
| 6 | Next.js CloudFront/S3 デプロイ | ⏳ 未着手 |
| 7 | MCP HTTP/SSE モード化 | ⏳ 未着手 |
| 8 | 段階的カットオーバー | ⏳ 未着手 |

---

## 7. 参考資料

- [AWS Fargate ユーザガイド](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [ElastiCache for Redis ユーザガイド](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/WhatIs.html)
- [Secrets Manager 開発者ガイド](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [Next.js 静的エクスポート](https://nextjs.org/docs/app/building-your-application/deploying/static-exports)
