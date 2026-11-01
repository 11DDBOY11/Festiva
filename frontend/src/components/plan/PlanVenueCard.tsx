import React from "react";
import { AlertTriangle, Building2, ExternalLink, MapPin, Utensils } from "lucide-react";
import { PlanSchema } from "../../lib/api";

interface PlanVenueCardProps {
  currentPlan: PlanSchema;
  formatCurrency: (amt: number | null | undefined) => string;
  onChangeVenue: () => void;
}

export const PlanVenueCard: React.FC<PlanVenueCardProps> = ({
  currentPlan,
  formatCurrency,
  onChangeVenue,
}) => {
  // Identify confirmed or recommended venue
  const venueVendor = currentPlan.vendor_shortlist?.find(
    (v) =>
      v.category.toLowerCase().includes("venue") ||
      v.vendor_name.toLowerCase().includes("hall") ||
      v.vendor_name.toLowerCase().includes("centre") ||
      v.vendor_name.toLowerCase().includes("lawn") ||
      v.vendor_name.toLowerCase().includes("ballroom") ||
      v.vendor_name.toLowerCase().includes("pavilion") ||
      v.vendor_name.toLowerCase().includes("resort")
  );

  const rawVenueName =
    venueVendor?.vendor_name ||
    currentPlan.run_of_show?.[0]?.location ||
    "Mangala Heritage Grand Convention Centre";

  const isSampleVenue = Boolean(
    venueVendor?.is_sample || rawVenueName.startsWith("[Sample] ") || rawVenueName.includes("Sample")
  );
  const displayVenueName =
    venueVendor?.is_sample && rawVenueName.startsWith("[Sample] ")
      ? rawVenueName.slice(9)
      : rawVenueName;
  const venueLocation = "Mangaluru, Karnataka";
  const mapsSearchUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    `${displayVenueName}, ${venueLocation}`
  )}`;

  return (
    <div className="space-y-4">
      {/* Top Metric Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Total Budget
          </span>
          <div className="text-lg sm:text-xl font-bold text-amber-600 dark:text-amber-400 mt-0.5">
            {formatCurrency(currentPlan.total_budget)}
          </div>
        </div>
        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Budget Breakdown
          </span>
          <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-0.5">
            {currentPlan.budget?.categories?.length || 0} Categories
          </div>
        </div>
        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Milestones
          </span>
          <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-0.5">
            {currentPlan.timeline?.length || 0} Tasks
          </div>
        </div>
        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Plan Iterations
          </span>
          <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-0.5">
            Version {currentPlan.version}
          </div>
        </div>
      </div>

      {/* Dedicated Venue & Location Showcase Card */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-slate-50 dark:to-slate-900/60 border-2 border-amber-400/80 dark:border-amber-600/80 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
            <MapPin className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-amber-800 dark:text-amber-400">
                Event Venue • ಸ್ಥಳ (Location)
              </span>
              {isSampleVenue ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                  Sample Venue • Demonstration Data
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                  Confirmed Venue
                </span>
              )}
            </div>
            <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white leading-tight mt-0.5">
              {displayVenueName}
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 flex flex-wrap items-center gap-1 mt-0.5">
              <span className="font-medium">📍 {venueLocation}</span>
              {isSampleVenue && (
                <span className="text-[11px] font-medium text-amber-700 dark:text-amber-400">
                  • (Sample venue data for demonstration)
                </span>
              )}
              {venueVendor?.estimated_price_low && (
                <span className="text-slate-500 dark:text-slate-400 font-mono ml-1">
                  • Tier: {formatCurrency(venueVendor.estimated_price_low)} – {formatCurrency(venueVendor.estimated_price_high)}
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 pt-1 md:pt-0">
          <a
            href={mapsSearchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-white dark:bg-slate-800 text-slate-900 dark:text-white border-2 border-slate-300 dark:border-slate-600 hover:border-amber-500 dark:hover:border-amber-400 hover:text-amber-600 dark:hover:text-amber-300 transition shadow-xs"
            title={
              isSampleVenue
                ? "Search illustrative sample venue on Google Maps"
                : "Open venue location in Google Maps"
            }
          >
            <ExternalLink className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            <span>View on Google Maps</span>
            {isSampleVenue && (
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700 ml-0.5">
                Sample Data
              </span>
            )}
          </a>
          <button
            type="button"
            onClick={onChangeVenue}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-amber-500 hover:bg-amber-400 text-stone-950 shadow-xs transition cursor-pointer"
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>Change Venue</span>
          </button>
        </div>
      </div>

      {/* Theme Concept & Summary */}
      {currentPlan.summary && (
        <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
          {currentPlan.summary}
        </p>
      )}

      {/* Compressed Timeline Warning */}
      {currentPlan.meta?.compressed_timeline && (
        <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-amber-100/90 dark:bg-amber-950/70 border-2 border-amber-400 dark:border-amber-600/80 text-amber-950 dark:text-amber-100 shadow-xs">
          <AlertTriangle className="w-4 h-4 text-amber-700 dark:text-amber-300 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block text-xs sm:text-sm text-amber-900 dark:text-amber-200">
              Compressed Timeline Advisory
            </span>
            <span className="text-xs text-amber-950 dark:text-amber-100">
              {typeof currentPlan.meta.timeline_warning === "string"
                ? currentPlan.meta.timeline_warning
                : "This celebration is scheduled on short notice. Standard planning lead times have been expedited. Confirm venue and priority vendors immediately."}
            </span>
          </div>
        </div>
      )}

      {/* Curated Menu / Regional Ideas Pill */}
      {currentPlan.meta?.menu_ideas && currentPlan.meta.menu_ideas.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs py-1">
          <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-300 font-bold mr-1">
            <Utensils className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            <span>Curated Menu:</span>
          </div>
          {currentPlan.meta.menu_ideas.map((dish, i) => (
            <span
              key={i}
              className="inline-block px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 text-xs font-medium shadow-2xs"
            >
              {dish}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
