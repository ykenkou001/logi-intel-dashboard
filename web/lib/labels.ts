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
  DecisionAxis,
  JsicCategory,
  KpiFrequency,
  MeetingFrequency,
  OutputFormat,
  OverrideCategory,
  OverrideTargetKind,
  RefreshCadence,
  ReportAudience,
  ReportFrequency,
  RootCause,
  TrapSeverity,
  VerdictLevel,
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

// ─── Override 4 分類 ──────────────────────────────────────────────
export const OVERRIDE_CATEGORY_LABEL: Record<OverrideCategory, string> = {
  unmanaged_deviation: "管理外逸脱",
  approved_better_practice: "承認済差別化",
  required_localization: "必要ローカル",
  temporary_exception: "期限付き例外",
};

// ─── 業種カテゴリ（JSIC ベース） ──────────────────────────────────
export const INDUSTRY_LABEL: Record<JsicCategory, string> = {
  manufacturing: "製造業",
  wholesale: "卸売業",
  retail: "小売業",
  chain_franchise: "連鎖化（FC本部）",
  transport: "運輸業",
  other: "その他",
};

// ─── 意思決定 3 軸（J3 デイリーコックピット） ──────────────────────
export const DECISION_AXIS_LABEL: Record<DecisionAxis, string> = {
  compliance: "軸A 法令準拠リスク",
  kpi_reach: "軸B KPI達成見通し",
  measure_pick: "軸C 今週決める施策",
};

// ─── 全体健全度 / 緑黄赤 判定 ───────────────────────────────────
export const VERDICT_LEVEL_LABEL: Record<VerdictLevel, string> = {
  green: "全体健全",
  yellow: "要注視",
  red: "重大対応",
};

// ─── 重大度（絵文字インジケータ） ────────────────────────────────
export const SEVERITY_EMOJI: Record<"green" | "yellow" | "red" | "none", string> = {
  green: "🟢",
  yellow: "🟡",
  red: "🔴",
  none: "⚪",
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

// ─── J2 罠スコア（waste_trap）系 — フェーズ5.5 α-1 ────────────────────
//
// 経営会議で「なぜこの施策が罠候補と判定されたか」を即答するための日本語化層。
// 識別子は core/analytics/waste_trap.py の RootCause 9 種 / 6 軸セーフガードに準拠。

export const TRAP_SEVERITY_LABEL: Record<TrapSeverity, string> = {
  high: "重大",
  medium: "要注意",
  low: "軽微 / 判定保留",
};

export const TRAP_SEVERITY_TONE: Record<
  TrapSeverity,
  { card: string; dot: string; badge: string }
> = {
  high: {
    card: "bg-rose-50 border-rose-300",
    dot: "bg-rose-500",
    badge: "bg-rose-100 text-rose-900 border-rose-300",
  },
  medium: {
    card: "bg-amber-50 border-amber-300",
    dot: "bg-amber-500",
    badge: "bg-amber-100 text-amber-900 border-amber-300",
  },
  low: {
    card: "bg-emerald-50 border-emerald-200",
    dot: "bg-emerald-500",
    badge: "bg-emerald-100 text-emerald-900 border-emerald-300",
  },
};

export const ROOT_CAUSE_LABEL: Record<RootCause, string> = {
  scale_misfit: "規模不適合",
  resource_missing: "必要リソース不足",
  governance_gap: "ガバナンス不足",
  wrong_kpi: "KPI 設計の誤り",
  external_factor: "外部要因の影響",
  data_quality: "計測データの品質",
  adoption_resistance: "現場への定着不足",
  implementation_quality: "実装品質の問題",
  unknown: "原因未特定",
};

/**
 * 6 軸セーフガード識別子（core/analytics/waste_trap.py の _check_safeguards）の
 * 日本語ラベル。発火した識別子をユーザーに見せる際に使う。
 */
export const SAFEGUARD_LABEL: Record<string, string> = {
  ramp_up_period: "立ち上げ期間中（6 ヶ月未満）",
  data_incomplete: "データ欠損 50% 超",
  insufficient_samples: "サンプル数不足（< 30）",
  seasonal_factor: "季節性影響中",
  external_event: "外部要因（燃料急騰等）影響中",
  before_payback: "想定回収期間内",
  actual_not_measured: "実績未計測",
};

export function safeguardLabel(value: string): string {
  return SAFEGUARD_LABEL[value] ?? value;
}
