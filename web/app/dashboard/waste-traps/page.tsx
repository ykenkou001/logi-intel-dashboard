"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchSamples,
  fetchWasteTraps,
  type SampleCompany,
  type ToolResponse,
  type WasteTrapItem,
  type WasteTrapResult,
} from "@/lib/api";
import {
  ROOT_CAUSE_LABEL,
  safeguardLabel,
  TRAP_SEVERITY_LABEL,
  TRAP_SEVERITY_TONE,
} from "@/lib/labels";
import { useFetchTool } from "@/lib/useFetchTool";

function formatJpy(value: number | null): string {
  if (value == null) return "—";
  if (value >= 1e8) return `${(value / 1e8).toFixed(2)}億円`;
  if (value >= 1e4) return `${(value / 1e4).toFixed(0)}万円`;
  return `${value.toLocaleString()}円`;
}

function formatRatio(actual: number | null, denom: number | null): string {
  if (actual == null || denom == null || denom <= 0) return "—";
  const ratio = actual / denom;
  return `${(ratio * 100).toFixed(0)}%`;
}

function CountBadge({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "rose" | "amber" | "emerald" | "slate";
}) {
  const cls = {
    rose: "bg-rose-50 border-rose-200 text-rose-900",
    amber: "bg-amber-50 border-amber-200 text-amber-900",
    emerald: "bg-emerald-50 border-emerald-200 text-emerald-900",
    slate: "bg-slate-50 border-slate-200 text-slate-900",
  }[tone];
  return (
    <div className={`rounded-lg border px-3 py-3 text-center ${cls}`}>
      <div className="text-[11px] opacity-80 mb-0.5">{label}</div>
      <div
        className="text-2xl font-bold"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {value}
      </div>
    </div>
  );
}

function TrapCard({ item }: { item: WasteTrapItem }) {
  const tone = TRAP_SEVERITY_TONE[item.trap_severity];
  return (
    <div className={`rounded-xl border-2 px-5 py-4 ${tone.card}`}>
      <div className="flex items-start gap-3 mb-3">
        <span className={`mt-1.5 w-2.5 h-2.5 rounded-full ${tone.dot} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h4 className="font-bold text-gray-900 text-base">
              {item.measure_name}
            </h4>
            <span
              className={`inline-flex items-center gap-1 text-[11px] font-bold border rounded-full px-2 py-0.5 ${tone.badge}`}
            >
              {TRAP_SEVERITY_LABEL[item.trap_severity]}
            </span>
            {item.investment_freeze_recommended && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold bg-rose-600 text-white rounded-full px-2 py-0.5">
                投資凍結を推奨
              </span>
            )}
          </div>
          <code
            className="text-[10px] text-gray-500"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {item.measure_id}
          </code>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3 text-xs">
        <div className="bg-white/60 rounded-md px-2.5 py-2">
          <div className="text-gray-500 mb-0.5">投資額</div>
          <div
            className="font-bold text-gray-900"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {formatJpy(item.invested_jpy)}
          </div>
        </div>
        <div className="bg-white/60 rounded-md px-2.5 py-2">
          <div className="text-gray-500 mb-0.5">期待効果/年</div>
          <div
            className="font-bold text-gray-900"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {formatJpy(item.expected_effect_jpy)}
          </div>
        </div>
        <div className="bg-white/60 rounded-md px-2.5 py-2">
          <div className="text-gray-500 mb-0.5">実績効果/年</div>
          <div
            className="font-bold text-gray-900"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {formatJpy(item.actual_effect_jpy)}
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">
            実績/投資 {formatRatio(item.actual_effect_jpy, item.invested_jpy)}
          </div>
        </div>
        <div className="bg-white/60 rounded-md px-2.5 py-2">
          <div className="text-gray-500 mb-0.5">経過月数</div>
          <div
            className="font-bold text-gray-900"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {item.months_since_start != null
              ? `${item.months_since_start} ヶ月`
              : "—"}
          </div>
        </div>
      </div>

      <div className="bg-white/70 rounded-md px-3 py-2.5 text-xs space-y-1.5">
        <div>
          <span className="text-gray-500">推定原因:</span>{" "}
          <strong className="text-gray-900">
            {ROOT_CAUSE_LABEL[item.suspected_root_cause]}
          </strong>
        </div>
        <div>
          <span className="text-gray-500">推奨対応:</span>{" "}
          <span className="text-gray-800">{item.suggested_remediation}</span>
        </div>
        {item.safeguard_triggered.length > 0 && (
          <div className="pt-1.5 border-t border-gray-200/70">
            <div className="text-gray-500 mb-1">
              発火セーフガード（誤検知抑止のため severity を低に固定）:
            </div>
            <ul className="flex flex-wrap gap-1.5">
              {item.safeguard_triggered.map((s) => (
                <li
                  key={s}
                  className="text-[10px] bg-gray-100 text-gray-700 rounded px-2 py-0.5 border border-gray-200"
                >
                  {safeguardLabel(s)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default function WasteTrapsPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState<string>("sample_mfg_01");
  const { data, loading, error, run } = useFetchTool<ToolResponse>();

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch(() => setSamples([]));
  }, []);

  async function handleSubmit() {
    // measure_runs は空配列で送る → 永続化済み実行記録があればそれで分析、
    // 無ければ items 0 件（「データ未登録」表示）。
    await run(() => fetchWasteTraps(companyId, []));
  }

  const result = useMemo<WasteTrapResult | null>(() => {
    const md = data?.metadata as WasteTrapResult | undefined;
    if (!md || md.company_id === undefined) return null;
    return md;
  }, [data]);

  const sortedItems = useMemo(() => {
    if (!result) return [];
    const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return [...result.items].sort(
      (a, b) =>
        (order[a.trap_severity] ?? 9) - (order[b.trap_severity] ?? 9),
    );
  }, [result]);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          J2 罠スコア — 効果が出ていない施策の検出
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          施策実行記録（投資額・期待効果・実績効果）から「投資が回っていない罠」を検出します。
          立ち上げ期間 / データ欠損 / サンプル数不足 / 季節性 / 外部要因 / 投資回収前 の
          <strong> 6 軸セーフガード</strong>
          が発火した場合は重大度を低に固定し、誤検知を抑止します。
          重大かつ規模不適合・KPI 設計誤り・実装品質に該当する場合は
          <strong> 投資凍結推奨</strong>として表示されます。
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <label className="block mb-5">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1.5">
            会社 ID
          </span>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
          >
            {samples.length === 0 && (
              <option value="sample_mfg_01">sample_mfg_01（製造）</option>
            )}
            {samples.map((s) => (
              <option key={s.company_id} value={s.company_id}>
                {s.company_id} — {s.name}
              </option>
            ))}
          </select>
          <p className="text-[11px] text-gray-500 mt-2 leading-relaxed">
            outputs/measure_runs/&lt;company_id&gt;.json に永続化された
            実行記録を使用します。記録が無い場合は 0 件表示になります。
          </p>
        </label>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Spinner /> 検出中...
            </>
          ) : (
            "J2 罠スコアを検出"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {result && (
        <>
          <section>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
              検出サマリ
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <CountBadge label="重大" value={result.high_count} tone="rose" />
              <CountBadge
                label="要注意"
                value={result.medium_count}
                tone="amber"
              />
              <CountBadge
                label="軽微 / 保留"
                value={result.low_count}
                tone="emerald"
              />
              <CountBadge
                label="投資凍結推奨"
                value={result.investment_freeze_count}
                tone={result.investment_freeze_count > 0 ? "rose" : "slate"}
              />
            </div>
          </section>

          {sortedItems.length === 0 ? (
            <section className="bg-white rounded-xl border border-gray-100 px-5 py-8 text-center">
              <p className="text-sm text-gray-600 leading-relaxed">
                施策実行記録が登録されていません。
              </p>
              <p className="text-xs text-gray-500 mt-2 leading-relaxed">
                MCP ツール{" "}
                <code
                  className="text-[11px] bg-gray-100 rounded px-1.5 py-0.5"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  logi_clo_waste_traps
                </code>
                {" "}または REST{" "}
                <code
                  className="text-[11px] bg-gray-100 rounded px-1.5 py-0.5"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  POST /api/v1/clo/waste-traps/{"{id}"}
                </code>
                {" "}に measure_runs を渡すと永続化されます。
              </p>
            </section>
          ) : (
            <section>
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
                罠候補一覧（重大度順）
              </h3>
              <ul className="space-y-3">
                {sortedItems.map((item) => (
                  <li key={item.measure_id}>
                    <TrapCard item={item} />
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {data && <ToolResponseDisplay response={data} />}
    </div>
  );
}
