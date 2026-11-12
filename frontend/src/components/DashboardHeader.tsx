import React from "react";
import { Download, FileText, RotateCcw } from "lucide-react";
import type { HealthStatus, MetricKey, StateRecord } from "../types/dashboard";

interface DashboardHeaderProps {
  selectedYear: number;
  availableYears: number[];
  onChangeYear: (year: number) => void;
  selectedStateCode: string;
  stateOptions: StateRecord[];
  onChangeState: (code: string) => void;
  selectedMetric: MetricKey;
  onChangeMetric: (metric: MetricKey) => void;
  onResetFilters: () => void;
  hasActiveFilters: boolean;
  onExportCsv: () => void;
  onExportSummary: () => void;
  onExportPdf: () => void;
  exporting: boolean;
  exportingPdf?: boolean;
  health: HealthStatus | null;
  healthError: string | null;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  selectedYear,
  availableYears,
  onChangeYear,
  selectedStateCode,
  stateOptions,
  onChangeState,
  selectedMetric,
  onChangeMetric,
  onResetFilters,
  hasActiveFilters,
  onExportCsv,
  onExportSummary,
  onExportPdf,
  exporting,
  exportingPdf = false,
  health,
  healthError,
}) => {
  const yearModified = selectedYear !== 2022;
  const stateModified = selectedStateCode !== "ALL";
  const metricModified = selectedMetric !== "count";

  return (
    <header className="sticky top-0 z-40 border-b border-[#2D2D34] bg-[#101012]/95 backdrop-blur-md">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-8 py-3 flex flex-col xl:flex-row xl:items-center justify-between gap-3">
        {/* Brand Masthead */}
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <span className="font-serif text-xl sm:text-2xl font-semibold tracking-tight text-[#F5F2EF]">
                THE UNHEARD
              </span>
              <span className="hidden sm:inline-block font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-[#F5F2EF] border border-[#B51F32]/70 bg-[#B51F32]/20 px-2 py-0.5">
                NCRB 2018–2023
              </span>
            </div>
            <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-[#B8B4B4] mt-0.5">
              Investigative Data Journalism · Crime in India Chapter 3A
            </p>
          </div>

          {/* Mobile Status Dot */}
          <div
            className="xl:hidden flex items-center gap-1.5 border border-[#2D2D34] bg-[#19191D] px-2.5 py-1"
            title={healthError ?? "Database status"}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                health?.database_connected
                  ? "bg-[#E53945]"
                  : healthError
                  ? "bg-amber-400"
                  : "bg-[#B8B4B4]"
              }`}
              aria-hidden="true"
            />
            <span className="font-mono text-[9px] font-medium uppercase tracking-[0.14em] text-[#F5F2EF]">
              {health?.database_connected ? "DB LIVE" : healthError ? "OFFLINE" : "..."}
            </span>
          </div>
        </div>

        {/* Global Filters + Reset + Exports + Status */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Reporting Year */}
          <div
            className={`flex items-center border px-2.5 py-1.5 gap-2 max-w-full transition-colors ${
              yearModified
                ? "border-[#E53945] bg-[#B51F32]/20"
                : "border-[#2D2D34] bg-[#19191D]"
            }`}
          >
            <label
              htmlFor="global-year-filter"
              className={`font-mono text-[10px] font-medium uppercase tracking-[0.14em] ${
                yearModified ? "text-[#E53945]" : "text-[#B8B4B4]"
              }`}
            >
              Year
            </label>
            <select
              id="global-year-filter"
              value={selectedYear}
              onChange={(e) => onChangeYear(Number(e.target.value))}
              className="bg-transparent font-mono text-xs font-medium text-[#F5F2EF] focus:outline-none cursor-pointer min-w-0 truncate"
            >
              {availableYears.map((yr) => (
                <option key={yr} value={yr} className="bg-[#19191D] text-[#F5F2EF]">
                  {yr}{" "}
                  {yr >= 2020 && yr <= 2022
                    ? "· Sec. 376 + CAW"
                    : yr === 2023
                    ? "· CAW Snapshot"
                    : "· CAW Only"}
                </option>
              ))}
            </select>
          </div>

          {/* State / UT Filter */}
          <div
            className={`flex items-center border px-2.5 py-1.5 gap-2 max-w-full transition-colors ${
              stateModified
                ? "border-[#E53945] bg-[#B51F32]/20"
                : "border-[#2D2D34] bg-[#19191D]"
            }`}
          >
            <label
              htmlFor="global-state-filter"
              className={`font-mono text-[10px] font-medium uppercase tracking-[0.14em] ${
                stateModified ? "text-[#E53945]" : "text-[#B8B4B4]"
              }`}
            >
              State
            </label>
            <select
              id="global-state-filter"
              value={selectedStateCode}
              onChange={(e) => onChangeState(e.target.value)}
              className="bg-transparent font-mono text-xs font-medium text-[#F5F2EF] focus:outline-none cursor-pointer max-w-[170px]"
            >
              <option value="ALL" className="bg-[#19191D] text-[#F5F2EF]">
                All India (National)
              </option>
              {stateOptions.map((st) => (
                <option
                  key={st.state_code}
                  value={st.state_code}
                  className="bg-[#19191D] text-[#F5F2EF]"
                >
                  {st.state_name} ({st.state_code})
                </option>
              ))}
            </select>
          </div>

          {/* Metric Filter */}
          <div
            className={`flex items-center border px-2.5 py-1.5 gap-2 max-w-full transition-colors ${
              metricModified
                ? "border-[#E53945] bg-[#B51F32]/20"
                : "border-[#2D2D34] bg-[#19191D]"
            }`}
          >
            <label
              htmlFor="global-metric-filter"
              className={`font-mono text-[10px] font-medium uppercase tracking-[0.14em] ${
                metricModified ? "text-[#E53945]" : "text-[#B8B4B4]"
              }`}
            >
              Metric
            </label>
            <select
              id="global-metric-filter"
              value={selectedMetric}
              onChange={(e) => onChangeMetric(e.target.value as MetricKey)}
              className="bg-transparent font-mono text-xs font-medium text-[#F5F2EF] focus:outline-none cursor-pointer"
            >
              <option value="count" className="bg-[#19191D] text-[#F5F2EF]">
                Cases (Sec. 376 IPC)
              </option>
              <option value="victims" className="bg-[#19191D] text-[#F5F2EF]">
                Female Victims (V)
              </option>
              <option value="rate_per_100k" className="bg-[#19191D] text-[#F5F2EF]">
                Rate / 100k Female Pop.
              </option>
              <option value="charge_sheet_pct" className="bg-[#19191D] text-[#F5F2EF]">
                Chargesheet % (Nat.)
              </option>
              <option value="conviction_pct" className="bg-[#19191D] text-[#F5F2EF]">
                Conviction % (Nat.)
              </option>
            </select>
          </div>

          {/* Reset Filters */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={onResetFilters}
              title="Reset Year, State, and Metric to defaults (2022 · All India · Cases)"
              className="inline-flex items-center gap-1 border border-[#2D2D34] bg-[#19191D] hover:border-[#E53945] hover:text-[#F5F2EF] px-2.5 py-1.5 font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-[#B8B4B4] transition-colors"
            >
              <RotateCcw className="h-3 w-3" aria-hidden="true" />
              Reset
            </button>
          )}

          {/* Export CSV */}
          <button
            type="button"
            onClick={onExportCsv}
            disabled={exporting}
            className="inline-flex items-center gap-1.5 border border-[#E53945]/70 bg-[#B51F32] hover:bg-[#E53945] disabled:opacity-50 px-3 py-1.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-[#F5F2EF] transition-colors"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            {exporting ? "Exporting..." : "CSV"}
          </button>

          {/* Export 1-Page Analytical PDF Brief */}
          <button
            type="button"
            onClick={onExportPdf}
            disabled={exportingPdf}
            title="Download verified 1-page A4 landscape analytical executive brief for current filters"
            className="inline-flex items-center gap-1.5 border border-[#E53945]/70 bg-[#B51F32]/80 hover:bg-[#E53945] disabled:opacity-50 px-2.5 py-1.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-[#F5F2EF] transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-[#F5F2EF]" aria-hidden="true" />
            {exportingPdf ? "Generating..." : "PDF Brief"}
          </button>

          {/* Export Markdown Summary */}
          <button
            type="button"
            onClick={onExportSummary}
            title="Download Markdown summary of currently filtered metrics, insights & sources"
            className="inline-flex items-center gap-1.5 border border-[#F5F2EF]/25 bg-[#19191D] hover:border-[#E53945] hover:bg-[#202025] px-2.5 py-1.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-[#F5F2EF] transition-colors"
          >
            <FileText className="h-3.5 w-3.5 text-[#E53945]" aria-hidden="true" />
            MD
          </button>

          {/* Desktop Live DB Indicator */}
          <div
            className="hidden 2xl:flex items-center gap-2 border border-[#2D2D34] bg-[#19191D] px-3 py-1.5"
            title={
              health
                ? `API ${health.status} · ${health.database_dialect} · Verified rows: ${health.verified_records_count}`
                : healthError ?? "Checking backend..."
            }
          >
            <span
              className={`h-2 w-2 rounded-full ${
                health?.database_connected
                  ? "bg-[#E53945]"
                  : healthError
                  ? "bg-amber-400"
                  : "bg-[#B8B4B4]"
              }`}
              aria-hidden="true"
            />
            <span className="font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-[#F5F2EF]">
              {health?.database_connected
                ? `${health.verified_records_count.toLocaleString()} VERIFIED`
                : healthError
                ? "OFFLINE"
                : "..."}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
