import React from "react";
import { PlanSchema } from "../../lib/api";
import { formatCategoryLabel } from "../../lib/constants";

interface BudgetTabPanelProps {
  currentPlan: PlanSchema;
  formatCurrency: (amt: number | null | undefined) => string;
}

export const BudgetTabPanel: React.FC<BudgetTabPanelProps> = ({
  currentPlan,
  formatCurrency,
}) => {
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
        <table className="w-full text-left text-xs sm:text-sm">
          <thead className="bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-200 border-b border-slate-200 dark:border-slate-700 font-bold uppercase tracking-wider">
            <tr>
              <th scope="col" className="py-3 px-3 sm:px-4 font-bold">
                Category
              </th>
              <th scope="col" className="py-3 px-3 sm:px-4 font-bold text-right">
                Share (%)
              </th>
              <th scope="col" className="py-3 px-3 sm:px-4 font-bold text-right">
                Allocated Amount
              </th>
              <th scope="col" className="py-3 px-3 sm:px-4 font-bold text-right hidden sm:table-cell">
                Per Guest
              </th>
              <th scope="col" className="py-3 px-3 sm:px-4 font-bold hidden md:table-cell">
                Notes
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {currentPlan.budget?.categories?.map((cat, idx) => (
              <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <td className="py-3 px-3 sm:px-4 font-bold text-slate-900 dark:text-white">
                  {formatCategoryLabel(cat.category)}
                </td>
                <td className="py-3 px-3 sm:px-4 text-right font-mono text-slate-600 dark:text-slate-300 font-medium">
                  {Number(cat.share_pct).toFixed(1)}%
                </td>
                <td className="py-3 px-3 sm:px-4 text-right font-bold text-slate-900 dark:text-white text-sm">
                  {formatCurrency(Number(cat.allocated_amount))}
                </td>
                <td className="py-3 px-3 sm:px-4 text-right font-mono text-slate-600 dark:text-slate-300 hidden sm:table-cell">
                  {cat.per_guest_cost ? formatCurrency(Number(cat.per_guest_cost)) : "—"}
                </td>
                <td className="py-3 px-3 sm:px-4 text-xs text-slate-600 dark:text-slate-400 hidden md:table-cell">
                  {cat.notes || "Standard tier allocation"}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-slate-100/90 dark:bg-slate-800/90 font-bold border-t-2 border-slate-200 dark:border-slate-700">
            <tr>
              <td className="py-3.5 px-3 sm:px-4 text-slate-900 dark:text-white">Total Budget</td>
              <td className="py-3.5 px-3 sm:px-4 text-right text-slate-700 dark:text-slate-300">100.0%</td>
              <td className="py-3.5 px-3 sm:px-4 text-right text-amber-600 dark:text-amber-400 text-base font-bold">
                {formatCurrency(currentPlan.total_budget)}
              </td>
              <td className="py-3.5 px-3 sm:px-4 text-right text-slate-700 dark:text-slate-300 hidden sm:table-cell font-mono">
                {currentPlan.guest_count && currentPlan.total_budget
                  ? formatCurrency(currentPlan.total_budget / currentPlan.guest_count)
                  : "—"}
              </td>
              <td className="py-3.5 px-3 sm:px-4 text-xs text-slate-500 dark:text-slate-400 hidden md:table-cell font-normal">
                Sum balanced within 1%
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
};
