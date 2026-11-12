import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { NationalTrendPoint } from "../types/dashboard";
import { VerifiedStamp } from "../components/DemoStamp";
import { JusticeScaleIcon } from "../components/EditorialMotifs";

interface DisposalAnalysisChartProps {
  data: NationalTrendPoint[];
  selectedYear: number;
}

export const DisposalAnalysisChart: React.FC<DisposalAnalysisChartProps> = ({
  data,
  selectedYear,
}) => {
  const validRows = data.filter(
    (pt) =>
      pt.charge_sheet_pct !== null ||
      pt.conviction_pct !== null ||
      pt.trial_pendency_pct !== null
  );

  return (
    <div className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6 flex flex-col justify-between h-full">
      <div>
        <div className="flex flex-wrap items-start justify-between gap-2 pb-4 mb-5 border-b border-[#2D2D34]">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <JusticeScaleIcon className="h-4 w-4 text-[#E53945]" />
              <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">
                Chargesheet &amp; Conviction Analysis
              </h3>
              <VerifiedStamp label="TABLES 3A.5 & 3A.7" />
            </div>
            <p className="mt-1 text-xs text-[#B8B4B4]">
              All-India Sec. 376 IPC police chargesheet, court conviction &amp; trial pendency rates
              (valid official series: 2020–2022).
            </p>
          </div>
        </div>

        {validRows.length === 0 ? (
          <div className="border border-[#2D2D34] bg-[#19191D] p-6 text-xs text-[#B8B4B4]">
            No validated Sec. 376 chargesheet or conviction records available.
          </div>
        ) : (
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={validRows} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
                <CartesianGrid stroke="rgba(245, 242, 239, 0.08)" vertical={false} />
                <XAxis
                  dataKey="year"
                  stroke="#B8B4B4"
                  tick={{ fill: "#F5F2EF", fontSize: 11, fontFamily: "JetBrains Mono" }}
                  axisLine={{ stroke: "rgba(245, 242, 239, 0.2)" }}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  unit="%"
                  stroke="#B8B4B4"
                  tick={{ fill: "#B8B4B4", fontSize: 11, fontFamily: "JetBrains Mono" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "rgba(245, 242, 239, 0.04)" }}
                  content={({ active, payload, label }) => {
                    if (!active || !payload || !payload.length) return null;
                    const row = payload[0].payload as NationalTrendPoint;
                    return (
                      <div className="border border-[#F5F2EF]/20 bg-[#101012] p-3 text-xs tabular-nums shadow-2xl text-[#F5F2EF]">
                        <div className="flex items-center justify-between gap-4 pb-1.5 mb-1.5 border-b border-[#2D2D34]">
                          <span className="font-mono font-semibold text-[#F5F2EF]">
                            All-India · {label}
                          </span>
                          <span className="font-mono text-[9px] font-semibold text-[#E53945]">
                            SEC. 376
                          </span>
                        </div>
                        <div className="space-y-1">
                          <div className="flex justify-between gap-4">
                            <span className="text-[#B8B4B4]">Chargesheet Rate</span>
                            <span className="font-mono font-semibold text-[#F5F2EF]">
                              {row.charge_sheet_pct !== null
                                ? `${row.charge_sheet_pct.toFixed(1)}%`
                                : "Unavailable"}
                            </span>
                          </div>
                          <div className="flex justify-between gap-4">
                            <span className="text-[#B8B4B4]">Conviction Rate</span>
                            <span className="font-mono font-semibold text-[#E53945]">
                              {row.conviction_pct !== null
                                ? `${row.conviction_pct.toFixed(1)}%`
                                : "Unavailable"}
                            </span>
                          </div>
                          <div className="flex justify-between gap-4">
                            <span className="text-[#B8B4B4]">Trial Pendency</span>
                            <span className="font-mono font-medium text-[#B8B4B4]">
                              {row.trial_pendency_pct !== null
                                ? `${row.trial_pendency_pct.toFixed(1)}%`
                                : "Unavailable"}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  }}
                />
                <Legend
                  wrapperStyle={{
                    fontSize: "11px",
                    fontFamily: "JetBrains Mono",
                    color: "#F5F2EF",
                    paddingTop: "8px",
                  }}
                />
                <Bar
                  dataKey="charge_sheet_pct"
                  name="Chargesheet %"
                  fill="#F5F2EF"
                  isAnimationActive={false}
                  radius={[2, 2, 0, 0]}
                />
                <Bar
                  dataKey="conviction_pct"
                  name="Conviction %"
                  fill="#E53945"
                  isAnimationActive={false}
                  radius={[2, 2, 0, 0]}
                />
                <Bar
                  dataKey="trial_pendency_pct"
                  name="Trial Pendency %"
                  fill="#5E5E68"
                  isAnimationActive={false}
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <p className="mt-4 pt-3 border-t border-[#2D2D34] text-xs text-[#B8B4B4] leading-relaxed">
        <span className="font-mono font-semibold text-[#E53945] uppercase mr-1.5">Scope Note:</span>
        State-level Sec. 376 disposal rates are omitted because NCRB Tables 3A.6 &amp; 3A.8 aggregate
        all Crimes Against Women.
        {(selectedYear < 2020 || selectedYear > 2022) && (
          <span className="text-amber-300 font-medium ml-1">
            (Selected year {selectedYear} has no national Sec. 376 disposal release.)
          </span>
        )}
      </p>
    </div>
  );
};
