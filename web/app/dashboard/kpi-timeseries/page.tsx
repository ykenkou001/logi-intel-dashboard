"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchKpiTimeseries,
  fetchSamples,
  recordMonthlySnapshot,
  type KpiDeteriorationAlert,
  type KpiTimeSeriesMetadata,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";
import {
  BASELINE_SOURCE_LABEL,
  DETERIORATION_SEVERITY_CLASS,
  DETERIORATION_SEVERITY_LABEL,
  INDUSTRY_CATEGORY_LABEL,
  KPI_SNAPSHOT_SOURCE_LABEL,
} from "@/lib/labels";
import { useFetchTool } from "@/lib/useFetchTool";

const KpiTimeseriesChart = dynamic(
  () =>
    import("@/components/KpiTimeseriesChart").then((m) => m.KpiTimeseriesChart),
  { ssr: false, loading: () => <Spinner /> },
);

function currentYearMonth(): string {
  const now = new Date();
  const m = (now.getMonth() + 1).toString().padStart(2, "0");
  return `${now.getFullYear()}-${m}`;
}

export default function KpiTimeseriesPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState<string>("sample_wholesale_01");
  const [yearMonth, setYearMonth] = useState<string>(currentYearMonth());
  // v1.1: 当月の物流コスト実績入力（円・空文字 = 未入力 → null で送信）
  const [monthlyLogisticsCostJpy, setMonthlyLogisticsCostJpy] =
    useState<string>("");
  const { data: result, loading, error, run } = useFetchTool<ToolResponse>();
  const [recording, setRecording] = useState<boolean>(false);
  const [recordError, setRecordError] = useState<string | null>(null);
  const [recordedSummary, setRecordedSummary] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch(() => setSamples([]));
  }, []);

  async function handleQuery() {
    setRecordedSummary(null);
    await run(() => fetchKpiTimeseries(companyId, { limitMonths: 24 }));
  }

  async function handleRecord() {
    setRecording(true);
    setRecordError(null);
    try {
      const trimmedCost = monthlyLogisticsCostJpy.trim();
      const costPayload =
        trimmedCost === "" || Number.isNaN(Number(trimmedCost))
          ? null
          : Math.max(0, Math.trunc(Number(trimmedCost)));
      const res = await recordMonthlySnapshot(
        companyId,
        yearMonth,
        [],
        costPayload,
      );
      setRecordedSummary(res.summary);
      await run(() => fetchKpiTimeseries(companyId, { limitMonths: 24 }));
    } catch (e) {
      setRecordError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setRecording(false);
    }
  }

  const timeseries = useMemo<KpiTimeSeriesMetadata | null>(() => {
    const md = result?.metadata as KpiTimeSeriesMetadata | undefined;
    if (!md || !Array.isArray(md.months)) return null;
    return md;
  }, [result]);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          KPI 月次推移 — 悪化の早期発見
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          積載率・荷待ち時間・荷役等時間・CO2 原単位・F2 標準化スコアの月次推移を
          可視化し、3 ヶ月前との差分または 3 ヶ月連続悪化を検出した指標に
          severity（注意 / 警告 / 重大）付きのアラートを添えます。日次
          cockpit_snapshots からの自動ロールアップに加え、当月分の手動記録も可能。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <div className="grid md:grid-cols-2 gap-4 mb-5">
          <label className="block">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
              会社 ID
            </span>
            <select
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
            >
              {samples.length === 0 && (
                <option value="sample_wholesale_01">
                  sample_wholesale_01（卸）
                </option>
              )}
              {samples.map((s) => (
                <option key={s.company_id} value={s.company_id}>
                  {s.company_id} — {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
              記録対象月（YYYY-MM）
            </span>
            <input
              type="month"
              value={yearMonth}
              onChange={(e) => setYearMonth(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
            />
          </label>
        </div>
        <label className="block mb-5">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
            当月の物流コスト実績（円・任意）
          </span>
          <input
            type="number"
            min={0}
            inputMode="numeric"
            value={monthlyLogisticsCostJpy}
            onChange={(e) => setMonthlyLogisticsCostJpy(e.target.value)}
            placeholder="未入力なら profile.kpi_history の最新 fy 値にフォールバック"
            className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
          />
          <span className="block text-[11px] text-gray-500 mt-1">
            年間売上 / 12 で当月推計売上を割り、物流コスト/売上比率を計算します。
          </span>
        </label>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleQuery}
            disabled={loading}
            className="bg-[#1F4E79] hover:bg-[#173E60] disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition"
          >
            {loading ? "取得中…" : "月次推移を表示"}
          </button>
          <button
            type="button"
            onClick={handleRecord}
            disabled={recording}
            className="bg-amber-50 hover:bg-amber-100 disabled:opacity-50 text-amber-900 border border-amber-300 px-5 py-2.5 rounded-lg text-sm font-semibold transition"
          >
            {recording ? "記録中…" : `${yearMonth} 月のスナップショットを記録`}
          </button>
        </div>
        {recordError && (
          <div className="mt-4">
            <ErrorBanner message={recordError} />
          </div>
        )}
        {recordedSummary && (
          <div className="mt-4 text-xs bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 text-emerald-900">
            {recordedSummary}
          </div>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {timeseries && (
        <>
          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h3
              className="text-lg font-bold text-[#1F4E79] mb-3"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              月次推移チャート（最大 24 ヶ月）
            </h3>
            <KpiTimeseriesChart
              months={timeseries.months}
              industryBenchmarkLogisticsCostRatio={
                timeseries.industry_benchmark_logistics_cost_ratio
              }
            />
            <p className="text-[11px] text-gray-500 mt-2">
              左軸: 積載率 / 物流コスト比率 / F2 標準化スコア（%・pt）/ 右軸: 荷待ち平均 /
              荷役等時間 / CO2 原単位（分・g）
            </p>
            {timeseries.industry_benchmark_logistics_cost_ratio != null && (
              <p className="text-[11px] text-rose-700 mt-1">
                破線: 業界平均 物流コスト比率（JILS 2021・
                {timeseries.industry_category
                  ? INDUSTRY_CATEGORY_LABEL[timeseries.industry_category] ??
                    timeseries.industry_category
                  : "業種未解決"}
                ）
              </p>
            )}
          </div>

          <DeteriorationPanel alerts={timeseries.deteriorations} />

          <SnapshotTable months={timeseries.months} />

          <ToolResponseDisplay response={result as ToolResponse} />
        </>
      )}
    </div>
  );
}

function DeteriorationPanel({ alerts }: { alerts: KpiDeteriorationAlert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
        <div className="text-sm font-semibold text-emerald-900">
          ✅ 悪化アラートなし
        </div>
        <p className="text-xs text-emerald-800 mt-1">
          全指標が計画線上または改善傾向にあります。
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-6">
      <h3
        className="text-lg font-bold text-[#1F4E79] mb-3"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        悪化アラート（{alerts.length} 件）
      </h3>
      <div className="space-y-2">
        {alerts.map((a) => (
          <div
            key={`${a.metric}-${a.severity}`}
            className={`rounded-lg border px-4 py-3 text-sm ${
              DETERIORATION_SEVERITY_CLASS[a.severity]
            }`}
          >
            <div className="flex flex-wrap items-baseline gap-2 mb-1">
              <span className="text-xs font-bold uppercase">
                {DETERIORATION_SEVERITY_LABEL[a.severity]}
              </span>
              <span className="font-bold">{a.metric_label}</span>
              <span className="text-[10px] opacity-80 bg-white/40 px-1.5 py-0.5 rounded">
                基準: {BASELINE_SOURCE_LABEL[a.baseline_source]}
              </span>
              {a.consecutive_months > 0 && (
                <span className="text-[10px] opacity-80">
                  連続悪化 {a.consecutive_months} ヶ月
                </span>
              )}
            </div>
            <p className="text-xs leading-relaxed">{a.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SnapshotTable({
  months,
}: {
  months: KpiTimeSeriesMetadata["months"];
}) {
  if (months.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-100 p-6">
      <h3
        className="text-lg font-bold text-[#1F4E79] mb-3"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        月次スナップショット一覧
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-gray-600">
              <th className="text-left py-2 px-2">年月</th>
              <th className="text-right px-2">積載率</th>
              <th className="text-right px-2">荷待ち平均</th>
              <th className="text-right px-2">荷役等時間</th>
              <th className="text-right px-2">CO2 原単位</th>
              <th className="text-right px-2">物流コスト比率</th>
              <th className="text-right px-2">F2 スコア</th>
              <th className="text-right px-2">罠 high/med/low</th>
              <th className="text-left px-2">由来</th>
            </tr>
          </thead>
          <tbody>
            {[...months].reverse().map((m) => (
              <tr key={m.year_month} className="border-b border-gray-100">
                <td className="py-2 px-2 font-semibold">{m.year_month}</td>
                <td
                  className="text-right px-2"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {m.load_factor_pct?.toFixed(1) ?? "—"}
                </td>
                <td
                  className="text-right px-2"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {m.wait_time_avg_min?.toFixed(1) ?? "—"}
                </td>
                <td
                  className="text-right px-2"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {m.handling_time_avg_min?.toFixed(1) ?? "—"}
                </td>
                <td
                  className="text-right px-2"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {m.co2_intensity_g_per_tonkm?.toFixed(1) ?? "—"}
                </td>
                <td
                  className="text-right px-2"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {m.logistics_cost_ratio == null
                    ? "—"
                    : `${(m.logistics_cost_ratio * 100).toFixed(2)}%`}
                </td>
                <td
                  className="text-right px-2"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {m.standardization_score?.toFixed(1) ?? "—"}
                </td>
                <td
                  className="text-right px-2"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {m.waste_trap_count_high}/{m.waste_trap_count_medium}/
                  {m.waste_trap_count_low}
                </td>
                <td className="px-2 text-gray-500">
                  {KPI_SNAPSHOT_SOURCE_LABEL[m.source]}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
