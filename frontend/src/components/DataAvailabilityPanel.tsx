import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import type { DataQualityReportResponse, NationalTrendPoint } from "../types/dashboard";
import { VerifiedStamp } from "./DemoStamp";

interface DataAvailabilityPanelProps {
  nationalTrend: NationalTrendPoint[];
  qualitySummary: DataQualityReportResponse | null;
  selectedYear: number;
}

export const DataAvailabilityPanel: React.FC<DataAvailabilityPanelProps> = ({
  nationalTrend,
  qualitySummary,
  selectedYear,
}) => {
  const [showFlags, setShowFlags] = useState(false);

  const verifiedCount = qualitySummary?.validation_status_breakdown?.verified ?? 0;
  const warningCount = qualitySummary?.validation_status_breakdown?.warning ?? 0;
  const totalIssues = qualitySummary?.total_issues ?? 0;

  return (
    <section className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#2D2D34]">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">
              Data Availability &amp; Quality Indicators
            </h3>
            <VerifiedStamp label={`${verifiedCount.toLocaleString()} VERIFIED RECORDS`} />
          </div>
          <p className="mt-1 text-xs text-[#B8B4B4]">
            Transparent year-by-year NCRB table coverage and automated ingestion validation flags.
          </p>
        </div>

        {qualitySummary && (
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
            <span className="inline-flex items-center gap-1.5 border border-[#2D2D34] bg-[#19191D] px-2.5 py-1 text-[#F5F2EF] font-medium">
              <CheckCircle2 className="h-3 w-3 text-[#E53945]" aria-hidden="true" />
              Verified: {verifiedCount.toLocaleString()}
            </span>
            <span className="inline-flex items-center gap-1.5 border border-amber-500/40 bg-amber-950/35 px-2.5 py-1 text-amber-200 font-medium">
              <AlertTriangle className="h-3 w-3 text-amber-400" aria-hidden="true" />
              Warnings: {warningCount} · Audit Flags: {totalIssues}
            </span>
          </div>
        )}
      </div>

      {/* Year-by-Year Coverage Matrix */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {nationalTrend.map((pt) => {
          const isSelected = pt.year === selectedYear;
          return (
            <div
              key={pt.year}
              className={`border p-3 text-xs transition-colors ${
                isSelected
                  ? "border-[#E53945] bg-[#B51F32]/20 ring-1 ring-[#E53945]"
                  : "border-[#2D2D34] bg-[#19191D]"
              }`}
            >
              <div className="flex items-center justify-between gap-1 pb-1.5 mb-2 border-b border-[#2D2D34]">
                <span className="font-mono font-semibold text-[#F5F2EF]">{pt.year}</span>
                <span
                  className={`font-mono text-[9px] font-semibold uppercase ${
                    pt.rape_cases_available ? "text-[#E53945]" : "text-amber-300"
                  }`}
                >
                  {pt.rape_cases_available ? "Full 3A" : "CAW Only"}
                </span>
              </div>
              <div className="space-y-1 font-mono text-[10px] text-[#B8B4B4]">
                <div className="flex justify-between">
                  <span>Sec. 376:</span>
                  <span
                    className={
                      pt.rape_cases_available ? "text-[#F5F2EF] font-semibold" : "text-[#6E6E78]"
                    }
                  >
                    {pt.rape_cases_available ? "Yes" : "No"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Disposal:</span>
                  <span
                    className={
                      pt.charge_sheet_pct !== null
                        ? "text-[#F5F2EF] font-semibold"
                        : "text-[#6E6E78]"
                    }
                  >
                    {pt.charge_sheet_pct !== null ? "Nat." : "No"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Total CAW:</span>
                  <span
                    className={
                      pt.caw_total_cases !== null
                        ? "text-[#F5F2EF] font-semibold"
                        : "text-[#6E6E78]"
                    }
                  >
                    {pt.caw_total_cases !== null ? "Yes" : "No"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Collapsible Audit Flags */}
      {qualitySummary && qualitySummary.issues.length > 0 && (
        <div className="border-t border-[#2D2D34] pt-3">
          <button
            type="button"
            onClick={() => setShowFlags((prev) => !prev)}
            className="inline-flex items-center gap-2 font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[#B8B4B4] hover:text-[#E53945] transition-colors"
          >
            {showFlags ? (
              <ChevronUp className="h-3.5 w-3.5 text-[#E53945]" aria-hidden="true" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-[#E53945]" aria-hidden="true" />
            )}
            {showFlags ? "Hide" : "Inspect"} Ingestion Audit Flags ({qualitySummary.issues.length})
          </button>

          {showFlags && (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              {qualitySummary.issues.slice(0, 8).map((iss) => (
                <div key={iss.id} className="border border-[#2D2D34] bg-[#19191D] p-3 text-xs">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-mono text-[10px] font-semibold text-[#E53945]">
                      {iss.issue_code} · {iss.reporting_year ?? "Multi-year"}
                    </span>
                    <span className="font-mono text-[9px] uppercase text-[#B8B4B4]">
                      {iss.severity}
                    </span>
                  </div>
                  <p className="text-[#F5F2EF] font-semibold">{iss.title}</p>
                  <p className="mt-1 text-[11px] text-[#B8B4B4] leading-relaxed">
                    {iss.description}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
};
