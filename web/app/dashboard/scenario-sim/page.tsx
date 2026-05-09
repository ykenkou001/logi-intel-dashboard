"use client";

import { useEffect, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchSamples,
  runScenarioSim,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";
import { useFetchTool } from "@/lib/useFetchTool";

const PLAYBOOK_MEASURES = [
  { id: "modal_shift_to_rail", label: "鉄道貨物へのモーダルシフト" },
  { id: "load_factor_tms", label: "積載率向上（TMS 配車最適化）" },
  { id: "joint_delivery_competitor", label: "同業他社との共同配送" },
  { id: "pallet_standardization", label: "パレット標準化（T11／T12）" },
  { id: "visualization_baseline", label: "物流実態の把握・可視化" },
  { id: "lead_time_review", label: "発注頻度・リードタイム見直し" },
  { id: "berth_booking_vbs", label: "バース予約受付システム（VBS）" },
  { id: "delivery_time_distribution", label: "納入時間帯の分散・拡大" },
  { id: "relay_transport", label: "中継輸送（長距離運行の分割）" },
  { id: "warehouse_dx_wms", label: "WMS 導入による倉庫オペレーション DX" },
] as const;

export default function ScenarioSimPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState("sample_mfg_01");
  const [selectedMeasures, setSelectedMeasures] = useState<string[]>([]);
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

  function toggleMeasure(id: string) {
    setSelectedMeasures((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  }

  async function handleSubmit() {
    setSamplesError(null);
    await run(() =>
      runScenarioSim(
        companyId,
        selectedMeasures.length > 0 ? selectedMeasures : undefined
      )
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          シナリオシミュレーション
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          保守 / 標準 / 上振れの 3 区分 × What-if 8 種（燃料±20%・運賃±10%・需要±10%・
          改善基準強化）でシナリオ試算します。堅牢性を
          🟢 70%以上 / 🟡 50-70% / 🔴 50%未満 で判定し、「燃料 +20% でも黒字維持」を
          CFO に説明できる出力形です。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-5">
        <label className="block">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
            対象企業
          </span>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full md:w-2/3 border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
          >
            {samples.map((s) => (
              <option key={s.company_id} value={s.company_id}>
                {s.name} ({s.company_id})
              </option>
            ))}
          </select>
        </label>

        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              評価対象施策
            </span>
            <span className="text-xs text-gray-400">
              未選択時は Top 3 推薦を自動採用
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {PLAYBOOK_MEASURES.map((m) => {
              const isSelected = selectedMeasures.includes(m.id);
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => toggleMeasure(m.id)}
                  className={`flex items-center gap-3 text-sm rounded-lg px-3 py-2.5 border transition-all text-left ${
                    isSelected
                      ? "border-[#1F4E79] bg-[#1F4E79]/8 text-[#1F4E79] font-medium"
                      : "border-gray-200 bg-white text-gray-700 hover:border-[#2E73AC]/40 hover:bg-slate-50"
                  }`}
                >
                  <span
                    className={`w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border transition-colors ${
                      isSelected
                        ? "bg-[#1F4E79] border-[#1F4E79]"
                        : "border-gray-300"
                    }`}
                  >
                    {isSelected && (
                      <svg
                        className="w-2.5 h-2.5 text-white"
                        fill="currentColor"
                        viewBox="0 0 12 12"
                      >
                        <path d="M3.707 5.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4a1 1 0 00-1.414-1.414L5 6.586 3.707 5.293z" />
                      </svg>
                    )}
                  </span>
                  {m.label}
                </button>
              );
            })}
          </div>
          {selectedMeasures.length > 0 && (
            <p className="text-xs text-[#1F4E79] mt-2">
              {selectedMeasures.length} 件選択中
            </p>
          )}
        </div>

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Spinner /> シミュレーション実行中...
            </>
          ) : (
            "シナリオを試算"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
