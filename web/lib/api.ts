/**
 * FastAPI バックエンドと通信する型付き API クライアント。
 *
 * `api/schemas/responses.py` の Pydantic モデルと構造を一致させている。
 * バックエンドのレスポンス変更時はこちらも追従させること。
 */

/**
 * データの出所:
 * - "sample"   : デモ用架空企業のデータ（経営判断には使わない）
 * - "estimated": ユーザー入力 + 業界統計推計（一部実測なし）
 * - "actual"   : 自社実測データに基づく
 */
export type DataSource = "sample" | "estimated" | "actual";

export interface Citation {
  label: string;
  url: string;
  stats_data_id: string | null;
  notice_number: string | null;
  ordinance_number: string | null;
  fetched_at: string;
  accessed_via: string | null;
}

export interface ToolResponse {
  summary: string;
  files: Record<string, string>;
  citations: Citation[];
  freshness_warnings: string[];
  data_source: DataSource;
  metadata?: Record<string, unknown> | null;
}

export type HeatmapSeverity = "green" | "yellow" | "red" | "none";

export interface HeatmapCell {
  site_name: string;
  time_slot: string;
  avg_minutes: number | null;
  max_minutes: number | null;
  measured_count: number;
  over_2h_count: number;
  severity: HeatmapSeverity;
  confidence_low: boolean;
}

export interface HeatmapMetadata {
  company_id: string;
  company_name: string;
  site_names: string[];
  time_slots: string[];
  cells: HeatmapCell[];
  overall_avg_minutes: number | null;
  overall_max_minutes: number | null;
  threshold_minutes: number;
  avg_target_minutes: number;
  // Tier S3: 施設フィルタ時のみ意味のあるフィールド
  facility_id: string | null;
  facility_name: string | null;
  measurement_period_label: string | null;
  measurement_conditions: string[];
  exclusion_reasons: string[];
  is_consigned_warehouse: boolean;
  consigned_notice: string | null;
  // Tier S3 フォロー PR: 全社集計時の寄託先除外可視化
  include_consigned: boolean;
  primary_aggregated_site_count: number;
  excluded_consigned_site_count: number;
  excluded_consigned_site_names: string[];
}

export type FacilityControlType =
  | "owned"
  | "leased"
  | "operated_by_3pl"
  | "consigned";

// ─── Tier S3: 報告単位 Facility（施設マスタ）─────────────────
export interface FacilityMeasurementPeriod {
  start_on: string;       // YYYY-MM-DD
  end_on: string;         // YYYY-MM-DD
  unit_label: string;     // 月次 / 四半期 / 年次 等
}

export interface Facility {
  facility_id: string;
  company_id: string;
  name: string;
  address: string;
  prefecture: string;
  industry_code: string;
  site_name: string | null;
  measurement_period: FacilityMeasurementPeriod;
  measurement_conditions: string[];
  exclusion_reasons: string[];
  is_consigned_warehouse: boolean;
  // Tier S3 フォロー PR: Codex §8.4-1 追加フィールド
  facility_control_type: FacilityControlType | null;
  measurement_source: string | null;
  consigned_partner_name: string | null;
  contract_scope_note: string | null;
  notes: string | null;
  created_at: string;     // ISO datetime
  updated_at: string;     // ISO datetime
}

export interface FacilityListMetadata {
  company_id: string;
  count: number;
  consigned_count: number;
  facilities: Facility[];
}

export interface SampleCompany {
  company_id: string;
  name: string;
  industry: string;
  data_source: DataSource;
}

// ─── J3 デイリーコックピット（フェーズ4.5 b）─────────────────────────
export type DecisionAxis = "compliance" | "kpi_reach" | "measure_pick";
export type CardState =
  | "healthy"
  | "insufficient_data"
  | "out_of_scope"
  | "attention_needed";
export type ObjectionRole = "cfo" | "sales" | "operation" | "partner" | "board";
export type EvidenceAxis = "cost" | "legal" | "supply" | "brand_risk";
export type DecisionStatus =
  | "pending"
  | "adopt"
  | "postpone"
  | "reject"
  | "escalate";
export type VerdictLevel = "green" | "yellow" | "red";
export type ComplianceStatus =
  | "compliant"
  | "violation"
  | "borderline"
  | "not_measured";

export interface ObjectionItem {
  role: ObjectionRole;
  objection: string;
  rebuttal: string;
  evidence_axis: EvidenceAxis;
}

export interface CockpitItem {
  item_id: string;
  decision_axis: DecisionAxis;
  card_state: CardState;
  headline: string;
  rationale: string;
  urgency_score: number;
  impact_score: number;
  confidence_score: number;
  total_score: number;
  related_measure_id: string | null;
  related_kpi_name: string | null;
  related_compliance_item: string | null;
  suggested_action: string;
  deadline_label: string;
  next_review_due: string | null;
  days_pending: number;
  delta_from_last: string | null;
  estimated_pnl_jpy: number | null;
  citation_keys: string[];
  anticipated_objections: ObjectionItem[];
}

export interface CockpitSnapshot {
  snapshot_date: string;
  load_factor_pct: number | null;
  wait_time_avg_min: number | null;
  wait_time_max_min: number | null;
  handling_time_avg_min: number | null;
  co2_intensity_g_per_tonkm: number | null;
  over_2h_count_total: number;
  compliance_overall: ComplianceStatus;
  feasibility_kpi_level: VerdictLevel;
  open_items: string[];
}

export interface CockpitMetadata {
  company_id: string;
  company_name: string;
  generated_at: string;
  data_source: DataSource;
  overall_health: VerdictLevel;
  one_line_summary: string;
  delta_from_yesterday: Record<string, number | null>;
  snapshot: CockpitSnapshot;
  items: CockpitItem[];
}

export interface DecisionLogRequest {
  cockpit_item_id: string;
  decision: DecisionStatus;
  decided_by?: string;
  rationale?: string;
  expected_effect_jpy?: number | null;
  review_due?: string | null;
  linked_alerts?: string[];
}

export interface DecisionLogResponse {
  record_id: string;
  company_id: string;
  decision: DecisionStatus;
  log_path: string;
}

/**
 * API ベース URL。
 * - 本番（CloudFront 同居）: `""`（同一 origin の `/api/v1/...` を直接叩く）— 既定
 * - ローカル開発: `web/.env.development.local` に
 *   `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` を設定（または手動で env を渡す）
 *
 * 安全側のデフォルトは `""`（同一 origin）。環境変数未設定でも本番動作が壊れない。
 * 過去に発生した事故: 旧 default が `http://localhost:8000` だったため、放置された
 * 古い uvicorn を本番フロントが叩き続け、修正反映が確認できない不具合に至った。
 */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function buildUrl(
  path: string,
  searchParams?: Record<string, string | number | boolean | undefined>,
): string {
  // API_BASE が "" のとき new URL("/path") は invalid URL となるため、
  // 文字列結合 + URLSearchParams で組み立てる（同一 origin / 絶対 URL 両対応）。
  let query = "";
  if (searchParams) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(searchParams)) {
      if (value !== undefined) {
        params.append(key, String(value));
      }
    }
    const s = params.toString();
    if (s) query = `?${s}`;
  }
  return `${API_BASE}${path}${query}`;
}

async function request<T>(
  path: string,
  init?: RequestInit & { searchParams?: Record<string, string | number | boolean | undefined> },
): Promise<T> {
  const url = buildUrl(path, init?.searchParams);
  const response = await fetch(url, {
    method: init?.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    body: init?.body,
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return (await response.json()) as T;
}

// ─── 業界ベンチマーク ──────────────────────────────────────────
export async function fetchBenchmark(params: {
  jsic_code: string;
  prefecture: string;
  revenue_jpy: number;
  logistics_cost_jpy?: number;
}): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/benchmark", { searchParams: params });
}

// ─── ドライバー需給ギャップ ────────────────────────────────────
export async function fetchDriverGap(prefecture: string): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/driver-gap", {
    searchParams: { prefecture },
  });
}

// ─── 拠点別待機時間ヒートマップ（フェーズ4.1 a.1 / Tier S3 で施設フィルタ追加）─
export async function fetchWaitHeatmap(
  companyId: string,
  facilityId?: string,
  includeConsigned?: boolean,
): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/wait-heatmap", {
    searchParams: {
      company_id: companyId,
      facility_id: facilityId,
      include_consigned: includeConsigned ? true : undefined,
    },
  });
}

// ─── Tier S3: 施設マスタ ──────────────────────────────────────
export async function fetchFacilities(companyId: string): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/facilities", {
    searchParams: { company_id: companyId },
  });
}

export async function registerFacility(
  facility: Omit<Facility, "created_at" | "updated_at"> &
    Partial<Pick<Facility, "created_at" | "updated_at">>,
): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/facilities", {
    method: "POST",
    body: JSON.stringify(facility),
  });
}

// ─── デイリーコックピット（フェーズ4.5 b）─────────────────────
export async function fetchTodayDecisions(
  companyId: string,
  options: { targetYear?: number; persistSnapshot?: boolean } = {},
): Promise<ToolResponse> {
  return request<ToolResponse>(
    `/api/v1/clo/today-decisions/${encodeURIComponent(companyId)}`,
    {
      searchParams: {
        target_year: options.targetYear,
        persist_snapshot:
          options.persistSnapshot === undefined ? undefined : options.persistSnapshot,
      },
    },
  );
}

export async function logDecision(
  companyId: string,
  body: DecisionLogRequest,
): Promise<DecisionLogResponse> {
  return request<DecisionLogResponse>(
    `/api/v1/clo/decisions/${encodeURIComponent(companyId)}`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

// ─── 適用判定 ─────────────────────────────────────────────────
export async function fetchEligibility(params: {
  jsic_code: string;
  annual_revenue_jpy?: number;
  annual_freight_tons_total?: number;
  is_chain_franchise?: boolean;
}): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/eligibility", { searchParams: params });
}

// ─── プレイブック検索 ─────────────────────────────────────────
export async function fetchPlaybook(params: {
  industry?: string;
  max_difficulty?: number;
  form3_section?: string;
  measure_type?: string;
}): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/playbook", { searchParams: params });
}

// ─── 施策評価エンジン（Top 3 推薦 + Bottom 3 judgment trail）─────────
//
// Pydantic / dataclass スキーマと一致する型。`api/routers/clo.py` の
// `_measure_eval_to_metadata` が返す metadata 構造を厳密に反映する。

export interface PlaybookMeasureSummary {
  measure_id: string;
  name: string;
  description: string;
  form3_section: string;
  measure_type: string;
  implementation_difficulty: number;
  typical_investment_jpy_low: number;
  typical_investment_jpy_high: number;
  typical_payback_years: number | null;
}

export interface MeasureScoreSummary {
  measure: PlaybookMeasureSummary;
  roi_score: number;
  feasibility_score: number;
  compliance_score: number;
  subsidy_score: number;
  total_score: number;
  estimated_annual_cost_saving_jpy: number | null;
  estimated_annual_co2_reduction_kg: number | null;
  estimated_payback_years: number | null;
  selection_reason: string;
  missing_resources: string[];
  responsible_dept: string;
  monthly_kpi: string;
  dependencies: string[];
  comparison_note: string;
}

export interface MeasureEvalMetadata {
  company_id: string;
  company_name: string;
  industry: string;
  derived_resources: string[];
  eligible_count: number;
  scored_count: number;
  top_recommendations: MeasureScoreSummary[];
  bottom_candidates: MeasureScoreSummary[];
}

export async function fetchMeasureEval(companyId: string): Promise<ToolResponse> {
  return request<ToolResponse>(`/api/v1/clo/measure-eval/${companyId}`);
}

// ─── 計画書ドラフト統合生成 ──────────────────────────────────
export async function generatePlanDraft(companyId: string): Promise<ToolResponse> {
  return request<ToolResponse>(`/api/v1/clo/plan-draft/${companyId}`, {
    method: "POST",
  });
}

// ─── シナリオシミュレーション ────────────────────────────────
export async function runScenarioSim(
  companyId: string,
  selectedMeasureIds?: string[],
): Promise<ToolResponse> {
  // 配列クエリパラメータは buildUrl に渡しにくいので個別組立
  const params = new URLSearchParams();
  if (selectedMeasureIds && selectedMeasureIds.length > 0) {
    for (const id of selectedMeasureIds) {
      params.append("selected_measure_ids", id);
    }
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  const url = `${API_BASE}/api/v1/clo/scenario-sim/${companyId}${query}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return (await response.json()) as ToolResponse;
}

// ─── 自社プロフィール: テンプレ生成 ───────────────────────────
/**
 * 自社プロフィール入力 Excel テンプレートの利用用途。
 * - "annual"  : 計画策定用（年 1 回・網羅版）— 既定
 * - "monthly" : 月次集計用（月次レビュー）
 * - "daily"   : 日次運用入力用（コックピット／ヒートマップ）
 */
export type TemplatePurpose = "daily" | "monthly" | "annual";

export async function generateCompanyTemplate(
  purpose: TemplatePurpose = "annual",
): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/company/template", {
    method: "POST",
    searchParams: { purpose },
  });
}

// ─── 自社プロフィール: 取込 (Excel multipart) ─────────────────
export async function loadCompanyProfile(file: File): Promise<ToolResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/api/v1/company/load`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return (await response.json()) as ToolResponse;
}

// ─── マクロ概況 ─────────────────────────────────────────────
export async function fetchMacroOverview(prefecture: string): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/macro/overview", {
    searchParams: { prefecture },
  });
}

// ─── サンプル企業一覧 ────────────────────────────────────────
export async function fetchSamples(): Promise<SampleCompany[]> {
  return request<SampleCompany[]>("/api/v1/company/samples");
}

// ─── ヘルスチェック ──────────────────────────────────────────
export async function fetchHealth(): Promise<{ status: string; service: string }> {
  return request<{ status: string; service: string }>("/health");
}

// ─── 成果物ダウンロード URL ─────────────────────────────────
export function fileDownloadUrl(relativePath: string): string {
  // 例: "outputs/ppt/clo_plan_xxx.pptx" → "/api/v1/files/ppt/clo_plan_xxx.pptx"
  const cleaned = relativePath.replace(/^outputs[\\/]/, "");
  return `${API_BASE}/api/v1/files/${cleaned.replace(/\\/g, "/")}`;
}

// ─── 業種別パッケージ + F2/J2 スコア（フェーズ5.0 c.7 / c.9）─────────────
//
// Pydantic スキーマと完全一致する型。`api/routers/clo.py` の
// industry_package / standardization_score / waste_traps エンドポイントが返す
// metadata 構造を厳密に反映する。

export type JsicCategory =
  | "manufacturing"
  | "wholesale"
  | "retail"
  | "chain_franchise"
  | "transport"
  | "other";

export type KpiFrequency = "daily" | "weekly" | "monthly" | "quarterly" | "annual";
export type MeetingFrequency =
  | "weekly"
  | "biweekly"
  | "monthly"
  | "quarterly"
  | "annual";
export type ReportFrequency = "weekly" | "monthly" | "quarterly" | "annual";
export type ReportAudience = "board" | "clo" | "operation" | "external_partner";
export type OutputFormat = "ppt" | "docx" | "excel" | "markdown";
export type DataItemSource = "tms" | "wms" | "manual" | "gps" | "pos" | "edi";
export type RefreshCadence = "realtime" | "daily" | "weekly" | "monthly";

export type OverrideCategory =
  | "unmanaged_deviation"
  | "approved_better_practice"
  | "required_localization"
  | "temporary_exception";

export type OverrideTargetKind =
  | "kpi"
  | "measure"
  | "meeting"
  | "report"
  | "data_item";

export interface StandardKpiDef {
  metric_id: string;
  label: string;
  target_value: number | null;
  unit: string;
  baseline_value: number | null;
  frequency: KpiFrequency;
  owner_role: string;
  legal_basis: string | null;
  related_measure_ids: string[];
}

export interface StandardMeetingDef {
  meeting_id: string;
  name: string;
  frequency: MeetingFrequency;
  participants: string[];
  agenda_items: string[];
  standard_duration_min: number;
  output_artifact: string;
}

export interface StandardReportDef {
  report_id: string;
  name: string;
  audience: ReportAudience;
  frequency: ReportFrequency;
  source_kpi_ids: string[];
  output_format: OutputFormat;
  related_meeting_ids: string[];
}

export interface StandardDataItemDef {
  data_item_id: string;
  label: string;
  source: DataItemSource;
  refresh_cadence: RefreshCadence;
  used_by_kpi_ids: string[];
}

export interface IndustryPackage {
  category: JsicCategory;
  label: string;
  version: string;
  kpis: StandardKpiDef[];
  measure_ids: string[];
  meetings: StandardMeetingDef[];
  reports: StandardReportDef[];
  data_items: StandardDataItemDef[];
  plan_template_paths: Record<string, string>;
  benchmark_refs: string[];
  notes: string[];
}

export interface OverrideEntry {
  target_kind: OverrideTargetKind;
  target_id: string;
  category: OverrideCategory;
  rationale: string;
  approved_by: string | null;
  expires_at: string | null;
  diff: Record<string, unknown>;
}

export interface CompanyPackageOverride {
  company_id: string;
  base_industry: JsicCategory;
  entries: OverrideEntry[];
  last_reviewed: string;
}

export interface MeasureDetail {
  measure_id: string;
  name: string;
  description: string;
  form3_section: string;
  measure_type: string;
}

export interface ChainFranchiseNotice {
  legal_article: string;
  headline: string;
  scope_note: string;
}

export interface IndustryPackageMetadata {
  company_id: string;
  base_industry: JsicCategory;
  package: IndustryPackage;
  override: CompanyPackageOverride | null;
  measure_details: MeasureDetail[];
  chain_franchise_notice: ChainFranchiseNotice | null;
}

export interface StandardizationScoreResult {
  company_id: string;
  base_package_category: JsicCategory;
  coverage_pct: number;
  deviation_count_unmanaged: number;
  deviation_count_total: number;
  chain_franchise_loading_misuse_count: number;
  missing_kpi_ids: string[];
  missing_measure_ids: string[];
  score: number;
  rationale: string[];
  citations: Citation[];
  freshness_warnings: string[];
}

export type TrapSeverity = "low" | "medium" | "high";

export type RootCause =
  | "scale_misfit"
  | "resource_missing"
  | "governance_gap"
  | "wrong_kpi"
  | "external_factor"
  | "data_quality"
  | "adoption_resistance"
  | "implementation_quality"
  | "unknown";

export interface WasteTrapItem {
  measure_id: string;
  measure_name: string;
  invested_jpy: number | null;
  expected_effect_jpy: number | null;
  actual_effect_jpy: number | null;
  months_since_start: number | null;
  trap_severity: TrapSeverity;
  suspected_root_cause: RootCause;
  suggested_remediation: string;
  investment_freeze_recommended: boolean;
  safeguard_triggered: string[];
}

export interface WasteTrapResult {
  company_id: string;
  items: WasteTrapItem[];
  high_count: number;
  medium_count: number;
  low_count: number;
  investment_freeze_count: number;
  citations: Citation[];
  freshness_warnings: string[];
}

export interface MeasureExecutionRecord {
  measure_id: string;
  started_on?: string | null;
  invested_jpy?: number | null;
  expected_effect_jpy?: number | null;
  actual_effect_jpy?: number | null;
  measured_count?: number | null;
  data_completeness?: number | null;
  seasonal_factor_active?: boolean;
  external_event_active?: boolean;
  payback_months_estimated?: number | null;
  suspected_root_cause?: RootCause;
}

export async function fetchIndustryPackage(
  companyId: string,
): Promise<ToolResponse> {
  return request<ToolResponse>(
    `/api/v1/clo/industry-package/${encodeURIComponent(companyId)}`,
  );
}

export async function fetchStandardizationScore(
  companyId: string,
): Promise<ToolResponse> {
  return request<ToolResponse>(
    `/api/v1/clo/standardization-score/${encodeURIComponent(companyId)}`,
  );
}

export async function fetchWasteTraps(
  companyId: string,
  measureRuns: MeasureExecutionRecord[] = [],
): Promise<ToolResponse> {
  return request<ToolResponse>(
    `/api/v1/clo/waste-traps/${encodeURIComponent(companyId)}`,
    {
      method: "POST",
      body: JSON.stringify(measureRuns),
    },
  );
}

// ─── Tier S2: KPI 時系列トラッキング ─────────────────────────────

export type KpiSnapshotSource =
  | "rolled_up_from_daily"
  | "manual_entry"
  | "merged";

export interface MonthlyKpiSnapshot {
  company_id: string;
  year_month: string;
  load_factor_pct: number | null;
  wait_time_avg_min: number | null;
  wait_time_max_min: number | null;
  handling_time_avg_min: number | null;
  co2_intensity_g_per_tonkm: number | null;
  standardization_score: number | null;
  waste_trap_count_high: number;
  waste_trap_count_medium: number;
  waste_trap_count_low: number;
  source: KpiSnapshotSource;
  daily_sample_count: number;
  recorded_at: string;
}

export type DeteriorationSeverity = "watch" | "warn" | "critical";
export type DeteriorationDirection = "down" | "up";

export interface KpiDeteriorationAlert {
  metric: string;
  metric_label: string;
  severity: DeteriorationSeverity;
  direction: DeteriorationDirection;
  consecutive_months: number;
  latest_value: number | null;
  baseline_value: number | null;
  delta_pct: number | null;
  message: string;
}

export interface KpiTimeSeriesMetadata {
  company_id: string;
  months: MonthlyKpiSnapshot[];
  deteriorations: KpiDeteriorationAlert[];
  citations: Citation[];
  freshness_warnings: string[];
}

export async function fetchKpiTimeseries(
  companyId: string,
  params: {
    limitMonths?: number;
    fromYearMonth?: string;
    toYearMonth?: string;
  } = {},
): Promise<ToolResponse> {
  const search = new URLSearchParams();
  if (params.limitMonths !== undefined) {
    search.set("limit_months", String(params.limitMonths));
  }
  if (params.fromYearMonth) search.set("from_year_month", params.fromYearMonth);
  if (params.toYearMonth) search.set("to_year_month", params.toYearMonth);
  const query = search.toString() ? `?${search}` : "";
  return request<ToolResponse>(
    `/api/v1/clo/kpi-timeseries/${encodeURIComponent(companyId)}${query}`,
  );
}

export async function recordMonthlySnapshot(
  companyId: string,
  yearMonth: string,
  measureRuns: MeasureExecutionRecord[] = [],
): Promise<ToolResponse> {
  return request<ToolResponse>(
    `/api/v1/clo/kpi-timeseries/${encodeURIComponent(companyId)}`,
    {
      method: "POST",
      body: JSON.stringify({
        year_month: yearMonth,
        measure_runs: measureRuns,
      }),
    },
  );
}

// ─── CLO 義務対象スクリーニング（/check 画面）─────────────────
//
// `api/routers/check.py` の Pydantic スキーマと一致させる。
export type CheckIndustryHint =
  | "food"
  | "chemical"
  | "retail"
  | "chain_franchise"
  | "transport"
  | "warehouse"
  | "other";
export type CheckFreightTonsBand =
  | "lt_10k"
  | "10k_50k"
  | "50k_90k"
  | "ge_90k"
  | "unknown";
export type CheckVehiclesBand = "lt_50" | "50_150" | "ge_150" | "none";
export type CheckWarehouseTonsBand = "lt_100k" | "100k_700k" | "ge_700k" | "none";
export type CheckCloStatus = "appointed" | "planning" | "not_considered";
export type CheckVerdict = "applies" | "gray_zone" | "not_applies";
export type CheckCategory =
  | "shipper"
  | "chain_franchise"
  | "warehouse"
  | "freight_transport";

export interface CheckRequest {
  industry: CheckIndustryHint;
  freight_tons_band: CheckFreightTonsBand;
  vehicles_band: CheckVehiclesBand;
  warehouse_tons_band: CheckWarehouseTonsBand;
  annual_revenue_jpy?: number | null;
  clo_status: CheckCloStatus;
  is_chain_franchise: boolean;
}

export interface CategoryFinding {
  category: CheckCategory;
  verdict: CheckVerdict;
  reason: string;
  legal_article: string;
  threshold_label: string;
}

export interface CheckMetadata {
  overall_verdict: CheckVerdict;
  findings: CategoryFinding[];
  notes: string[];
  days_until_deadline: number;
  submission_deadline: string;
  submission_deadline_label: string;
  submission_deadline_source_label: string;
  submission_deadline_source_url: string;
  enforcement_date: string;
  penalty: Record<string, string>;
}

export async function runEligibilityCheck(
  body: CheckRequest,
): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/check", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ─── Tier S1: DecisionLog 永続化 ─────────────────────────────────────────
// Tier S1 PR でのみ追加。並列セッション B/C は本セクションをスキップして良い。

export type DecisionType =
  | "cockpit_single"
  | "measure_eval_topbottom"
  | "scenario_sim_baseline"
  | "plan_draft_freeze"
  | "free_form";

export interface ContextSnapshotPayload {
  snapshot_date: string; // ISO date YYYY-MM-DD
  load_factor_pct: number | null;
  wait_time_avg_min: number | null;
  wait_time_max_min: number | null;
  handling_time_avg_min: number | null;
  over_2h_count_total: number | null;
  co2_intensity_g_per_tonkm: number | null;
  f2_score: number | null;
  j2_trap_count_high: number | null;
  related_kpi_name: string | null;
  compliance_overall: ComplianceStatus | null;
  feasibility_kpi_level: VerdictLevel | null;
  extra: Record<string, number | string | string[] | null>;
}

export interface DecisionLogEntry {
  entry_id: string;
  company_id: string;
  decision_type: DecisionType;
  decided_at: string; // ISO datetime
  decided_by: string;
  headline: string;
  rationale: string;
  selected_measures: string[];
  rejected_measures: string[];
  sources: Citation[];
  context_snapshot: ContextSnapshotPayload;
  linked_cockpit_record_id: string | null;
  review_due: string | null;
  tags: string[];
  legacy_source: boolean;
}

export interface DecisionLogQueryResponse {
  company_id: string;
  count: number;
  entries: DecisionLogEntry[];
}

export interface DecisionLogRecordRequest {
  decision_type: DecisionType;
  decided_by: string;
  headline: string;
  rationale?: string;
  selected_measures?: string[];
  rejected_measures?: string[];
  sources?: Citation[];
  context_snapshot: ContextSnapshotPayload;
  linked_cockpit_record_id?: string | null;
  review_due?: string | null;
  tags?: string[];
}

export async function fetchDecisionLogEntries(
  companyId: string,
  opts: {
    decisionType?: DecisionType;
    fromDate?: string;
    toDate?: string;
    decidedBy?: string;
    includeLegacyCockpit?: boolean;
    limit?: number;
  } = {},
): Promise<DecisionLogQueryResponse> {
  const qs = new URLSearchParams();
  if (opts.decisionType) qs.set("decision_type", opts.decisionType);
  if (opts.fromDate) qs.set("from_date", opts.fromDate);
  if (opts.toDate) qs.set("to_date", opts.toDate);
  if (opts.decidedBy) qs.set("decided_by", opts.decidedBy);
  if (opts.includeLegacyCockpit === false)
    qs.set("include_legacy_cockpit", "false");
  if (opts.limit) qs.set("limit", String(opts.limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<DecisionLogQueryResponse>(
    `/api/v1/clo/decision-logs/${encodeURIComponent(companyId)}${suffix}`,
  );
}

export async function recordDecisionLogEntry(
  companyId: string,
  body: DecisionLogRecordRequest,
): Promise<{
  entry_id: string;
  company_id: string;
  decision_type: DecisionType;
  log_path: string;
}> {
  return request(
    `/api/v1/clo/decision-logs/${encodeURIComponent(companyId)}`,
    {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    },
  );
}
