import React from "react";
import { Clock } from "lucide-react";
import { PlanSchema } from "../../lib/api";

interface RunOfShowTabPanelProps {
  currentPlan: PlanSchema;
}

export const RunOfShowTabPanel: React.FC<RunOfShowTabPanelProps> = ({ currentPlan }) => {
  return (
    <div className="space-y-3">
      {!currentPlan.run_of_show || currentPlan.run_of_show.length === 0 ? (
        <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/50">
          <Clock className="w-10 h-10 mx-auto text-slate-400 mb-2" />
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            No run-of-show schedule yet
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            A minute-by-minute event day schedule will appear here.
          </p>
        </div>
      ) : (
        currentPlan.run_of_show.map((slot, idx) => (
          <div
            key={idx}
            className="flex items-start gap-4 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs hover:border-amber-400/60 transition-colors"
          >
            <div className="w-28 flex-shrink-0 text-left">
              <span className="text-xs font-mono font-bold text-amber-600 dark:text-amber-400 block">
                {slot.time_slot}
              </span>
              <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                {slot.location}
              </span>
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                  {slot.activity}
                </h3>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                  {slot.lead_person}
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
                {slot.notes}
              </p>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
