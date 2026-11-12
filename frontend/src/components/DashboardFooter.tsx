import React from "react";
import { ExternalLink } from "lucide-react";
import type { DatasetSource, MethodologySection } from "../types/dashboard";

interface DashboardFooterProps {
  datasets: DatasetSource[];
  methodologySections: MethodologySection[];
}

export const DashboardFooter: React.FC<DashboardFooterProps> = ({
  datasets,
  methodologySections,
}) => {
  return (
    <footer className="border-t border-[#2D2D34] bg-[#19191D] mt-10">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-8 py-8 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Official Sources */}
          <div className="lg:col-span-6 space-y-3">
            <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[#E53945]">
              Official Source Provenance
            </span>
            <h4 className="font-serif text-lg font-semibold text-[#F5F2EF]">
              National Crime Records Bureau (NCRB) · Crime in India
            </h4>
            <ul className="space-y-2 text-xs">
              {datasets.map((src) => (
                <li
                  key={src.slug}
                  className="border border-[#2D2D34] bg-[#101012] px-3 py-2 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <p className="text-[#F5F2EF] font-medium truncate">{src.name}</p>
                    <p className="font-mono text-[10px] text-[#B8B4B4]">
                      {src.publisher} · Period: {src.reporting_period} · {src.status}
                    </p>
                  </div>
                  <a
                    href={src.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 inline-flex items-center gap-1 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#E53945] hover:text-[#F5F2EF] transition-colors"
                  >
                    NCRB <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Compact Methodology Notes */}
          <div className="lg:col-span-6 space-y-3">
            <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[#E53945]">
              Methodology &amp; Statistical Boundaries
            </span>
            <h4 className="font-serif text-lg font-semibold text-[#F5F2EF]">
              Definitions, Denominators &amp; Caveats
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {methodologySections.map((sec) => (
                <div key={sec.id} className="border border-[#2D2D34] bg-[#101012] p-3 text-xs">
                  <p className="font-semibold text-[#F5F2EF]">{sec.title}</p>
                  <p className="mt-1 text-[11px] text-[#B8B4B4] leading-relaxed">
                    {sec.summary}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-[#2D2D34] flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono text-[10px] text-[#B8B4B4]">
          <span className="font-medium text-[#F5F2EF]">
            THE UNHEARD · Investigative Data Journalism · Zero Fabricated Figures
          </span>
          <span>
            Principal Offence Rule · RGI/MoHFW Female Population Denominators · BNS 2023 effective 1
            July 2024
          </span>
        </div>
      </div>
    </footer>
  );
};
