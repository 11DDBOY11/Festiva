import React from "react";
import {
  Calendar,
  CircleDollarSign,
  Loader2,
  MapPin,
  Trash2,
  Users,
} from "lucide-react";
import { EventItem } from "../../lib/api";

interface EventCardProps {
  event: EventItem;
  loadingPlanEventId: string | null;
  onViewPlan: (id: string) => void;
  onDelete: (id: string, title: string) => void;
  formatINR: (amount: number | null) => string;
  getEventTypeBadge: (type: string) => string;
}

export const EventCard: React.FC<EventCardProps> = ({
  event,
  loadingPlanEventId,
  onViewPlan,
  onDelete,
  formatINR,
  getEventTypeBadge,
}) => {
  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-200 dark:border-slate-800 flex flex-col justify-between hover:border-amber-400/80 dark:hover:border-amber-500/50 transition-all hover:shadow-lg hover:shadow-amber-500/5 group bg-white dark:bg-slate-900">
      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <span
            className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border capitalize ${getEventTypeBadge(
              event.event_type
            )}`}
          >
            {event.event_type}
          </span>
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
            {event.status === "draft" ? "Drafting" : "Plan generated"}
          </span>
        </div>

        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2 leading-snug group-hover:text-amber-700 dark:group-hover:text-amber-400 transition-colors">
          {event.title}
        </h3>

        <div className="space-y-2 text-xs text-slate-700 dark:text-slate-300 mb-6">
          <div className="flex items-center gap-2">
            <CircleDollarSign className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="font-semibold text-slate-900 dark:text-slate-100">
              {formatINR(event.total_budget)}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-500 dark:text-slate-400 shrink-0" />
            <span>{event.guest_count ? `${event.guest_count} Guests` : "Guest count unset"}</span>
          </div>

          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-500 dark:text-slate-400 shrink-0" />
            <span>{event.event_date ? event.event_date : "Date to be decided"}</span>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
            <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span>{event.city || "Mangaluru"}</span>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-slate-200 dark:border-slate-800/80 flex items-center justify-between">
        <button
          onClick={() => onDelete(event.id, event.title)}
          className="text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 p-1.5 rounded-lg transition"
          title="Delete celebration"
        >
          <Trash2 className="w-4 h-4" />
        </button>

        {/* View Plan enabled in Phase 4 */}
        <button
          id="btn-view-plan"
          type="button"
          onClick={() => onViewPlan(event.id)}
          disabled={loadingPlanEventId === event.id}
          className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-900 dark:text-amber-200 bg-amber-100 dark:bg-amber-950/60 hover:bg-amber-200 dark:hover:bg-amber-900/80 border border-amber-300 dark:border-amber-700 px-3 py-1.5 rounded-lg transition"
        >
          {loadingPlanEventId === event.id ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-900 dark:text-amber-200" />
              <span>Loading...</span>
            </>
          ) : (
            <span>View plan</span>
          )}
        </button>
      </div>
    </div>
  );
};
