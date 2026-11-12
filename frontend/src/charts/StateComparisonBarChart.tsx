import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricKey, StateRecord } from "../types/dashboard";
import { VerifiedStamp } from "../components/DemoStamp";

interface StateComparisonBarChartProps {
  states: StateRecord[];
  metric: MetricKey;
  selectedStateCode?: string | null;
  onSelectState?: (stateCode: string) => void;
  height?: number;
  unavailableReason?: string | null;
}

const METRIC_LABELS: Record<MetricKey, { title: string; key: keyof StateRecord; unit: string }> = {
  count: { title: "Reported Rape Cases (Sec. 376 IPC)", key: "reported_cases", unit: "" },
  victims: { title: "Female Victims (Sec. 376 IPC)", key: "victims_count", unit: " victims" },
  rate_per_100k: { title: "Rate per 100k Female Pop.", key: "rate_per_100k_female", unit: "/100k" },
  charge_sheet_pct: { title: "Chargesheet % (National Only)", key: "charge_sheet_pct", unit: "%" },
  conviction_pct: { title: "Conviction % (National Only)", key: "conviction_pct", unit: "%" },
};

export const StateComparisonBarChart: React.FC<StateComparisonBarChartProps> = ({
  states,
  metric,
  selectedStateCode,
  onSelectState,
  height = 370,
  unavailableReason,
}) => {
  const meta = METRIC_LABELS[metric];
  const plottable = states.filter((s) => typeof s[meta.key] === "number");

  return (
    <div className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6 h-full flex flex-col justify-between">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2 pb-4 mb-5 border-b border-[#2D2D34]">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">
                State Ranking — {meta.title}
              </h3>
              <VerifiedStamp label="NCRB OFFICIAL" />
            </div>
            <p className="mt-1 text-xs text-[#B8B4B4]">
              Official Table 3A.2 comparison. Absolute counts are not adjusted for population size.
            </p>
          </div>
        </div>

        {plottable.length === 0 ? (
          <div className="border border-[#2D2D34] bg-[#19191D] p-6 text-xs text-[#B8B4B4] leading-relaxed">
            <p className="font-mono font-semibold uppercase tracking-[0.14em] text-[#E53945] mb-2">
              Metric Unavailable at State Level
            </p>
            <p>
              {unavailableReason ??
                "No verified State/UT figures are available for the selected year and metric."}
            </p>
          </div>
        ) : (
          <div style={{ width: "100%", height }}>
            <ResponsiveContainer>
              <BarChart
                data={plottable}
                layout="vertical"
                margin={{ top: 4, right: 20, left: 20, bottom: 4 }}
              >
                <CartesianGrid stroke="rgba(245, 242, 239, 0.08)" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="#B8B4B4"
                  tick={{ fill: "#B8B4B4", fontSize: 11, fontFamily: "JetBrains Mono" }}
                  axisLine={{ stroke: "rgba(245, 242, 239, 0.2)" }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="state_name"
                  width={122}
                  stroke="#B8B4B4"
                  tick={{ fill: "#F5F2EF", fontSize: 11, fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "rgba(245, 242, 239, 0.05)" }}
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const row = payload[0].payload as StateRecord;
                    const val = row[meta.key];
                    return (
                      <div className="border border-[#F5F2EF]/20 bg-[#101012] p-3 text-xs shadow-2xl text-[#F5F2EF]">
                        <div className="flex items-center justify-between gap-4 pb-1.5 mb-1.5 border-b border-[#2D2D34]">
                          <span className="font-serif text-sm font-semibold text-[#F5F2EF]">
                            {row.state_name}
                          </span>
                          <span className="font-mono text-[9px] font-semibold text-[#E53945]">
                            NCRB #{row.rank_by_selected ?? "—"}
                          </span>
                        </div>
                        <p className="font-mono font-semibold text-[#E53945] tabular-nums">
                          {typeof val === "number" ? val.toLocaleString() : "Unavailable"}
                          {typeof val === "number" ? meta.unit : ""}
                        </p>
                        <p className="text-[11px] text-[#B8B4B4] mt-0.5">
                          {row.source_table} · {row.region_zone}
                        </p>
                      </div>
                    );
                  }}
                />
                <Bar
                  dataKey={meta.key}
                  isAnimationActive={false}
                  radius={[0, 2, 2, 0]}
                  onClick={(entry) => {
                    if (onSelectState && entry?.state_code) {
                      onSelectState(String(entry.state_code));
                    }
                  }}
                  className="cursor-pointer"
                >
                  {plottable.map((row) => {
                    const active = selectedStateCode === row.state_code;
                    const isTopThree = row.rank_by_selected !== null && row.rank_by_selected <= 3;
                    return (
                      <Cell
                        key={row.state_code}
                        fill={active ? "#F5F2EF" : isTopThree ? "#E53945" : "#B51F32"}
                      />
                    );
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
};
