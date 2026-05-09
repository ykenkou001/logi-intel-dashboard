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
  fetchStandardizationScore,
  type IndustryPackage,
  type IndustryPackageMetadata,
  type MeasureDetail,
  type SampleCompany,
  type StandardizationScoreResult,
  type StandardKpiDef,
  type ToolResponse,
} from "@/lib/api";
import { formatTargetValue, freqLabel, INDUSTRY_LABEL } from "@/lib/labels";

function scoreColor(score: number): string {
  if (score >= 80) return "bg-emerald-50 border-emerald-300 text-emerald-900";
  if (score >= 50) return "bg-amber-50 border-amber-300 text-amber-900";
  return "bg-rose-50 border-rose-300 text-rose-900";
}

function scoreDot(score: number): string {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-rose-500";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "標準遵守";
  if (score >= 50) return "改善余地大";
  return "標準逸脱";
}

function MissingKpiTable({
  missingIds,
  pkg,
}: {
  missingIds: string[];
  pkg: IndustryPackage | null;
}) {
  if (missingIds.length === 0) {
    return (
      <p className="text-xs text-emerald-700">未計測 KPI なし（全件履歴あり）</p>
    );
  }
  // package がある場合は KPI 詳細を引いて表示。無ければ ID のみ。
  const kpiByMetric: Record<string, StandardKpiDef> = {};
  if (pkg) {
    for (const k of pkg.kpis) {
      kpiByMetric[k.metric_id] = k;
    }
  }
  return (
    <table className="w-full text-xs border-collapse">
      <thead className="bg-rose-50 text-rose-900">
        <tr>
          <th className="text-left px-3 py-2 font-semibold">未計測 KPI</th>
          <th className="text-right px-3 py-2 font-semibold">標準目標</th>
          <th className="text-left px-3 py-2 font-semibold">頻度</th>
          <th className="text-left px-3 py-2 font-semibold">主管</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {missingIds.map((mid) => {
          const kpi = kpiByMetric[mid];
          return (
            <tr key={mid} className="hover:bg-gray-50">
              <td className="px-3 py-2">
                <div className="font-semibold text-gray-900">
                  {kpi?.label ?? mid}
                </div>
                <code
                  className="text-[10px] text-gray-400"
                  style={{ fontFamily: "var(--font-mono)" }}
                  aria-label={`内部識別子 ${mid}`}
                >
                  {mid}
                </code>
              </td>
              <td
                className="px-3 py-2 text-right text-gray-900"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {kpi
                  ? formatTargetValue(kpi.target_value, kpi.unit)
                  : "—"}
              </td>
              <td className="px-3 py-2 text-gray-700">
                {kpi ? freqLabel(kpi.frequency) : "—"}
              </td>
              <td className="px-3 py-2 text-gray-700">
                {kpi?.owner_role ?? "—"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function MissingMeasureList({
  missingIds,
  measureDetails,
}: {
  missingIds: string[];
  measureDetails: MeasureDetail[];
}) {
  if (missingIds.length === 0) {
    return (
      <p className="text-xs text-emerald-700">
        未採用 施策なし（全件 approved/required で採用済）
      </p>
    );
  }
  const detailById: Record<string, MeasureDetail> = {};
  for (const m of measureDetails) {
    detailById[m.measure_id] = m;
  }
  return (
    <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
      {missingIds.map((mid) => {
        const m = detailById[mid];
        return (
          <li
            key={mid}
            className="bg-rose-50 border border-rose-200 rounded-lg px-3 py-2.5"
          >
            <div className="font-semibold text-rose-900 mb-0.5">
              {m?.name ?? mid}
            </div>
            {m?.description && (
              <p className="text-[11px] text-rose-800/80 leading-relaxed mb-1 line-clamp-2">
                {m.description}
              </p>
            )}
            <code
              className="text-[10px] text-rose-700/60"
              style={{ fontFamily: "var(--font-mono)" }}
              aria-label={`施策ID ${mid}`}
            >
              {mid}
            </code>
          </li>
        );
      })}
    </ul>
  );
}

export default function StandardizationPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState<string>("sample_mfg_01");
  const [scoreResult, setScoreResult] = useState<ToolResponse | null>(null);
  const [pkgResult, setPkgResult] = useState<ToolResponse | null>(null);
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
      // 並列フェッチ：F2 スコア + 業種別パッケージ（差分テーブルで KPI 詳細を出すため）
      const [score, pkg] = await Promise.all([
        fetchStandardizationScore(companyId),
        fetchIndustryPackage(companyId).catch(() => null),
      ]);
      setScoreResult(score);
      setPkgResult(pkg);
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  const score = useMemo<StandardizationScoreResult | null>(() => {
    const md = scoreResult?.metadata as
      | StandardizationScoreResult
      | undefined;
    if (!md || md.score === undefined) return null;
    return md;
  }, [scoreResult]);

  const pkgMetadata = useMemo<IndustryPackageMetadata | null>(() => {
    const md = pkgResult?.metadata as IndustryPackageMetadata | undefined;
    if (!md || !md.package) return null;
    return md;
  }, [pkgResult]);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          F2 標準化スコア
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          業種別 CLO 標準パッケージへの準拠度を 0-100 で評価。coverage（KPI 履歴
          + 施策採用率）から unmanaged_deviation 件数 × 5pt の減点を引き、
          approved_better_practice ≥ 2 件で +5pt のボーナスを加算します。連鎖化
          事業者で loading 系施策（warehouse_dx_wms 等）を Override 採用すると
          c.8 強制ガードにより同等の追加減点が乗ります。
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
              <Spinner /> 算出中...
            </>
          ) : (
            "F2 スコアを算出"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {score && (
        <>
          <div
            className={`rounded-xl border-2 px-5 py-5 ${scoreColor(
              score.score,
            )}`}
          >
            <div className="flex items-start gap-4">
              <span
                className={`mt-2 w-3 h-3 rounded-full ${scoreDot(
                  score.score,
                )} animate-pulse`}
              />
              <div className="flex-1">
                <div className="flex items-baseline gap-3 mb-2">
                  <span
                    className="text-5xl font-bold"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {score.score.toFixed(1)}
                  </span>
                  <span className="text-sm font-semibold opacity-80">
                    / 100
                  </span>
                  <span className="text-base font-bold ml-2">
                    {scoreLabel(score.score)}
                  </span>
                </div>
                <div className="text-xs opacity-80 mb-1">
                  業種:{" "}
                  <strong>
                    {INDUSTRY_LABEL[score.base_package_category] ??
                      score.base_package_category}
                  </strong>{" "}
                  / coverage{" "}
                  <strong
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {score.coverage_pct.toFixed(1)}%
                  </strong>
                </div>
                <div className="text-xs opacity-80">
                  Override:{" "}
                  <strong>{score.deviation_count_total}</strong> 件 / 減点対象
                  unmanaged{" "}
                  <strong className="text-rose-700">
                    {score.deviation_count_unmanaged}
                  </strong>{" "}
                  件
                  {score.chain_franchise_loading_misuse_count > 0 && (
                    <>
                      {" "}
                      / ⚠️ 連鎖化 loading 誤用{" "}
                      <strong className="text-rose-700">
                        {score.chain_franchise_loading_misuse_count}
                      </strong>{" "}
                      件
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          <section className="bg-white rounded-xl border border-gray-100 p-5">
            <h4 className="text-sm font-bold text-gray-800 mb-3">
              算出根拠（rationale）
            </h4>
            <ul className="text-xs text-gray-700 space-y-1.5 list-disc list-inside">
              {score.rationale.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </section>

          <section className="bg-white rounded-xl border border-gray-100 p-5">
            <h4 className="text-sm font-bold text-gray-800 mb-3">
              未計測 KPI（{score.missing_kpi_ids.length} 件）
            </h4>
            <MissingKpiTable
              missingIds={score.missing_kpi_ids}
              pkg={pkgMetadata?.package ?? null}
            />
          </section>

          <section className="bg-white rounded-xl border border-gray-100 p-5">
            <h4 className="text-sm font-bold text-gray-800 mb-3">
              未採用 施策（{score.missing_measure_ids.length} 件）
            </h4>
            <MissingMeasureList
              missingIds={score.missing_measure_ids}
              measureDetails={pkgMetadata?.measure_details ?? []}
            />
          </section>

          <section className="bg-white rounded-xl border border-gray-100 p-5">
            <h4 className="text-sm font-bold text-gray-800 mb-3">差分テーブル</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
              <DiffStat
                label="標準 KPI 充足"
                value={
                  pkgMetadata
                    ? pkgMetadata.package.kpis.length -
                      score.missing_kpi_ids.length
                    : null
                }
                total={pkgMetadata?.package.kpis.length ?? null}
                tone="emerald"
              />
              <DiffStat
                label="標準 施策 採用"
                value={
                  pkgMetadata
                    ? pkgMetadata.package.measure_ids.length -
                      score.missing_measure_ids.length
                    : null
                }
                total={pkgMetadata?.package.measure_ids.length ?? null}
                tone="emerald"
              />
              <DiffStat
                label="未計測 KPI"
                value={score.missing_kpi_ids.length}
                total={pkgMetadata?.package.kpis.length ?? null}
                tone="rose"
              />
              <DiffStat
                label="未採用 施策"
                value={score.missing_measure_ids.length}
                total={pkgMetadata?.package.measure_ids.length ?? null}
                tone="rose"
              />
            </div>
          </section>
        </>
      )}

      {scoreResult && <ToolResponseDisplay response={scoreResult} />}
    </div>
  );
}

function DiffStat({
  label,
  value,
  total,
  tone,
}: {
  label: string;
  value: number | null;
  total: number | null;
  tone: "emerald" | "rose";
}) {
  const cls =
    tone === "emerald"
      ? "bg-emerald-50 border-emerald-200 text-emerald-900"
      : "bg-rose-50 border-rose-200 text-rose-900";
  return (
    <div className={`rounded-lg border px-3 py-3 ${cls}`}>
      <div className="text-[11px] opacity-80 mb-0.5">{label}</div>
      <div
        className="text-2xl font-bold"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {value != null ? value : "—"}
        {total != null && (
          <span className="text-xs font-normal opacity-70 ml-1">
            / {total}
          </span>
        )}
      </div>
    </div>
  );
}
