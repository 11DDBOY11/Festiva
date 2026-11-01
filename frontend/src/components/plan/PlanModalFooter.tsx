import React from "react";
import { Download, Loader2, Sparkles } from "lucide-react";

interface PlanModalFooterProps {
  exportingPdf: boolean;
  onExportPdf: () => void;
  onClose: () => void;
}

export const PlanModalFooter: React.FC<PlanModalFooterProps> = ({
  exportingPdf,
  onExportPdf,
  onClose,
}) => {
  return (
    <div className="shrink-0 p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between">
      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">
        <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
        <span className="hidden sm:inline">
          Balanced budget & structured timeline • Grounded in Mangaluru dataset
        </span>
        <span className="sm:hidden text-[11px]">Mangaluru event plan</span>
      </div>
      <div className="flex items-center gap-2">
        <button
          id="btn-footer-export-pdf"
          type="button"
          onClick={onExportPdf}
          disabled={exportingPdf}
          className="px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 transition shadow-xs cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
        >
          {exportingPdf ? (
            <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
          ) : (
            <Download className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          )}
          <span>Export PDF</span>
        </button>
        <button
          id="btn-close-plan"
          onClick={onClose}
          className="px-5 py-2 rounded-xl text-xs sm:text-sm font-bold bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 transition shadow-xs cursor-pointer"
        >
          Close Plan
        </button>
      </div>
    </div>
  );
};
