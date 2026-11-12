from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

MetricKey = Literal["count", "victims", "rate_per_100k", "charge_sheet_pct", "conviction_pct"]


class HealthResponse(BaseModel):
    """Backend health and database connectivity status."""

    status: str
    app_name: str
    version: str
    environment: str
    database_connected: bool
    database_dialect: str
    data_mode: str = "VERIFIED_OFFICIAL_PHASE_2"
    verified_records_count: int = 0
    latest_granular_year: Optional[int] = None
    latest_publication_year: Optional[int] = None
    timestamp: datetime


class KPIItem(BaseModel):
    """Executive KPI readout grounded in verified database records (or explicit unavailable state)."""

    id: str
    label: str
    value: str
    available: bool = True
    unavailable_reason: Optional[str] = None
    delta_label: Optional[str] = None
    delta_direction: Literal["up", "down", "neutral"] = "neutral"
    unit: str
    source_table: str
    footnote: str


class NationalTrendPoint(BaseModel):
    """Annual longitudinal observation mixing Sec. 376 Rape and contextual CAW without conflation."""

    year: int
    rape_cases_available: bool = True
    reported_cases: Optional[int] = None
    victims_count: Optional[int] = None
    rate_per_100k_female: Optional[float] = None
    charge_sheet_pct: Optional[float] = None
    conviction_pct: Optional[float] = None
    trial_pendency_pct: Optional[float] = None
    caw_total_cases: Optional[int] = None
    caw_rate_per_100k_female: Optional[float] = None
    yoy_change_pct: Optional[float] = None
    caw_yoy_change_pct: Optional[float] = None
    statutory_note: Optional[str] = None
    source_table: str


class StateRecord(BaseModel):
    """Normalized State/UT verified statistical observation with strict unit & denominator attribution."""

    state_code: str
    state_name: str
    unit_type: str
    region_zone: str
    year: int
    reported_cases: Optional[int] = None
    victims_count: Optional[int] = None
    rate_per_100k_female: Optional[float] = None
    female_population_lakhs: Optional[float] = None
    caw_total_cases: Optional[int] = None
    caw_charge_sheet_pct: Optional[float] = None
    caw_conviction_pct: Optional[float] = None
    charge_sheet_pct: Optional[float] = None
    conviction_pct: Optional[float] = None
    metric_available: bool = True
    unavailable_reason: Optional[str] = None
    rank_by_selected: Optional[int] = None
    validation_status: str = "verified"
    source_table: str
    boundary_note: Optional[str] = None


class StatisticalObservation(BaseModel):
    """Traceable analytical observation computed directly from verified NCRB figures."""

    id: str
    title: str
    category: str
    summary: str
    source_table: str


class DeterministicInsight(BaseModel):
    """Deterministic DB-computed insight separating observed data from interpretation."""

    id: str
    category: str
    title: str
    observed_data: str
    interpretation: str
    reporting_year: int
    metric: MetricKey
    source_table: str
    source_url: Optional[str] = None


class DashboardInsightsResponse(BaseModel):
    """Payload for deterministic contextual dashboard insights."""

    selected_year: int
    selected_state_code: str
    selected_state_name: str
    selected_metric: MetricKey
    calculation_mode: Literal["deterministic_db"] = "deterministic_db"
    llm_provider_configured: bool = False
    insights: List[DeterministicInsight]


class SourceTransparencyBadge(BaseModel):
    """Live provenance & ingestion freshness indicator."""

    dataset_name: str
    reporting_period: str
    latest_granular_year: int
    latest_publication_year: int
    last_ingested_at: Optional[str] = None
    source_status: str
    data_notice: str


class DashboardOverviewResponse(BaseModel):
    """Payload for the Overview analytical workspace."""

    data_mode: str = "VERIFIED_OFFICIAL"
    data_banner: str
    selected_year: int
    available_years: List[int]
    granular_rape_years: List[int]
    selected_metric: MetricKey
    metric_available: bool = True
    metric_unavailable_reason: Optional[str] = None
    kpis: List[KPIItem]
    national_trend: List[NationalTrendPoint]
    top_states: List[StateRecord]
    research_insights: List[StatisticalObservation]
    source_transparency: SourceTransparencyBadge


class GeographicAnalysisResponse(BaseModel):
    """Payload for Geographic Analysis workspace."""

    data_mode: str = "VERIFIED_OFFICIAL"
    data_banner: str
    selected_year: int
    available_years: List[int]
    granular_rape_years: List[int]
    selected_metric: MetricKey
    metric_available: bool = True
    metric_unavailable_reason: Optional[str] = None
    regions: List[str]
    states: List[StateRecord]
    denominator_methodology: str
    map_architecture_status: str


class DemographicBucket(BaseModel):
    """Official NCRB structural disaggregation bucket (Table 3A.3 Age / Table 3A.4 Offender Relation)."""

    category: str
    count: Optional[int] = None
    share_pct: Optional[float] = None
    unit: str
    year: int
    source_table: str
    note: str


class TrendsPatternsResponse(BaseModel):
    """Payload for Trends & Patterns workspace."""

    data_mode: str = "VERIFIED_OFFICIAL"
    data_banner: str
    start_year: int
    end_year: int
    available_years: List[int]
    disaggregation_year: int
    series: List[NationalTrendPoint]
    offender_relationship: List[DemographicBucket]
    age_group_breakdown: List[DemographicBucket]
    anomalies: List[StatisticalObservation]


class AIQueryRequest(BaseModel):
    """Natural-language question submitted to AI Intelligence."""

    question: str = Field(..., min_length=3, max_length=600)


class AIQueryResponse(BaseModel):
    """Phase 3 AI readiness response until AI synthesis is connected."""

    status: Literal["unavailable_phase_3"]
    answered: bool = False
    question: str
    message: str
    suggested_questions: List[str]
    citation_requirements: List[str]


class ResearchPreviewRequest(BaseModel):
    """Filter configuration for Research & Export workspace."""

    metric: MetricKey = "count"
    years: List[int] = Field(default_factory=lambda: [2020, 2021, 2022])
    state_codes: List[str] = Field(default_factory=list)


class ResearchPreviewResponse(BaseModel):
    """Filtered comparative official records and citation-embedded CSV export preview."""

    data_mode: str = "VERIFIED_OFFICIAL"
    data_banner: str
    metric: MetricKey
    metric_available: bool = True
    unavailable_reason: Optional[str] = None
    years: List[int]
    state_codes: List[str]
    rows: List[StateRecord]
    csv_preview: str


class DatasetSourceSchema(BaseModel):
    """Official publisher source entry returned in Sources & Methodology."""

    slug: str
    name: str
    publisher: str
    reporting_period: str
    publication_date: Optional[str] = None
    download_date: str
    status: str
    granularity: str
    definitions_summary: str
    missing_data_notes: str
    source_url: str


class DatasetVersionDetailSchema(BaseModel):
    """Versioned table ingestion record exposed by GET /api/datasets."""

    dataset_key: str
    source_slug: str
    table_number: str
    title: str
    crime_domain: str
    granularity: str
    unit_description: str
    reporting_year: int
    version_label: str
    file_format: str
    file_sha256: str
    record_count: int
    ingestion_status: str
    ingested_at: datetime
    extraction_notes: str


class DatasetListResponse(BaseModel):
    """Registry of ingested datasets and active versions."""

    total_datasets: int
    total_crime_records: int
    total_population_records: int
    latest_ingested_at: Optional[datetime] = None
    datasets: List[DatasetVersionDetailSchema]


class DataQualityIssueSchema(BaseModel):
    """Automated audit/quality finding exposed by GET /api/data-quality."""

    id: int
    issue_code: str
    severity: str
    category: str
    reporting_year: Optional[int] = None
    geo_code: Optional[str] = None
    geo_name: Optional[str] = None
    title: str
    description: str
    source_table: str
    resolved: bool
    detected_at: datetime


class DataQualityReportResponse(BaseModel):
    """Summary & itemized report from automated ingestion validation checks."""

    total_issues: int
    counts_by_severity: Dict[str, int]
    counts_by_category: Dict[str, int]
    validation_status_breakdown: Dict[str, int]
    issues: List[DataQualityIssueSchema]


class MethodologySectionSchema(BaseModel):
    """Structured documentation block for methodology & definitions."""

    id: str
    title: str
    summary: str
    details: List[str]


class SourcesMethodologyResponse(BaseModel):
    """Combined Sources, Dataset Versions, Data Quality summary & Methodology payload."""

    datasets: List[DatasetSourceSchema]
    dataset_versions: List[DatasetVersionDetailSchema]
    quality_summary: DataQualityReportResponse
    methodology_sections: List[MethodologySectionSchema]
