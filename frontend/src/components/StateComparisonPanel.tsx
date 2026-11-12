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
import { ArrowLeftRight } from "lucide-react";
import type { MetricKey, StateRecord } from "../types/dashboard";
import { VerifiedStamp } from "./DemoStamp";

interface StateComparisonPanelProps {
  states: StateRecord[];
  primaryCode: string;
  compareCode: string;
  onChangePrimary: (code: string) => void;
  onChangeCompare: (code: string) => void;
  selectedYear: number;
  selectedMetric: MetricKey;
}

const fmtInt = (v: number | null) => (v !== null ? v.toLocaleString() : "Unavailable");
const fmtDec = (v: number | null, suffix = "") =>
  v !== null ? `${v.toFixed(1)}${suffix}` : "Unavailable";

export const StateComparisonPanel: React.FC<StateComparisonPanelProps> = ({
  states,
  primaryCode,
  compareCode,
  onChangePrimary,
  onChangeCompare,
  selectedYear,
  selectedMetric,
}) => {
  const primary =
    states.find((s) => s.state_code === primaryCode) ?? states[0] ?? null;
  const secondary =
    states.find((s) => s.state_code === compareCode) ??
    states.find((s) => s.state_code !== primary?.state_code) ??
    null;

  const isDisposalMetric =
    selectedMetric === "charge_sheet_pct" || selectedMetric === "conviction_pct";

  const hasSec376 =
    primary &&
    secondary &&
    (primary.reported_cases !== null || secondary.reported_cases !== null);

  const chartData =
    primary && secondary && !isDisposalMetric
      ? selectedMetric === "rate_per_100k" && hasSec376
        ? [
            {
              dimension: "Sec. 376 Rate / 100k Fem.",
              [primary.state_name]: primary.rate_per_100k_female ?? 0,
              [secondary.state_name]: secondary.rate_per_100k_female ?? 0,
            },
          ]
        : hasSec376
        ? [
            {
              dimension: "Rape Cases (Sec. 376)",
              [primary.state_name]: primary.reported_cases ?? 0,
              [secondary.state_name]: secondary.reported_cases ?? 0,
            },
            {
              dimension: "Female Victims (V)",
              [primary.state_name]: primary.victims_count ?? 0,
              [secondary.state_name]: secondary.victims_count ?? 0,
            },
          ]
        : []
      : [];

  return (
    <section className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 mb-5 border-b border-[#2D2D34]">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <ArrowLeftRight className="h-4 w-4 text-[#E53945]" aria-hidden="true" />
            <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">
              State-to-State Comparison · {selectedYear}
            </h3>
            <VerifiedStamp label={`METRIC: ${selectedMetric}`} />
          </div>
          <p className="mt-1 text-xs text-[#B8B4B4]">
            Side-by-side comparison of official counts, female population denominators, and rates.
          </p>
        </div>

        {/* Selectors */}
        {states.length > 0 && (
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center border border-[#E53945]/60 bg-[#B51F32]/20 px-2.5 py-1.5 gap-2">
              <label
                htmlFor="compare-primary-state"
                className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#E53945]"
              >
                State A
              </label>
              <select
                id="compare-primary-state"
                value={primary?.state_code ?? ""}
                onChange={(e) => onChangePrimary(e.target.value)}
                className="bg-transparent font-mono text-xs font-medium text-[#F5F2EF] focus:outline-none cursor-pointer"
              >
                {states.map((st) => (
                  <option
                    key={st.state_code}
                    value={st.state_code}
                    className="bg-[#19191D] text-[#F5F2EF]"
                  >
                    {st.state_name}
                  </option>
                ))}
              </select>
            </div>

            <span className="font-mono text-[10px] font-semibold uppercase text-[#B8B4B4]">
              vs
            </span>

            <div className="flex items-center border border-[#2D2D34] bg-[#19191D] px-2.5 py-1.5 gap-2">
              <label
                htmlFor="compare-secondary-state"
                className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#B8B4B4]"
              >
                State B
              </label>
              <select
                id="compare-secondary-state"
                value={secondary?.state_code ?? ""}
                onChange={(e) => onChangeCompare(e.target.value)}
                className="bg-transparent font-mono text-xs font-medium text-[#F5F2EF] focus:outline-none cursor-pointer"
              >
                {states.map((st) => (
                  <option
                    key={st.state_code}
                    value={st.state_code}
                    className="bg-[#19191D] text-[#F5F2EF]"
                  >
                    {st.state_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {!primary || !secondary ? (
        <div className="border border-[#2D2D34] bg-[#19191D] p-5 text-xs text-[#B8B4B4]">
          No State/UT records are available for comparison in {selectedYear}. Switch to
          2020–2022 for verified Sec. 376 State comparisons.
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-center">
          {/* Bar Chart or Unavailable State */}
          <div className="xl:col-span-5">
            {chartData.length === 0 ? (
              <div className="border border-[#2D2D34] bg-[#19191D] p-5 text-xs text-[#B8B4B4] leading-relaxed">
                <p className="font-mono font-semibold uppercase tracking-[0.14em] text-[#E53945] mb-1.5">
                  Chart Unavailable for {selectedYear} · {selectedMetric}
                </p>
                <p>
                  {isDisposalMetric
                    ? "Sec. 376 chargesheet and conviction rates are published only at the All-India level. See the table for CAW-level disposal context."
                    : `Granular State/UT Sec. 376 data is unavailable for ${selectedYear}. Total CAW counts are shown in the table.`}
                </p>
              </div>
            ) : (
              <div style={{ width: "100%", height: 220 }}>
                <ResponsiveContainer>
                  <BarChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                    <CartesianGrid stroke="rgba(245, 242, 239, 0.08)" vertical={false} />
                    <XAxis
                      dataKey="dimension"
                      stroke="#B8B4B4"
                      tick={{ fill: "#F5F2EF", fontSize: 11 }}
                      axisLine={{ stroke: "rgba(245, 242, 239, 0.2)" }}
                      tickLine={false}
                    />
                    <YAxis
                      stroke="#B8B4B4"
                      tick={{ fill: "#B8B4B4", fontSize: 11, fontFamily: "JetBrains Mono" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      cursor={{ fill: "rgba(245, 242, 239, 0.04)" }}
                      contentStyle={{
                        backgroundColor: "#101012",
                        borderColor: "rgba(245, 242, 239, 0.2)",
                        fontSize: "12px",
                        color: "#F5F2EF",
                      }}
                    />
                    <Legend
                      wrapperStyle={{
                        fontSize: "11px",
                        fontFamily: "JetBrains Mono",
                        color: "#F5F2EF",
                      }}
                    />
                    <Bar
                      dataKey={primary.state_name}
                      fill="#E53945"
                      isAnimationActive={false}
                      radius={[2, 2, 0, 0]}
                    />
                    <Bar
                      dataKey={secondary.state_name}
                      fill="#B8B4B4"
                      isAnimationActive={false}
                      radius={[2, 2, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Structured Comparison Table */}
          <div className="xl:col-span-7 overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#2D2D34] bg-[#19191D] text-[#B8B4B4] font-mono text-[10px] uppercase tracking-[0.14em]">
                  <th className="py-2.5 px-3">Official Indicator</th>
                  <th className="py-2.5 px-3 text-[#E53945] font-semibold">
                    {primary.state_name}
                  </th>
                  <th className="py-2.5 px-3 text-[#F5F2EF] font-semibold">
                    {secondary.state_name}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2D2D34] tabular-nums">
                <tr>
                  <td className="py-2.5 px-3 text-[#B8B4B4]">Sec. 376 Rape Cases (I)</td>
                  <td className="py-2.5 px-3 font-mono font-semibold text-[#F5F2EF]">
                    {fmtInt(primary.reported_cases)}
                  </td>
                  <td className="py-2.5 px-3 font-mono font-medium text-[#F5F2EF]">
                    {fmtInt(secondary.reported_cases)}
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 text-[#B8B4B4]">Female Victims (V)</td>
                  <td className="py-2.5 px-3 font-mono font-semibold text-[#F5F2EF]">
                    {fmtInt(primary.victims_count)}
                  </td>
                  <td className="py-2.5 px-3 font-mono font-medium text-[#F5F2EF]">
                    {fmtInt(secondary.victims_count)}
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 text-[#B8B4B4]">Sec. 376 Rate / 100k Female Pop.</td>
                  <td className="py-2.5 px-3 font-mono font-semibold text-[#E53945]">
                    {fmtDec(primary.rate_per_100k_female, " / 100k")}
                  </td>
                  <td className="py-2.5 px-3 font-mono font-semibold text-[#E53945]">
                    {fmtDec(secondary.rate_per_100k_female, " / 100k")}
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 text-[#B8B4B4]">Projected Female Pop. (Lakhs)</td>
                  <td className="py-2.5 px-3 font-mono text-[#F5F2EF]">
                    {fmtDec(primary.female_population_lakhs, " L")}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[#F5F2EF]">
                    {fmtDec(secondary.female_population_lakhs, " L")}
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 text-[#B8B4B4]">Total CAW Cases (IPC+SLL)</td>
                  <td className="py-2.5 px-3 font-mono text-[#F5F2EF]">
                    {fmtInt(primary.caw_total_cases)}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[#F5F2EF]">
                    {fmtInt(secondary.caw_total_cases)}
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 text-[#B8B4B4]">
                    CAW Chargesheet / Conviction % (All CAW, Not Rape-Only)
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[#B8B4B4]">
                    {fmtDec(primary.caw_charge_sheet_pct, "%")} /{" "}
                    {fmtDec(primary.caw_conviction_pct, "%")}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[#B8B4B4]">
                    {fmtDec(secondary.caw_charge_sheet_pct, "%")} /{" "}
                    {fmtDec(secondary.caw_conviction_pct, "%")}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
};
