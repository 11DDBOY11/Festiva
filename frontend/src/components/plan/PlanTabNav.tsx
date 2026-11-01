import React from "react";
import { Calendar, Clock, DollarSign, Sparkles, Store } from "lucide-react";
import { PlanSchema } from "../../lib/api";
import { PlanTab } from "../../hooks/usePlanModal";

interface PlanTabNavProps {
  activeTab: PlanTab;
  setActiveTab: (tab: PlanTab) => void;
  currentPlan: PlanSchema;
  hasActiveProposal: boolean;
  tabRefs: React.MutableRefObject<{ [key: string]: HTMLButtonElement | null }>;
}

export const PlanTabNav: React.FC<PlanTabNavProps> = ({
  activeTab,
  setActiveTab,
  currentPlan,
  hasActiveProposal,
  tabRefs,
}) => {
  return (
    <div className="sticky top-0 z-20 px-3 sm:px-6 py-2.5 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-y-2 border-slate-200 dark:border-slate-800 shadow-xs">
      <div className="flex items-center gap-2 p-1.5 rounded-2xl bg-slate-100 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 overflow-x-auto no-scrollbar">
        <button
          id="tab-btn-budget"
          ref={(el) => {
            tabRefs.current["budget"] = el;
          }}
          onClick={() => setActiveTab("budget")}
          className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
            activeTab === "budget"
              ? "bg-amber-500 text-stone-950 font-bold shadow-md shadow-amber-500/20 scale-[1.02] border border-amber-600"
              : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
          }`}
        >
          <DollarSign className="w-4 h-4" />
          <span>Budget Table</span>
        </button>

        <button
          id="tab-btn-timeline"
          ref={(el) => {
            tabRefs.current["timeline"] = el;
          }}
          onClick={() => setActiveTab("timeline")}
          className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
            activeTab === "timeline"
              ? "bg-amber-500 text-stone-950 font-bold shadow-md shadow-amber-500/20 scale-[1.02] border border-amber-600"
              : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Timeline & Tasks</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              activeTab === "timeline"
                ? "bg-stone-950/20 text-stone-950"
                : "bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200"
            }`}
          >
            {currentPlan.timeline?.length || 0}
          </span>
        </button>

        <button
          id="tab-btn-run-of-show"
          ref={(el) => {
            tabRefs.current["run_of_show"] = el;
          }}
          onClick={() => setActiveTab("run_of_show")}
          className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
            activeTab === "run_of_show"
              ? "bg-amber-500 text-stone-950 font-bold shadow-md shadow-amber-500/20 scale-[1.02] border border-amber-600"
              : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Run-of-Show</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              activeTab === "run_of_show"
                ? "bg-stone-950/20 text-stone-950"
                : "bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200"
            }`}
          >
            {currentPlan.run_of_show?.length || 0}
          </span>
        </button>

        <button
          id="tab-btn-vendors"
          ref={(el) => {
            tabRefs.current["vendors"] = el;
          }}
          onClick={() => setActiveTab("vendors")}
          className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
            activeTab === "vendors"
              ? "bg-amber-500 text-stone-950 font-bold shadow-md shadow-amber-500/20 scale-[1.02] border border-amber-600"
              : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
          }`}
        >
          <Store className="w-4 h-4" />
          <span>Vendors & Checklist</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              activeTab === "vendors"
                ? "bg-stone-950/20 text-stone-950"
                : "bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200"
            }`}
          >
            {currentPlan.vendor_shortlist?.length || 0}
          </span>
        </button>

        <button
          id="tab-btn-refine"
          ref={(el) => {
            tabRefs.current["refine"] = el;
          }}
          onClick={() => setActiveTab("refine")}
          className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
            activeTab === "refine"
              ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30 scale-[1.02] border border-emerald-500"
              : "bg-amber-500/15 text-amber-900 dark:text-amber-200 hover:bg-amber-500/25 border border-amber-400/60 dark:border-amber-700"
          }`}
        >
          <Sparkles className="w-4 h-4 text-amber-500" />
          <span>Suggestions / Changes</span>
          {hasActiveProposal && (
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
          )}
        </button>
      </div>
    </div>
  );
};
