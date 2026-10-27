import React, { useState } from "react";
import {
  AlertTriangle,
  Calendar,
  Clock,
  DollarSign,
  HelpCircle,
  Sparkles,
  Store,
  Utensils,
  X,
} from "lucide-react";
import { PlanSchema } from "../lib/api";

interface PlanViewModalProps {
  plan: PlanSchema;
  onClose: () => void;
}

export const PlanViewModal: React.FC<PlanViewModalProps> = ({ plan, onClose }) => {
  const [activeTab, setActiveTab] = useState<"budget" | "timeline" | "run_of_show" | "vendors">(
    "budget"
  );

  const formatCurrency = (amt: number | null | undefined): string => {
    if (amt === null || amt === undefined) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amt);
  };

  const formatDate = (d: string | null): string => {
    if (!d) return "Date TBD";
    return new Date(d).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Event Plan Modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-4xl max-h-[92vh] flex flex-col rounded-2xl bg-card border border-border shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-5 sm:p-6 border-b border-border bg-muted/40">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
                  Plan v{plan.version}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium capitalize bg-secondary text-secondary-foreground">
                  {plan.event_type}
                </span>
                {plan.guest_count && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
                    {plan.guest_count} guests
                  </span>
                )}
                {plan.event_date && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
                    {formatDate(plan.event_date)}
                  </span>
                )}
              </div>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
                {plan.title}
              </h2>
            </div>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Top Metric Strip */}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-card border border-border">
              <span className="text-xs font-medium text-muted-foreground">Total Planned Budget</span>
              <div className="text-lg sm:text-xl font-bold text-primary mt-0.5">
                {formatCurrency(plan.total_budget)}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-card border border-border">
              <span className="text-xs font-medium text-muted-foreground">Budget Breakdown</span>
              <div className="text-lg sm:text-xl font-bold text-foreground mt-0.5">
                {plan.budget?.categories?.length || 0} Categories
              </div>
            </div>
            <div className="col-span-2 sm:col-span-1 p-3 rounded-xl bg-card border border-border">
              <span className="text-xs font-medium text-muted-foreground">Milestones</span>
              <div className="text-lg sm:text-xl font-bold text-foreground mt-0.5">
                {plan.timeline?.length || 0} Tasks
              </div>
            </div>
          </div>

          {/* Theme Concept & Summary */}
          {plan.summary && (
            <p className="mt-3 text-xs sm:text-sm text-muted-foreground leading-relaxed">
              {plan.summary}
            </p>
          )}

          {/* Compressed Timeline Warning */}
          {plan.meta?.compressed_timeline && (
            <div className="mt-3 flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-200 text-xs sm:text-sm">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">Compressed Timeline Advisory</span>
                <span className="text-xs">
                  {typeof plan.meta.timeline_warning === "string"
                    ? plan.meta.timeline_warning
                    : "This celebration is scheduled on short notice. Standard planning lead times have been expedited. Confirm venue and priority vendors immediately."}
                </span>
              </div>
            </div>
          )}

          {/* Menu / Regional Ideas Pill */}
          {plan.meta?.menu_ideas && plan.meta.menu_ideas.length > 0 && (
            <div className="mt-3 flex items-center gap-2 overflow-x-auto text-xs text-muted-foreground py-1">
              <Utensils className="w-3.5 h-3.5 text-primary flex-shrink-0" />
              <span className="font-semibold text-foreground flex-shrink-0">Curated Menu:</span>
              <div className="flex items-center gap-1.5 flex-nowrap">
                {plan.meta.menu_ideas.map((dish, i) => (
                  <span
                    key={i}
                    className="inline-block px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground text-[11px] whitespace-nowrap"
                  >
                    {dish}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-border bg-card px-4 sm:px-6 overflow-x-auto">
          <button
            onClick={() => setActiveTab("budget")}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === "budget"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <DollarSign className="w-4 h-4" />
            Budget Table
          </button>
          <button
            onClick={() => setActiveTab("timeline")}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === "timeline"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Calendar className="w-4 h-4" />
            Timeline & Tasks ({plan.timeline?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("run_of_show")}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === "run_of_show"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Clock className="w-4 h-4" />
            Run-of-Show ({plan.run_of_show?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("vendors")}
            className={`flex items-center gap-2 py-3 px-3 text-xs sm:text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === "vendors"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Store className="w-4 h-4" />
            Vendors & Checklist
          </button>
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {/* TAB 1: BUDGET TABLE */}
          {activeTab === "budget" && (
            <div className="space-y-4">
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-left text-xs sm:text-sm">
                  <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold">Category</th>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold text-right">Share (%)</th>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold text-right">Allocated Amount</th>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold text-right hidden sm:table-cell">
                        Per Guest
                      </th>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold hidden md:table-cell">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {plan.budget?.categories?.map((cat, idx) => (
                      <tr key={idx} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3 px-3 sm:px-4 font-medium text-foreground">
                          {cat.category}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-right font-mono text-muted-foreground">
                          {Number(cat.share_pct).toFixed(1)}%
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-right font-bold text-foreground">
                          {formatCurrency(Number(cat.allocated_amount))}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-right font-mono text-muted-foreground hidden sm:table-cell">
                          {cat.per_guest_cost ? formatCurrency(Number(cat.per_guest_cost)) : "—"}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-xs text-muted-foreground hidden md:table-cell">
                          {cat.notes || "Standard tier allocation"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-muted/50 font-bold border-t border-border">
                    <tr>
                      <td className="py-3 px-3 sm:px-4 text-foreground">Total Budget</td>
                      <td className="py-3 px-3 sm:px-4 text-right text-muted-foreground">100.0%</td>
                      <td className="py-3 px-3 sm:px-4 text-right text-primary text-base">
                        {formatCurrency(plan.total_budget)}
                      </td>
                      <td className="py-3 px-3 sm:px-4 text-right text-muted-foreground hidden sm:table-cell">
                        {plan.guest_count && plan.total_budget
                          ? formatCurrency(plan.total_budget / plan.guest_count)
                          : "—"}
                      </td>
                      <td className="py-3 px-3 sm:px-4 text-xs text-muted-foreground hidden md:table-cell">
                        Sum balanced within 1%
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: TIMELINE & TASKS */}
          {activeTab === "timeline" && (
            <div className="space-y-3">
              {plan.meta?.compressed_timeline && (
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-200 text-xs sm:text-sm">
                  <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block">Compressed Timeline Schedule</span>
                    <span className="text-xs">
                      {typeof plan.meta.timeline_warning === "string"
                        ? plan.meta.timeline_warning
                        : "Milestones have been compressed to fit the short preparation window."}
                    </span>
                  </div>
                </div>
              )}
              {plan.timeline?.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start justify-between gap-3 p-3.5 rounded-xl border border-border bg-card hover:border-primary/40 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-primary/10 text-primary">
                        {item.phase}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-muted text-muted-foreground">
                        {item.category}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          item.priority === "high"
                            ? "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                            : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                        }`}
                      >
                        {item.priority}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-foreground">{item.task}</p>
                    <p className="text-xs text-muted-foreground">Owner: {item.owner}</p>
                  </div>

                  {item.target_date && (
                    <div className="text-right flex-shrink-0">
                      <span className="text-xs font-semibold text-foreground block">
                        {formatDate(item.target_date)}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {item.days_before_event === 0 ? "Event Day" : `${item.days_before_event}d left`}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: RUN OF SHOW */}
          {activeTab === "run_of_show" && (
            <div className="space-y-3">
              <div className="rounded-xl border border-border overflow-hidden">
                <table className="w-full text-left text-xs sm:text-sm">
                  <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                    <tr>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold w-28 sm:w-36">Time Slot</th>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold">Activity</th>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold hidden sm:table-cell">Location</th>
                      <th className="py-2.5 px-3 sm:px-4 font-semibold hidden md:table-cell">Lead Person</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {plan.run_of_show?.map((slot, idx) => (
                      <tr key={idx} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3 px-3 sm:px-4 font-mono font-semibold text-primary">
                          {slot.time_slot}
                        </td>
                        <td className="py-3 px-3 sm:px-4">
                          <div className="font-medium text-foreground">{slot.activity}</div>
                          {slot.notes && (
                            <div className="text-xs text-muted-foreground mt-0.5">{slot.notes}</div>
                          )}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-muted-foreground hidden sm:table-cell">
                          {slot.location}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-muted-foreground hidden md:table-cell">
                          {slot.lead_person}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: VENDORS & CHECKLIST */}
          {activeTab === "vendors" && (
            <div className="space-y-6">
              {/* Grounded Vendor Shortlist */}
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5 mb-3">
                  <Store className="w-4 h-4 text-primary" />
                  Recommended Grounded Vendors (Mangaluru)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {plan.vendor_shortlist?.map((v, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-border bg-card space-y-2 hover:border-primary/40 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[11px] font-semibold uppercase text-muted-foreground">
                            {v.category}
                          </span>
                          <h4 className="font-bold text-foreground text-sm">{v.vendor_name}</h4>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            v.price_status === "confirmed"
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          }`}
                        >
                          {v.price_status === "confirmed" ? "Price Confirmed" : "To confirm"}
                        </span>
                      </div>

                      <p className="text-xs text-muted-foreground leading-relaxed">{v.reason}</p>

                      <div className="pt-2 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                        <span>Estimated Pricing:</span>
                        <span className="font-bold text-foreground">
                          {v.estimated_price_low !== null && v.estimated_price_low !== undefined
                            ? `${formatCurrency(Number(v.estimated_price_low))} – ${formatCurrency(
                                Number(v.estimated_price_high || v.estimated_price_low)
                              )}`
                            : "Pricing to confirm"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Vendor Category Questions Checklist */}
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5 mb-3">
                  <HelpCircle className="w-4 h-4 text-primary" />
                  Vendor Category Checklist & Negotiation Questions
                </h3>
                <div className="space-y-3">
                  {plan.checklist?.map((chk, idx) => (
                    <div key={idx} className="p-4 rounded-xl border border-border bg-card space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-foreground">
                          {chk.category}: {chk.item}
                        </span>
                        <span className="text-xs text-muted-foreground">{chk.due_phase}</span>
                      </div>
                      <ul className="space-y-1.5 text-xs text-muted-foreground">
                        {chk.questions_to_ask_vendor.map((q, qIdx) => (
                          <li key={qIdx} className="flex items-start gap-2">
                            <span className="text-primary font-bold">•</span>
                            <span>{q}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-border bg-muted/30 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            <span>Deterministic budget & timeline • Grounded in Mangaluru dataset</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
          >
            Close Plan
          </button>
        </div>
      </div>
    </div>
  );
};
