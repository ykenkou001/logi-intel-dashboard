import Link from "next/link";

const FEATURES = [
  {
    href: "/dashboard/cockpit",
    title: "🆕 デイリーコックピット（CLO 今日の3判断）",
    description:
      "未達 KPI ／ 放置リスク ／ 今週決める施策 を 3 件だけ提示。緊急度・経営インパクト・自信度・想定反論まで 1 画面で確認、採用／保留／却下を I2 ログに記録",
  },
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
    href: "/dashboard/industry-package",
    title: "🆕 業種別 CLO 標準パッケージ",
    description:
      "製造 / 卸 / 小売 / 連鎖化（FC本部）の 4 業種で KPI ／ 施策 ／ 会議 ／ レポート ／ データ項目を標準型として固定。Override 4 分類別件数も併記",
  },
  {
    href: "/dashboard/standardization",
    title: "🆕 F2 標準化スコア",
    description:
      "業種別 CLO 標準パッケージへの準拠度を 0-100 で評価。coverage + Override 4 分類の減点 / bonus を可視化、未計測 KPI と未採用施策の差分テーブル付き",
  },
  {
    href: "/dashboard/waste-traps",
    title: "🆕 J2 罠スコア",
    description:
      "投資が回っていない施策を 6 軸セーフガード付きで検出。重大度（重大/要注意/軽微）と推定原因を経営会議向けに整理し、投資凍結推奨も明示",
  },
  {
    href: "/dashboard/company",
    title: "自社プロフィール入力",
    description:
      "Excel テンプレ DL → 記入 → アップロードで CompanyProfile を構築・JSON 永続化",
  },
] as const;

// 4 業種サンプルのデモ動線（社内デモで「業種を選ぶ → 5 画面を順に見る」流れを作る）
const INDUSTRY_DEMOS = [
  {
    industry: "製造業",
    companyId: "sample_mfg_01",
    description:
      "サンプル：中堅 食品製造（年商 50 億）。荷主 第46条適用",
    accent: "from-blue-50 to-blue-100/50 border-blue-200",
    chipColor: "bg-blue-100 text-blue-900",
  },
  {
    industry: "卸売業",
    companyId: "sample_wholesale_01",
    description:
      "サンプル：日用品卸（年商 200 億）。荷主 第46条適用",
    accent: "from-emerald-50 to-emerald-100/50 border-emerald-200",
    chipColor: "bg-emerald-100 text-emerald-900",
  },
  {
    industry: "小売業",
    companyId: "sample_retail_01",
    description:
      "サンプル：地域チェーン（年商 80 億）。荷主 第46条適用",
    accent: "from-amber-50 to-amber-100/50 border-amber-200",
    chipColor: "bg-amber-100 text-amber-900",
  },
  {
    industry: "連鎖化（FC本部）",
    companyId: "sample_chain_01",
    description:
      "サンプル：コンビニ FC 本部（年商 3,200 億）。第65条 連鎖化適用",
    accent: "from-violet-50 to-violet-100/50 border-violet-200",
    chipColor: "bg-violet-100 text-violet-900",
  },
] as const;

const DEMO_FLOW = [
  { href: "/dashboard/industry-package", label: "業種別パッケージ" },
  { href: "/dashboard/standardization", label: "F2 標準化" },
  { href: "/dashboard/waste-traps", label: "J2 罠" },
  { href: "/dashboard/cockpit", label: "コックピット" },
  { href: "/dashboard/plan-draft", label: "計画書" },
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
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/check"
              className="inline-flex items-center gap-2 bg-white text-[#1F4E79] font-bold text-sm px-5 py-2.5 rounded-lg hover:bg-blue-50 transition-colors shadow-md"
            >
              まず対象か 30 秒チェック
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
            <Link
              href="/dashboard/plan-draft"
              className="inline-flex items-center gap-2 border border-white/40 bg-white/10 text-white font-bold text-sm px-5 py-2.5 rounded-lg hover:bg-white/20 transition-colors"
            >
              計画書ドラフトを生成する
            </Link>
            <Link
              href="/guide"
              className="inline-flex items-center gap-2 border border-white/30 bg-white/5 text-white font-bold text-sm px-5 py-2.5 rounded-lg hover:bg-white/15 transition-colors"
            >
              まず使い方を見る
            </Link>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-blue-100 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="font-bold text-gray-900">どの機能を使えばよいか迷ったら</h3>
            <p className="mt-1 text-sm leading-relaxed text-gray-600">
              初見ユーザー向けに、目的別のおすすめ画面・各機能の入力と出力・結果の読み方をまとめています。
            </p>
          </div>
          <Link
            href="/guide"
            className="inline-flex flex-shrink-0 items-center justify-center rounded-lg bg-[#1F4E79] px-4 py-2 text-sm font-bold text-white hover:bg-[#173C5C]"
          >
            機能別利用ガイド
          </Link>
        </div>
      </section>

      {/* 業種別デモ動線（4 業種サンプル → 5 画面を順に巡る） */}
      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">
            業種別 デモ動線（社内デモ向け 4 業種サンプル）
          </h3>
          <span className="text-[11px] text-gray-400">
            {DEMO_FLOW.map((s) => s.label).join(" → ")}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {INDUSTRY_DEMOS.map((demo) => (
            <div
              key={demo.companyId}
              className={`bg-gradient-to-br ${demo.accent} rounded-xl border px-4 py-4 flex flex-col`}
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-bold text-gray-900 text-sm">
                  {demo.industry}
                </h4>
                <span
                  className={`text-[10px] font-bold rounded-full px-2 py-0.5 ${demo.chipColor}`}
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {demo.companyId}
                </span>
              </div>
              <p className="text-[11px] text-gray-700 leading-relaxed mb-3">
                {demo.description}
              </p>
              <div className="mt-auto flex flex-wrap gap-1.5">
                {DEMO_FLOW.map((step, i) => (
                  <Link
                    key={step.href}
                    href={step.href}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold bg-white/70 hover:bg-white border border-gray-200 hover:border-[#2E73AC]/40 text-gray-700 hover:text-[#1F4E79] rounded px-2 py-1 transition-colors"
                  >
                    <span
                      className="text-[9px] text-gray-400"
                      style={{ fontFamily: "var(--font-mono)" }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    {step.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-gray-500 leading-relaxed">
          各画面の「会社 ID」セレクタで対応するサンプルを選ぶと、全画面でストーリーが繋がります。
          連鎖化（sample_chain_01）は荷役等セクション対象外で、F2 標準化スコアで loading 系施策を採用すると追加減点される仕様です。
        </p>
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

    </div>
  );
}
