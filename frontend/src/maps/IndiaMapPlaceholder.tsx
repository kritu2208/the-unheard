import React from "react";
import { Layers, MapPin } from "lucide-react";
import type { MetricKey, StateRecord } from "../types/dashboard";
import { VerifiedStamp } from "../components/DemoStamp";

interface IndiaMapPlaceholderProps {
  states: StateRecord[];
  metric: MetricKey;
  selectedYear: number;
  selectedStateCode: string | null;
  onSelectState: (code: string) => void;
}

export const IndiaMapPlaceholder: React.FC<IndiaMapPlaceholderProps> = ({
  states,
  metric,
  selectedYear,
  selectedStateCode,
  onSelectState,
}) => {
  const activeState =
    states.find((s) => s.state_code === selectedStateCode) ?? states[0] ?? null;

  const getNumericValue = (row: StateRecord): number | null => {
    if (metric === "rate_per_100k") return row.rate_per_100k_female;
    if (metric === "victims") return row.victims_count;
    if (metric === "charge_sheet_pct" || metric === "conviction_pct") return null;
    return row.reported_cases;
  };

  const plottableCount = states.filter((s) => getNumericValue(s) !== null).length;
  const maxVal = Math.max(1, ...states.map((s) => getNumericValue(s) ?? 0));

  const formatMetric = (row: StateRecord) => {
    if (metric === "rate_per_100k") {
      return row.rate_per_100k_female !== null
        ? `${row.rate_per_100k_female.toFixed(1)} / 100k`
        : "Unavailable";
    }
    if (metric === "victims") {
      return row.victims_count !== null
        ? `${row.victims_count.toLocaleString()} victims`
        : "Unavailable";
    }
    if (metric === "charge_sheet_pct" || metric === "conviction_pct") {
      return "Nat. Only";
    }
    return row.reported_cases !== null
      ? `${row.reported_cases.toLocaleString()} cases`
      : "Unavailable";
  };

  return (
    <div className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6 flex flex-col justify-between h-full">
      <div>
        <div className="flex flex-wrap items-start justify-between gap-3 pb-4 mb-4 border-b border-[#2D2D34]">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">
                India State/UT Intensity Matrix
              </h3>
              <VerifiedStamp label={`${states.length} JURISDICTIONS · ${selectedYear}`} />
            </div>
            <p className="mt-1 text-xs text-[#B8B4B4]">
              Polygon choropleth map omitted (verified India GeoJSON boundaries not loaded).
              Click any jurisdiction tile to filter KPIs &amp; comparison.
            </p>
          </div>
        </div>

        {states.length === 0 ? (
          <div className="border border-[#2D2D34] bg-[#19191D] p-6 text-xs text-[#B8B4B4] leading-relaxed">
            <p className="font-mono font-semibold uppercase tracking-[0.14em] text-[#E53945] mb-2">
              State/UT Records Unavailable for {selectedYear}
            </p>
            <p>
              NCRB has not released granular State/UT Chapter 3A spreadsheets for {selectedYear}.
              Switch to 2020–2022 to inspect State/UT Sec. 376 figures.
            </p>
          </div>
        ) : (
          <div className="border border-[#2D2D34] bg-[#19191D] p-3.5 sm:p-4">
            <div className="flex items-center justify-between gap-2 pb-2.5 mb-3 border-b border-[#2D2D34]">
              <span className="inline-flex items-center gap-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#E53945]">
                <Layers className="h-3.5 w-3.5" aria-hidden="true" />
                {plottableCount > 0
                  ? `Relative Intensity · ${metric}`
                  : `Sec. 376 Metric Unavailable at State Level (${selectedYear})`}
              </span>
              <span className="font-mono text-[10px] font-medium text-[#B8B4B4]">
                {plottableCount}/{states.length} Plottable
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-[310px] overflow-y-auto pr-1">
              {states.map((st) => {
                const isSelected = selectedStateCode === st.state_code;
                const num = getNumericValue(st);
                const ratio = num !== null ? Math.min(1, Math.max(0.06, num / maxVal)) : 0;

                return (
                  <button
                    key={st.state_code}
                    type="button"
                    onClick={() => onSelectState(st.state_code)}
                    title={`${st.state_name} (${st.region_zone}) — ${formatMetric(st)}`}
                    className={`p-2.5 border text-left transition-colors relative overflow-hidden ${
                      isSelected
                        ? "border-[#E53945] bg-[#B51F32]/25 ring-1 ring-[#E53945]"
                        : "border-[#2D2D34] bg-[#202025] hover:border-[#F5F2EF]/40"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono text-[10px] font-semibold text-[#B8B4B4]">
                        {st.state_code}
                      </span>
                      <span className="font-mono text-[9px] font-semibold text-[#E53945]">
                        {st.rank_by_selected ? `#${st.rank_by_selected}` : "—"}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] font-semibold text-[#F5F2EF] truncate">
                      {st.state_name}
                    </p>
                    <p className="mt-0.5 font-mono text-[11px] text-[#B8B4B4] tabular-nums">
                      {formatMetric(st)}
                    </p>
                    {num !== null && (
                      <div className="mt-1.5 h-1.5 w-full bg-[#101012]">
                        <div
                          className="h-full bg-[#B51F32]"
                          style={{ width: `${Math.round(ratio * 100)}%` }}
                        />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {activeState && (
        <div className="mt-4 pt-3 border-t border-[#2D2D34] flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-[#F5F2EF]">
            <MapPin className="h-3.5 w-3.5 text-[#E53945] shrink-0" aria-hidden="true" />
            <span className="font-semibold">{activeState.state_name}</span>
            <span className="text-[#B8B4B4]">({activeState.region_zone})</span>
          </div>
          <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-[#B8B4B4] tabular-nums">
            <span>
              Sec. 376 Cases:{" "}
              <strong className="text-[#F5F2EF]">
                {activeState.reported_cases !== null
                  ? activeState.reported_cases.toLocaleString()
                  : "Unavailable"}
              </strong>
            </span>
            <span>
              Rate:{" "}
              <strong className="text-[#E53945]">
                {activeState.rate_per_100k_female !== null
                  ? `${activeState.rate_per_100k_female.toFixed(1)}/100k`
                  : "Unavailable"}
              </strong>
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
