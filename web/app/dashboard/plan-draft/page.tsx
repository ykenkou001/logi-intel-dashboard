"use client";

import { useEffect, useState } from "react";
import {
  fetchSamples,
  fileDownloadUrl,
  generatePlanDraft,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";
import { useFetchTool } from "@/lib/useFetchTool";

const FILE_CONFIG: Record<
  string,
  { label: string; sub: string; color: string; bg: string }
> = {
  ppt: {
    label: "PPT",
    sub: "経営会議用・最優先",
    color: "text-orange-700",
    bg: "bg-orange-50 border-orange-200 hover:bg-orange-100",
  },
  docx: {
    label: "Word",
    sub: "様式第3別紙・e-Gov 提出用",
    color: "text-blue-700",
    bg: "bg-blue-50 border-blue-200 hover:bg-blue-100",
  },
  excel: {
    label: "Excel",
    sub: "数値表 + 出典シート",
    color: "text-green-700",
    bg: "bg-green-50 border-green-200 hover:bg-green-100",
  },
  markdown: {
    label: "MD",
    sub: "人間レビュー用",
    color: "text-gray-700",
    bg: "bg-gray-50 border-gray-200 hover:bg-gray-100",
  },
};

export default function PlanDraftPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState("sample_mfg_01");
  const [samplesError, setSamplesError] = useState<string | null>(null);
  const { data: result, loading, error: fetchError, run, reset } = useFetchTool<ToolResponse>();
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
    reset();
    await run(() => generatePlanDraft(companyId));
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          計画書ドラフト統合生成
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Step 1〜6（業界ベンチマーク・ドライバー需給・適用判定・数値目標・施策効果・
          認定事業マッチング）を順次実行し、PPT / Word（様式第3別紙）/ Excel /
          Markdown の 4 種類を一括生成します。生成には 30〜60 秒かかる場合があります。
        </p>
      </div>

      {/* Form */}
      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          対象企業
        </label>
        <select
          value={companyId}
          onChange={(e) => setCompanyId(e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition mb-4"
        >
          {samples.map((s) => (
            <option key={s.company_id} value={s.company_id}>
              {s.name} ({s.company_id})
            </option>
          ))}
        </select>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-[#1F4E79] text-white rounded-lg px-6 py-3 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
        >
          {loading ? (
            <>
              <svg
                className="animate-spin w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              生成中（30〜60 秒）...
            </>
          ) : (
            <>
              計画書を生成する
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
                />
              </svg>
            </>
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm flex items-start gap-3">
          <svg
            className="w-4 h-4 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          {/* Download cards */}
          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h3 className="text-sm font-bold text-gray-700 mb-4">
              生成成果物をダウンロード
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(result.files).map(([key, path]) => {
                const cfg = FILE_CONFIG[key] ?? {
                  label: key.toUpperCase(),
                  sub: "",
                  color: "text-gray-700",
                  bg: "bg-gray-50 border-gray-200 hover:bg-gray-100",
                };
                return (
                  <a
                    key={key}
                    href={fileDownloadUrl(path)}
                    download={String(path).split("/").pop() ?? ""}
                    rel="noreferrer"
                    className={`flex items-center gap-3 border rounded-lg p-4 transition-colors duration-150 ${cfg.bg}`}
                  >
                    <div
                      className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-white border ${cfg.color} border-current`}
                    >
                      <span
                        className="text-xs font-bold"
                        style={{ fontFamily: "var(--font-mono)" }}
                      >
                        {cfg.label}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className={`font-bold text-sm ${cfg.color}`}>
                        {cfg.label}
                      </div>
                      <div className="text-xs text-gray-500">{cfg.sub}</div>
                    </div>
                    <svg
                      className={`w-4 h-4 flex-shrink-0 ${cfg.color}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                      />
                    </svg>
                  </a>
                );
              })}
            </div>
          </div>

          {/* Summary */}
          <details
            open
            className="bg-white rounded-xl border border-gray-100 overflow-hidden"
          >
            <summary className="px-6 py-4 cursor-pointer font-bold text-sm text-[#1F4E79] hover:bg-gray-50 transition-colors list-none flex items-center justify-between">
              統合サマリー
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
              </svg>
            </summary>
            <div className="px-6 pb-5 border-t border-gray-100">
              <pre className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed mt-4 font-sans">
                {result.summary}
              </pre>
            </div>
          </details>

          {/* Citations */}
          <details className="bg-white rounded-xl border border-gray-100 overflow-hidden">
            <summary className="px-6 py-4 cursor-pointer text-sm text-gray-500 hover:bg-gray-50 transition-colors list-none flex items-center justify-between">
              出典 ({result.citations.length} 件)
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
              </svg>
            </summary>
            <div className="px-6 pb-4 border-t border-gray-100">
              <ul className="mt-3 space-y-1.5">
                {result.citations.map((c) => (
                  <li key={c.url}>
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-[#2E73AC] hover:underline"
                    >
                      {c.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </details>

          {/* Data source */}
          {result.data_source === "sample" ? (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-800 flex items-start gap-3">
              <svg
                className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
              <div>
                <strong>デモ用架空企業データ</strong>{" "}
                — 経営判断には使用不可。実データを取り込むには{" "}
                <a
                  href="/dashboard/company"
                  className="underline font-semibold"
                >
                  自社プロフィール入力
                </a>{" "}
                から Excel テンプレートを記入・アップロードしてください。
              </div>
            </div>
          ) : (
            <p className="text-xs text-gray-400">
              データ出所:{" "}
              <strong>
                {result.data_source === "actual"
                  ? "自社実測データ"
                  : "業界統計推計"}
              </strong>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
