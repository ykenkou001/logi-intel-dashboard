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
}

export interface SampleCompany {
  company_id: string;
  name: string;
  industry: string;
  data_source: DataSource;
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

// ─── 拠点別待機時間ヒートマップ（フェーズ4.1 a.1）─────────────
export async function fetchWaitHeatmap(companyId: string): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/clo/wait-heatmap", {
    searchParams: { company_id: companyId },
  });
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

// ─── 施策評価エンジン（Top 3 推薦）─────────────────────────────
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
export async function generateCompanyTemplate(): Promise<ToolResponse> {
  return request<ToolResponse>("/api/v1/company/template", { method: "POST" });
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
