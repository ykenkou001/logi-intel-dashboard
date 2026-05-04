"use client";

import { useState } from "react";
import { ErrorBanner, ToolResponseDisplay } from "@/components/ToolResponseDisplay";
import { fetchBenchmark, type ToolResponse } from "@/lib/api";
import { JSIC_PRESETS, PREFECTURES } from "@/lib/constants";

export default function BenchmarkPage() {
  const [jsicCode, setJsicCode] = useState("5411");
  const [prefecture, setPrefecture] = useState("東京都");
  const [revenueOku, setRevenueOku] = useState(50);
  const [logisticsCostOku, setLogisticsCostOku] = useState<string>("");
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchBenchmark({
        jsic_code: jsicCode,
        prefecture,
        revenue_jpy: Math.round(revenueOku * 1e8),
        logistics_cost_jpy: logisticsCostOku
          ? Math.round(Number(logisticsCostOku) * 1e8)
          : undefined,
      });
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-primary">業界ベンチマーク</h2>
      <p className="text-sm text-gray-700 leading-relaxed">
        JSIC 細分類 × 都道府県で全国・地域内の規模感と業界平均物流コスト比率を提示します。
        e-Stat 経済センサス 2024 と JILS 物流コスト調査を組合せ、CLO 計画書「現状分析」
        セクションの根拠数値として活用できます。
      </p>

      <div className="bg-white rounded-lg shadow p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <label>
          <span className="text-xs text-muted block mb-1">JSIC 細分類4桁</span>
          <select
            value={jsicCode}
            onChange={(e) => setJsicCode(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
          >
            {JSIC_PRESETS.map((p) => (
              <option key={p.code} value={p.code}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
        <label>
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
        <label>
          <span className="text-xs text-muted block mb-1">年間売上（億円）</span>
          <input
            type="number"
            min={1}
            value={revenueOku}
            onChange={(e) => setRevenueOku(Number(e.target.value))}
            className="w-full border border-gray-300 rounded px-3 py-2 tabular-nums"
          />
        </label>
        <label>
          <span className="text-xs text-muted block mb-1">
            物流コスト（億円・任意）
          </span>
          <input
            type="number"
            min={0}
            value={logisticsCostOku}
            placeholder="未入力で省略"
            onChange={(e) => setLogisticsCostOku(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 tabular-nums"
          />
        </label>
        <div className="md:col-span-2">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
          >
            {loading ? "取得中..." : "ベンチマーク取得"}
          </button>
          <span className="text-xs text-muted ml-3">
            ※ e-Stat への問い合わせのため 5〜15 秒かかる場合あり
          </span>
        </div>
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {result ? <ToolResponseDisplay response={result} /> : null}
    </div>
  );
}
