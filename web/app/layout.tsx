import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Logi-Intel Dashboard",
  description: "CLO 中長期計画策定・運用支援ダッシュボード",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="bg-muted-bg text-gray-900 min-h-screen">
        <header className="bg-primary text-white px-6 py-4 shadow">
          <h1 className="text-xl font-bold">Logi-Intel Dashboard</h1>
          <p className="text-xs text-primary-light/80 mt-0.5">
            CLO 中長期計画策定・運用支援
          </p>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
        <footer className="text-center text-xs text-muted py-6">
          物流効率化法 第46条／第65条 / 改善基準告示 2024年4月施行版に準拠
        </footer>
      </body>
    </html>
  );
}
