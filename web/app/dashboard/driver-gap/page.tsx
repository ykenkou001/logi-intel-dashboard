"use client";

import { useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import { fetchDriverGap, type ToolResponse } from "@/lib/api";
import { PREFECTURES } from "@/lib/constants";
import { useFetchTool } from "@/lib/useFetchTool";

export default function DriverGapPage() {
  const [prefecture, setPrefecture] = useState("東京都");
  const { data: result, loading, error, run } = useFetchTool<ToolResponse>();

  async function handleSubmit() {
    await run(() => fetchDriverGap(prefecture));
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          ドライバー需給ギャップ
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          改善基準告示（2024年4月施行）の年間時間外上限960h規制により、
          トラック運転者の実効稼働力が約13.5%減少します。
          e-Stat 経済センサスから道路貨物運送業（中分類44）の従業者数を取得し、
          2024年問題の影響規模と国交省の2030年試算を併せて提示します。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <label className="block mb-5">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
            都道府県
          </span>
          <select
            value={prefecture}
            onChange={(e) => setPrefecture(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
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
          className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Spinner /> 取得中...
            </>
          ) : (
            "需給ギャップを取得"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
