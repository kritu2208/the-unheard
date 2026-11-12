import React from "react";
import { AlertCircle, Database, RefreshCw } from "lucide-react";

export const PanelLoading: React.FC<{ message?: string }> = ({
  message = "Synchronizing analytical records...",
}) => (
  <div className="border border-[#2D2D34] bg-[#202025] p-6 sm:p-8">
    <div className="flex items-center gap-3 text-[#B8B4B4]">
      <RefreshCw className="h-4 w-4 animate-spin text-[#E53945]" aria-hidden="true" />
      <span className="font-mono text-xs uppercase tracking-[0.16em]">{message}</span>
    </div>
    <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
      {[0, 1, 2, 3].map((idx) => (
        <div key={idx} className="h-24 border border-[#2D2D34] bg-[#19191D] animate-pulse" />
      ))}
    </div>
  </div>
);

export const PanelError: React.FC<{
  title?: string;
  message: string;
  onRetry?: () => void;
}> = ({ title = "Data retrieval error", message, onRetry }) => (
  <div
    role="alert"
    className="border border-[#E53945]/60 bg-[#202025] p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
  >
    <div className="flex items-start gap-3">
      <AlertCircle className="h-5 w-5 text-[#E53945] shrink-0 mt-0.5" aria-hidden="true" />
      <div>
        <h3 className="font-serif text-lg text-[#F5F2EF]">{title}</h3>
        <p className="mt-1 text-sm text-[#B8B4B4]">{message}</p>
      </div>
    </div>
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="self-start sm:self-auto inline-flex items-center gap-2 border border-[#F5F2EF]/25 px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-[#F5F2EF] hover:border-[#E53945] hover:bg-[#B51F32]/25 transition-colors"
      >
        <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
        Retry
      </button>
    )}
  </div>
);

export const PanelEmpty: React.FC<{
  title: string;
  description: string;
  action?: React.ReactNode;
}> = ({ title, description, action }) => (
  <div className="border border-[#2D2D34] bg-[#202025] p-10 text-center">
    <Database className="h-6 w-6 text-[#B8B4B4] mx-auto mb-3" aria-hidden="true" />
    <h3 className="font-serif text-xl text-[#F5F2EF]">{title}</h3>
    <p className="mt-2 max-w-lg mx-auto text-sm text-[#B8B4B4]">{description}</p>
    {action && <div className="mt-5">{action}</div>}
  </div>
);
