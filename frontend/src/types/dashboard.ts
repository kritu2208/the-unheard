export type DashboardSectionId =
  | "overview"
  | "geographic"
  | "trends"
  | "ai"
  | "research"
  | "sources";

export type MetricKey =
  | "count"
  | "victims"
  | "rate_per_100k"
  | "charge_sheet_pct"
  | "conviction_pct";

export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  database_connected: boolean;
  database_dialect: string;
  data_mode: string;
  verified_records_count: number;
  latest_granular_year: number | null;
  latest_publication_year: number | null;
  timestamp: string;
}

export interface KPIItem {
  id: string;
  label: string;
  value: string;
  available: boolean;
  unavailable_reason: string | null;
  delta_label: string | null;
  delta_direction: "up" | "down" | "neutral";
  unit: string;
  source_table: string;
  footnote: string;
}

export interface NationalTrendPoint {
  year: number;
  rape_cases_available: boolean;
  reported_cases: number | null;
  victims_count: number | null;
  rate_per_100k_female: number | null;
  charge_sheet_pct: number | null;
  conviction_pct: number | null;
  trial_pendency_pct: number | null;
  caw_total_cases: number | null;
  caw_rate_per_100k_female: number | null;
  yoy_change_pct: number | null;
  caw_yoy_change_pct: number | null;
  statutory_note: string | null;
  source_table: string;
}

export interface StateRecord {
  state_code: string;
  state_name: string;
  unit_type: string;
  region_zone: string;
  year: number;
  reported_cases: number | null;
  victims_count: number | null;
  rate_per_100k_female: number | null;
  female_population_lakhs: number | null;
  caw_total_cases: number | null;
  caw_charge_sheet_pct: number | null;
  caw_conviction_pct: number | null;
  charge_sheet_pct: number | null;
  conviction_pct: number | null;
  metric_available: boolean;
  unavailable_reason: string | null;
  rank_by_selected: number | null;
  validation_status: string;
  source_table: string;
  boundary_note: string | null;
}

export interface StatisticalObservation {
  id: string;
  title: string;
  category: string;
  summary: string;
  source_table: string;
}

export interface DeterministicInsight {
  id: string;
  category: string;
  title: string;
  observed_data: string;
  interpretation: string;
  reporting_year: number;
  metric: MetricKey;
  source_table: string;
  source_url: string | null;
}

export interface DashboardInsightsResponse {
  selected_year: number;
  selected_state_code: string;
  selected_state_name: string;
  selected_metric: MetricKey;
  calculation_mode: "deterministic_db";
  llm_provider_configured: boolean;
  insights: DeterministicInsight[];
}

export interface SourceTransparencyBadge {
  dataset_name: string;
  reporting_period: string;
  latest_granular_year: number;
  latest_publication_year: number;
  last_ingested_at: string | null;
  source_status: string;
  data_notice: string;
}

export interface DashboardOverviewResponse {
  data_mode: string;
  data_banner: string;
  selected_year: number;
  available_years: number[];
  granular_rape_years: number[];
  selected_metric: MetricKey;
  metric_available: boolean;
  metric_unavailable_reason: string | null;
  kpis: KPIItem[];
  national_trend: NationalTrendPoint[];
  top_states: StateRecord[];
  research_insights: StatisticalObservation[];
  source_transparency: SourceTransparencyBadge;
}

export interface GeographicAnalysisResponse {
  data_mode: string;
  data_banner: string;
  selected_year: number;
  available_years: number[];
  granular_rape_years: number[];
  selected_metric: MetricKey;
  metric_available: boolean;
  metric_unavailable_reason: string | null;
  regions: string[];
  states: StateRecord[];
  denominator_methodology: string;
  map_architecture_status: string;
}

export interface DemographicBucket {
  category: string;
  count: number | null;
  share_pct: number | null;
  unit: string;
  year: number;
  source_table: string;
  note: string;
}

export interface TrendsPatternsResponse {
  data_mode: string;
  data_banner: string;
  start_year: number;
  end_year: number;
  available_years: number[];
  disaggregation_year: number;
  series: NationalTrendPoint[];
  offender_relationship: DemographicBucket[];
  age_group_breakdown: DemographicBucket[];
  anomalies: StatisticalObservation[];
}

export interface AIQueryResponse {
  status: "unavailable_phase_3";
  answered: boolean;
  question: string;
  message: string;
  suggested_questions: string[];
  citation_requirements: string[];
}

export interface ResearchPreviewRequest {
  metric: MetricKey;
  years: number[];
  state_codes: string[];
}

export interface ResearchPreviewResponse {
  data_mode: string;
  data_banner: string;
  metric: MetricKey;
  metric_available: boolean;
  unavailable_reason: string | null;
  years: number[];
  state_codes: string[];
  rows: StateRecord[];
  csv_preview: string;
}

export interface DatasetSource {
  slug: string;
  name: string;
  publisher: string;
  reporting_period: string;
  publication_date: string | null;
  download_date: string;
  status: string;
  granularity: string;
  definitions_summary: string;
  missing_data_notes: string;
  source_url: string;
}

export interface DatasetVersionDetail {
  dataset_key: string;
  source_slug: string;
  table_number: string;
  title: string;
  crime_domain: string;
  granularity: string;
  unit_description: string;
  reporting_year: number;
  version_label: string;
  file_format: string;
  file_sha256: string;
  record_count: number;
  ingestion_status: string;
  ingested_at: string;
  extraction_notes: string;
}

export interface DatasetListResponse {
  total_datasets: number;
  total_crime_records: number;
  total_population_records: number;
  latest_ingested_at: string | null;
  datasets: DatasetVersionDetail[];
}

export interface DataQualityIssue {
  id: number;
  issue_code: string;
  severity: string;
  category: string;
  reporting_year: number | null;
  geo_code: string | null;
  geo_name: string | null;
  title: string;
  description: string;
  source_table: string;
  resolved: boolean;
  detected_at: string;
}

export interface DataQualityReportResponse {
  total_issues: number;
  counts_by_severity: Record<string, number>;
  counts_by_category: Record<string, number>;
  validation_status_breakdown: Record<string, number>;
  issues: DataQualityIssue[];
}

export interface MethodologySection {
  id: string;
  title: string;
  summary: string;
  details: string[];
}

export interface SourcesMethodologyResponse {
  datasets: DatasetSource[];
  dataset_versions: DatasetVersionDetail[];
  quality_summary: DataQualityReportResponse;
  methodology_sections: MethodologySection[];
}
