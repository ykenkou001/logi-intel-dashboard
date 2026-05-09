"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchIndustryPackage,
  fetchSamples,
  type IndustryPackage,
  type IndustryPackageMetadata,
  type MeasureDetail,
  type OverrideCategory,
  type OverrideEntry,
  type SampleCompany,
  type StandardKpiDef,
  type ToolResponse,
} from "@/lib/api";
import {
  DATA_SOURCE_LABEL,
  formatTargetValue,
  freqLabel,
  INDUSTRY_LABEL,
  OUTPUT_FORMAT_LABEL,
  OVERRIDE_CATEGORY_LABEL,
  REPORT_AUDIENCE_LABEL,
  targetValueMissingNote,
} from "@/lib/labels";
import { useFetchTool } from "@/lib/useFetchTool";

const OVERRIDE_BADGE: Record<OverrideCategory, string> = {
  unmanaged_deviation: "bg-rose-100 text-rose-800 border-rose-200",
  approved_better_practice: "bg-emerald-100 text-emerald-800 border-emerald-200",
  required_localization: "bg-blue-100 text-blue-800 border-blue-200",
  temporary_exception: "bg-amber-100 text-amber-800 border-amber-200",
};

function countByCategory(
  entries: OverrideEntry[],
): Record<OverrideCategory, number> {
  const counts: Record<OverrideCategory, number> = {
    unmanaged_deviation: 0,
    approved_better_practice: 0,
    required_localization: 0,
    temporary_exception: 0,
  };
  for (const e of entries) {
    counts[e.category] = (counts[e.category] ?? 0) + 1;
  }
  return counts;
}

function KpiTable({ kpis }: { kpis: StandardKpiDef[] }) {
  if (kpis.length === 0) {
    return <p className="text-xs text-gray-500">KPI 未登録</p>;
  }
  return (
    <table className="w-full text-xs border-collapse">
      <thead className="bg-gray-50 text-gray-600">
        <tr>
          <th className="text-left px-3 py-2 font-semibold">KPI</th>
          <th className="text-right px-3 py-2 font-semibold">標準目標</th>
          <th className="text-right px-3 py-2 font-semibold">業界平均</th>
          <th className="text-left px-3 py-2 font-semibold">頻度</th>
          <th className="text-left px-3 py-2 font-semibold">主管</th>
          <th className="text-left px-3 py-2 font-semibold">出典</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {kpis.map((kpi) => (
          <tr key={kpi.metric_id} className="hover:bg-gray-50 align-top">
            <td className="px-3 py-2">
              <div className="font-semibold text-gray-900">{kpi.label}</div>
              <code
                className="text-[10px] text-gray-400"
                style={{ fontFamily: "var(--font-mono)" }}
                aria-label={`内部識別子 ${kpi.metric_id}`}
              >
                {kpi.metric_id}
              </code>
            </td>
            <td className="px-3 py-2 text-right">
              <div
                className="text-gray-900"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {formatTargetValue(kpi.target_value, kpi.unit)}
              </div>
              {kpi.target_value == null && (
                <div className="text-[10px] text-gray-400 mt-0.5 leading-tight max-w-[180px]">
                  {targetValueMissingNote(kpi.legal_basis)}
                </div>
              )}
            </td>
            <td
              className="px-3 py-2 text-right text-gray-500"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {kpi.baseline_value != null
                ? `${kpi.baseline_value.toFixed(1)}${kpi.unit}`
                : "—"}
            </td>
            <td className="px-3 py-2 text-gray-700">
              {freqLabel(kpi.frequency)}
            </td>
            <td className="px-3 py-2 text-gray-700">{kpi.owner_role}</td>
            <td className="px-3 py-2">
              {kpi.legal_basis ? (
                <a
                  href={kpi.legal_basis}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[#2E73AC] hover:underline text-[11px]"
                >
                  根拠
                </a>
              ) : (
                <span className="text-gray-300 text-[11px]">—</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MeasureCardList({
  details,
  fallbackIds,
}: {
  details: MeasureDetail[];
  fallbackIds: string[];
}) {
  // measure_details がある場合はそれを優先。無い場合は ID のみのフォールバック表示。
  if (details.length === 0 && fallbackIds.length === 0) {
    return <p className="text-xs text-gray-500">標準施策が登録されていません</p>;
  }
  if (details.length === 0) {
    return (
      <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-800">
        {fallbackIds.map((mid) => (
          <li
            key={mid}
            className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2"
          >
            <code
              className="text-[12px]"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {mid}
            </code>
          </li>
        ))}
      </ul>
    );
  }
  return (
    <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {details.map((m) => (
        <li
          key={m.measure_id}
          className="border border-gray-100 rounded-lg p-3 bg-white hover:border-[#2E73AC]/30 transition-colors"
        >
          <div className="font-semibold text-sm text-gray-900 mb-1">
            {m.name}
          </div>
          <p className="text-xs text-gray-600 leading-relaxed mb-2 line-clamp-2">
            {m.description}
          </p>
          <div className="flex items-center gap-2 text-[10px] text-gray-400">
            <code
              style={{ fontFamily: "var(--font-mono)" }}
              aria-label={`施策ID ${m.measure_id}`}
            >
              {m.measure_id}
            </code>
            <span className="bg-gray-100 px-1.5 py-0.5 rounded">
              様式第3:{" "}
              {m.form3_section === "load"
                ? "積載率向上"
                : m.form3_section === "wait"
                  ? "荷待ち時間短縮"
                  : m.form3_section === "loading"
                    ? "荷役等時間短縮"
                    : m.form3_section}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function PackageDetail({
  pkg,
  override,
  measureDetails,
}: {
  pkg: IndustryPackage;
  override: IndustryPackageMetadata["override"];
  measureDetails: MeasureDetail[];
}) {
  const overrideCounts = useMemo(
    () => (override ? countByCategory(override.entries) : null),
    [override],
  );

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-gray-100 p-5">
        <div className="flex items-baseline gap-3 mb-2">
          <h3 className="text-lg font-bold text-[#1F4E79]">{pkg.label}</h3>
          <span
            className="text-xs text-gray-400"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            v{pkg.version}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
          <SummaryStat label="KPI" count={pkg.kpis.length} />
          <SummaryStat label="施策" count={pkg.measure_ids.length} />
          <SummaryStat label="会議" count={pkg.meetings.length} />
          <SummaryStat label="レポート" count={pkg.reports.length} />
          <SummaryStat label="データ項目" count={pkg.data_items.length} />
        </div>
        {pkg.notes.length > 0 && (
          <ul className="mt-4 list-disc list-inside text-xs text-gray-600 space-y-1">
            {pkg.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </div>

      {overrideCounts && override && (
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <h4 className="text-sm font-bold text-gray-800 mb-3">
            自社 Override（差分計 {override.entries.length} 件 / 最終レビュー{" "}
            {override.last_reviewed}）
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {(Object.keys(OVERRIDE_CATEGORY_LABEL) as OverrideCategory[]).map((cat) => (
              <div
                key={cat}
                className={`rounded-lg border px-3 py-2 ${OVERRIDE_BADGE[cat]}`}
              >
                <div className="text-[11px] font-semibold opacity-80">
                  {OVERRIDE_CATEGORY_LABEL[cat]}
                </div>
                <div
                  className="text-xl font-bold"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {overrideCounts[cat]}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Section title={`標準 KPI（${pkg.kpis.length} 件）`}>
        <KpiTable kpis={pkg.kpis} />
      </Section>

      <Section title={`標準施策（${pkg.measure_ids.length} 件）`}>
        <MeasureCardList
          details={measureDetails}
          fallbackIds={pkg.measure_ids}
        />
      </Section>

      <Section title={`標準会議体（${pkg.meetings.length} 件）`}>
        <div className="space-y-3">
          {pkg.meetings.map((m) => (
            <div
              key={m.meeting_id}
              className="border border-gray-100 rounded-lg p-3"
            >
              <div className="flex items-baseline justify-between">
                <span className="font-semibold text-sm text-gray-900">
                  {m.name}
                </span>
                <span className="text-[11px] text-gray-500">
                  {freqLabel(m.frequency)} / {m.standard_duration_min} 分
                </span>
              </div>
              <div className="text-[11px] text-gray-500 mt-0.5">
                参加: {m.participants.join("、") || "—"}
              </div>
              {m.agenda_items.length > 0 && (
                <ul className="text-[11px] text-gray-600 list-disc list-inside mt-1.5 space-y-0.5">
                  {m.agenda_items.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </Section>

      <Section title={`標準レポート（${pkg.reports.length} 件）`}>
        <ul className="space-y-2">
          {pkg.reports.map((r) => (
            <li
              key={r.report_id}
              className="flex items-baseline justify-between border border-gray-100 rounded-lg px-3 py-2 text-sm"
            >
              <span className="font-semibold text-gray-900">{r.name}</span>
              <span className="text-[11px] text-gray-500">
                {REPORT_AUDIENCE_LABEL[r.audience]} / {freqLabel(r.frequency)} /{" "}
                {OUTPUT_FORMAT_LABEL[r.output_format]}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={`標準データ項目（${pkg.data_items.length} 件）`}>
        <ul className="space-y-2">
          {pkg.data_items.map((d) => (
            <li
              key={d.data_item_id}
              className="flex items-baseline justify-between border border-gray-100 rounded-lg px-3 py-2 text-sm"
            >
              <span className="font-semibold text-gray-900">{d.label}</span>
              <span className="text-[11px] text-gray-500">
                {DATA_SOURCE_LABEL[d.source]} / {freqLabel(d.refresh_cadence)}
              </span>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

function SummaryStat({ label, count }: { label: string; count: number }) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-2">
      <div className="text-[11px] text-gray-500">{label}</div>
      <div
        className="text-2xl font-bold text-gray-900"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {count}
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-white rounded-xl border border-gray-100 p-5">
      <h4 className="text-sm font-bold text-gray-800 mb-3">{title}</h4>
      {children}
    </section>
  );
}

export default function IndustryPackagePage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState<string>("sample_mfg_01");
  const { data: result, loading, error, run } = useFetchTool<ToolResponse>();

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch(() => setSamples([]));
  }, []);

  async function handleSubmit() {
    await run(() => fetchIndustryPackage(companyId));
  }

  const metadata = useMemo<IndustryPackageMetadata | null>(() => {
    const md = result?.metadata as IndustryPackageMetadata | undefined;
    if (!md || !md.package) return null;
    return md;
  }, [result]);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          業種別 CLO 標準パッケージ
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          製造 / 卸 / 小売 / 連鎖化（FC本部）の 4 業種について、KPI ／ 施策 ／
          会議体 ／ レポート ／ データ項目の 5 要素を「標準型」として保持する
          ビュー。個社差分は Override 4 分類（管理外逸脱 ／ 承認済差別化 ／
          必要ローカル ／ 期限付き例外）で別管理し、F2 標準化スコアと連動します。
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
        </label>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Spinner /> 読込中...
            </>
          ) : (
            "業種別パッケージを表示"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {metadata && (
        <>
          <div className="rounded-xl border-2 border-[#1F4E79]/20 bg-[#1F4E79]/5 px-5 py-4">
            <div className="text-xs text-gray-500 mb-1">業種解決結果</div>
            <div className="flex items-baseline gap-3">
              <span className="text-2xl font-bold text-[#1F4E79]">
                {INDUSTRY_LABEL[metadata.base_industry] ??
                  metadata.base_industry}
              </span>
              <span className="text-xs text-gray-400 ml-auto">
                {metadata.company_id}
              </span>
            </div>
          </div>

          {metadata.chain_franchise_notice && (
            <div
              role="note"
              aria-label="連鎖化事業者の制度上の注意"
              className="rounded-xl border-2 border-amber-300 bg-amber-50 px-5 py-4"
            >
              <div className="flex items-start gap-3">
                <span className="text-amber-600 text-lg leading-none mt-0.5">
                  ⚖️
                </span>
                <div className="flex-1">
                  <div className="font-bold text-amber-900 mb-1">
                    {metadata.chain_franchise_notice.headline}
                  </div>
                  <p className="text-xs text-amber-800 leading-relaxed">
                    {metadata.chain_franchise_notice.scope_note}
                  </p>
                </div>
              </div>
            </div>
          )}

          <PackageDetail
            pkg={metadata.package}
            override={metadata.override}
            measureDetails={metadata.measure_details ?? []}
          />
        </>
      )}

      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
