"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchMeasureEval,
  fetchSamples,
  type MeasureEvalMetadata,
  type MeasureScoreSummary,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";
import { useFetchTool } from "@/lib/useFetchTool";

function formatJpy(value: number | null): string {
  if (value == null) return "—";
  if (value >= 1e8) return `${(value / 1e8).toFixed(2)}億円`;
  if (value >= 1e4) return `${(value / 1e4).toFixed(0)}万円`;
  return `${value.toLocaleString()}円`;
}

function formatYears(value: number | null): string {
  if (value == null) return "—";
  return `${value.toFixed(1)}年`;
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">
          {label}
        </span>
        <span
          className="text-xs font-bold text-gray-900"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {value.toFixed(0)}
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-[#2E73AC]"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function MeasureCard({
  rank,
  score,
  tone,
}: {
  rank: number;
  score: MeasureScoreSummary;
  tone: "top" | "bottom";
}) {
  const accent =
    tone === "top"
      ? "bg-emerald-50 border-emerald-200"
      : "bg-rose-50 border-rose-200";
  const rankBadge =
    tone === "top"
      ? "bg-emerald-600 text-white"
      : "bg-rose-600 text-white";
  const rankText = tone === "top" ? `Top ${rank}` : `Bottom ${rank}`;
  const noteLabel = tone === "top" ? "他施策との比較" : "不採用理由";

  return (
    <div className={`rounded-xl border-2 px-4 py-4 ${accent} flex flex-col`}>
      <div className="flex items-start gap-3 mb-3">
        <span
          className={`text-[10px] font-bold rounded-full px-2 py-0.5 ${rankBadge} flex-shrink-0`}
        >
          {rankText}
        </span>
        <div className="flex-1 min-w-0">
          <h4 className="font-bold text-gray-900 text-sm leading-snug">
            {score.measure.name}
          </h4>
          <code
            className="text-[10px] text-gray-500"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {score.measure.measure_id}
          </code>
        </div>
        <div className="text-right flex-shrink-0">
          <div
            className="text-2xl font-bold text-[#1F4E79]"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {score.total_score.toFixed(0)}
          </div>
          <div className="text-[10px] text-gray-500">/ 100</div>
        </div>
      </div>

      <p className="text-xs text-gray-700 leading-relaxed mb-3 line-clamp-3">
        {score.measure.description}
      </p>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <ScoreBar label="ROI 35%" value={score.roi_score} />
        <ScoreBar label="可能性 30%" value={score.feasibility_score} />
        <ScoreBar label="法令 25%" value={score.compliance_score} />
        <ScoreBar label="補助金 10%" value={score.subsidy_score} />
      </div>

      <dl className="text-[11px] grid grid-cols-2 gap-x-3 gap-y-1.5 mb-3 bg-white/60 rounded-md px-3 py-2">
        <dt className="text-gray-500">期待コスト削減/年</dt>
        <dd
          className="text-right font-bold text-gray-900"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {formatJpy(score.estimated_annual_cost_saving_jpy)}
        </dd>
        <dt className="text-gray-500">回収期間</dt>
        <dd
          className="text-right font-bold text-gray-900"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {formatYears(score.estimated_payback_years)}
        </dd>
        <dt className="text-gray-500">投資レンジ</dt>
        <dd
          className="text-right text-gray-700"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {formatJpy(score.measure.typical_investment_jpy_low)} 〜{" "}
          {formatJpy(score.measure.typical_investment_jpy_high)}
        </dd>
        <dt className="text-gray-500">実装難易度</dt>
        <dd
          className="text-right text-gray-700"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {score.measure.implementation_difficulty} / 5
        </dd>
      </dl>

      {score.comparison_note && (
        <div className="bg-white/80 border border-gray-200 rounded-md px-3 py-2 mb-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">
            {noteLabel}
          </div>
          <p className="text-xs text-gray-800 leading-relaxed">
            {score.comparison_note}
          </p>
        </div>
      )}

      {tone === "top" && (score.responsible_dept || score.monthly_kpi) && (
        <div className="border-t border-gray-200/70 pt-2 mt-auto text-[11px] space-y-1">
          {score.responsible_dept && (
            <div>
              <span className="text-gray-500">主管部門:</span>{" "}
              <strong className="text-gray-800">{score.responsible_dept}</strong>
            </div>
          )}
          {score.monthly_kpi && (
            <div>
              <span className="text-gray-500">月次 KPI:</span>{" "}
              <span className="text-gray-800">{score.monthly_kpi}</span>
            </div>
          )}
          {score.dependencies.length > 0 && (
            <div>
              <span className="text-gray-500">前提:</span>{" "}
              <span className="text-gray-800">
                {score.dependencies.join(" / ")}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

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

  const meta = useMemo<MeasureEvalMetadata | null>(() => {
    const md = result?.metadata as MeasureEvalMetadata | undefined;
    if (!md || md.company_id === undefined) return null;
    return md;
  }, [result]);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          施策評価エンジン（Top 3 推薦 + judgment trail）
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          プレイブック施策を ROI（35%）・実装可能性（30%）・法令適合度（25%）・補助金カバー率（10%）の
          4 軸で 0-100 スコアリングし、加重合計で <strong>Top 3</strong> を推薦します。
          経営会議で「<strong>なぜそれを選んだか</strong>」「<strong>他はなぜダメか</strong>」を即答できるよう、
          <strong> Bottom 3</strong>（不採用施策）も並べて表示し、各カードに比較ノートを付与します。
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
            "Top 3 + Bottom 3 を取得"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {meta && (
        <>
          <section className="rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3 text-xs text-gray-700 flex flex-wrap gap-x-5 gap-y-1">
            <span>
              評価対象:{" "}
              <strong className="text-gray-900">{meta.scored_count}</strong> 施策
              （絞込後）
            </span>
            <span>
              自社推定リソース:{" "}
              <strong className="text-gray-900">
                {meta.derived_resources.length > 0
                  ? meta.derived_resources.join(" / ")
                  : "なし"}
              </strong>
            </span>
          </section>

          {meta.top_recommendations.length > 0 && (
            <section>
              <h3 className="text-xs font-bold text-emerald-700 uppercase tracking-widest mb-3 flex items-center gap-2">
                <span className="w-1 h-4 bg-emerald-500 rounded-full" />
                推薦 Top 3 — 経営会議で「やる」と説明する施策
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {meta.top_recommendations.map((s, i) => (
                  <MeasureCard
                    key={s.measure.measure_id}
                    rank={i + 1}
                    score={s}
                    tone="top"
                  />
                ))}
              </div>
            </section>
          )}

          {meta.bottom_candidates.length > 0 && (
            <section>
              <h3 className="text-xs font-bold text-rose-700 uppercase tracking-widest mb-3 flex items-center gap-2">
                <span className="w-1 h-4 bg-rose-500 rounded-full" />
                不採用 Bottom 3 — 「なぜ選ばなかったか」の説明責任
              </h3>
              <p className="text-xs text-gray-500 mb-3 leading-relaxed">
                経営会議や外部レビューで「他の施策はなぜ却下したのか」と問われた際に、
                スコア差・主因軸・比較ノートでフラットに説明できるよう Bottom 3 を出力します。
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {meta.bottom_candidates.map((s, i) => (
                  <MeasureCard
                    key={s.measure.measure_id}
                    rank={i + 1}
                    score={s}
                    tone="bottom"
                  />
                ))}
              </div>
            </section>
          )}

          {meta.bottom_candidates.length === 0 &&
            meta.top_recommendations.length > 0 && (
              <section className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
                対象施策数が少ないため Bottom 3 は出力されていません（Top 推薦のみ）。
              </section>
            )}
        </>
      )}

      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
