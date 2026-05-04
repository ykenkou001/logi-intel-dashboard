"use client";

import { useEffect, useState } from "react";
import { ErrorBanner, ToolResponseDisplay } from "@/components/ToolResponseDisplay";
import {
  fetchMeasureEval,
  fetchSamples,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";

export default function MeasureEvalPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState("sample_mfg_01");
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch((e) => setError(e instanceof Error ? e.message : "サンプル取得失敗"));
  }, []);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchMeasureEval(companyId);
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-primary">施策評価エンジン（Top 3 推薦）</h2>
      <p className="text-sm text-gray-700 leading-relaxed">
        フェーズ3.5 の差別化の心臓部。プレイブック10施策を
        ROI（35%）・実装可能性（30%）・法令適合度（25%）・補助金カバー率（10%）の
        4 軸で 0-100 スコアリングし、加重合計で Top 3 を推薦します。
        各推薦には期待コスト削減・期待 CO2 削減・回収期間 + 選定根拠が付与されます。
      </p>

      <div className="bg-white rounded-lg shadow p-6 flex gap-3 items-end">
        <label className="flex-1">
          <span className="text-xs text-muted block mb-1">対象企業</span>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
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
          className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
        >
          {loading ? "評価中..." : "Top 3 を取得"}
        </button>
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {result ? <ToolResponseDisplay response={result} /> : null}
    </div>
  );
}
