"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchSamples,
  fetchWaitHeatmap,
  type HeatmapCell,
  type HeatmapMetadata,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";
import { SEVERITY_EMOJI } from "@/lib/labels";

const TIME_SLOT_LABEL_JP: Record<string, string> = {
  morning: "朝便（6-10時）",
  midday: "昼便（10-15時）",
  evening: "夕便（15-19時）",
  night: "夜便（19-翌6時）",
  all_day: "時間帯不明",
};

const SEVERITY_BG: Record<string, string> = {
  green: "bg-emerald-100 border-emerald-300",
  yellow: "bg-amber-100 border-amber-300",
  red: "bg-rose-100 border-rose-400",
  none: "bg-gray-50 border-gray-200",
};


function findCell(
  cells: HeatmapCell[],
  site: string,
  slot: string,
): HeatmapCell | undefined {
  return cells.find((c) => c.site_name === site && c.time_slot === slot);
}

export default function WaitHeatmapPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState<string>("sample_retail_01");
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch(() => setSamples([]));
  }, []);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchWaitHeatmap(companyId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  const heatmap = useMemo<HeatmapMetadata | null>(() => {
    const md = result?.metadata as HeatmapMetadata | undefined;
    if (!md || !md.cells) return null;
    return md;
  }, [result]);

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          拠点別 × 時間帯 荷待ち時間ヒートマップ
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          拠点 × 時間帯 4 区分（朝/昼/夕/夜）で荷待ち時間の平均値・最大値を可視化します。
          🟢 30 分以下（目標）／🟡 30-90 分／🔴 90 分超 の 3 段階で
          バース予約・時間帯分散・トラック予約システム導入の対象拠点を特定します。
          基準値・目標値は改善基準告示（2024 年 4 月施行）に準拠。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <label className="block mb-5">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
            会社 ID（time_slot 付き wait_time_rows を持つ会社が対象）
          </span>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
          >
            {samples.length === 0 && (
              <option value="sample_retail_01">sample_retail_01（小売）</option>
            )}
            {samples.map((s) => (
              <option key={s.company_id} value={s.company_id}>
                {s.company_id} — {s.name}
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
            "ヒートマップを生成"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {heatmap && heatmap.cells.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 overflow-x-auto">
          <div className="mb-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-gray-700">
            <span>
              全体平均:{" "}
              <strong>
                {heatmap.overall_avg_minutes != null
                  ? `${heatmap.overall_avg_minutes.toFixed(0)} 分`
                  : "計測なし"}
              </strong>
            </span>
            <span>
              全体最大:{" "}
              <strong>
                {heatmap.overall_max_minutes != null
                  ? `${heatmap.overall_max_minutes.toFixed(0)} 分`
                  : "—"}
              </strong>
            </span>
            <span>
              基準: 平均 {heatmap.avg_target_minutes} 分以下 / 上限{" "}
              {heatmap.threshold_minutes} 分（改善基準告示）
            </span>
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="border border-gray-200 bg-gray-50 px-3 py-2 text-left text-xs font-semibold text-gray-700">
                  拠点 ＼ 時間帯
                </th>
                {heatmap.time_slots.map((slot) => (
                  <th
                    key={slot}
                    className="border border-gray-200 bg-gray-50 px-3 py-2 text-center text-xs font-semibold text-gray-700"
                  >
                    {TIME_SLOT_LABEL_JP[slot] ?? slot}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heatmap.site_names.map((site) => (
                <tr key={site}>
                  <td className="border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-semibold text-gray-800">
                    {site}
                  </td>
                  {heatmap.time_slots.map((slot) => {
                    const cell = findCell(heatmap.cells, site, slot);
                    if (!cell) {
                      return (
                        <td
                          key={slot}
                          className="border border-gray-200 bg-gray-50 px-3 py-3 text-center text-xs text-gray-400"
                        >
                          —
                        </td>
                      );
                    }
                    const cls =
                      cell.measured_count === 0
                        ? SEVERITY_BG.none
                        : SEVERITY_BG[cell.severity];
                    return (
                      <td
                        key={slot}
                        className={`border px-3 py-3 text-center text-xs ${cls}`}
                        title={`${cell.measured_count} 便計測 / 最大 ${cell.max_minutes ?? "—"} 分${
                          cell.confidence_low
                            ? "（計測 100 便未満：信頼性低）"
                            : ""
                        }`}
                      >
                        <div className="text-base font-bold text-gray-800">
                          {cell.avg_minutes != null
                            ? `${cell.avg_minutes.toFixed(0)} 分`
                            : "未計測"}
                        </div>
                        <div className="mt-1 flex items-center justify-center gap-1 text-[10px] text-gray-600">
                          <span>{SEVERITY_EMOJI[cell.severity as keyof typeof SEVERITY_EMOJI] ?? "⚪"}</span>
                          <span>{cell.measured_count} 便</span>
                          {cell.over_2h_count > 0 && (
                            <span className="text-rose-700 font-semibold">
                              ／2h超 {cell.over_2h_count}
                            </span>
                          )}
                          {cell.confidence_low && cell.measured_count > 0 && (
                            <span className="text-amber-700">⚠️</span>
                          )}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 text-[11px] text-gray-500">
            🟢 平均 ≤ 30 分（目標達成） / 🟡 30-90 分（改善対象） / 🔴 90 分超（即対応） / ⚪ 未計測
            ／ ⚠️ 計測 100 便未満は統計的有意性が低く、参考値扱い
          </div>
        </div>
      )}

      {result && <ToolResponseDisplay response={result} />}

      {result && heatmap && heatmap.cells.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-xl p-4 text-sm">
          この企業は拠点別の time_slot 付き wait_time_rows を持っていないため、
          ヒートマップを生成できません。
          Excel 取込時に「site_name 列」と「time_slot 列（morning/midday/evening/night）」
          を埋めると可視化対象になります。
        </div>
      )}
    </div>
  );
}
