import React from "react";
import { HelpCircle, Loader2, Mail, Store } from "lucide-react";
import { PlanSchema } from "../../lib/api";
import { formatCategoryLabel } from "../../lib/constants";

interface VendorsTabPanelProps {
  currentPlan: PlanSchema;
  formatCurrency: (amt: number | null | undefined) => string;
  draftingCategory: string | null;
  onDraftVendorInquiry: (category: string, vendorName?: string) => void;
}

export const VendorsTabPanel: React.FC<VendorsTabPanelProps> = ({
  currentPlan,
  formatCurrency,
  draftingCategory,
  onDraftVendorInquiry,
}) => {
  return (
    <div className="space-y-6">
      {/* Grounded Vendor Directory Recommendations */}
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5 mb-3">
          <Store className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          Grounded Mangaluru Vendor Shortlist
        </h3>
        {!currentPlan.vendor_shortlist || currentPlan.vendor_shortlist.length === 0 ? (
          <div className="text-center py-8 px-4 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/50">
            <Store className="w-8 h-8 mx-auto text-slate-400 mb-2" />
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              No vendor recommendations yet
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Curated vendor recommendations for your location will appear here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {currentPlan.vendor_shortlist.map((v, idx) => {
              const isSample = Boolean(v.is_sample || v.vendor_name.startsWith("[Sample] "));
              const cleanVendorName = v.vendor_name.replace(/^\[Sample\]\s*/i, "");
              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-2 shadow-xs hover:border-amber-400/60 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 block">
                        {formatCategoryLabel(v.category)}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                          {cleanVendorName}
                        </h3>
                        {isSample && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700">
                            Sample Data
                          </span>
                        )}
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        v.price_status === "confirmed"
                          ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700"
                          : "bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700"
                      }`}
                    >
                      {v.price_status === "confirmed" ? "Price Confirmed" : "Estimate"}
                    </span>
                  </div>

                  <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    {v.estimated_price_low && v.estimated_price_high
                      ? `${formatCurrency(v.estimated_price_low)} – ${formatCurrency(v.estimated_price_high)}`
                      : "Custom Quote"}
                    {v.price_unit && (
                      <span className="text-[11px] text-slate-500 dark:text-slate-400 font-normal ml-1">
                        ({v.price_unit})
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-300 italic leading-relaxed">
                    "{v.reason}"
                  </p>

                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <button
                      id={`btn-draft-vendor-${idx}`}
                      type="button"
                      onClick={() => onDraftVendorInquiry(v.category, cleanVendorName)}
                      disabled={draftingCategory === v.category}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-500/10 hover:bg-amber-500/20 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700 transition cursor-pointer disabled:opacity-50"
                    >
                      {draftingCategory === v.category ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-600" />
                      ) : (
                        <Mail className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                      )}
                      <span>Draft Message</span>
                    </button>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {v.questions_to_ask?.length || 0} questions
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Vendor Category Questions Checklist */}
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5 mb-3">
          <HelpCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          Vendor Category Checklist & Negotiation Questions
        </h3>
        {!currentPlan.checklist || currentPlan.checklist.length === 0 ? (
          <div className="text-center py-8 px-4 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/50">
            <HelpCircle className="w-8 h-8 mx-auto text-slate-400 mb-2" />
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              No checklist items yet
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Vendor questions and checklist items will appear here.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {currentPlan.checklist.map((chk, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-slate-900 dark:text-white">
                    {formatCategoryLabel(chk.category)}: {chk.item}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {chk.due_phase}
                    </span>
                    <button
                      id={`btn-draft-chk-${idx}`}
                      type="button"
                      onClick={() => onDraftVendorInquiry(chk.category)}
                      disabled={draftingCategory === chk.category}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold bg-amber-500/10 hover:bg-amber-500/20 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700 transition cursor-pointer disabled:opacity-50"
                    >
                      <Mail className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                      <span>Draft Message</span>
                    </button>
                  </div>
                </div>
                <ul className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                  {chk.questions_to_ask_vendor.map((q, qIdx) => (
                    <li key={qIdx} className="flex items-start gap-2">
                      <span className="text-amber-600 dark:text-amber-400 font-bold">•</span>
                      <span>{q}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
