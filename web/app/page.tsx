import Link from "next/link";

const FEATURES: { href: string; title: string; description: string; phase: string }[] = [
  {
    href: "/dashboard/macro",
    title: "都道府県マクロ概況",
    description:
      "e-Stat / 国税庁 / 気象庁 / エネ庁を並列フェッチし、運輸業事業所数・燃料価格・気象警報を一覧表示",
    phase: "実装済",
  },
  {
    href: "/dashboard/benchmark",
    title: "業界ベンチマーク",
    description:
      "JSIC 細分類 × 都道府県で全国・地域内の規模感と業界平均物流コスト比率を提示",
    phase: "実装済",
  },
  {
    href: "/dashboard/driver-gap",
    title: "ドライバー需給ギャップ",
    description: "改善基準告示（13.5%減）+ 国交省2030年試算（▲34.1%）から都道府県別ギャップを試算",
    phase: "実装済",
  },
  {
    href: "/dashboard/playbook",
    title: "施策プレイブック",
    description: "標準10施策（モーダルシフト・積載率向上・共同配送 等）を業種・難易度で絞込",
    phase: "実装済",
  },
  {
    href: "/dashboard/measure-eval",
    title: "施策評価（Top 3 推薦）",
    description: "自社プロフィール × 4軸スコアリングで Top 3 を推薦・選定根拠を可視化",
    phase: "実装済",
  },
  {
    href: "/dashboard/scenario-sim",
    title: "シナリオシミュレーション",
    description:
      "保守/標準/上振れ × What-if 8 種で「燃料 +20% でも黒字維持」を検証",
    phase: "実装済",
  },
  {
    href: "/dashboard/company",
    title: "自社プロフィール入力",
    description:
      "Excel テンプレ DL → 記入 → アップロードで CompanyProfile を構築・JSON 永続化",
    phase: "実装済",
  },
  {
    href: "/dashboard/plan-draft",
    title: "計画書ドラフト統合生成",
    description: "PPT / Word（様式第3別紙）/ Excel / Markdown を一括生成・ダウンロード",
    phase: "実装済",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-primary mb-2">
          CLO 中長期計画策定・運用支援
        </h2>
        <p className="text-sm text-gray-700 leading-relaxed">
          2026年4月義務化の CLO（物流統括管理者）の計画策定を、データ・施策評価・
          法令ロジックの 3 層から支援します。経営会議で配れる成果物（PPT / Word /
          Excel / Markdown）まで自動生成し、提出前の defensibility を担保します。
        </p>
        <div className="mt-4 flex gap-2 text-xs">
          <span className="bg-primary text-white px-2 py-1 rounded">
            物流効率化法 第46条／第65条
          </span>
          <span className="bg-accent text-white px-2 py-1 rounded">
            改善基準告示 2024年4月施行版
          </span>
          <span className="bg-primary-light text-white px-2 py-1 rounded">
            初回計画提出: 2026年10月末
          </span>
        </div>
      </section>

      <section>
        <h3 className="text-lg font-bold text-primary mb-3">主要機能</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FEATURES.map((feature) => (
            <Link
              key={feature.href}
              href={feature.href}
              className="bg-white rounded-lg shadow p-4 hover:shadow-md transition border-l-4 border-primary"
            >
              <div className="flex justify-between items-start">
                <h4 className="font-bold text-primary">{feature.title}</h4>
                <span className="text-xs bg-muted-bg text-muted px-2 py-0.5 rounded">
                  {feature.phase}
                </span>
              </div>
              <p className="text-sm text-gray-700 mt-2 leading-relaxed">
                {feature.description}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow p-6 text-sm text-gray-700">
        <h3 className="text-lg font-bold text-primary mb-2">バックエンド接続</h3>
        <p>
          このダッシュボードは <code className="bg-muted-bg px-1">api.main:app</code>{" "}
          で起動した FastAPI を呼び出します。事前に下記を起動してください:
        </p>
        <pre className="bg-gray-900 text-green-300 text-xs p-3 rounded mt-2 overflow-x-auto">
          uv run uvicorn api.main:app --reload --port 8000
        </pre>
        <p className="mt-2 text-xs text-muted">
          API 仕様: <a className="text-primary underline" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">http://localhost:8000/docs</a>
        </p>
      </section>
    </div>
  );
}
