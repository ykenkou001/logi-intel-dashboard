# Logi-Intel Dashboard Web (Next.js)

CLO 中長期計画策定・運用支援の Web ダッシュボード。FastAPI バックエンド（`api/`）の
クライアントとして動作する。

## 前提

- Node.js 22 以上 / npm 10 以上
- バックエンド（FastAPI）が `http://localhost:8000` で起動していること

## セットアップ

```bash
cd web
npm install
cp .env.local.example .env.local  # 必要に応じて API URL を変更
```

### 起動（必読）

**`npm run dev` を直接叩かず、リポジトリルートのヘルパースクリプトを使う。**

```powershell
# リポジトリルートから
pwsh scripts/dev_api.ps1            # FastAPI :8000（先に起動）
pwsh scripts/dev_web.ps1            # Next.js :3000（別シェルで）
```

http://localhost:3000 でダッシュボードが開く。

### なぜヘルパースクリプト経由か

`dev_web.ps1` は **既存の `next dev` を起動時に kill** したうえで、
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` を環境変数で固定して
起動する。素の `npm run dev` だと:

- 過去に立てた古いプロセスが残り、ポート競合 / 古いビルドが配信される
- 環境変数が未設定だと `lib/api.ts` のデフォルト `""` で同一 origin を叩き、
  Next.js dev サーバーは `/api/v1/*` を解決できないため 404 になる

詳細経緯は [../CLAUDE.md §6.5](../CLAUDE.md) を参照。

### 直接 npm run dev を使う場合（非推奨）

どうしても素で起動したいときは、必ず環境変数を明示する:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

## ディレクトリ構成

```
web/
├── app/                                # Next.js App Router
│   ├── layout.tsx                      # 共通レイアウト
│   ├── page.tsx                        # トップページ（機能カード一覧）
│   ├── globals.css                     # Tailwind + 日本語フォント設定
│   └── dashboard/
│       ├── macro/page.tsx              # 都道府県マクロ概況
│       ├── benchmark/page.tsx          # 業界ベンチマーク
│       ├── driver-gap/page.tsx         # ドライバー需給ギャップ
│       ├── playbook/page.tsx           # 施策プレイブック検索
│       ├── measure-eval/page.tsx       # 施策評価（Top 3 推薦）
│       ├── scenario-sim/page.tsx       # シナリオシミュレーション
│       ├── company/page.tsx            # 自社プロフィール入力フォーム
│       └── plan-draft/page.tsx         # 計画書ドラフト統合生成
├── components/
│   └── ToolResponseDisplay.tsx         # ToolResponse 共通表示 + ErrorBanner
├── lib/
│   ├── api.ts                          # 型付き API クライアント（FastAPI へ）
│   └── constants.ts                    # 都道府県・JSIC・施策タイプ等の定数
├── tailwind.config.ts                  # Logi-Intel CLO Report のデザイントークン
├── tsconfig.json
├── next.config.ts                      # /api/proxy/* → FastAPI rewrites
└── package.json
```

## 実装方針

- **バックエンドは FastAPI** — `lib/api.ts` の `ToolResponse` 型は
  `api/schemas/responses.py` の Pydantic モデルと完全一致させる
- **デザインは Logi-Intel CLO Report ベース** — `docs/ppt_design.md` のトークンを
  Tailwind の primary / accent / muted に反映済み
- **App Router** — Next.js 15 の標準。Server Component と Client Component を
  使い分け、データ取得は基本的に Server Component で
- **成果物ダウンロード** — `fileDownloadUrl(path)` で相対パスを `/api/v1/files/`
  経由の絶対 URL に変換

## 実装済み画面

| ルート | 機能 | 状態 |
|--------|------|------|
| `/` | トップ（機能カード一覧） | ✅ |
| `/dashboard/macro` | 都道府県マクロ概況 | ✅ |
| `/dashboard/benchmark` | 業界ベンチマーク | ✅ |
| `/dashboard/driver-gap` | ドライバー需給ギャップ | ✅ |
| `/dashboard/playbook` | 施策プレイブック検索 | ✅ |
| `/dashboard/measure-eval` | 施策評価（Top 3 推薦） | ✅ |
| `/dashboard/scenario-sim` | シナリオシミュレーション | ✅ |
| `/dashboard/company` | 自社プロフィール入力フォーム | ✅ |
| `/dashboard/plan-draft` | 計画書ドラフト統合生成 | ✅ |

## 環境変数

| 変数 | デフォルト | 用途 |
|------|----------|------|
| `NEXT_PUBLIC_API_BASE_URL` | `""`（同一 origin） | FastAPI バックエンドの URL。本番（CloudFront 同居）はそのまま空文字、ローカル開発では `http://localhost:8000` を `dev_web.ps1` 経由で注入 |

> 旧バージョンではデフォルトが `http://localhost:8000` だったが、本番ビルドが
> 意図せず localhost を叩く事故防止のため `""` に変更（2026-05-05）。
> 経緯は [../CLAUDE.md §6.5](../CLAUDE.md) を参照。

## ビルド・型チェック

```bash
npm run lint        # ESLint
npm run type-check  # tsc --noEmit
npm run build       # 本番ビルド
```

## デプロイ（フェーズ4 後半）

AWS 移行時は次のいずれかを想定:

- **CloudFront + S3 静的エクスポート**（軽量。SSR 不要なら推奨）
- **Vercel 互換 Lambda + ECR**（SSR 必要時）

詳細は `docs/architecture.md` の AWS 移行計画セクション参照。
