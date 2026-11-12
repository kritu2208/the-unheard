import React from "react";
import type { DemographicBucket } from "../types/dashboard";
import { VerifiedStamp } from "../components/DemoStamp";

interface DistributionBarChartProps {
  title: string;
  subtitle: string;
  buckets: DemographicBucket[];
}

export const DistributionBarChart: React.FC<DistributionBarChartProps> = ({
  title,
  subtitle,
  buckets,
}) => {
  return (
    <div className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-4 mb-5 border-b border-[#2D2D34]">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">{title}</h3>
            <VerifiedStamp label="NCRB OFFICIAL" />
          </div>
          <p className="mt-1 text-xs text-[#B8B4B4]">{subtitle}</p>
        </div>
      </div>

      {buckets.length === 0 ? (
        <p className="text-xs text-[#B8B4B4]">
          No structural disaggregation records available for the selected window.
        </p>
      ) : (
        <div className="space-y-4">
          {buckets.map((bucket) => (
            <div key={bucket.category} className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-4 text-xs">
                <span className="text-[#F5F2EF] font-medium">{bucket.category}</span>
                <span className="font-mono font-semibold text-[#F5F2EF] tabular-nums shrink-0">
                  {bucket.count !== null ? `${bucket.count.toLocaleString()} ` : ""}
                  {bucket.share_pct !== null ? (
                    <span className="text-[#E53945]">({bucket.share_pct.toFixed(1)}%)</span>
                  ) : (
                    ""
                  )}
                </span>
              </div>
              <div className="h-2.5 w-full bg-[#19191D] border border-[#2D2D34] overflow-hidden">
                <div
                  className="h-full bg-[#B51F32]"
                  style={{ width: `${Math.min(100, Math.max(0, bucket.share_pct ?? 0))}%` }}
                />
              </div>
              <p className="text-[11px] text-[#B8B4B4]">
                {bucket.note} · <span className="font-mono text-[#F5F2EF]/85">{bucket.source_table}</span>
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
