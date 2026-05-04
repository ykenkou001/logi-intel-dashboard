"use client";

import { useState } from "react";
import { ErrorBanner, ToolResponseDisplay } from "@/components/ToolResponseDisplay";
import { fetchDriverGap, type ToolResponse } from "@/lib/api";
import { PREFECTURES } from "@/lib/constants";

export default function DriverGapPage() {
  const [prefecture, setPrefecture] = useState("東京都");
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchDriverGap(prefecture);
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-primary">ドライバー需給ギャップ</h2>
      <p className="text-sm text-gray-700 leading-relaxed">
        改善基準告示（2024年4月施行）の年間時間外上限960h規制により、
        トラック運転者の実効稼働力が約13.5%減少します。
        e-Stat 経済センサスから道路貨物運送業（中分類44）の従業者数を取得し、
        2024年問題の影響規模と国交省の2030年試算を併せて提示します。
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
          {loading ? "取得中..." : "需給ギャップ取得"}
        </button>
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {result ? <ToolResponseDisplay response={result} /> : null}
    </div>
  );
}
