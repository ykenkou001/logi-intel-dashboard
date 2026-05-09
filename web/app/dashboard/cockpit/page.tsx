"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  fetchSamples,
  fetchTodayDecisions,
  logDecision,
  type CardState,
  type CockpitItem,
  type CockpitMetadata,
  type DecisionAxis,
  type DecisionStatus,
  type SampleCompany,
  type ToolResponse,
  type VerdictLevel,
} from "@/lib/api";
import { DECISION_AXIS_LABEL, VERDICT_LEVEL_LABEL } from "@/lib/labels";

const AXIS_ORDER: DecisionAxis[] = ["compliance", "kpi_reach", "measure_pick"];

const HEALTH_BG: Record<VerdictLevel, string> = {
  green: "bg-emerald-50 border-emerald-300 text-emerald-900",
  yellow: "bg-amber-50 border-amber-300 text-amber-900",
  red: "bg-rose-50 border-rose-400 text-rose-900",
};

const HEALTH_DOT: Record<VerdictLevel, string> = {
  green: "bg-emerald-500",
  yellow: "bg-amber-500",
  red: "bg-rose-500",
};

const STATE_BADGE: Record<CardState, { label: string; cls: string }> = {
  attention_needed: {
    label: "要対応",
    cls: "bg-rose-100 text-rose-700 border-rose-200",
  },
  healthy: {
    label: "健全",
    cls: "bg-emerald-100 text-emerald-700 border-emerald-200",
  },
  insufficient_data: {
    label: "計測不足",
    cls: "bg-amber-100 text-amber-800 border-amber-200",
  },
  out_of_scope: {
    label: "対象外",
    cls: "bg-gray-100 text-gray-600 border-gray-200",
  },
};

const ROLE_LABEL: Record<string, string> = {
  cfo: "CFO",
  sales: "営業",
  operation: "現場",
  partner: "取引先",
  board: "取締役会",
};

const EVIDENCE_LABEL: Record<string, string> = {
  cost: "コスト",
  legal: "法令",
  supply: "オペ",
  brand_risk: "ブランド",
};

const DELTA_KEY_LABEL: Record<string, string> = {
  load_factor_pct: "積載率(%)",
  wait_time_avg_min: "荷待ち平均(分)",
  wait_time_max_min: "荷待ち最大(分)",
  handling_time_avg_min: "荷役平均(分)",
  co2_intensity_g_per_tonkm: "CO2 原単位(g/トンキロ)",
};

function formatDelta(key: string, v: number | null): string | null {
  if (v == null) return null;
  const sign = v > 0 ? "+" : "";
  if (key === "load_factor_pct") return `${sign}${v.toFixed(1)}pp`;
  return `${sign}${v.toFixed(1)}`;
}

function CockpitCard({
  item,
  companyId,
  onDecisionLogged,
}: {
  item: CockpitItem;
  companyId: string;
  onDecisionLogged: (axis: DecisionAxis, decision: DecisionStatus) => void;
}) {
  const [submitting, setSubmitting] = useState<DecisionStatus | null>(null);
  const [logged, setLogged] = useState<DecisionStatus | null>(null);
  const [showObjections, setShowObjections] = useState(false);

  const badge = STATE_BADGE[item.card_state];

  async function submitDecision(decision: DecisionStatus) {
    setSubmitting(decision);
    try {
      await logDecision(companyId, {
        cockpit_item_id: item.item_id,
        decision,
        decided_by: "web_ui",
      });
      setLogged(decision);
      onDecisionLogged(item.decision_axis, decision);
    } catch (e) {
      // 失敗時は alert で通知（簡易実装）
      const msg = e instanceof Error ? e.message : "通信エラー";
      window.alert(`意思決定ログの記録に失敗しました: ${msg}`);
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold text-[#1F4E79]">
          {DECISION_AXIS_LABEL[item.decision_axis]}
        </span>
        <span
          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badge.cls}`}
        >
          {badge.label}
        </span>
      </div>

      <h4 className="text-sm font-bold text-gray-900 leading-snug mb-2">
        {item.headline}
      </h4>
      <p className="text-xs text-gray-700 leading-relaxed mb-3">
        {item.rationale}
      </p>

      <div className="border-t border-gray-100 pt-3 mb-3 grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="text-[10px] text-gray-500">緊急度</div>
          <div
            className="text-base font-bold text-rose-700"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {item.urgency_score.toFixed(0)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500">インパクト</div>
          <div
            className="text-base font-bold text-blue-700"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {item.impact_score.toFixed(0)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500">自信度</div>
          <div
            className="text-base font-bold text-emerald-700"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {item.confidence_score.toFixed(0)}
          </div>
        </div>
      </div>

      <div className="text-[11px] text-gray-600 mb-3 space-y-1">
        <div className="flex items-start gap-1.5">
          <span className="text-gray-400 flex-shrink-0">📅</span>
          <span>
            <strong>{item.deadline_label}</strong>
            {item.next_review_due && (
              <span className="text-gray-400 ml-1.5">
                （次レビュー {item.next_review_due}）
              </span>
            )}
          </span>
        </div>
        {item.days_pending > 0 && (
          <div className="flex items-start gap-1.5">
            <span className="text-gray-400 flex-shrink-0">⏱</span>
            <span className="text-amber-800">
              滞留 <strong>{item.days_pending}</strong> 日
            </span>
          </div>
        )}
        {item.delta_from_last && (
          <div className="flex items-start gap-1.5">
            <span className="text-gray-400 flex-shrink-0">📈</span>
            <span>{item.delta_from_last}</span>
          </div>
        )}
        {item.estimated_pnl_jpy != null && item.estimated_pnl_jpy !== 0 && (
          <div className="flex items-start gap-1.5">
            <span className="text-gray-400 flex-shrink-0">💴</span>
            <span>
              想定インパクト 年 約{" "}
              <strong>{(item.estimated_pnl_jpy / 1e8).toFixed(2)}</strong> 億円
            </span>
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-lg p-2.5 mb-3">
        <div className="text-[10px] font-bold text-blue-900 mb-1 uppercase tracking-wider">
          推奨アクション
        </div>
        <div className="text-xs text-blue-950 leading-relaxed">
          {item.suggested_action}
        </div>
      </div>

      {item.anticipated_objections.length > 0 && (
        <div className="mb-3">
          <button
            onClick={() => setShowObjections((v) => !v)}
            className="text-[11px] text-gray-600 hover:text-[#1F4E79] flex items-center gap-1"
          >
            <span>{showObjections ? "▼" : "▶"}</span>
            <span>
              想定反論 {item.anticipated_objections.length} 件（J4 薄版）
            </span>
          </button>
          {showObjections && (
            <ul className="mt-2 space-y-2">
              {item.anticipated_objections.map((o, i) => (
                <li
                  key={i}
                  className="text-[11px] bg-gray-50 border border-gray-200 rounded-md p-2"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-gray-700">
                      {ROLE_LABEL[o.role] ?? o.role}
                    </span>
                    <span className="text-gray-400">/</span>
                    <span className="text-gray-500">
                      {EVIDENCE_LABEL[o.evidence_axis] ?? o.evidence_axis}
                    </span>
                  </div>
                  <div className="text-gray-700 leading-snug mb-1">
                    Q: {o.objection}
                  </div>
                  <div className="text-gray-900 leading-snug">
                    A: {o.rebuttal}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {item.card_state === "attention_needed" && (
        <div className="mt-auto pt-3 border-t border-gray-100">
          {logged ? (
            <div className="text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md px-3 py-2 text-center">
              ✓ 「{decisionLabel(logged)}」として I2 ログに記録しました
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-1.5">
              {(["adopt", "postpone", "reject"] as DecisionStatus[]).map(
                (d) => (
                  <button
                    key={d}
                    onClick={() => submitDecision(d)}
                    disabled={submitting !== null}
                    className={`text-[11px] font-semibold py-1.5 rounded-md border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${decisionBtnCls(d)}`}
                  >
                    {submitting === d ? "..." : decisionLabel(d)}
                  </button>
                ),
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function decisionLabel(d: DecisionStatus): string {
  return {
    pending: "保留",
    adopt: "採用",
    postpone: "延期",
    reject: "却下",
    escalate: "上申",
  }[d];
}

function decisionBtnCls(d: DecisionStatus): string {
  if (d === "adopt") return "bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100";
  if (d === "reject") return "bg-rose-50 text-rose-800 border-rose-200 hover:bg-rose-100";
  return "bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100";
}

export default function CockpitPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState<string>("sample_wholesale_01");
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
      setResult(
        await fetchTodayDecisions(companyId, { persistSnapshot: true }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "通信エラー");
    } finally {
      setLoading(false);
    }
  }

  const cockpit = useMemo<CockpitMetadata | null>(() => {
    const md = result?.metadata as CockpitMetadata | undefined;
    if (!md || !md.items) return null;
    return md;
  }, [result]);

  const sortedItems = useMemo(() => {
    if (!cockpit) return [];
    return [...cockpit.items].sort(
      (a, b) =>
        AXIS_ORDER.indexOf(a.decision_axis) -
        AXIS_ORDER.indexOf(b.decision_axis),
    );
  }, [cockpit]);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          CLO デイリーコックピット — 今日の3判断
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          朝 1 回開けば「未達 KPI ／ 放置リスク ／ 今週決める施策」が 3 件だけ並ぶ
          意思決定支援ビュー。緊急度・経営インパクト・自信度・想定反論（J4 薄版）
          まで 1 画面で確認でき、採用／保留／却下の意思決定を I2 ログ
          （append-only jsonl）に記録します。
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
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Spinner /> 集計中...
            </>
          ) : (
            "今日の3判断を生成"
          )}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {cockpit && (
        <>
          <div
            className={`rounded-xl border-2 px-5 py-4 flex items-start gap-3 ${HEALTH_BG[cockpit.overall_health]}`}
          >
            <span
              className={`mt-1 w-3 h-3 rounded-full ${HEALTH_DOT[cockpit.overall_health]} animate-pulse`}
            />
            <div className="flex-1">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-base font-bold uppercase">
                  {VERDICT_LEVEL_LABEL[cockpit.overall_health]}
                </span>
                <span className="text-xs opacity-80">
                  ({cockpit.overall_health.toUpperCase()})
                </span>
              </div>
              <div className="text-sm">{cockpit.one_line_summary}</div>
              {Object.values(cockpit.delta_from_yesterday).some(
                (v) => v !== null,
              ) && (
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs opacity-80">
                  <span className="opacity-60">前日比:</span>
                  {Object.entries(cockpit.delta_from_yesterday).map(
                    ([k, v]) => {
                      const formatted = formatDelta(k, v);
                      if (formatted == null) return null;
                      return (
                        <span key={k}>
                          {DELTA_KEY_LABEL[k] ?? k}{" "}
                          <strong
                            style={{ fontFamily: "var(--font-mono)" }}
                          >
                            {formatted}
                          </strong>
                        </span>
                      );
                    },
                  )}
                </div>
              )}
            </div>
            <div className="text-right text-[11px] opacity-70">
              <div>{cockpit.snapshot.snapshot_date}</div>
              <div className="mt-0.5">
                data_source: {cockpit.data_source}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {sortedItems.map((item) => (
              <CockpitCard
                key={item.item_id}
                item={item}
                companyId={cockpit.company_id}
                onDecisionLogged={() => {
                  /* I2 ログ記録の即時反映は次の生成時に days_pending に出る */
                }}
              />
            ))}
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-5 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <div className="text-gray-500 mb-0.5">積載率</div>
              <div
                className="text-lg font-bold text-gray-900"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {cockpit.snapshot.load_factor_pct != null
                  ? `${cockpit.snapshot.load_factor_pct.toFixed(0)}%`
                  : "未計測"}
              </div>
            </div>
            <div>
              <div className="text-gray-500 mb-0.5">荷待ち平均</div>
              <div
                className="text-lg font-bold text-gray-900"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {cockpit.snapshot.wait_time_avg_min != null
                  ? `${cockpit.snapshot.wait_time_avg_min.toFixed(0)} 分`
                  : "未計測"}
              </div>
            </div>
            <div>
              <div className="text-gray-500 mb-0.5">荷待ち最大</div>
              <div
                className="text-lg font-bold text-gray-900"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {cockpit.snapshot.wait_time_max_min != null
                  ? `${cockpit.snapshot.wait_time_max_min.toFixed(0)} 分`
                  : "—"}
              </div>
            </div>
            <div>
              <div className="text-gray-500 mb-0.5">2h超 便数</div>
              <div
                className="text-lg font-bold text-gray-900"
                style={{ fontFamily: "var(--font-mono)" }}
              >
                {cockpit.snapshot.over_2h_count_total}
              </div>
            </div>
          </div>
        </>
      )}

      {result && <ToolResponseDisplay response={result} />}
    </div>
  );
}
