"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  type CategoryFinding,
  type CheckCategory,
  type CheckCloStatus,
  type CheckFreightTonsBand,
  type CheckIndustryHint,
  type CheckMetadata,
  type CheckRequest,
  type CheckVehiclesBand,
  type CheckVerdict,
  type CheckWarehouseTonsBand,
  runEligibilityCheck,
  type ToolResponse,
} from "@/lib/api";
import { ErrorBanner, Spinner } from "@/components/ToolResponseDisplay";
import { useFetchTool } from "@/lib/useFetchTool";

const INDUSTRY_OPTIONS: { value: CheckIndustryHint; label: string }[] = [
  { value: "food", label: "食品（製造・卸・小売）" },
  { value: "chemical", label: "化学・素材" },
  { value: "retail", label: "小売（一般）" },
  { value: "chain_franchise", label: "連鎖化（フランチャイズ本部）" },
  { value: "transport", label: "貨物自動車運送業" },
  { value: "warehouse", label: "倉庫業" },
  { value: "other", label: "その他" },
];

const FREIGHT_OPTIONS: { value: CheckFreightTonsBand; label: string }[] = [
  { value: "lt_10k", label: "1 万トン未満" },
  { value: "10k_50k", label: "1 〜 5 万トン" },
  { value: "50k_90k", label: "5 〜 9 万トン（閾値前後）" },
  { value: "ge_90k", label: "9 万トン以上" },
  { value: "unknown", label: "不明" },
];

const VEHICLES_OPTIONS: { value: CheckVehiclesBand; label: string }[] = [
  { value: "none", label: "保有していない（該当なし）" },
  { value: "lt_50", label: "50 台未満" },
  { value: "50_150", label: "50 〜 150 台（閾値前後）" },
  { value: "ge_150", label: "150 台以上" },
];

const WAREHOUSE_OPTIONS: { value: CheckWarehouseTonsBand; label: string }[] = [
  { value: "none", label: "営業倉庫なし（該当なし）" },
  { value: "lt_100k", label: "10 万トン未満" },
  { value: "100k_700k", label: "10 〜 70 万トン（閾値前後）" },
  { value: "ge_700k", label: "70 万トン以上" },
];

const CLO_STATUS_OPTIONS: { value: CheckCloStatus; label: string }[] = [
  { value: "not_considered", label: "未検討" },
  { value: "planning", label: "選任予定" },
  { value: "appointed", label: "既に選任済み" },
];

const CATEGORY_LABEL: Record<CheckCategory, string> = {
  shipper: "特定荷主",
  chain_franchise: "特定連鎖化事業者",
  warehouse: "特定倉庫業者",
  freight_transport: "特定貨物自動車運送事業者等",
};

const VERDICT_STYLES: Record<
  CheckVerdict,
  { label: string; badge: string; ring: string; bg: string }
> = {
  applies: {
    label: "✅ 対象",
    badge: "bg-red-100 text-red-800 border-red-300",
    ring: "ring-red-200",
    bg: "bg-red-50 border-red-200",
  },
  gray_zone: {
    label: "⚠️ グレーゾーン",
    badge: "bg-amber-100 text-amber-800 border-amber-300",
    ring: "ring-amber-200",
    bg: "bg-amber-50 border-amber-200",
  },
  not_applies: {
    label: "❌ 対象外",
    badge: "bg-gray-100 text-gray-600 border-gray-300",
    ring: "ring-gray-200",
    bg: "bg-gray-50 border-gray-200",
  },
};

const OVERALL_HEADLINE: Record<CheckVerdict, string> = {
  applies:
    "CLO 義務対象に該当する見込みです。直ちに選任 + 中長期計画策定の準備が必要です。",
  gray_zone:
    "閾値前後（グレーゾーン）の項目があります。実測データでの再判定を推奨します。",
  not_applies:
    "現時点では CLO 義務対象外の見込みです。事業拡大時は閾値を再確認してください。",
};

function defaultRequest(): CheckRequest {
  return {
    industry: "other",
    freight_tons_band: "unknown",
    vehicles_band: "none",
    warehouse_tons_band: "none",
    annual_revenue_jpy: null,
    clo_status: "not_considered",
    is_chain_franchise: false,
  };
}

function parseSearch(sp: URLSearchParams): CheckRequest {
  const base = defaultRequest();
  const industry = sp.get("industry") as CheckIndustryHint | null;
  if (industry && INDUSTRY_OPTIONS.some((o) => o.value === industry)) {
    base.industry = industry;
  }
  const freight = sp.get("freight") as CheckFreightTonsBand | null;
  if (freight && FREIGHT_OPTIONS.some((o) => o.value === freight)) {
    base.freight_tons_band = freight;
  }
  const vehicles = sp.get("vehicles") as CheckVehiclesBand | null;
  if (vehicles && VEHICLES_OPTIONS.some((o) => o.value === vehicles)) {
    base.vehicles_band = vehicles;
  }
  const warehouse = sp.get("warehouse") as CheckWarehouseTonsBand | null;
  if (warehouse && WAREHOUSE_OPTIONS.some((o) => o.value === warehouse)) {
    base.warehouse_tons_band = warehouse;
  }
  const revenue = sp.get("revenue");
  if (revenue && /^\d+$/.test(revenue)) {
    base.annual_revenue_jpy = Number.parseInt(revenue, 10);
  }
  const clo = sp.get("clo") as CheckCloStatus | null;
  if (clo && CLO_STATUS_OPTIONS.some((o) => o.value === clo)) {
    base.clo_status = clo;
  }
  if (sp.get("franchise") === "1") {
    base.is_chain_franchise = true;
  }
  return base;
}

function buildShareUrl(req: CheckRequest): string {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams({
    industry: req.industry,
    freight: req.freight_tons_band,
    vehicles: req.vehicles_band,
    warehouse: req.warehouse_tons_band,
    clo: req.clo_status,
  });
  if (req.annual_revenue_jpy !== null && req.annual_revenue_jpy !== undefined) {
    params.set("revenue", String(req.annual_revenue_jpy));
  }
  if (req.is_chain_franchise) {
    params.set("franchise", "1");
  }
  return `${window.location.origin}/check?${params.toString()}`;
}

function CheckPageInner() {
  const search = useSearchParams();
  const [form, setForm] = useState<CheckRequest>(defaultRequest());
  const [revenueInput, setRevenueInput] = useState<string>("");
  const [copied, setCopied] = useState(false);

  const { data, loading, error, run } = useFetchTool<ToolResponse>();

  // URL クエリパラメータから初期値復元
  useEffect(() => {
    if (!search) return;
    const initial = parseSearch(search);
    setForm(initial);
    if (initial.annual_revenue_jpy) {
      setRevenueInput(String(initial.annual_revenue_jpy));
    }
  }, [search]);

  const metadata = useMemo<CheckMetadata | null>(() => {
    if (!data?.metadata) return null;
    return data.metadata as unknown as CheckMetadata;
  }, [data]);

  const handleSubmit = useCallback(async () => {
    const body: CheckRequest = {
      ...form,
      annual_revenue_jpy:
        revenueInput && /^\d+$/.test(revenueInput)
          ? Number.parseInt(revenueInput, 10)
          : null,
    };
    setForm(body);
    setCopied(false);
    await run(() => runEligibilityCheck(body));
  }, [form, revenueInput, run]);

  const handleCopyShare = useCallback(async () => {
    const url = buildShareUrl(form);
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // クリップボード API 失敗時は手動コピー用に表示するだけ
      setCopied(false);
    }
  }, [form]);

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Hero */}
      <section className="rounded-2xl bg-gradient-to-br from-[#0F2D4F] via-[#1F4E79] to-[#2569A8] px-8 py-8 text-white shadow-lg">
        <div className="inline-flex items-center gap-2 border border-red-400/40 bg-red-900/20 text-red-200 rounded-full px-3 py-1 text-xs mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
          物流効率化法 改正 / CLO 義務化 2026年4月施行
        </div>
        <h1
          className="text-2xl md:text-3xl font-bold mb-3 leading-snug"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          貴社は CLO 義務対象か？
          <br />
          30 秒チェック
        </h1>
        <p className="text-blue-100 text-sm leading-relaxed">
          年間取扱貨物量・保有車両・倉庫規模の 3
          軸で、特定荷主・特定倉庫業者・特定貨物自動車運送事業者等への該当性を一次判定します。
          全数値は国交省ポータルの公式定義に基づきます。
        </p>
      </section>

      {/* 質問フォーム */}
      <section className="bg-white rounded-xl border border-gray-100 p-6 shadow-sm space-y-5">
        <h2 className="text-base font-bold text-[#1F4E79] mb-1">
          1. 業種カテゴリ
        </h2>
        <select
          aria-label="業種カテゴリ"
          value={form.industry}
          onChange={(e) =>
            setForm({ ...form, industry: e.target.value as CheckIndustryHint })
          }
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
        >
          {INDUSTRY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-700 pl-1 cursor-pointer">
          <input
            type="checkbox"
            checked={form.is_chain_franchise}
            onChange={(e) =>
              setForm({ ...form, is_chain_franchise: e.target.checked })
            }
            className="rounded border-gray-300 text-[#1F4E79] focus:ring-[#2E73AC]/40"
          />
          連鎖化事業者（フランチャイズ本部）として運営している
        </label>

        <h2 className="text-base font-bold text-[#1F4E79] mb-1 pt-2">
          2. 年間取扱貨物量
          <span className="ml-2 text-[11px] font-normal text-gray-500">
            特定荷主の閾値: 9 万トン以上
          </span>
        </h2>
        <select
          aria-label="年間取扱貨物量"
          value={form.freight_tons_band}
          onChange={(e) =>
            setForm({
              ...form,
              freight_tons_band: e.target.value as CheckFreightTonsBand,
            })
          }
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
        >
          {FREIGHT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <h2 className="text-base font-bold text-[#1F4E79] mb-1 pt-2">
          3. 保有車両台数
          <span className="ml-2 text-[11px] font-normal text-gray-500">
            特定貨物自動車運送事業者等の閾値: 150 台以上
          </span>
        </h2>
        <select
          aria-label="保有車両台数"
          value={form.vehicles_band}
          onChange={(e) =>
            setForm({
              ...form,
              vehicles_band: e.target.value as CheckVehiclesBand,
            })
          }
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
        >
          {VEHICLES_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <h2 className="text-base font-bold text-[#1F4E79] mb-1 pt-2">
          4. 営業倉庫の年間入庫貨物量
          <span className="ml-2 text-[11px] font-normal text-gray-500">
            特定倉庫業者の閾値: 70 万トン以上
          </span>
        </h2>
        <select
          aria-label="営業倉庫の年間入庫貨物量"
          value={form.warehouse_tons_band}
          onChange={(e) =>
            setForm({
              ...form,
              warehouse_tons_band: e.target.value as CheckWarehouseTonsBand,
            })
          }
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
        >
          {WAREHOUSE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <h2 className="text-base font-bold text-[#1F4E79] mb-1 pt-2">
          5. 年間売上（参考・任意）
          <span className="ml-2 text-[11px] font-normal text-gray-500">
            連鎖化判定に使用 / 円単位で入力
          </span>
        </h2>
        <input
          type="text"
          inputMode="numeric"
          placeholder="例: 50000000000"
          value={revenueInput}
          onChange={(e) => setRevenueInput(e.target.value.replace(/[^0-9]/g, ""))}
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
          style={{ fontFamily: "var(--font-mono)" }}
        />

        <h2 className="text-base font-bold text-[#1F4E79] mb-1 pt-2">
          6. 物流統括管理者（CLO）の選任状況
        </h2>
        <select
          aria-label="CLO 選任状況"
          value={form.clo_status}
          onChange={(e) =>
            setForm({ ...form, clo_status: e.target.value as CheckCloStatus })
          }
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#2E73AC]/40 focus:border-[#2E73AC] transition"
        >
          {CLO_STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <div className="pt-4">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-2 bg-[#1F4E79] text-white rounded-lg px-6 py-3 font-bold text-sm hover:bg-[#2E73AC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <Spinner /> 判定中...
              </>
            ) : (
              "義務対象か判定する"
            )}
          </button>
        </div>
      </section>

      {error && <ErrorBanner message={error} />}

      {metadata && (
        <ResultSection
          metadata={metadata}
          shareUrl={buildShareUrl(form)}
          copied={copied}
          onCopyShare={handleCopyShare}
        />
      )}
    </div>
  );
}

function ResultSection({
  metadata,
  shareUrl,
  copied,
  onCopyShare,
}: {
  metadata: CheckMetadata;
  shareUrl: string;
  copied: boolean;
  onCopyShare: () => void;
}) {
  const overall = metadata.overall_verdict;
  const overallStyle = VERDICT_STYLES[overall];
  return (
    <section className="space-y-6">
      {/* 総合判定 + カウントダウン */}
      <div
        className={`rounded-xl border-2 ${overallStyle.bg} p-6 shadow-sm`}
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-3">
          <span
            className={`inline-flex items-center gap-2 border rounded-full px-4 py-1.5 text-sm font-bold ${overallStyle.badge}`}
          >
            {overallStyle.label}
          </span>
          <span className="text-xs text-gray-600">
            初回提出期限まで{" "}
            <strong
              className="tabular-nums text-base text-[#1F4E79]"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              {metadata.days_until_deadline}
            </strong>{" "}
            日（{metadata.submission_deadline}）
          </span>
        </div>
        <p className="text-sm text-gray-800 leading-relaxed">
          {OVERALL_HEADLINE[overall]}
        </p>
      </div>

      {/* 区分別カード */}
      <div>
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
          区分別判定
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {metadata.findings.map((f) => (
            <FindingCard key={f.category} finding={f} />
          ))}
        </div>
      </div>

      {/* 注意事項 */}
      {metadata.notes.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h3 className="text-sm font-bold text-amber-900 mb-2">注意事項</h3>
          <ul className="space-y-1.5">
            {metadata.notes.map((n) => (
              <li key={n} className="text-xs text-amber-900 leading-relaxed">
                ・{n}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 罰則 */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-bold text-gray-900 mb-3">罰則</h3>
        <div className="space-y-1.5">
          {Object.entries(metadata.penalty).map(([k, v]) => (
            <div key={k} className="flex items-baseline gap-3 text-xs">
              <span className="font-bold text-gray-700 min-w-[5rem]">{k}</span>
              <span className="text-gray-800">{v}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-gray-500">
          出典: 国土交通省「物資の流通の効率化に関する法律」ポータル
          <br />
          <a
            href="https://www.revised-logistics-act-portal.mlit.go.jp/designation/"
            target="_blank"
            rel="noreferrer"
            className="text-[#1F4E79] underline hover:text-[#2E73AC]"
          >
            https://www.revised-logistics-act-portal.mlit.go.jp/designation/
          </a>
        </p>
      </div>

      {/* 次のアクション動線 */}
      <div className="bg-gradient-to-r from-[#1F4E79] to-[#2E73AC] rounded-xl p-6 text-white shadow-md">
        <h3
          className="text-lg font-bold mb-2"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          次のアクション
        </h3>
        <p className="text-sm text-blue-100 mb-4 leading-relaxed">
          業種別の標準パッケージ（KPI / 施策 / 会議体 / レポート様式）を確認し、
          自社の中長期計画書ドラフトを生成できます。
        </p>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/dashboard/industry-package"
            className="inline-flex items-center gap-2 bg-white text-[#1F4E79] font-bold text-xs px-4 py-2 rounded-lg hover:bg-blue-50 transition-colors"
          >
            業種別パッケージを見る
          </Link>
          <Link
            href="/dashboard/plan-draft"
            className="inline-flex items-center gap-2 border border-white/40 bg-white/10 text-white font-bold text-xs px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
          >
            計画書ドラフトを生成
          </Link>
          <Link
            href="/guide"
            className="inline-flex items-center gap-2 border border-white/40 bg-white/10 text-white font-bold text-xs px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
          >
            機能別ガイド
          </Link>
        </div>
      </div>

      {/* 結果シェア */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-bold text-gray-900 mb-2">
          この判定結果を共有
        </h3>
        <p className="text-[11px] text-gray-500 mb-3">
          URL には入力した回答が含まれます。個人情報は含まれません。
        </p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            readOnly
            value={shareUrl}
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 text-xs"
            style={{ fontFamily: "var(--font-mono)" }}
            aria-label="共有 URL"
          />
          <button
            type="button"
            onClick={onCopyShare}
            className="bg-[#1F4E79] text-white rounded-lg px-4 py-2 font-bold text-xs hover:bg-[#2E73AC] transition-colors"
          >
            {copied ? "✓ コピーしました" : "URL をコピー"}
          </button>
        </div>
      </div>

      {/* 個別相談 */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
        <h3 className="text-sm font-bold text-gray-900 mb-2">
          個別相談・お問い合わせ
        </h3>
        <p className="text-xs text-gray-600 leading-relaxed mb-3">
          グレーゾーン項目の精査・自社実測データでの再判定・中長期計画策定の支援が必要な場合は、
          以下からご連絡ください。
        </p>
        <a
          href="mailto:ykenkou001@gmail.com?subject=CLO%20%E7%BE%A9%E5%8B%99%E5%AF%BE%E8%B1%A1%E5%88%A4%E5%AE%9A%20%E5%80%8B%E5%88%A5%E7%9B%B8%E8%AB%87"
          className="inline-flex items-center gap-2 bg-white border border-gray-300 text-gray-800 font-bold text-xs px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          📧 メールで相談する
        </a>
      </div>
    </section>
  );
}

function FindingCard({ finding }: { finding: CategoryFinding }) {
  const style = VERDICT_STYLES[finding.verdict];
  return (
    <div className={`rounded-xl border-2 ${style.bg} p-5`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="font-bold text-sm text-gray-900">
          {CATEGORY_LABEL[finding.category]}
        </h4>
        <span
          className={`text-[10px] font-bold border rounded-full px-2 py-0.5 ${style.badge}`}
        >
          {style.label}
        </span>
      </div>
      <p className="text-xs text-gray-700 leading-relaxed mb-2">
        {finding.reason}
      </p>
      <div className="text-[11px] text-gray-500 space-y-0.5 border-t border-gray-200/70 pt-2">
        <div>
          <span className="font-semibold text-gray-600">閾値: </span>
          {finding.threshold_label}
        </div>
        <div>
          <span className="font-semibold text-gray-600">法令: </span>
          {finding.legal_article}
        </div>
      </div>
    </div>
  );
}

export default function CheckPage() {
  // useSearchParams は Suspense boundary 配下で使う必要がある
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Spinner /> 読み込み中...
        </div>
      }
    >
      <CheckPageInner />
    </Suspense>
  );
}
