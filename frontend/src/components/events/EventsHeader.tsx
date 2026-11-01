import React from "react";
import { CheckSquare, CircleDollarSign, Clock, Sparkles } from "lucide-react";
import { EventItem } from "../../lib/api";

interface EventsHeaderProps {
  events: EventItem[];
  nextEvent: EventItem | null;
  daysUntilNext: number | null;
  activeEventsCount: number;
  formatINR: (amount: number | null) => string;
  onOpenCreateModal: () => void;
}

export const EventsHeader: React.FC<EventsHeaderProps> = ({
  events,
  nextEvent,
  daysUntilNext,
  activeEventsCount,
  formatINR,
  onOpenCreateModal,
}) => {
  const isDev = import.meta.env.DEV || import.meta.env.VITE_ENV === "dev";

  return (
    <>
      {/* Top Header & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 sm:mb-8">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
              Celebrations & Plans
            </h1>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20">
              Mangaluru Copilot
            </span>
            {isDev && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 border border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700">
                20 sample vendors
              </span>
            )}
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Plan weddings, birthdays and community events within your budget.
          </p>
        </div>

        <button
          onClick={onOpenCreateModal}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-orange-500 text-slate-950 font-bold text-sm hover:brightness-105 active:brightness-95 transition shadow-md shadow-amber-500/20 cursor-pointer self-start sm:self-auto"
        >
          <Sparkles className="w-4 h-4 text-slate-950" />
          <span>New Celebration</span>
        </button>
      </div>

      {/* Overview Stats: Next Upcoming, Total Planned Budget, Tasks Due This Week */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {/* Card 1: Next Upcoming Event */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-2">
            <span>Next Upcoming Event</span>
            <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          {nextEvent ? (
            <div>
              <div
                className="text-base sm:text-lg font-bold text-slate-900 dark:text-white truncate"
                title={nextEvent.title}
              >
                {nextEvent.title}
              </div>
              <div className="text-xs font-medium text-amber-700 dark:text-amber-400 mt-1">
                {daysUntilNext === 0
                  ? "Today!"
                  : `In ${daysUntilNext} day${daysUntilNext === 1 ? "" : "s"} (${nextEvent.event_date})`}
              </div>
            </div>
          ) : (
            <div>
              <div className="text-base sm:text-lg font-bold text-slate-700 dark:text-slate-300">
                No upcoming dates
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Set a target date on your celebration
              </div>
            </div>
          )}
        </div>

        {/* Card 2: Total Planned Budget */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-2">
            <span>Total Planned Budget</span>
            <CircleDollarSign className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-700 dark:text-amber-400">
            {formatINR(events.reduce((sum, e) => sum + (e.total_budget || 0), 0))}
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Across {events.length} planned celebration{events.length === 1 ? "" : "s"} ({activeEventsCount} active)
          </div>
        </div>

        {/* Card 3: Tasks Due This Week */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-2">
            <span>Tasks Due This Week</span>
            <CheckSquare className="w-4 h-4 text-slate-500 dark:text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white">0</div>
          <div className="text-xs text-slate-600 dark:text-slate-400 mt-1">Coming soon</div>
        </div>
      </div>
    </>
  );
};
