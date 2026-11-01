import React from "react";
import { Download, History, Loader2, Sparkles, X } from "lucide-react";
import { PlanSchema, PlanVersionSummary } from "../../lib/api";

interface PlanModalHeaderProps {
  currentPlan: PlanSchema;
  versions: PlanVersionSummary[];
  selectedVersionNum: number;
  versionLoading: boolean;
  exportingPdf: boolean;
  onSelectVersion: (vNum: number) => void;
  onExportPdf: () => void;
  onSuggestChanges: () => void;
  onClose: () => void;
  formatDate: (d: string | null) => string;
}

export const PlanModalHeader: React.FC<PlanModalHeaderProps> = ({
  currentPlan,
  versions,
  selectedVersionNum,
  versionLoading,
  exportingPdf,
  onSelectVersion,
  onExportPdf,
  onSuggestChanges,
  onClose,
  formatDate,
}) => {
  return (
    <div className="shrink-0 px-4 py-3 sm:px-6 sm:py-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/95">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-1">
            {/* Version Selector Pill */}
            {versions.length > 1 ? (
              <div className="flex items-center gap-1 bg-amber-100 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-700 rounded-full px-2.5 py-0.5 text-xs font-bold text-amber-900 dark:text-amber-200">
                <History className="w-3.5 h-3.5" />
                <span>Plan:</span>
                <select
                  aria-label="Select Plan Version"
                  value={selectedVersionNum}
                  onChange={(e) => onSelectVersion(Number(e.target.value))}
                  className="bg-transparent text-amber-900 dark:text-amber-200 font-bold focus:outline-none cursor-pointer"
                >
                  {versions.map((v) => (
                    <option
                      key={v.version}
                      value={v.version}
                      className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    >
                      v{v.version} {v.version === currentPlan.version ? "(Current)" : ""}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                Plan v{currentPlan.version}
              </span>
            )}

            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700">
              {currentPlan.event_type}
            </span>
            {currentPlan.guest_count && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-200/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300">
                {currentPlan.guest_count} guests
              </span>
            )}
            {currentPlan.event_date && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-200/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300">
                {formatDate(currentPlan.event_date)}
              </span>
            )}
          </div>
          <h2 className="text-lg sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white truncate flex items-center gap-2">
            <span className="truncate">{currentPlan.title}</span>
            {versionLoading && <Loader2 className="w-4 h-4 animate-spin text-amber-600 shrink-0" />}
          </h2>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            id="btn-header-export-pdf"
            type="button"
            onClick={onExportPdf}
            disabled={exportingPdf}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 transition shadow-2xs cursor-pointer disabled:opacity-50"
            title="Export this plan as a printable PDF"
          >
            {exportingPdf ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-600" />
            ) : (
              <Download className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            )}
            <span className="hidden sm:inline">Export PDF</span>
            <span className="sm:hidden">PDF</span>
          </button>
          <button
            id="btn-header-suggest-changes"
            type="button"
            onClick={onSuggestChanges}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-500/15 hover:bg-amber-500/25 text-amber-900 dark:text-amber-200 border border-amber-400/60 dark:border-amber-700 transition shadow-2xs cursor-pointer"
            title="Suggest changes or modifications to AI"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            <span className="hidden sm:inline">Suggestions / Changes</span>
            <span className="sm:hidden">Suggest</span>
          </button>
          <button
            id="btn-close-modal-x"
            onClick={onClose}
            aria-label="Close modal"
            className="p-2 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-200/80 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};
