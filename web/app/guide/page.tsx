import fs from "node:fs/promises";
import path from "node:path";
import Link from "next/link";
import { renderMarkdown } from "@/lib/markdown";

export const metadata = {
  title: "機能別利用ガイド | Logi-Intel Dashboard",
  description: "Logi-Intel Dashboard の各機能の使い方と推奨利用順を確認できます。",
};

export default async function GuidePage() {
  const guidePath = path.join(
    process.cwd(),
    "..",
    "docs",
    "dashboard_feature_guide.md"
  );
  const markdown = await fs.readFile(guidePath, "utf8");

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-blue-100 bg-white p-6 shadow-sm">
        <div
          className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#2E73AC]"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          Guide
        </div>
        <h1
          className="text-2xl font-bold text-gray-950 md:text-3xl"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          機能別利用ガイド
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-gray-600">
          初めて使う人が、どの機能で何ができるかを理解するためのガイドです。
          目的別のおすすめ画面、画面ごとの入力・出力、結果の読み方を確認できます。
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link
            href="/"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold text-gray-700 hover:border-[#2E73AC] hover:text-[#1F4E79]"
          >
            ホームへ戻る
          </Link>
          <Link
            href="/dashboard/company"
            className="rounded-lg bg-[#1F4E79] px-3 py-2 text-sm font-semibold text-white hover:bg-[#173C5C]"
          >
            自社データ入力へ
          </Link>
          <Link
            href="/dashboard/plan-draft"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold text-gray-700 hover:border-[#2E73AC] hover:text-[#1F4E79]"
          >
            計画書生成へ
          </Link>
        </div>
      </section>

      <section
        aria-labelledby="guide-media-heading"
        className="rounded-xl border border-blue-100 bg-white p-6 shadow-sm"
      >
        <div
          className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#2E73AC]"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          Media
        </div>
        <h2
          id="guide-media-heading"
          className="text-xl font-bold text-gray-950 md:text-2xl"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          動画と PDF で全体像を掴む
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-gray-600">
          まず 15 秒の紹介動画でアプリの全体像を掴み、詳しくは約 5 分の解説動画とスライド PDF（CLO Command Center）を確認してください。
          下のテキストガイドは、画面ごとの詳細な使い方を参照する用途に向いています。
        </p>

        <div className="mt-5 grid gap-4 rounded-lg border border-gray-100 bg-gray-50 p-4 md:grid-cols-[minmax(0,420px)_minmax(0,1fr)] md:items-center">
          <video
            data-testid="guide-promo-video"
            controls
            muted
            playsInline
            preload="metadata"
            poster="/promo/logi-intel-promo-15s-poster.jpg"
            className="w-full aspect-video rounded-lg border border-gray-200 bg-[#050b16]"
            src="/promo/logi-intel-promo-15s.mp4"
          >
            お使いのブラウザは video タグに対応していません。
            <a
              href="/promo/logi-intel-promo-15s.mp4"
              className="text-[#2E73AC] underline"
            >
              動画ファイルをダウンロード
            </a>
            してご覧ください。
          </video>
          <div>
            <h3 className="text-base font-bold text-gray-900">
              まず 15 秒で全体像: Logi-Intel とは
            </h3>
            <p className="mt-2 text-sm leading-7 text-gray-600">
              「何をやれば一番効くか」に答える 3 つの画面（デイリーコックピット / 施策評価 / 成果物ダウンロード）を 15 秒で紹介します。
              画面はサンプル企業のデータです。
            </p>
            <p className="mt-2 text-xs text-gray-500">再生時間 15 秒 / 約 3.4 MB / 無音</p>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div>
            <h3 className="mb-2 text-base font-bold text-gray-900">
              解説動画: CLO 戦略とダッシュボード活用
            </h3>
            <video
              data-testid="guide-overview-video"
              controls
              preload="metadata"
              className="w-full rounded-lg border border-gray-200 bg-black"
              src="/guide/clo-strategy-overview.mp4"
            >
              お使いのブラウザは video タグに対応していません。
              <a
                href="/guide/clo-strategy-overview.mp4"
                className="text-[#2E73AC] underline"
              >
                動画ファイルをダウンロード
              </a>
              してご覧ください。
            </video>
            <p className="mt-2 text-xs text-gray-500">
              再生時間 約 5 分 / 約 40 MB（モバイル回線では Wi-Fi 環境を推奨）
            </p>
          </div>

          <div>
            <h3 className="mb-2 text-base font-bold text-gray-900">
              スライド PDF: CLO Command Center
            </h3>
            <iframe
              data-testid="guide-overview-pdf"
              title="CLO Command Center スライド PDF"
              src="/guide/clo-command-center.pdf"
              className="h-[480px] w-full rounded-lg border border-gray-200 bg-white"
            />
            <div className="mt-2 flex flex-wrap gap-2">
              <a
                href="/guide/clo-command-center.pdf"
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold text-gray-700 hover:border-[#2E73AC] hover:text-[#1F4E79]"
              >
                別タブで開く
              </a>
              <a
                href="/guide/clo-command-center.pdf"
                download
                className="rounded-lg bg-[#1F4E79] px-3 py-2 text-sm font-semibold text-white hover:bg-[#173C5C]"
              >
                PDF をダウンロード
              </a>
            </div>
            <p className="mt-2 text-xs text-gray-500">約 15 MB</p>
          </div>
        </div>
      </section>

      <article className="rounded-xl border border-gray-100 bg-white px-5 py-6 shadow-sm md:px-8 md:py-8">
        {renderMarkdown(markdown)}
      </article>
    </div>
  );
}
