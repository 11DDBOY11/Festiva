import React from "react";
import { Calendar } from "lucide-react";
import { PlanSchema } from "../../lib/api";
import { formatCategoryLabel } from "../../lib/constants";

interface TimelineTabPanelProps {
  currentPlan: PlanSchema;
  formatDate: (d: string | null) => string;
}

export const TimelineTabPanel: React.FC<TimelineTabPanelProps> = ({
  currentPlan,
  formatDate,
}) => {
  return (
    <div className="space-y-3">
      {!currentPlan.timeline || currentPlan.timeline.length === 0 ? (
        <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/50">
          <Calendar className="w-10 h-10 mx-auto text-slate-400 mb-2" />
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            No timeline tasks found
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Timeline milestones and tasks will appear here once generated.
          </p>
        </div>
      ) : (
        currentPlan.timeline.map((item, idx) => (
          <div
            key={idx}
            className="flex items-start justify-between gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs hover:border-amber-400/60 transition-colors"
          >
            <div className="space-y-1.5 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700">
                  {item.phase}
                </span>
                <span className="px-2.5 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  {formatCategoryLabel(item.category)}
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                    item.priority === "high"
                      ? "bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800"
                      : "bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-800"
                  }`}
                >
                  {item.priority}
                </span>
              </div>
              <p className="text-sm sm:text-base font-bold text-slate-900 dark:text-white leading-snug">
                {item.task}
              </p>
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                Owner: {item.owner}
              </p>
            </div>

            <div className="text-right flex-shrink-0 pt-0.5">
              <span className="text-xs font-bold text-amber-600 dark:text-amber-400 block font-mono">
                {item.target_date ? formatDate(item.target_date) : "TBD"}
              </span>
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                T{item.days_before_event < 0 ? item.days_before_event : `-${item.days_before_event}`}d
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
