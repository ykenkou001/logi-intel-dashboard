import type { Metadata } from "next";
import { Noto_Serif_JP, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const notoSerif = Noto_Serif_JP({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-serif",
  display: "swap",
});

const ibmMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Logi-Intel Dashboard",
  description: "CLO 中長期計画策定・運用支援ダッシュボード",
};

const NAV = [
  { href: "/guide", label: "ガイド" },
  { href: "/dashboard/cockpit", label: "コックピット" },
  { href: "/dashboard/industry-package", label: "業種別パッケージ" },
  { href: "/dashboard/standardization", label: "標準化スコア" },
  { href: "/dashboard/waste-traps", label: "罠スコア" },
  { href: "/dashboard/measure-eval", label: "施策評価" },
  { href: "/dashboard/scenario-sim", label: "シナリオ" },
  { href: "/dashboard/plan-draft", label: "計画書生成" },
  { href: "/dashboard/company", label: "自社情報" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ja">
      <body
        className={`${notoSerif.variable} ${ibmMono.variable} bg-slate-50 text-gray-900 min-h-screen`}
      >
        <header className="bg-[#1F4E79] shadow-lg">
          <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-white/15 border border-white/25 flex items-center justify-center">
                <span
                  className="text-[11px] font-bold text-white"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  LI
                </span>
              </div>
              <div>
                <div
                  className="text-white font-bold text-base leading-tight"
                  style={{ fontFamily: "var(--font-serif)" }}
                >
                  Logi-Intel
                </div>
                <div className="text-blue-200 text-[10px] leading-tight">
                  CLO 計画策定支援
                </div>
              </div>
            </Link>
            <nav className="hidden md:flex items-center gap-0.5">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="px-3 py-1.5 text-sm text-blue-100 hover:text-white hover:bg-white/10 rounded-md transition-all duration-150"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
        <footer className="border-t border-gray-200 mt-12 py-6">
          <p className="text-center text-xs text-gray-400">
            物流効率化法 第46条／第65条 · 改善基準告示 2024年4月施行版に準拠
          </p>
        </footer>
      </body>
    </html>
  );
}
