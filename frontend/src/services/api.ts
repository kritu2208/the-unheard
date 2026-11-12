import type {
  AIQueryResponse,
  DashboardInsightsResponse,
  DashboardOverviewResponse,
  DataQualityReportResponse,
  DatasetListResponse,
  GeographicAnalysisResponse,
  HealthStatus,
  MetricKey,
  ResearchPreviewRequest,
  ResearchPreviewResponse,
  SourcesMethodologyResponse,
  TrendsPatternsResponse,
} from "../types/dashboard";

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, "") || "/api";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!res.ok) {
    let msg = `API request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.error?.message) {
        msg = body.error.message;
      }
    } catch {
      // Ignore non-JSON error payloads
    }
    throw new Error(msg);
  }

  return (await res.json()) as T;
}

export const dashboardApi = {
  getHealth: () => fetchJson<HealthStatus>("/health"),

  getOverview: (year: number, metric: MetricKey) =>
    fetchJson<DashboardOverviewResponse>(
      `/dashboard/overview?year=${encodeURIComponent(year)}&metric=${encodeURIComponent(metric)}`
    ),

  getGeographic: (year: number, metric: MetricKey, region: string, search: string) =>
    fetchJson<GeographicAnalysisResponse>(
      `/dashboard/geographic?year=${encodeURIComponent(year)}&metric=${encodeURIComponent(metric)}&region=${encodeURIComponent(region)}&search=${encodeURIComponent(search)}`
    ),

  getTrends: (startYear?: number, endYear?: number) => {
    const params = new URLSearchParams();
    if (startYear !== undefined) params.set("start_year", String(startYear));
    if (endYear !== undefined) params.set("end_year", String(endYear));
    const qs = params.toString();
    return fetchJson<TrendsPatternsResponse>(`/dashboard/trends${qs ? `?${qs}` : ""}`);
  },

  getAISuggestions: () =>
    fetchJson<{ status: string; suggested_questions: string[] }>("/ai/suggestions"),

  queryAI: (question: string) =>
    fetchJson<AIQueryResponse>("/ai/query", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  previewResearch: (payload: ResearchPreviewRequest) =>
    fetchJson<ResearchPreviewResponse>("/research/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSources: () => fetchJson<SourcesMethodologyResponse>("/sources"),

  getDatasets: () => fetchJson<DatasetListResponse>("/datasets"),

  getDataQuality: () => fetchJson<DataQualityReportResponse>("/data-quality"),

  getInsights: (
    year: number,
    stateCode: string,
    metric: MetricKey,
    compareCode?: string
  ) => {
    const params = new URLSearchParams({
      year: String(year),
      state_code: stateCode,
      metric,
    });
    if (compareCode) params.set("compare_code", compareCode);
    return fetchJson<DashboardInsightsResponse>(`/dashboard/insights?${params.toString()}`);
  },
  downloadPdfBrief: async (
    year: number,
    stateCode: string,
    metric: MetricKey,
    compareCode?: string
  ): Promise<Blob> => {
    const params = new URLSearchParams({
      year: String(year),
      state_code: stateCode,
      metric,
    });
    if (compareCode) params.set("compare_code", compareCode);
    const res = await fetch(`${API_BASE}/research/pdf?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to generate analytical PDF brief (${res.status})`);
    }
    return await res.blob();
  },
};

