"use client";

import { useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
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
      setResult(
        await fetchBenchmark({
          jsic_code: jsicCode,
          prefecture,
          revenue_jpy: Math.round(revenueOku * 1e8),
          logistics_cost_jpy: logisticsCostOku
            ? Math.round(Number(logisticsCostOku) * 1e8)
            : undefined,
        })
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  const fieldClass =
    "w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition";
  const labelClass =
    "text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5";

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          業界ベンチマーク
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          JSIC 細分類 × 都道府県で全国・地域内の規模感と業界平均物流コスト比率を提示します。
          e-Stat 経済センサス 2024 と JILS 物流コスト調査を組合せ、CLO 計画書「現状分析」
          セクションの根拠数値として活用できます。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          <label className="block">
            <span className={labelClass}>JSIC 細分類4桁</span>
            <select
              value={jsicCode}
              onChange={(e) => setJsicCode(e.target.value)}
              className={fieldClass}
            >
              {JSIC_PRESETS.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>都道府県</span>
            <select
              value={prefecture}
              onChange={(e) => setPrefecture(e.target.value)}
              className={fieldClass}
            >
              {PREFECTURES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>年間売上（億円）</span>
            <input
              type="number"
              min={1}
              value={revenueOku}
              onChange={(e) => setRevenueOku(Number(e.target.value))}
              className={`${fieldClass} tabular-nums`}
              style={{ fontFamily: "var(--font-mono)" }}
            />
          </label>
          <label className="block">
            <span className={labelClass}>物流コスト（億円・任意）</span>
            <input
              type="number"
              min={0}
              value={logisticsCostOku}
              placeholder="未入力で省略"
              onChange={(e) => setLogisticsCostOku(e.target.value)}
              className={`${fieldClass} tabular-nums`}
              style={{ fontFamily: "var(--font-mono)" }}
            />
          </label>
        </div>
        <div className="flex items-center gap-4">
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
              "ベンチマーク取得"
            )}
          </button>
          <span className="text-xs text-gray-400">
            ※ e-Stat への問い合わせのため 5〜15 秒かかる場合あり
          </span>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}
      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
