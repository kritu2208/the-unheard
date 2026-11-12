import React from "react";
import { BarChart3, ExternalLink } from "lucide-react";
import type { DashboardInsightsResponse } from "../types/dashboard";
import { VerifiedStamp } from "./DemoStamp";

interface AnalyticalInsightsPanelProps {
  insightsData: DashboardInsightsResponse | null;
  loading?: boolean;
}

export const AnalyticalInsightsPanel: React.FC<AnalyticalInsightsPanelProps> = ({
  insightsData,
  loading = false,
}) => {
  if (!insightsData && !loading) return null;

  return (
    <section className="border border-[#2D2D34] bg-[#202025] p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-4 mb-5 border-b border-[#2D2D34]">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <BarChart3 className="h-4 w-4 text-[#E53945]" aria-hidden="true" />
            <h3 className="font-serif text-xl font-semibold text-[#F5F2EF]">
              Deterministic Statistical Insights
            </h3>
            <VerifiedStamp label="DB-COMPUTED · NO LLM" />
          </div>
          {insightsData && (
            <p className="mt-1 text-xs text-[#B8B4B4]">
              Deterministic calculations from validated NCRB SQLite records for{" "}
              <span className="font-semibold text-[#F5F2EF]">{insightsData.selected_year}</span> ·{" "}
              <span className="font-semibold text-[#F5F2EF]">
                {insightsData.selected_state_name}
              </span>{" "}
              · Metric:{" "}
              <span className="font-mono font-medium text-[#E53945]">
                {insightsData.selected_metric}
              </span>
              .
            </p>
          )}
        </div>
      </div>

      {loading && !insightsData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1].map((i) => (
            <div key={i} className="h-28 border border-[#2D2D34] bg-[#19191D] animate-pulse" />
          ))}
        </div>
      ) : (
        insightsData && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insightsData.insights.map((item) => (
              <article
                key={item.id}
                className="border border-[#2D2D34] bg-[#19191D] p-4 flex flex-col justify-between gap-3"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[#E53945]">
                      {item.category}
                    </span>
                    <span className="font-mono text-[10px] text-[#B8B4B4]">
                      {item.reporting_year} · {item.metric}
                    </span>
                  </div>
                  <h4 className="font-serif text-base font-semibold text-[#F5F2EF]">
                    {item.title}
                  </h4>

                  <div className="text-xs leading-relaxed">
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#F5F2EF] mr-1.5">
                      Observed:
                    </span>
                    <span className="text-[#F5F2EF]/90">{item.observed_data}</span>
                  </div>

                  <div className="text-[11px] leading-relaxed text-[#B8B4B4] border-l-2 border-[#B51F32] pl-2.5">
                    <span className="font-mono text-[9px] font-semibold uppercase tracking-[0.12em] text-[#B8B4B4] mr-1.5">
                      Context:
                    </span>
                    {item.interpretation}
                  </div>
                </div>

                <div className="flex items-center justify-between gap-2 pt-2 border-t border-[#2D2D34] font-mono text-[10px] text-[#B8B4B4]">
                  <span>Source: {item.source_table}</span>
                  {item.source_url && (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-[#E53945] hover:text-[#F5F2EF] transition-colors"
                    >
                      NCRB <ExternalLink className="h-2.5 w-2.5" aria-hidden="true" />
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        )
      )}
    </section>
  );
};
