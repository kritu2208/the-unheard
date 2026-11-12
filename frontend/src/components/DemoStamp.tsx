import React from "react";

interface DemoStampProps {
  label?: string;
  tone?: "verified" | "partial" | "muted";
  className?: string;
}

export const VerifiedStamp: React.FC<DemoStampProps> = ({
  label = "OFFICIAL NCRB DATA",
  tone = "verified",
  className = "",
}) => {
  const toneClasses =
    tone === "verified"
      ? "border-[#B51F32]/60 bg-[#B51F32]/15 text-[#F5F2EF]"
      : tone === "partial"
      ? "border-amber-500/45 bg-amber-950/35 text-amber-200"
      : "border-[#383842] bg-[#19191D] text-[#B8B4B4]";

  const dotClass =
    tone === "verified"
      ? "bg-[#E53945]"
      : tone === "partial"
      ? "bg-amber-400"
      : "bg-[#B8B4B4]";

  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em] shrink-0 ${toneClasses} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} aria-hidden="true" />
      {label}
    </span>
  );
};

export const DemoStamp = VerifiedStamp;
