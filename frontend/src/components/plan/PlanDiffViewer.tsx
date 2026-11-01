import React from "react";
import { ArrowRight, Check, Loader2, X } from "lucide-react";
import { ProposedChangeResponse } from "../../lib/api";
import { formatCategoryLabel } from "../../lib/constants";

interface PlanDiffViewerProps {
  activeProposal: ProposedChangeResponse;
  applyingChange: boolean;
  onAcceptChange: () => void;
  onRejectChange: () => void;
  formatCurrency: (amt: number | null | undefined) => string;
}

export const PlanDiffViewer: React.FC<PlanDiffViewerProps> = ({
  activeProposal,
  applyingChange,
  onAcceptChange,
  onRejectChange,
  formatCurrency,
}) => {
  return (
    <div
      role="region"
      aria-label="Proposed Plan Diff"
      aria-live="polite"
      className="p-5 rounded-2xl border-2 border-amber-500 bg-amber-50/70 dark:bg-amber-950/40 space-y-4 shadow-xl"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200 dark:border-amber-800/80 pb-3">
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-200 dark:bg-amber-900/80 text-amber-950 dark:text-amber-100 border border-amber-400 dark:border-amber-700">
            Proposed Change (Pending Review)
          </span>
          <span className="text-xs text-slate-700 dark:text-slate-300 font-bold font-mono">
            Base: v{activeProposal.base_version} → Target: v{activeProposal.base_version + 1}
          </span>
        </div>

        {/* Net Budget Impact Pill */}
        <div
          className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
            activeProposal.budget_impact < 0
              ? "bg-emerald-200 dark:bg-emerald-900/70 text-emerald-950 dark:text-emerald-100 border border-emerald-400 dark:border-emerald-700"
              : activeProposal.budget_impact > 0
              ? "bg-rose-200 dark:bg-rose-900/70 text-rose-950 dark:text-rose-100 border border-rose-400 dark:border-rose-700"
              : "bg-blue-200 dark:bg-blue-900/70 text-blue-950 dark:text-blue-100 border border-blue-400 dark:border-blue-700"
          }`}
        >
          <span>
            Net Impact: {activeProposal.budget_impact < 0 ? "−" : "+"}
            {formatCurrency(Math.abs(activeProposal.budget_impact))}
            {activeProposal.budget_impact < 0 ? " (Savings)" : " (Increase)"}
          </span>
        </div>
      </div>

      {/* Summary */}
      <div>
        <div className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
          Change Summary
        </div>
        <p className="text-sm font-semibold text-slate-900 dark:text-white bg-white dark:bg-slate-900 p-3.5 rounded-xl border border-amber-300 dark:border-amber-800 shadow-xs">
          {activeProposal.diff.summary}
        </p>
      </div>

      {/* Structured Delta Table */}
      {activeProposal.diff.category_changes.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-bold uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th scope="col" className="py-2.5 px-3 font-bold">Category</th>
                <th scope="col" className="py-2.5 px-3 font-bold text-right">Current Amount</th>
                <th scope="col" className="py-2.5 px-3 font-bold text-center"></th>
                <th scope="col" className="py-2.5 px-3 font-bold text-right">Proposed Amount</th>
                <th scope="col" className="py-2.5 px-3 font-bold text-right">Difference</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {activeProposal.diff.category_changes.map((delta, idx) => (
                <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="py-3 px-3 font-bold text-slate-900 dark:text-white">
                    {formatCategoryLabel(delta.category)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-slate-600 dark:text-slate-400">
                    {formatCurrency(delta.old_amount)}
                  </td>
                  <td className="py-3 px-3 text-center text-slate-400">
                    <ArrowRight className="w-3.5 h-3.5 mx-auto text-slate-400" />
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                    {formatCurrency(delta.new_amount)}
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-bold">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold ${
                        delta.delta < 0
                          ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800"
                          : "bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800"
                      }`}
                    >
                      {delta.delta < 0 ? "−" : "+"}
                      {formatCurrency(Math.abs(delta.delta))}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-slate-100 dark:bg-slate-800/90 font-bold border-t-2 border-slate-200 dark:border-slate-700">
              <tr>
                <td className="py-3 px-3 text-slate-900 dark:text-white">Total Event Budget</td>
                <td className="py-3 px-3 text-right text-slate-600 dark:text-slate-400 line-through font-mono">
                  {formatCurrency(activeProposal.diff.old_total_budget)}
                </td>
                <td className="py-3 px-3 text-center text-slate-400">
                  <ArrowRight className="w-3.5 h-3.5 mx-auto text-slate-400" />
                </td>
                <td className="py-3 px-3 text-right text-amber-600 dark:text-amber-400 font-mono font-bold text-sm">
                  {formatCurrency(activeProposal.diff.new_total_budget)}
                </td>
                <td className="py-3 px-3 text-right text-amber-600 dark:text-amber-400 font-mono font-bold">
                  {activeProposal.diff.budget_impact < 0 ? "−" : "+"}
                  {formatCurrency(Math.abs(activeProposal.diff.budget_impact))}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Accept / Reject Action Bar */}
      <div className="pt-2 flex items-center justify-end gap-3">
        <button
          id="btn-reject-change"
          type="button"
          onClick={onRejectChange}
          disabled={applyingChange}
          className="px-4 py-2.5 rounded-xl text-xs sm:text-sm font-bold border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-slate-800 transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          <X className="w-4 h-4" />
          Discard Proposal
        </button>
        <button
          id="btn-accept-change"
          type="button"
          onClick={onAcceptChange}
          disabled={applyingChange}
          className="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/30 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 transition"
        >
          {applyingChange ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Applying & Creating Version...</span>
            </>
          ) : (
            <>
              <Check className="w-4 h-4" />
              <span>Accept Changes (Creates Plan v{activeProposal.base_version + 1})</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
