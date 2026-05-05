import Link from "next/link";

const FEATURES = [
  {
    href: "/dashboard/macro",
    title: "都道府県マクロ概況",
    description:
      "e-Stat / 国税庁 / 気象庁 / エネ庁を並列フェッチし、運輸業事業所数・燃料価格・気象警報を一覧表示",
  },
  {
    href: "/dashboard/benchmark",
    title: "業界ベンチマーク",
    description:
      "JSIC 細分類 × 都道府県で全国・地域内の規模感と業界平均物流コスト比率を提示",
  },
  {
    href: "/dashboard/driver-gap",
    title: "ドライバー需給ギャップ",
    description:
      "改善基準告示（13.5%減）+ 国交省2030年試算（▲34.1%）から都道府県別ギャップを試算",
  },
  {
    href: "/dashboard/wait-heatmap",
    title: "拠点別 荷待ち時間ヒートマップ",
    description:
      "拠点 × 時間帯（朝/昼/夕/夜）で荷待ち時間を可視化。30 分以下を🟢／90 分超を🔴で即対応対象拠点を特定",
  },
  {
    href: "/dashboard/playbook",
    title: "施策プレイブック",
    description:
      "標準10施策（モーダルシフト・積載率向上・共同配送 等）を業種・難易度で絞込",
  },
  {
    href: "/dashboard/measure-eval",
    title: "施策評価（Top 3 推薦）",
    description:
      "自社プロフィール × 4軸スコアリングで Top 3 を推薦・選定根拠を可視化",
  },
  {
    href: "/dashboard/scenario-sim",
    title: "シナリオシミュレーション",
    description:
      "保守/標準/上振れ × What-if 8 種で「燃料 +20% でも黒字維持」を検証",
  },
  {
    href: "/dashboard/company",
    title: "自社プロフィール入力",
    description:
      "Excel テンプレ DL → 記入 → アップロードで CompanyProfile を構築・JSON 永続化",
  },
] as const;

export default function HomePage() {
  const today = new Date();
  const deadline = new Date("2026-10-31");
  const daysLeft = Math.ceil(
    (deadline.getTime() - today.getTime()) / 86400000
  );

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-[#0F2D4F] via-[#1F4E79] to-[#2569A8] px-8 py-10 text-white">
        <div className="absolute top-0 right-0 w-80 h-80 rounded-full bg-white/5 translate-x-1/3 -translate-y-1/3 pointer-events-none" />
        <div className="absolute bottom-0 right-1/3 w-52 h-52 rounded-full bg-white/5 translate-y-1/2 pointer-events-none" />
        <div className="relative">
          <div className="inline-flex items-center gap-2 border border-red-400/40 bg-red-900/20 text-red-200 rounded-full px-3 py-1 text-xs mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
            初回計画提出期限 2026年10月31日 — 残り{" "}
            <strong
              className="tabular-nums"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {daysLeft}
            </strong>{" "}
            日
          </div>
          <h2
            className="text-2xl md:text-3xl font-bold mb-3 leading-snug"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            CLO 中長期計画策定・運用支援
          </h2>
          <p className="text-blue-100 text-sm leading-relaxed max-w-2xl mb-7">
            2026年4月義務化の CLO（物流統括管理者）の計画策定を、データ・施策評価・法令ロジックの
            3 層から本格支援。経営会議で使える成果物（PPT / Word / Excel）まで自動生成し、説明責任を担保します。
          </p>
          <div className="flex flex-wrap gap-2 mb-7">
            {["物流効率化法 第46条／第65条", "改善基準告示 2024年4月施行版"].map(
              (tag) => (
                <span
                  key={tag}
                  className="text-xs bg-white/10 border border-white/20 text-blue-50 px-3 py-1 rounded-full"
                >
                  {tag}
                </span>
              )
            )}
          </div>
          <Link
            href="/dashboard/plan-draft"
            className="inline-flex items-center gap-2 bg-white text-[#1F4E79] font-bold text-sm px-5 py-2.5 rounded-lg hover:bg-blue-50 transition-colors shadow-md"
          >
            計画書ドラフトを生成する
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
              />
            </svg>
          </Link>
        </div>
      </section>

      {/* Feature grid */}
      <section>
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">
          分析・支援ツール
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {FEATURES.map((f, i) => (
            <Link
              key={f.href}
              href={f.href}
              className="group bg-white rounded-xl border border-gray-100 p-5 hover:border-[#2E73AC]/30 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
            >
              <div className="flex items-center gap-3 mb-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#1F4E79]/10 flex items-center justify-center flex-shrink-0">
                  <span
                    className="text-xs font-bold text-[#1F4E79]"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h4 className="font-bold text-sm text-gray-900 group-hover:text-[#1F4E79] transition-colors leading-tight">
                  {f.title}
                </h4>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11">
                {f.description}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* Plan-draft featured CTA */}
      <section>
        <Link
          href="/dashboard/plan-draft"
          className="group flex items-center justify-between bg-gradient-to-r from-[#1F4E79] to-[#2E73AC] rounded-xl p-6 text-white hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200"
        >
          <div>
            <div
              className="text-xs text-blue-200 mb-1.5 tracking-widest uppercase"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              Main Output
            </div>
            <h4
              className="text-xl font-bold mb-1.5"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              計画書ドラフト統合生成
            </h4>
            <p className="text-sm text-blue-100">
              PPT · Word（様式第3別紙）· Excel · Markdown を一括生成・ダウンロード
            </p>
          </div>
          <div className="ml-8 flex-shrink-0 w-12 h-12 rounded-full bg-white/20 border border-white/30 flex items-center justify-center group-hover:bg-white/30 transition-colors">
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
              />
            </svg>
          </div>
        </Link>
      </section>

      {/* Backend info */}
      <section className="bg-white rounded-xl border border-gray-100 p-5">
        <h3 className="font-bold text-gray-800 text-sm mb-2">
          バックエンド接続
        </h3>
        <p className="text-xs text-gray-600 leading-relaxed mb-2">
          このダッシュボードは{" "}
          <code
            className="bg-gray-100 px-1 py-0.5 rounded text-xs"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            api.main:app
          </code>{" "}
          で起動した FastAPI を呼び出します。
        </p>
        <pre
          className="bg-gray-900 text-emerald-400 text-xs p-3 rounded-lg overflow-x-auto"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          uv run uvicorn api.main:app --reload --port 8000
        </pre>
        <p className="mt-2 text-xs text-gray-400">
          API 仕様:{" "}
          <a
            className="text-[#2E73AC] hover:underline"
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
          >
            http://localhost:8000/docs
          </a>
        </p>
      </section>
    </div>
  );
}
