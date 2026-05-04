import type { NextConfig } from "next";

/**
 * 静的エクスポート (`output: "export"`) を既定にしている。
 *
 * - 本番（CloudFront + S3）: `out/` を S3 にアップロード、CloudFront から配信。
 * - ローカル開発:
 *   - `LOGI_NEXT_OUTPUT=export npm run build && npx serve out` で本番同等を確認、
 *   - もしくは `npm run dev` で従来の SSR 開発サーバー（output 設定は dev では無視される）。
 *
 * API は別 origin の FastAPI を `NEXT_PUBLIC_API_BASE_URL` で叩く。
 * 本番（CloudFront 同居）では `""` を指定して同一 origin の `/api/v1/...` を使う。
 */
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,           // S3 静的配信で `/dashboard/macro` → `/dashboard/macro/index.html`
  images: { unoptimized: true }, // S3 静的配信では Next.js Image Optimizer を使えない
};

export default nextConfig;
