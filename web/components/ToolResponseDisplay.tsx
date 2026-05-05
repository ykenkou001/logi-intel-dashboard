"use client";

import type { ToolResponse } from "@/lib/api";
import { fileDownloadUrl } from "@/lib/api";

const FILE_CONFIG: Record<
  string,
  { label: string; sub: string; color: string; bg: string }
> = {
  ppt: {
    label: "PPT",
    sub: "PPT（経営会議用）",
    color: "text-orange-700",
    bg: "bg-orange-50 border-orange-200 hover:bg-orange-100",
  },
  docx: {
    label: "Word",
    sub: "Word（様式第3別紙）",
    color: "text-blue-700",
    bg: "bg-blue-50 border-blue-200 hover:bg-blue-100",
  },
  excel: {
    label: "Excel",
    sub: "Excel（数値表 + 出典）",
    color: "text-green-700",
    bg: "bg-green-50 border-green-200 hover:bg-green-100",
  },
  markdown: {
    label: "MD",
    sub: "Markdown",
    color: "text-gray-700",
    bg: "bg-gray-50 border-gray-200 hover:bg-gray-100",
  },
  pdf: {
    label: "PDF",
    sub: "PDF",
    color: "text-red-700",
    bg: "bg-red-50 border-red-200 hover:bg-red-100",
  },
  template_xlsx: {
    label: "XLSX",
    sub: "Excel テンプレ",
    color: "text-green-700",
    bg: "bg-green-50 border-green-200 hover:bg-green-100",
  },
  profile_json: {
    label: "JSON",
    sub: "プロフィール JSON",
    color: "text-violet-700",
    bg: "bg-violet-50 border-violet-200 hover:bg-violet-100",
  },
};

export function ToolResponseDisplay({
  response,
  showFiles = true,
}: {
  response: ToolResponse;
  showFiles?: boolean;
}) {
  const fileEntries = Object.entries(response.files);

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <pre
          className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
          style={{ fontFamily: "inherit" }}
        >
          {response.summary}
        </pre>
      </div>

      {/* Files */}
      {showFiles && fileEntries.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
            生成成果物
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {fileEntries.map(([key, path]) => {
              const cfg = FILE_CONFIG[key] ?? {
                label: key.toUpperCase(),
                sub: key,
                color: "text-gray-700",
                bg: "bg-gray-50 border-gray-200 hover:bg-gray-100",
              };
              return (
                <a
                  key={key}
                  href={fileDownloadUrl(path)}
                  target="_blank"
                  rel="noreferrer"
                  className={`flex items-center gap-3 border rounded-lg p-3 transition-colors duration-150 ${cfg.bg}`}
                >
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 bg-white border border-current ${cfg.color}`}
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
                      {cfg.sub}
                    </div>
                    <div className="text-xs text-gray-400 truncate">
                      {String(path).split("/").pop()}
                    </div>
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
      )}

      {/* Citations */}
      {response.citations.length > 0 && (
        <details className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <summary className="px-6 py-4 cursor-pointer text-sm text-gray-500 hover:bg-gray-50 transition-colors list-none flex items-center justify-between">
            出典 ({response.citations.length} 件)
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
              {response.citations.map((c, i) => (
                <li key={`${c.url}-${i}`} className="text-xs">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#2E73AC] hover:underline"
                  >
                    {c.label}
                  </a>
                  {c.stats_data_id ? (
                    <span className="text-gray-400 ml-1">
                      — statsDataId={c.stats_data_id}
                    </span>
                  ) : null}
                  {c.notice_number ? (
                    <span className="text-gray-400 ml-1">
                      — {c.notice_number}
                    </span>
                  ) : null}
                  {c.ordinance_number ? (
                    <span className="text-gray-400 ml-1">
                      — {c.ordinance_number}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        </details>
      )}

      {/* Freshness warnings */}
      {response.freshness_warnings.length > 0 && (
        <details className="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
          <summary className="px-6 py-4 cursor-pointer text-sm text-amber-700 hover:bg-amber-100 transition-colors list-none flex items-center justify-between">
            <span className="flex items-center gap-2">
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
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
              鮮度警告 ({response.freshness_warnings.length} 件)
            </span>
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
          <div className="px-6 pb-4 border-t border-amber-200">
            <ul className="mt-3 space-y-1.5 text-xs text-amber-800 list-disc ml-4">
              {response.freshness_warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        </details>
      )}

      <DataSourceBadge dataSource={response.data_source} />
    </div>
  );
}

function DataSourceBadge({
  dataSource,
}: {
  dataSource: ToolResponse["data_source"];
}) {
  if (dataSource === "sample") {
    return (
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
          <strong>デモ用架空企業データ</strong> — 経営判断には使用不可。実データを取り込むには{" "}
          <a href="/dashboard/company" className="underline font-semibold">
            自社プロフィール入力
          </a>{" "}
          から Excel テンプレートを記入・アップロードしてください。
        </div>
      </div>
    );
  }
  if (dataSource === "actual") {
    return (
      <p className="text-xs text-gray-400">
        データ出所:{" "}
        <strong className="text-[#1F4E79]">自社実測データ</strong>
      </p>
    );
  }
  return (
    <p className="text-xs text-gray-400">
      データ出所: <strong>業界統計推計</strong>
    </p>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
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
      <span className="whitespace-pre-wrap">{message}</span>
    </div>
  );
}

export function Spinner({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24">
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
  );
}
