"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MonthlyKpiSnapshot } from "@/lib/api";

const SERIES: Array<{
  key: keyof MonthlyKpiSnapshot;
  label: string;
  color: string;
  axis: "left" | "right";
}> = [
  {
    key: "load_factor_pct",
    label: "積載率(%)",
    color: "#1F4E79",
    axis: "left",
  },
  {
    key: "wait_time_avg_min",
    label: "荷待ち平均(分)",
    color: "#E0A030",
    axis: "right",
  },
  {
    key: "handling_time_avg_min",
    label: "荷役等時間(分)",
    color: "#A35F00",
    axis: "right",
  },
  {
    key: "co2_intensity_g_per_tonkm",
    label: "CO2原単位(g/t-km)",
    color: "#5B7E5A",
    axis: "right",
  },
  // v1.1: 物流コスト/売上比率（%表示用に 100 倍する別キー）
  {
    key: "logistics_cost_ratio_pct" as keyof MonthlyKpiSnapshot,
    label: "物流コスト比率(%)",
    color: "#C2526B",
    axis: "left",
  },
  {
    key: "standardization_score",
    label: "F2標準化スコア",
    color: "#2E73AC",
    axis: "left",
  },
];

export function KpiTimeseriesChart({
  months,
  industryBenchmarkLogisticsCostRatio,
}: {
  months: MonthlyKpiSnapshot[];
  industryBenchmarkLogisticsCostRatio?: number | null;
}) {
  if (months.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic py-12 text-center">
        月次スナップショット未登録。下の「当月スナップショットを記録」ボタンを押すと
        日次データから月平均を計算して履歴を作成します。
      </div>
    );
  }

  const data = months.map((m) => ({
    year_month: m.year_month,
    load_factor_pct: m.load_factor_pct,
    wait_time_avg_min: m.wait_time_avg_min,
    handling_time_avg_min: m.handling_time_avg_min,
    co2_intensity_g_per_tonkm: m.co2_intensity_g_per_tonkm,
    // v1.1: 0-1 比率 → % 表示
    logistics_cost_ratio_pct:
      m.logistics_cost_ratio == null ? null : m.logistics_cost_ratio * 100,
    standardization_score: m.standardization_score,
  }));

  const benchmarkPct =
    industryBenchmarkLogisticsCostRatio == null
      ? null
      : industryBenchmarkLogisticsCostRatio * 100;

  return (
    <div style={{ width: "100%", height: 360 }}>
      <ResponsiveContainer>
        <LineChart
          data={data}
          margin={{ top: 16, right: 32, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="year_month"
            tick={{ fontSize: 11, fill: "#374151" }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11, fill: "#374151" }}
            label={{
              value: "% / pt",
              angle: -90,
              position: "insideLeft",
              fontSize: 11,
              fill: "#6B7280",
            }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fontSize: 11, fill: "#374151" }}
            label={{
              value: "分 / g",
              angle: 90,
              position: "insideRight",
              fontSize: 11,
              fill: "#6B7280",
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#FFFFFF",
              border: "1px solid #E5E7EB",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value) =>
              typeof value === "number" ? value.toFixed(2) : "—"
            }
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            iconType="line"
          />
          {SERIES.map((s) => (
            <Line
              key={s.key}
              yAxisId={s.axis}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
          {benchmarkPct != null && (
            <ReferenceLine
              yAxisId="left"
              y={benchmarkPct}
              stroke="#C2526B"
              strokeDasharray="4 4"
              label={{
                value: `業界平均 ${benchmarkPct.toFixed(1)}%`,
                position: "insideTopRight",
                fill: "#C2526B",
                fontSize: 11,
              }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
