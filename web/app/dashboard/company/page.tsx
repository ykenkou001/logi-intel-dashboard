"use client";

import { useState } from "react";
import {
  ErrorBanner,
  Spinner,
  ToolResponseDisplay,
} from "@/components/ToolResponseDisplay";
import {
  generateCompanyTemplate,
  loadCompanyProfile,
  type ToolResponse,
} from "@/lib/api";

export default function CompanyPage() {
  const [templateResult, setTemplateResult] = useState<ToolResponse | null>(
    null
  );
  const [loadResult, setLoadResult] = useState<ToolResponse | null>(null);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [loadLoading, setLoadLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  async function handleGenerateTemplate() {
    setTemplateLoading(true);
    setError(null);
    try {
      setTemplateResult(await generateCompanyTemplate());
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
      setLoadResult(await loadCompanyProfile(file));
    } catch (e) {
      setError(e instanceof Error ? e.message : "アップロード失敗");
    } finally {
      setLoadLoading(false);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2
          className="text-2xl font-bold text-[#1F4E79] mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          自社プロフィール入力
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Excel テンプレートをダウンロードし、profile / sites / wait_time /
          handling_time / kpi_history シートに自社データを記入後、ここからアップロードして
          CompanyProfile を構築・JSON 永続化します。サンプル3社からの脱却・推計値→実測値への切替に必須です。
        </p>
      </div>

      {/* Step 1 */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
          <div className="w-7 h-7 rounded-full bg-[#1F4E79] text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
            1
          </div>
          <h3
            className="font-bold text-[#1F4E79] text-sm"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            Excel テンプレートを生成・ダウンロード
          </h3>
        </div>
        <div className="px-6 py-5 space-y-4">
          <p className="text-xs text-gray-600 leading-relaxed">
            下記ボタンで Excel テンプレートを生成します。生成後、「生成成果物」セクションの
            XLSX リンクからダウンロードし、各シートに自社データを記入してください。
          </p>
          <button
            onClick={handleGenerateTemplate}
            disabled={templateLoading}
            className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {templateLoading ? (
              <>
                <Spinner /> 生成中...
              </>
            ) : (
              "Excel テンプレを生成"
            )}
          </button>
          {templateResult && (
            <ToolResponseDisplay response={templateResult} />
          )}
        </div>
      </div>

      {/* Step 2 */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
          <div className="w-7 h-7 rounded-full bg-[#1F4E79] text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
            2
          </div>
          <h3
            className="font-bold text-[#1F4E79] text-sm"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            記入済み Excel をアップロード
          </h3>
        </div>
        <div className="px-6 py-5 space-y-4">
          <p className="text-xs text-gray-600 leading-relaxed">
            記入後の Excel ファイル（.xlsx）を選択し、アップロードしてください。
            連鎖化事業者は handling_time シートを空にしてもかまいません。
          </p>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Excel ファイル（.xlsx）
            </label>
            <label className="flex items-center gap-3 w-full border-2 border-dashed border-gray-200 rounded-lg px-4 py-4 cursor-pointer hover:border-[#2E73AC]/40 hover:bg-slate-50 transition-colors">
              <svg
                className="w-5 h-5 text-gray-400 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
              <div className="text-sm">
                {file ? (
                  <span className="text-[#1F4E79] font-medium">{file.name}</span>
                ) : (
                  <span className="text-gray-400">
                    クリックしてファイルを選択 または ドロップ
                  </span>
                )}
              </div>
              <input
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="sr-only"
              />
            </label>
          </div>
          <button
            onClick={handleUpload}
            disabled={loadLoading || !file}
            className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loadLoading ? (
              <>
                <Spinner /> アップロード中...
              </>
            ) : (
              "アップロードして取込"
            )}
          </button>
          {loadResult && <ToolResponseDisplay response={loadResult} />}
        </div>
      </div>

      {error && <ErrorBanner message={error} />}
    </div>
  );
}
