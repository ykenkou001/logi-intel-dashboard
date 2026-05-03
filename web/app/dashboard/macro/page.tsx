"use client";

import { useState } from "react";
import { fetchMacroOverview, type ToolResponse } from "@/lib/api";

const PREFECTURES = [
  "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
  "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
  "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
  "岐阜県", "静岡県", "愛知県", "三重県",
  "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
  "鳥取県", "島根県", "岡山県", "広島県", "山口県",
  "徳島県", "香川県", "愛媛県", "高知県",
  "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
];

export default function MacroPage() {
  const [prefecture, setPrefecture] = useState("東京都");
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchMacroOverview(prefecture);
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-primary">都道府県マクロ概況</h2>
      <p className="text-sm text-gray-700">
        e-Stat / 国税庁 / 気象庁 / エネ庁を並列フェッチします。
        一部の API が失敗しても、他のデータは表示されます。
      </p>

      <div className="bg-white rounded-lg shadow p-6 flex gap-3 items-end">
        <label className="flex-1">
          <span className="text-xs text-muted block mb-1">都道府県</span>
          <select
            value={prefecture}
            onChange={(e) => setPrefecture(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
          >
            {PREFECTURES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
        >
          {loading ? "取得中..." : "取得"}
        </button>
      </div>

      {error ? (
        <div className="bg-accent/10 border border-accent text-accent rounded p-4 text-sm">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
            {result.summary}
          </pre>

          {result.citations.length > 0 ? (
            <details className="text-xs text-muted">
              <summary className="cursor-pointer hover:text-primary">
                出典 ({result.citations.length} 件)
              </summary>
              <ul className="mt-2 space-y-1 ml-4">
                {result.citations.map((c) => (
                  <li key={c.url}>
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary underline"
                    >
                      {c.label}
                    </a>
                    {c.stats_data_id ? ` — statsDataId=${c.stats_data_id}` : null}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {result.freshness_warnings.length > 0 ? (
            <details className="text-xs text-muted">
              <summary className="cursor-pointer hover:text-primary">
                鮮度警告 ({result.freshness_warnings.length} 件)
              </summary>
              <ul className="mt-2 space-y-1 ml-4 list-disc">
                {result.freshness_warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
