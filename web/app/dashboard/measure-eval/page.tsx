"use client";

import { useEffect, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchMeasureEval,
  fetchSamples,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";
import { useFetchTool } from "@/lib/useFetchTool";

export default function MeasureEvalPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState("sample_mfg_01");
  const [samplesError, setSamplesError] = useState<string | null>(null);
  const { data: result, loading, error: fetchError, run } = useFetchTool<ToolResponse>();
  const error = samplesError ?? fetchError;

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch((e) =>
        setSamplesError(e instanceof Error ? e.message : "サンプル取得失敗")
      );
  }, []);

  async function handleSubmit() {
    setSamplesError(null);
    await run(() => fetchMeasureEval(companyId));
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          施策評価エンジン（Top 3 推薦）
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          プレイブック10施策を ROI（35%）・実装可能性（30%）・法令適合度（25%）・
          補助金カバー率（10%）の 4 軸で 0-100 スコアリングし、加重合計で Top 3 を推薦します。
          各推薦には期待コスト削減・期待 CO2 削減・回収期間 + 選定根拠が付与されます。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <label className="block mb-5">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
            対象企業
          </span>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
          >
            {samples.map((s) => (
              <option key={s.company_id} value={s.company_id}>
                {s.name} ({s.company_id})
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
              <Spinner /> 評価中...
            </>
          ) : (
            "Top 3 を取得"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
