"use client";

import { useEffect, useState } from "react";
import {
  fetchSamples,
  fileDownloadUrl,
  generatePlanDraft,
  type SampleCompany,
  type ToolResponse,
} from "@/lib/api";

const FILE_LABELS: Record<string, string> = {
  ppt: "PPT（経営会議用・最優先）",
  docx: "Word（様式第3別紙・e-Gov 提出用）",
  excel: "Excel（数値表 + 出典シート）",
  markdown: "Markdown（人間レビュー用）",
};

export default function PlanDraftPage() {
  const [samples, setSamples] = useState<SampleCompany[]>([]);
  const [companyId, setCompanyId] = useState("sample_mfg_01");
  const [result, setResult] = useState<ToolResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then(setSamples)
      .catch((e) => setError(e instanceof Error ? e.message : "サンプル取得失敗"));
  }, []);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await generatePlanDraft(companyId);
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "計画書生成失敗");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-primary">計画書ドラフト統合生成</h2>
      <p className="text-sm text-gray-700 leading-relaxed">
        Step 1〜6（業界ベンチマーク・ドライバー需給・適用判定・数値目標・施策効果・
        認定事業マッチング）を順次実行し、PPT / Word（様式第3別紙）/ Excel / Markdown
        の 4 種類を一括生成します。生成には 30〜60 秒かかる場合があります。
      </p>

      <div className="bg-white rounded-lg shadow p-6 flex gap-3 items-end">
        <label className="flex-1">
          <span className="text-xs text-muted block mb-1">対象企業</span>
          <select
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white"
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
          className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
        >
          {loading ? "生成中..." : "計画書を生成"}
        </button>
      </div>

      {error ? (
        <div className="bg-accent/10 border border-accent text-accent rounded p-4 text-sm">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-primary mb-2">生成成果物</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {Object.entries(result.files).map(([key, path]) => (
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

          <details>
            <summary className="cursor-pointer text-sm font-bold text-primary">
              統合サマリー
            </summary>
            <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono mt-2 leading-relaxed">
              {result.summary}
            </pre>
          </details>

          <details className="text-xs text-muted">
            <summary className="cursor-pointer hover:text-primary">
              出典 ({result.citations.length} 件)
            </summary>
            <ul className="mt-2 space-y-1 ml-4">
              {result.citations.map((c) => (
                <li key={c.url}>
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline"
                  >
                    {c.label}
                  </a>
                </li>
              ))}
            </ul>
          </details>

          <div className="text-xs text-muted">
            データ出所:{" "}
            <span className="font-bold">
              {result.data_source === "actual" ? "実測データ" : "業界統計推計"}
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
