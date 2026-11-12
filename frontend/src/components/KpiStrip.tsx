import React from "react";
import type { KPIItem, StateRecord } from "../types/dashboard";
import { VerifiedStamp } from "./DemoStamp";

interface KpiStripProps {
  kpis: KPIItem[];
  selectedYear: number;
  selectedState: StateRecord | null;
}

export const KpiStrip: React.FC<KpiStripProps> = ({
  kpis,
  selectedYear,
  selectedState,
}) => {
  const natDisposal = kpis[3];

  const cards: KPIItem[] = selectedState
    ? [
        {
          id: "state_reported_cases",
          label: `${selectedState.state_name} · Rape Cases (Sec. 376)`,
          value:
            selectedState.reported_cases !== null
              ? selectedState.reported_cases.toLocaleString()
              : "Unavailable",
          available: selectedState.reported_cases !== null,
          unavailable_reason:
            selectedState.reported_cases === null
              ? `Granular State/UT Sec. 376 figures are unavailable for ${selectedYear}.`
              : null,
          delta_label: selectedState.rank_by_selected
            ? `Rank #${selectedState.rank_by_selected} in ${selectedYear}`
            : selectedState.region_zone,
          delta_direction: "neutral",
          unit: "Cases (I)",
          source_table: selectedState.source_table,
          footnote: `Jurisdiction ${selectedState.state_code} · ${selectedState.region_zone}`,
        },
        {
          id: "state_victims_rate",
          label: `${selectedState.state_name} · Victims & Rate / 100k`,
          value:
            selectedState.victims_count !== null &&
            selectedState.rate_per_100k_female !== null
              ? `${selectedState.victims_count.toLocaleString()} · ${selectedState.rate_per_100k_female.toFixed(1)}`
              : selectedState.victims_count !== null
              ? selectedState.victims_count.toLocaleString()
              : "Unavailable",
          available: selectedState.victims_count !== null,
          unavailable_reason:
            selectedState.victims_count === null
              ? `State/UT Sec. 376 victim counts unavailable for ${selectedYear}.`
              : null,
          delta_label:
            selectedState.female_population_lakhs !== null
              ? `Fem. Pop: ${selectedState.female_population_lakhs.toFixed(1)}L`
              : null,
          delta_direction: "neutral",
          unit: "Victims (V) · Rate/100k",
          source_table: selectedState.source_table,
          footnote: "Denominator: RGI/MoHFW mid-year projected female population.",
        },
        {
          id: "state_caw_total",
          label: `${selectedState.state_name} · Total CAW (IPC+SLL)`,
          value:
            selectedState.caw_total_cases !== null
              ? selectedState.caw_total_cases.toLocaleString()
              : "Unavailable",
          available: selectedState.caw_total_cases !== null,
          unavailable_reason:
            selectedState.caw_total_cases === null
              ? `State/UT Total CAW unavailable for ${selectedYear}.`
              : null,
          delta_label:
            selectedState.caw_charge_sheet_pct !== null
              ? `CAW CS: ${selectedState.caw_charge_sheet_pct.toFixed(1)}%`
              : null,
          delta_direction: "neutral",
          unit: "All Crimes Against Women",
          source_table: "NCRB TABLE 3A.1 / 3A.6",
          footnote: "Aggregates all IPC+SLL Crimes Against Women; distinct from Sec. 376.",
        },
        {
          id: "state_sec376_disposal",
          label: `${selectedState.state_name} · Sec. 376 Disposal`,
          value: "Unavailable",
          available: false,
          unavailable_reason:
            "NCRB publishes Sec. 376 chargesheet & conviction rates only at All-India level (Tables 3A.5 & 3A.7).",
          delta_label: natDisposal?.available
            ? `Nat. Sec. 376: ${natDisposal.value}`
            : null,
          delta_direction: "neutral",
          unit: "State Sec. 376 Disposal (%)",
          source_table: "TABLES 3A.5–3A.8",
          footnote:
            selectedState.caw_conviction_pct !== null
              ? `CAW-only Conviction: ${selectedState.caw_conviction_pct.toFixed(1)}% (all CAW heads, not Rape-only).`
              : "State Tables 3A.6 & 3A.8 aggregate all Crimes Against Women.",
        },
      ]
    : kpis;

  return (
    <section aria-label="Key Performance Indicators">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map((kpi) => (
          <article
            key={kpi.id}
            className={`min-w-0 border bg-[#202025] p-5 flex flex-col justify-between transition-colors ${
              kpi.available
                ? "border-[#2D2D34] border-t-2 border-t-[#B51F32]"
                : "border-[#2D2D34] border-t-2 border-t-amber-500"
            }`}
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center justify-between gap-1.5 mb-2.5">
                <VerifiedStamp
                  label={kpi.available ? kpi.source_table.split("(")[0].trim() : "UNAVAILABLE"}
                  tone={kpi.available ? "verified" : "partial"}
                />
              </div>
              <p className="font-mono text-[11px] font-medium uppercase tracking-[0.11em] text-[#B8B4B4] leading-snug mb-2">
                {kpi.label}
              </p>
              <p
                className={`font-serif text-3xl sm:text-4xl font-semibold tabular-nums tracking-tight ${
                  kpi.available ? "text-[#F5F2EF]" : "text-[#B8B4B4]"
                }`}
              >
                {kpi.value}
              </p>
              {kpi.delta_label && (
                <p className="mt-1.5 font-mono text-xs font-medium text-[#E53945]">
                  {kpi.delta_label}
                </p>
              )}
              {!kpi.available && kpi.unavailable_reason && (
                <p className="mt-2 text-xs text-amber-200 bg-amber-950/35 border border-amber-500/35 px-2.5 py-1.5 leading-relaxed">
                  {kpi.unavailable_reason}
                </p>
              )}
            </div>
            <p className="mt-4 pt-3 border-t border-[#2D2D34] text-xs text-[#B8B4B4] leading-relaxed">
              {kpi.unit} · {kpi.footnote}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
};
