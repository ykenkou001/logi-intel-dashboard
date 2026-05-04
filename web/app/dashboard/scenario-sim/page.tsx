"use client";

import { useEffect, useState } from "react";
import { ErrorBanner, ToolResponseDisplay } from "@/components/ToolResponseDisplay";
import {
  fetchSamples,
  runScenarioSim,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";

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
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch((e) => setError(e instanceof Error ? e.message : "サンプル取得失敗"));
  }, []);

  function toggleMeasure(id: string) {
    setSelectedMeasures((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id],
    );
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const response = await runScenarioSim(
        companyId,
        selectedMeasures.length > 0 ? selectedMeasures : undefined,
      );
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-primary">シナリオシミュレーション</h2>
      <p className="text-sm text-gray-700 leading-relaxed">
        保守 / 標準 / 上振れの 3 区分 × What-if 8 種（燃料±20%・運賃±10%・需要±10%・
        改善基準強化）でシナリオ試算します。同 form3_section に 2 施策以上ある場合は
        効果合算に 0.7 倍を適用し、堅牢性を 🟢 70%以上 / 🟡 50-70% / 🔴 50%未満 で判定します。
        「燃料 +20% でも黒字維持」を CFO に説明できる出力形です。
      </p>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <label className="block">
          <span className="text-xs text-muted block mb-1">対象企業</span>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full md:w-1/2 border border-gray-300 rounded px-3 py-2 bg-white"
          >
            {samples.map((s) => (
              <option key={s.company_id} value={s.company_id}>
                {s.name} ({s.company_id})
              </option>
            ))}
          </select>
        </label>

        <div>
          <div className="text-xs text-muted mb-2">
            評価対象施策（未選択時は Top 3 推薦を自動採用）
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {PLAYBOOK_MEASURES.map((m) => (
              <label
                key={m.id}
                className="flex items-center gap-2 text-sm bg-muted-bg rounded px-3 py-2 cursor-pointer hover:bg-primary/5"
              >
                <input
                  type="checkbox"
                  checked={selectedMeasures.includes(m.id)}
                  onChange={() => toggleMeasure(m.id)}
                />
                <span>{m.label}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
        >
          {loading ? "シミュレーション実行中..." : "シナリオを試算"}
        </button>
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {result ? <ToolResponseDisplay response={result} /> : null}
    </div>
  );
}
