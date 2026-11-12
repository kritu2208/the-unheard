import React, { useEffect, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricKey, NationalTrendPoint } from "../types/dashboard";
import { VerifiedStamp } from "../components/DemoStamp";

interface NationalTrendChartProps {
  data: NationalTrendPoint[];
  height?: number;
  selectedYear?: number;
  selectedMetric?: MetricKey;
}

type TrendSeriesMode =
  | "reported_cases"
  | "victims_count"
  | "rate_per_100k_female"
  | "caw_total_cases";

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: NationalTrendPoint }>;
  label?: number;
}

const TrendTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;
  const pt = payload[0].payload;

  return (
    <div className="border border-[#F5F2EF]/20 bg-[#101012] p-3.5 shadow-2xl max-w-xs text-[#F5F2EF]">
      <div className="flex items-center justify-between gap-4 pb-2 mb-2 border-b border-[#2D2D34]">
        <span className="font-mono text-xs font-semibold text-[#F5F2EF]">{label}</span>
        <span className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-[#E53945]">
          NCRB OFFICIAL
        </span>
      </div>
      <div className="space-y-1 text-xs tabular-nums">
        <div className="flex justify-between gap-5">
          <span className="text-[#B8B4B4]">Sec. 376 Rape Cases (I)</span>
          <span className="font-mono font-medium text-[#F5F2EF]">
            {pt.reported_cases !== null ? pt.reported_cases.toLocaleString() : "Unavailable"}
          </span>
        </div>
        <div className="flex justify-between gap-5">
          <span className="text-[#B8B4B4]">Female Victims (V)</span>
          <span className="font-mono font-medium text-[#F5F2EF]">
            {pt.victims_count !== null ? pt.victims_count.toLocaleString() : "Unavailable"}
          </span>
        </div>
        <div className="flex justify-between gap-5">
          <span className="text-[#B8B4B4]">Sec. 376 Rate / 100k Fem.</span>
          <span className="font-mono font-semibold text-[#E53945]">
            {pt.rate_per_100k_female !== null ? pt.rate_per_100k_female.toFixed(1) : "Unavailable"}
          </span>
        </div>
        <div className="flex justify-between gap-5 pt-1 border-t border-[#2D2D34]">
          <span className="text-[#B8B4B4]">Total CAW (IPC+SLL)</span>
          <span className="font-mono font-medium text-[#F5F2EF]">
            {pt.caw_total_cases !== null ? pt.caw_total_cases.toLocaleString() : "—"}
          </span>
        </div>
      </div>
      {pt.statutory_note && (
        <p className="mt-2 pt-2 border-t border-[#2D2D34] text-[11px] text-[#E53945]">
          {pt.statutory_note}
        </p>
      )}
    </div>
  );
};

export const NationalTrendChart: React.FC<NationalTrendChartProps> = ({
  data,
  height = 310,
  selectedYear,
  selectedMetric,
}) => {
  const [seriesMode, setSeriesMode] = useState<TrendSeriesMode>("reported_cases");

  useEffect(() => {
    if (selectedMetric === "rate_per_100k") {
      setSeriesMode("rate_per_100k_female");
    } else if (selectedMetric === "victims") {
      setSeriesMode("victims_count");
    } else if (selectedMetric === "count") {
      setSeriesMode("reported_cases");
    }
  }, [selectedMetric]);

  return (
    <div className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6 h-full flex flex-col justify-between">
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-5 border-b border-[#2D2D34]">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">
                All-India Longitudinal Trajectory
              </h3>
              <VerifiedStamp label="NATIONAL SERIES" />
            </div>
            <p className="mt-1 text-xs text-[#B8B4B4]">
              {seriesMode === "caw_total_cases"
                ? "Official All-India Total Crime Against Women (IPC+SLL, 2018–2023) including 2023 NCRB snapshot."
                : "Official All-India Sec. 376 Rape series (2020–2022). Gaps indicate years where Table 3A.2 spreadsheets are unavailable."}
            </p>
          </div>

          <div className="flex flex-wrap items-center border border-[#2D2D34] bg-[#19191D] p-0.5 self-start">
            <button
              type="button"
              onClick={() => setSeriesMode("reported_cases")}
              className={`px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.12em] transition-colors ${
                seriesMode === "reported_cases"
                  ? "bg-[#B51F32] text-[#F5F2EF]"
                  : "text-[#B8B4B4] hover:text-[#F5F2EF]"
              }`}
            >
              Cases (I)
            </button>
            <button
              type="button"
              onClick={() => setSeriesMode("victims_count")}
              className={`px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.12em] transition-colors ${
                seriesMode === "victims_count"
                  ? "bg-[#B51F32] text-[#F5F2EF]"
                  : "text-[#B8B4B4] hover:text-[#F5F2EF]"
              }`}
            >
              Victims (V)
            </button>
            <button
              type="button"
              onClick={() => setSeriesMode("rate_per_100k_female")}
              className={`px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.12em] transition-colors ${
                seriesMode === "rate_per_100k_female"
                  ? "bg-[#B51F32] text-[#F5F2EF]"
                  : "text-[#B8B4B4] hover:text-[#F5F2EF]"
              }`}
            >
              Rate / 100k
            </button>
            <button
              type="button"
              onClick={() => setSeriesMode("caw_total_cases")}
              className={`px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.12em] transition-colors ${
                seriesMode === "caw_total_cases"
                  ? "bg-[#B51F32] text-[#F5F2EF]"
                  : "text-[#B8B4B4] hover:text-[#F5F2EF]"
              }`}
            >
              CAW Total
            </button>
          </div>
        </div>

        <div style={{ width: "100%", height }}>
          <ResponsiveContainer>
            <ComposedChart data={data} margin={{ top: 14, right: 16, left: 4, bottom: 4 }}>
              <defs>
                <linearGradient id="unheardDarkCrimsonArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#E53945" stopOpacity={0.34} />
                  <stop offset="95%" stopColor="#B51F32" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(245, 242, 239, 0.08)" vertical={false} />
              <XAxis
                dataKey="year"
                stroke="#B8B4B4"
                tick={{ fill: "#F5F2EF", fontSize: 11, fontFamily: "JetBrains Mono" }}
                axisLine={{ stroke: "rgba(245, 242, 239, 0.2)" }}
                tickLine={false}
              />
              <YAxis
                stroke="#B8B4B4"
                tick={{ fill: "#B8B4B4", fontSize: 11, fontFamily: "JetBrains Mono" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<TrendTooltip />} />
              <ReferenceLine
                x={2020}
                stroke="#B8B4B4"
                strokeDasharray="3 3"
                strokeOpacity={0.6}
                label={{
                  value: "2020 COVID",
                  position: "insideTopLeft",
                  fill: "#B8B4B4",
                  fontSize: 10,
                  fontFamily: "JetBrains Mono",
                }}
              />
              {selectedYear && (
                <ReferenceLine
                  x={selectedYear}
                  stroke="#F5F2EF"
                  strokeOpacity={0.55}
                  strokeWidth={1.5}
                />
              )}
              <Area
                type="monotone"
                dataKey={seriesMode}
                connectNulls={false}
                isAnimationActive={false}
                stroke="#E53945"
                strokeWidth={2.5}
                fill="url(#unheardDarkCrimsonArea)"
                dot={{ r: 4, fill: "#E53945", stroke: "#101012", strokeWidth: 2 }}
                activeDot={{ r: 6, fill: "#F5F2EF", stroke: "#E53945", strokeWidth: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
