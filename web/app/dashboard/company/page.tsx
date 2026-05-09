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
  type TemplatePurpose,
  type ToolResponse,
} from "@/lib/api";
import { useFetchTool } from "@/lib/useFetchTool";

const PURPOSE_OPTIONS: ReadonlyArray<{
  value: TemplatePurpose;
  title: string;
  subtitle: string;
  body: string;
}> = [
  {
    value: "annual",
    title: "計画策定（年 1 回）",
    subtitle: "annual ・ 既定",
    body:
      "中長期計画の網羅入力用。profile / sites / wait_time(年集計) / handling_time / kpi_history の 6 シート構成。年 1 回の計画策定に。",
  },
  {
    value: "monthly",
    title: "月次レビュー",
    subtitle: "monthly ・ KPI 中心",
    body:
      "月次集計用。wait_time の bucket_label を「2026-04 全体」のような月次集計形式にし、handling_time / kpi_history を残します。",
  },
  {
    value: "daily",
    title: "日次運用入力",
    subtitle: "daily ・ 軽量版",
    body:
      "コックピット／ヒートマップ向けの日次入力用。wait_time のみ（site×日付×slot）の軽量構成で、site_name と time_slot を埋めて配布。",
  },
];

export default function CompanyPage() {
  const [purpose, setPurpose] = useState<TemplatePurpose>("annual");
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // 独立した 2 操作はそれぞれ useFetchTool で管理
  const template = useFetchTool<ToolResponse>();
  const load = useFetchTool<ToolResponse>();

  // 表示用エラー: バリデーション > テンプレ生成 > 取込 の順で表示
  const error = validationError ?? template.error ?? load.error;

  async function handleGenerateTemplate() {
    setValidationError(null);
    await template.run(() => generateCompanyTemplate(purpose));
  }

  async function handleUpload() {
    if (!file) {
      setValidationError("Excel ファイル（.xlsx）を選択してください");
      return;
    }
    setValidationError(null);
    await load.run(() => loadCompanyProfile(file));
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
            下記から用途を選択し、Excel テンプレートを生成します。生成後、「生成成果物」セクションの
            XLSX リンクからダウンロードし、各シートに自社データを記入してください。
          </p>
          <fieldset className="space-y-2">
            <legend className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              テンプレ用途
            </legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {PURPOSE_OPTIONS.map((opt) => {
                const isSelected = purpose === opt.value;
                return (
                  <label
                    key={opt.value}
                    className={`cursor-pointer rounded-lg border p-3 flex flex-col gap-1 transition-colors ${
                      isSelected
                        ? "border-[#1F4E79] bg-[#1F4E79]/5"
                        : "border-gray-200 hover:border-[#2E73AC]/40 hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="template-purpose"
                      value={opt.value}
                      checked={isSelected}
                      onChange={() => setPurpose(opt.value)}
                      className="sr-only"
                    />
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-sm font-bold ${
                          isSelected ? "text-[#1F4E79]" : "text-gray-700"
                        }`}
                      >
                        {opt.title}
                      </span>
                      <span className="text-[10px] uppercase tracking-wider text-gray-400">
                        {opt.subtitle}
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-600 leading-snug">
                      {opt.body}
                    </p>
                  </label>
                );
              })}
            </div>
          </fieldset>
          <button
            onClick={handleGenerateTemplate}
            disabled={template.loading}
            className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {template.loading ? (
              <>
                <Spinner /> 生成中...
              </>
            ) : (
              `Excel テンプレを生成（${purpose}）`
            )}
          </button>
          {template.data && (
            <ToolResponseDisplay response={template.data} />
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
            disabled={load.loading || !file}
            className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-5 py-2.5 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {load.loading ? (
              <>
                <Spinner /> アップロード中...
              </>
            ) : (
              "アップロードして取込"
            )}
          </button>
          {load.data && <ToolResponseDisplay response={load.data} />}
        </div>
      </div>

      {error && <ErrorBanner message={error} />}
    </div>
  );
}
