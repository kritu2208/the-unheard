import React, { useCallback, useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { useHealth } from "./hooks/useHealth";
import { dashboardApi } from "./services/api";
import type {
  DashboardInsightsResponse,
  DashboardOverviewResponse,
  GeographicAnalysisResponse,
  MetricKey,
  SourcesMethodologyResponse,
  TrendsPatternsResponse,
} from "./types/dashboard";
import { DashboardHeader } from "./components/DashboardHeader";
import { KpiStrip } from "./components/KpiStrip";
import { NationalTrendChart } from "./charts/NationalTrendChart";
import { DisposalAnalysisChart } from "./charts/DisposalAnalysisChart";
import { IndiaMapPlaceholder } from "./maps/IndiaMapPlaceholder";
import { StateComparisonBarChart } from "./charts/StateComparisonBarChart";
import { StateComparisonPanel } from "./components/StateComparisonPanel";
import { DistributionBarChart } from "./charts/DistributionBarChart";
import { AnalyticalInsightsPanel } from "./components/AnalyticalInsightsPanel";
import { DataAvailabilityPanel } from "./components/DataAvailabilityPanel";
import { DashboardFooter } from "./components/DashboardFooter";
import { PanelError, PanelLoading } from "./components/PanelFeedback";
import { VerifiedStamp } from "./components/DemoStamp";
import heroJusticeImg from "./assets/hero-justice-3d.jpg";
import dividerShieldImg from "./assets/divider-shield-3d.jpg";

const GLOBAL_YEARS = [2018, 2019, 2020, 2021, 2022, 2023];

export const App: React.FC = () => {
  const [selectedYear, setSelectedYear] = useState<number>(2022);
  const [selectedStateCode, setSelectedStateCode] = useState<string>("ALL");
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("count");
  const [compareStateCode, setCompareStateCode] = useState<string>("MH");

  const { health, healthError } = useHealth();

  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null);
  const [geographic, setGeographic] = useState<GeographicAnalysisResponse | null>(null);
  const [trends, setTrends] = useState<TrendsPatternsResponse | null>(null);
  const [insightsData, setInsightsData] = useState<DashboardInsightsResponse | null>(null);
  const [sources, setSources] = useState<SourcesMethodologyResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [insightsLoading, setInsightsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<boolean>(false);
  const [exportingPdf, setExportingPdf] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Load source registry & quality summary once
  useEffect(() => {
    let active = true;
    dashboardApi
      .getSources()
      .then((src) => {
        if (active) setSources(src);
      })
      .catch(() => {
        // Non-fatal; footer & audit panel degrade gracefully
      });
    return () => {
      active = false;
    };
  }, []);

  // Load year- and metric-dependent overview, geographic, and demographic disaggregation
  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, geo, tr] = await Promise.all([
        dashboardApi.getOverview(selectedYear, selectedMetric),
        dashboardApi.getGeographic(selectedYear, selectedMetric, "ALL", ""),
        dashboardApi.getTrends(2018, Math.max(selectedYear, 2020)),
      ]);
      setOverview(ov);
      setGeographic(geo);
      setTrends(tr);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load NCRB analytics data."
      );
    } finally {
      setLoading(false);
    }
  }, [selectedYear, selectedMetric]);

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  // Load deterministic insights whenever year, state, metric, or comparison state changes
  useEffect(() => {
    let active = true;
    setInsightsLoading(true);
    dashboardApi
      .getInsights(
        selectedYear,
        selectedStateCode,
        selectedMetric,
        selectedStateCode !== "ALL" ? compareStateCode : undefined
      )
      .then((res) => {
        if (active) setInsightsData(res);
      })
      .catch(() => {
        if (active) setInsightsData(null);
      })
      .finally(() => {
        if (active) setInsightsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedYear, selectedStateCode, selectedMetric, compareStateCode]);

  const allStates = useMemo(() => geographic?.states ?? [], [geographic]);

  const selectedStateRecord = useMemo(() => {
    if (selectedStateCode === "ALL") return null;
    return allStates.find((s) => s.state_code === selectedStateCode) ?? null;
  }, [allStates, selectedStateCode]);

  const topRankedStates = useMemo(() => {
    if (!geographic) return [];
    const ranked = geographic.states.filter((s) => s.rank_by_selected !== null);
    return (ranked.length > 0 ? ranked : geographic.states).slice(0, 15);
  }, [geographic]);

  const handleSelectStateFromViz = useCallback((code: string) => {
    setSelectedStateCode((prev) => (prev === code ? "ALL" : code));
  }, []);

  const hasActiveFilters =
    selectedYear !== 2022 || selectedStateCode !== "ALL" || selectedMetric !== "count";

  const handleResetFilters = useCallback(() => {
    setSelectedYear(2022);
    setSelectedStateCode("ALL");
    setSelectedMetric("count");
  }, []);

  const triggerDownload = (filename: string, content: string, mime: string) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleExportCsv = useCallback(async () => {
    setExporting(true);
    setExportError(null);
    try {
      const stateCodes =
        selectedStateCode !== "ALL"
          ? [selectedStateCode]
          : allStates.map((s) => s.state_code);
      const preview = await dashboardApi.previewResearch({
        metric: selectedMetric,
        years: [selectedYear],
        state_codes: stateCodes,
      });
      triggerDownload(
        `the-unheard-ncrb-${selectedYear}-${selectedStateCode.toLowerCase()}-${selectedMetric}.csv`,
        preview.csv_preview,
        "text/csv;charset=utf-8;"
      );
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "CSV export failed.");
    } finally {
      setExporting(false);
    }
  }, [selectedYear, selectedStateCode, selectedMetric, allStates]);

  const handleExportSummary = useCallback(() => {
    if (!overview) return;
    const stateLabel = selectedStateRecord
      ? `${selectedStateRecord.state_name} (${selectedStateRecord.state_code})`
      : "All India (National)";

    const lines = [
      `# THE UNHEARD — Analytical Summary (${selectedYear})`,
      "",
      `- **Reporting Year:** ${selectedYear}`,
      `- **Jurisdiction:** ${stateLabel}`,
      `- **Active Metric:** ${selectedMetric}`,
      `- **Provenance:** ${overview.data_banner}`,
      "",
      "## Key Indicators",
      ...(selectedStateRecord
        ? [
            `- **Sec. 376 Rape Cases (I):** ${selectedStateRecord.reported_cases?.toLocaleString() ?? "Unavailable"}`,
            `- **Female Victims (V):** ${selectedStateRecord.victims_count?.toLocaleString() ?? "Unavailable"}`,
            `- **Rate per 100k Female Pop.:** ${selectedStateRecord.rate_per_100k_female?.toFixed(1) ?? "Unavailable"}`,
            `- **Total CAW (IPC+SLL):** ${selectedStateRecord.caw_total_cases?.toLocaleString() ?? "Unavailable"}`,
            `- **Source Table:** ${selectedStateRecord.source_table}`,
          ]
        : overview.kpis.map(
            (k) => `- **${k.label}:** ${k.value} (${k.source_table})`
          )),
      "",
      "## Deterministic Statistical Insights",
      ...(insightsData?.insights.flatMap((ins) => [
        `### ${ins.title} (${ins.reporting_year})`,
        `- **Observed:** ${ins.observed_data}`,
        `- **Context:** ${ins.interpretation}`,
        `- **Source:** ${ins.source_table}${ins.source_url ? ` (${ins.source_url})` : ""}`,
        "",
      ]) ?? ["- No insights loaded."]),
      "## Official NCRB Sources",
      ...(sources?.datasets.map((d) => `- ${d.name}: ${d.source_url}`) ?? []),
    ];

    triggerDownload(
      `the-unheard-summary-${selectedYear}-${selectedStateCode.toLowerCase()}.md`,
      lines.join("\n"),
      "text/markdown;charset=utf-8;"
    );
  }, [overview, selectedYear, selectedStateCode, selectedStateRecord, selectedMetric, insightsData, sources]);

  const handleExportPdf = useCallback(async () => {
    setExportingPdf(true);
    setExportError(null);
    try {
      const blob = await dashboardApi.downloadPdfBrief(
        selectedYear,
        selectedStateCode,
        selectedMetric
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `the-unheard-brief-${selectedYear}-${selectedStateCode.toLowerCase()}-${selectedMetric}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(
        err instanceof Error ? err.message : "Analytical PDF generation failed."
      );
    } finally {
      setExportingPdf(false);
    }
  }, [selectedYear, selectedStateCode, selectedMetric]);

  const primaryComparisonCode =
    selectedStateCode !== "ALL"
      ? selectedStateCode
      : allStates[0]?.state_code ?? "RJ";

  return (
    <div className="min-h-screen flex flex-col bg-[#101012] text-[#F5F2EF] overflow-x-hidden">
      <DashboardHeader
        selectedYear={selectedYear}
        availableYears={GLOBAL_YEARS}
        onChangeYear={setSelectedYear}
        selectedStateCode={selectedStateCode}
        stateOptions={allStates}
        onChangeState={setSelectedStateCode}
        selectedMetric={selectedMetric}
        onChangeMetric={setSelectedMetric}
        onResetFilters={handleResetFilters}
        hasActiveFilters={hasActiveFilters}
        onExportCsv={handleExportCsv}
        onExportSummary={handleExportSummary}
        onExportPdf={handleExportPdf}
        exporting={exporting}
        exportingPdf={exportingPdf}
        health={health}
        healthError={healthError}
      />

      <main className="flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-8 py-6 sm:py-8 space-y-7">
        {/* Cinematic Dark Investigative Hero */}
        <section className="relative border border-[#2D2D34] bg-[#19191D] overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-12 items-stretch">
            {/* Left Editorial Column */}
            <div className="lg:col-span-7 p-6 sm:p-8 lg:p-10 flex flex-col justify-between gap-5 relative z-10">
              <div>
                <div className="flex flex-wrap items-center gap-2.5 mb-3">
                  <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-[#E53945]">
                    Investigative Data Journalism · {selectedYear} · {selectedMetric}
                  </span>
                  <VerifiedStamp />
                  {selectedStateRecord && (
                    <button
                      type="button"
                      onClick={() => setSelectedStateCode("ALL")}
                      className="inline-flex items-center gap-1.5 border border-[#E53945] bg-[#B51F32]/25 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#F5F2EF] hover:bg-[#B51F32] transition-colors"
                    >
                      State: {selectedStateRecord.state_name}
                      <X className="h-3 w-3" aria-hidden="true" />
                    </button>
                  )}
                </div>

                <h1 className="font-serif text-3xl sm:text-5xl font-semibold text-[#F5F2EF] tracking-tight leading-[1.1]">
                  THE UNHEARD
                </h1>
                <p className="mt-2 font-serif text-xl sm:text-2xl text-[#E53945] italic">
                  Behind every number, there is a story.
                </p>
                <p className="mt-3 text-sm sm:text-base text-[#B8B4B4] leading-relaxed max-w-2xl">
                  An investigative data-analytics publication examining reported crimes against
                  women and children in India through official NCRB{" "}
                  <em className="text-[#F5F2EF] font-medium">Crime in India</em> Chapter 3A
                  records. Police-recorded FIR counts reflect registered cases under the Principal
                  Offence Rule rather than true societal prevalence.
                </p>
              </div>

              {overview && (
                <div className="border-l-2 border-[#B51F32] bg-[#101012]/80 px-3.5 py-2.5 text-xs text-[#B8B4B4]">
                  <span className="font-mono font-semibold uppercase tracking-[0.12em] text-[#E53945] mr-1.5">
                    Official Provenance:
                  </span>
                  {overview.data_banner}
                </div>
              )}
            </div>

            {/* Right 3D Symbolic Scene */}
            <div className="lg:col-span-5 relative min-h-[220px] sm:min-h-[280px] lg:min-h-full bg-[#101012] border-t lg:border-t-0 lg:border-l border-[#2D2D34]">
              <img
                src={heroJusticeImg}
                alt="Symbolic 3D editorial scene showing a child silhouette from behind facing a protective beam of light and distant justice scales"
                className="w-full h-full object-cover object-center"
              />
              <div
                aria-hidden="true"
                className="absolute inset-0 bg-gradient-to-t lg:bg-gradient-to-r from-[#19191D] via-[#19191D]/25 to-transparent"
              />
            </div>
          </div>
        </section>

        {exportError && (
          <div
            role="alert"
            className="border border-[#E53945]/60 bg-[#B51F32]/20 px-4 py-2.5 text-xs text-[#F5F2EF] font-medium"
          >
            Export error: {exportError}
          </div>
        )}

        {loading && !overview ? (
          <PanelLoading message="Loading official NCRB analytical dataset..." />
        ) : error ? (
          <PanelError message={error} onRetry={loadDashboardData} />
        ) : (
          overview && (
            <>
              {/* 1. KPI Cards Immediately Below Header */}
              <KpiStrip
                kpis={overview.kpis}
                selectedYear={selectedYear}
                selectedState={selectedStateRecord}
              />

              {/* 2. National Historical Trend + Chargesheet/Conviction Analysis */}
              <section className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                <div className="xl:col-span-7">
                  <NationalTrendChart
                    data={overview.national_trend}
                    selectedYear={selectedYear}
                    selectedMetric={selectedMetric}
                    height={300}
                  />
                </div>
                <div className="xl:col-span-5">
                  <DisposalAnalysisChart
                    data={overview.national_trend}
                    selectedYear={selectedYear}
                  />
                </div>
              </section>

              {/* Atmospheric Editorial Divider */}
              <section className="relative border border-[#2D2D34] bg-[#19191D] overflow-hidden px-5 py-4 sm:px-6 sm:py-5">
                <img
                  src={dividerShieldImg}
                  alt="Abstract 3D obsidian glass shield and subtle justice scale backdrop"
                  className="absolute inset-0 w-full h-full object-cover object-center opacity-35"
                />
                <div
                  aria-hidden="true"
                  className="absolute inset-0 bg-gradient-to-r from-[#101012]/90 via-[#101012]/75 to-[#101012]/90"
                />
                <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[#E53945]">
                      Jurisdictional Accountability · {selectedYear}
                    </span>
                    <p className="mt-0.5 text-xs sm:text-sm text-[#F5F2EF]">
                      Comparing State/UT reporting volumes alongside female population denominators —
                      never ranking jurisdictions as safe or unsafe from FIR counts alone.
                    </p>
                  </div>
                </div>
              </section>

              {/* 3. Jurisdiction Intensity Matrix + State-Wise Ranking */}
              <section className="grid grid-cols-1 xl:grid-cols-12 gap-6">
                <div className="xl:col-span-6">
                  <IndiaMapPlaceholder
                    states={allStates}
                    metric={selectedMetric}
                    selectedYear={selectedYear}
                    selectedStateCode={selectedStateCode === "ALL" ? null : selectedStateCode}
                    onSelectState={handleSelectStateFromViz}
                  />
                </div>
                <div className="xl:col-span-6">
                  <StateComparisonBarChart
                    states={topRankedStates}
                    metric={selectedMetric}
                    selectedStateCode={selectedStateCode === "ALL" ? null : selectedStateCode}
                    onSelectState={handleSelectStateFromViz}
                    height={370}
                    unavailableReason={
                      geographic?.metric_unavailable_reason ??
                      overview.metric_unavailable_reason ??
                      `Granular State/UT Sec. 376 Rape figures are unavailable for ${selectedYear}. Switch to 2020–2022 to inspect State rankings.`
                    }
                  />
                </div>
              </section>

              {/* 4. State-to-State Comparison */}
              <StateComparisonPanel
                states={allStates}
                primaryCode={primaryComparisonCode}
                compareCode={compareStateCode}
                onChangePrimary={(code) => setSelectedStateCode(code)}
                onChangeCompare={setCompareStateCode}
                selectedYear={selectedYear}
                selectedMetric={selectedMetric}
              />

              {/* 5. Victim & Offender Demographic Breakdowns */}
              {trends && (
                <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <DistributionBarChart
                    title={`Offender-to-Victim Relationship (${trends.disaggregation_year})`}
                    subtitle={`Official NCRB Table 3A.4 distribution across All-India registered Sec. 376 cases.${
                      trends.disaggregation_year !== selectedYear
                        ? ` (Shown for ${trends.disaggregation_year}; unavailable for ${selectedYear}.)`
                        : ""
                    }`}
                    buckets={trends.offender_relationship}
                  />
                  <DistributionBarChart
                    title={`Victim Age-Cohort Distribution (${trends.disaggregation_year})`}
                    subtitle={`Official NCRB Table 3A.3 female victim age brackets.${
                      trends.disaggregation_year !== selectedYear
                        ? ` (Shown for ${trends.disaggregation_year}; unavailable for ${selectedYear}.)`
                        : ""
                    }`}
                    buckets={trends.age_group_breakdown}
                  />
                </section>
              )}

              {/* 6. Deterministic Statistical Insights */}
              <AnalyticalInsightsPanel
                insightsData={insightsData}
                loading={insightsLoading}
              />

              {/* 7. Data Availability & Quality Indicators */}
              <DataAvailabilityPanel
                nationalTrend={overview.national_trend}
                qualitySummary={sources?.quality_summary ?? null}
                selectedYear={selectedYear}
              />
            </>
          )
        )}
      </main>

      {/* 8. Source & Methodology Footer */}
      {sources && (
        <DashboardFooter
          datasets={sources.datasets}
          methodologySections={sources.methodology_sections}
        />
      )}
    </div>
  );
};

export default App;
