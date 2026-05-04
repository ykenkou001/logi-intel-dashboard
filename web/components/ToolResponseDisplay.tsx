"use client";

import type { ToolResponse } from "@/lib/api";
import { fileDownloadUrl } from "@/lib/api";

const FILE_LABELS: Record<string, string> = {
  ppt: "PPT（経営会議用）",
  docx: "Word（様式第3別紙）",
  excel: "Excel（数値表 + 出典）",
  markdown: "Markdown",
  pdf: "PDF",
  template_xlsx: "Excel テンプレ",
  profile_json: "プロフィール JSON",
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
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed tabular-nums">
        {response.summary}
      </pre>

      {showFiles && fileEntries.length > 0 ? (
        <div>
          <h4 className="text-xs font-bold text-primary mb-2">生成成果物</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {fileEntries.map(([key, path]) => (
              <a
                key={key}
                href={fileDownloadUrl(path)}
                className="bg-primary/5 border border-primary/30 rounded p-3 text-sm hover:bg-primary/10 transition"
                target="_blank"
                rel="noreferrer"
              >
                <div className="font-bold text-primary">
                  {FILE_LABELS[key] ?? key}
                </div>
                <div className="text-xs text-muted truncate mt-0.5">{path}</div>
              </a>
            ))}
          </div>
        </div>
      ) : null}

      {response.citations.length > 0 ? (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer hover:text-primary">
            出典 ({response.citations.length} 件)
          </summary>
          <ul className="mt-2 space-y-1 ml-4">
            {response.citations.map((c, i) => (
              <li key={`${c.url}-${i}`}>
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary underline"
                >
                  {c.label}
                </a>
                {c.stats_data_id ? ` — statsDataId=${c.stats_data_id}` : null}
                {c.notice_number ? ` — ${c.notice_number}` : null}
                {c.ordinance_number ? ` — ${c.ordinance_number}` : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      {response.freshness_warnings.length > 0 ? (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer hover:text-primary">
            鮮度警告 ({response.freshness_warnings.length} 件)
          </summary>
          <ul className="mt-2 space-y-1 ml-4 list-disc">
            {response.freshness_warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </details>
      ) : null}

      <DataSourceBadge dataSource={response.data_source} />
    </div>
  );
}

function DataSourceBadge({ dataSource }: { dataSource: ToolResponse["data_source"] }) {
  if (dataSource === "sample") {
    return (
      <div className="bg-accent/10 border border-accent text-accent rounded p-3 text-xs">
        <strong>⚠️ デモ用架空企業データ</strong> — 経営判断には使用不可。
        実データを取り込むには{" "}
        <a href="/dashboard/company" className="underline">
          自社プロフィール入力
        </a>{" "}
        から Excel テンプレートを記入・アップロードしてください。
      </div>
    );
  }
  if (dataSource === "actual") {
    return (
      <div className="text-xs text-muted">
        データ出所: <span className="font-bold text-primary">自社実測データ</span>
      </div>
    );
  }
  return (
    <div className="text-xs text-muted">
      データ出所: <span className="font-bold">業界統計推計</span>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="bg-accent/10 border border-accent text-accent rounded p-4 text-sm whitespace-pre-wrap">
      {message}
    </div>
  );
}
