/**
 * 共通表示ラベル層 — Web 全画面で使う日本語ラベルマッピング。
 *
 * 設計方針（Codex 勧告 2026-05-06）:
 *   - enum コード値（snake_case の英語）を CLO 担当者向けに日本語化する
 *   - 画面ごとにローカル定義せず、すべてここに集約して二重管理を防ぐ
 *   - 不明値は警告ではなくフォールバックで raw 表示する（型変更時の事故を可視化）
 *
 * 対応する Pydantic スキーマ: core/playbook/industry_packages.py の Literal 群
 */
import type {
  DataItemSource,
  KpiFrequency,
  MeetingFrequency,
  OutputFormat,
  OverrideTargetKind,
  RefreshCadence,
  ReportAudience,
  ReportFrequency,
} from "./api";

// ─── 頻度系（KPI / 会議 / レポート / データ更新を統合） ──────────────
type AnyFrequency =
  | KpiFrequency
  | MeetingFrequency
  | ReportFrequency
  | RefreshCadence;

const FREQUENCY_LABEL: Record<AnyFrequency, string> = {
  realtime: "リアルタイム",
  daily: "日次",
  weekly: "週次",
  biweekly: "隔週",
  monthly: "月次",
  quarterly: "四半期",
  annual: "年次",
};

export function freqLabel(value: string): string {
  return FREQUENCY_LABEL[value as AnyFrequency] ?? value;
}

// ─── レポート読者 ────────────────────────────────────────────────
export const REPORT_AUDIENCE_LABEL: Record<ReportAudience, string> = {
  board: "取締役会",
  clo: "CLO",
  operation: "現場運用",
  external_partner: "取引先・対外",
};

// ─── 出力形式 ──────────────────────────────────────────────────
export const OUTPUT_FORMAT_LABEL: Record<OutputFormat, string> = {
  ppt: "PPT",
  docx: "Word",
  excel: "Excel",
  markdown: "Markdown",
};

// ─── データソース（自社システムからの取得元） ───────────────────────
export const DATA_SOURCE_LABEL: Record<DataItemSource, string> = {
  tms: "TMS（配車管理）",
  wms: "WMS（倉庫管理）",
  manual: "手入力",
  gps: "GPS",
  pos: "POS",
  edi: "EDI",
};

// ─── Override 対象の種別 ─────────────────────────────────────────
export const OVERRIDE_TARGET_KIND_LABEL: Record<OverrideTargetKind, string> = {
  kpi: "KPI",
  measure: "施策",
  meeting: "会議体",
  report: "レポート",
  data_item: "データ項目",
};

// ─── KPI 表示ヘルパ ──────────────────────────────────────────────
/**
 * 標準目標値の表示。null は「—」、unit が空（例: 円/SKU など特殊）でも値はそのまま結合。
 */
export function formatTargetValue(
  value: number | null,
  unit: string,
): string {
  if (value == null) return "—";
  return `${value}${unit}`;
}

/**
 * target_value が null の KPI に対する CLO 向け説明。
 *
 * legal_basis 有り = 制度ポータルに指標自体は載っているが標準値の根拠が無い
 * legal_basis 無し = JILS 等の調査も無く、自社前年比管理のみ可能
 */
export function targetValueMissingNote(legalBasis: string | null): string {
  if (legalBasis) {
    return "標準目標値は未設定（公的根拠未確定）。Override で挑戦値設定可。";
  }
  return "標準目標値なし。自社前年比で管理。";
}
