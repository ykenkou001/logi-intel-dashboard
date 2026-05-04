"use client";

import { useState } from "react";
import { ErrorBanner, ToolResponseDisplay } from "@/components/ToolResponseDisplay";
import { fetchPlaybook, type ToolResponse } from "@/lib/api";
import {
  FORM3_SECTIONS,
  INDUSTRY_CATEGORIES,
  MEASURE_TYPES,
} from "@/lib/constants";

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
      const response = await fetchPlaybook({
        industry: industry || undefined,
        max_difficulty: maxDifficulty ? Number(maxDifficulty) : undefined,
        form3_section: form3Section || undefined,
        measure_type: measureType || undefined,
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
      <h2 className="text-xl font-bold text-primary">施策プレイブック検索</h2>
      <p className="text-sm text-gray-700 leading-relaxed">
        標準施策10件（モーダルシフト・積載率向上・共同配送・パレット標準化・
        VBS・中継輸送・WMS 等）を業種・難易度・様式第3 セクション・取組タイプで絞り込みます。
        各施策には投資レンジ・期待効果・補助金・成功事例参照・失敗パターンが付きます。
      </p>

      <div className="bg-white rounded-lg shadow p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <label>
          <span className="text-xs text-muted block mb-1">業種カテゴリ</span>
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
          >
            <option value="">指定なし</option>
            {INDUSTRY_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-muted block mb-1">最大実装難易度（1-5）</span>
          <select
            value={maxDifficulty}
            onChange={(e) => setMaxDifficulty(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
          >
            <option value="">指定なし</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-muted block mb-1">様式第3 セクション</span>
          <select
            value={form3Section}
            onChange={(e) => setForm3Section(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
          >
            <option value="">指定なし</option>
            {FORM3_SECTIONS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-muted block mb-1">取組タイプ</span>
          <select
            value={measureType}
            onChange={(e) => setMeasureType(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
          >
            <option value="">指定なし</option>
            {MEASURE_TYPES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <div className="md:col-span-2">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
          >
            {loading ? "検索中..." : "施策を検索"}
          </button>
        </div>
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {result ? <ToolResponseDisplay response={result} /> : null}
    </div>
  );
}
