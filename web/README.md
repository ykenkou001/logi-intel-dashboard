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
npm run dev
```

http://localhost:3000 でダッシュボードが開く。

## ディレクトリ構成

```
web/
├── app/                      # Next.js App Router
│   ├── layout.tsx            # 共通レイアウト
│   ├── page.tsx              # トップページ（機能カード一覧）
│   ├── globals.css           # Tailwind + 日本語フォント設定
│   └── dashboard/
│       ├── macro/page.tsx          # 都道府県マクロ概況
│       └── plan-draft/page.tsx     # 計画書ドラフト統合生成
├── lib/
│   └── api.ts                # 型付き API クライアント（FastAPI へ）
├── tailwind.config.ts        # Logi-Intel CLO Report のデザイントークン
├── tsconfig.json
├── next.config.ts            # /api/proxy/* → FastAPI rewrites
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
| `/dashboard/plan-draft` | 計画書ドラフト統合生成 | ✅ |
| `/dashboard/benchmark` | 業界ベンチマーク | ⏳ 実装予定 |
| `/dashboard/driver-gap` | ドライバー需給ギャップ | ⏳ 実装予定 |
| `/dashboard/playbook` | 施策プレイブック検索 | ⏳ 実装予定 |
| `/dashboard/measure-eval` | 施策評価（Top 3） | ⏳ 実装予定 |
| `/dashboard/scenario-sim` | シナリオシミュレーション | ⏳ 実装予定 |
| `/dashboard/company` | 自社プロフィール入力フォーム | ⏳ 実装予定 |

## 環境変数

| 変数 | デフォルト | 用途 |
|------|----------|------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | FastAPI バックエンドの URL |

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
