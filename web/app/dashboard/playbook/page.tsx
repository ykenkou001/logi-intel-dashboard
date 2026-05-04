"use client";

import { useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import { fetchPlaybook, type ToolResponse } from "@/lib/api";
import { FORM3_SECTIONS, INDUSTRY_CATEGORIES, MEASURE_TYPES } from "@/lib/constants";

export default function PlaybookPage() {
  const [industry, setIndustry] = useState<string>("");
  const [maxDifficulty, setMaxDifficulty] = useState<string>("");
  const [form3Section, setForm3Section] = useState<string>("");
  const [measureType, setMeasureType] = useState<string>("");
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      setResult(
        await fetchPlaybook({
          industry: industry || undefined,
          max_difficulty: maxDifficulty ? Number(maxDifficulty) : undefined,
          form3_section: form3Section || undefined,
          measure_type: measureType || undefined,
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
          施策プレイブック検索
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          標準施策10件（モーダルシフト・積載率向上・共同配送・パレット標準化・
          VBS・中継輸送・WMS 等）を業種・難易度・様式第3 セクション・取組タイプで絞り込みます。
          各施策には投資レンジ・期待効果・補助金・成功事例・失敗パターンが付きます。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <p className="text-xs text-gray-400 mb-4">絞り込み条件（すべて任意）</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          <label className="block">
            <span className={labelClass}>業種カテゴリ</span>
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className={fieldClass}
            >
              <option value="">指定なし</option>
              {INDUSTRY_CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>最大実装難易度（1-5）</span>
            <select
              value={maxDifficulty}
              onChange={(e) => setMaxDifficulty(e.target.value)}
              className={fieldClass}
            >
              <option value="">指定なし</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>様式第3 セクション</span>
            <select
              value={form3Section}
              onChange={(e) => setForm3Section(e.target.value)}
              className={fieldClass}
            >
              <option value="">指定なし</option>
              {FORM3_SECTIONS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className={labelClass}>取組タイプ</span>
            <select
              value={measureType}
              onChange={(e) => setMeasureType(e.target.value)}
              className={fieldClass}
            >
              <option value="">指定なし</option>
              {MEASURE_TYPES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Spinner /> 検索中...
            </>
          ) : (
            "施策を検索"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
