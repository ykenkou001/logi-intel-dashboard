"use client";

import { useState } from "react";
import { ErrorBanner, ToolResponseDisplay } from "@/components/ToolResponseDisplay";
import {
  generateCompanyTemplate,
  loadCompanyProfile,
  type ToolResponse,
} from "@/lib/api";

export default function CompanyPage() {
  const [templateResult, setTemplateResult] = useState<ToolResponse | null>(null);
  const [loadResult, setLoadResult] = useState<ToolResponse | null>(null);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [loadLoading, setLoadLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  async function handleGenerateTemplate() {
    setTemplateLoading(true);
    setError(null);
    try {
      const response = await generateCompanyTemplate();
      setTemplateResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "テンプレ生成失敗");
    } finally {
      setTemplateLoading(false);
    }
  }

  async function handleUpload() {
    if (!file) {
      setError("Excel ファイル（.xlsx）を選択してください");
      return;
    }
    setLoadLoading(true);
    setError(null);
    try {
      const response = await loadCompanyProfile(file);
      setLoadResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "アップロード失敗");
    } finally {
      setLoadLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-primary">自社プロフィール入力</h2>
      <p className="text-sm text-gray-700 leading-relaxed">
        Excel テンプレートをダウンロードし、profile / sites / wait_time / handling_time /
        kpi_history シートに自社データを記入後、ここからアップロードして CompanyProfile を
        構築・JSON 永続化します。サンプル3社からの脱却・推計値→実測値への切替に必須です。
      </p>

      <section className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="text-sm font-bold text-primary">Step 1: テンプレート DL</h3>
        <p className="text-xs text-gray-700">
          下記ボタンで Excel テンプレートを生成します。生成後、「PPT/Word 等」のリンクと
          同じ要領で `template_xlsx` リンクからダウンロードしてください。
        </p>
        <button
          onClick={handleGenerateTemplate}
          disabled={templateLoading}
          className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
        >
          {templateLoading ? "生成中..." : "Excel テンプレを生成"}
        </button>
        {templateResult ? <ToolResponseDisplay response={templateResult} /> : null}
      </section>

      <section className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="text-sm font-bold text-primary">Step 2: 記入済み Excel をアップロード</h3>
        <p className="text-xs text-gray-700">
          記入後の Excel ファイル（.xlsx）を選択し、アップロードしてください。
          連鎖化事業者は handling_time シートを空にしてもかまいません。
        </p>
        <input
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <div>
          <button
            onClick={handleUpload}
            disabled={loadLoading || !file}
            className="bg-primary text-white rounded px-6 py-2 disabled:opacity-50"
          >
            {loadLoading ? "アップロード中..." : "アップロードして取込"}
          </button>
        </div>
        {loadResult ? <ToolResponseDisplay response={loadResult} /> : null}
      </section>

      {error ? <ErrorBanner message={error} /> : null}
    </div>
  );
}
