import React, { useEffect, useState } from "react";
import {
  Calendar,
  Users,
  Plus,
  Trash2,
  Sparkles,
  MapPin,
  CircleDollarSign,
  ArrowUpRight,
  X,
  AlertCircle,
} from "lucide-react";
import { EventItem, createEvent, deleteEvent, listEvents } from "../lib/api";

export const EventsPage: React.FC = () => {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newEventType, setNewEventType] = useState<"wedding" | "birthday" | "community">("wedding");
  const [newEventDate, setNewEventDate] = useState("");
  const [newGuestCount, setNewGuestCount] = useState<string>("150");
  const [newTotalBudget, setNewTotalBudget] = useState<string>("500000");

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listEvents();
      setEvents(data);
    } catch (err: any) {
      setError(err.message || "Failed to load events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      await createEvent({
        title: newTitle,
        event_type: newEventType,
        event_date: newEventDate || null,
        city: "Mangaluru",
        guest_count: newGuestCount ? parseInt(newGuestCount, 10) : null,
        total_budget: newTotalBudget ? parseFloat(newTotalBudget) : null,
        currency: "INR",
      });
      setIsModalOpen(false);
      setNewTitle("");
      await loadEvents();
    } catch (err: any) {
      alert(err.message || "Failed to create event");
    } finally {
      setCreateLoading(false);
    }
  };

  const handleDelete = async (id: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"?`)) return;
    try {
      await deleteEvent(id);
      setEvents((prev) => prev.filter((e) => e.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete event");
    }
  };

  const formatINR = (amount: number | null) => {
    if (amount === null || isNaN(amount)) return "—";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getEventTypeBadge = (type: string) => {
    switch (type) {
      case "wedding":
        return "bg-rose-500/10 text-rose-300 border-rose-500/20";
      case "birthday":
        return "bg-amber-500/10 text-amber-300 border-amber-500/20";
      case "community":
        return "bg-blue-500/10 text-blue-300 border-blue-500/20";
      default:
        return "bg-slate-500/10 text-slate-300 border-slate-500/20";
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <span>Your Events & Plans</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-normal">
              {events.length} Active
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic budgets, backwards timelines, and curated Mangaluru vendor shortlists.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-semibold text-sm hover:brightness-110 shadow-lg shadow-amber-500/20 transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>New Celebration</span>
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="glass-card rounded-xl p-4 border border-slate-800/80">
          <p className="text-xs text-slate-400 font-medium">Primary Hub</p>
          <div className="flex items-center justify-between mt-1">
            <span className="text-lg font-bold text-slate-100 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-amber-400" />
              Mangaluru, KA
            </span>
            <span className="text-xs text-emerald-400 bg-emerald-950/60 border border-emerald-500/20 px-2 py-0.5 rounded">
              20 Curated Vendors
            </span>
          </div>
        </div>

        <div className="glass-card rounded-xl p-4 border border-slate-800/80">
          <p className="text-xs text-slate-400 font-medium">Supported Events</p>
          <div className="flex items-center gap-2 mt-1 text-sm font-semibold text-slate-200">
            <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20 text-xs">Wedding</span>
            <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs">Birthday</span>
            <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 text-xs">Community</span>
          </div>
        </div>

        <div className="glass-card rounded-xl p-4 border border-slate-800/80">
          <p className="text-xs text-slate-400 font-medium">Architecture Core</p>
          <div className="flex items-center justify-between mt-1">
            <span className="text-sm font-semibold text-slate-200">LLM Proposes, Code Decides</span>
            <span className="text-xs text-amber-400 bg-amber-950/60 border border-amber-500/20 px-2 py-0.5 rounded">
              Versioned
            </span>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadEvents}
            className="text-xs underline hover:text-white"
          >
            Retry
          </button>
        </div>
      )}

      {/* Events Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-card rounded-2xl p-6 border border-slate-800 animate-pulse h-52">
              <div className="h-4 bg-slate-800 rounded w-1/3 mb-4"></div>
              <div className="h-6 bg-slate-800 rounded w-2/3 mb-2"></div>
              <div className="h-4 bg-slate-800 rounded w-1/2 mb-6"></div>
              <div className="h-8 bg-slate-800 rounded w-full"></div>
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-dashed border-slate-800">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-4 text-amber-400">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-1">No events planned yet</h3>
          <p className="text-sm text-slate-400 max-w-sm mx-auto mb-6">
            Create your first celebration brief to generate an automated budget breakdown, backward timeline, and vendor shortlist.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-semibold text-sm hover:brightness-110 transition shadow-lg shadow-amber-500/20"
          >
            <Plus className="w-4 h-4" />
            <span>Create First Event</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {events.map((evt) => (
            <div
              key={evt.id}
              className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-amber-500/30 transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span
                    className={`text-xs uppercase tracking-wider font-semibold px-2.5 py-0.5 rounded-full border ${getEventTypeBadge(
                      evt.event_type
                    )}`}
                  >
                    {evt.event_type}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400 font-mono">
                      v{evt.current_version || 1}
                    </span>
                    <button
                      onClick={() => handleDelete(evt.id, evt.title)}
                      className="text-slate-500 hover:text-rose-400 p-1 rounded transition opacity-0 group-hover:opacity-100"
                      title="Delete Event"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-amber-300 transition-colors line-clamp-1">
                  {evt.title}
                </h3>

                <div className="space-y-2 mt-4 text-xs text-slate-300">
                  <div className="flex items-center gap-2 text-slate-400">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>{evt.event_date ? new Date(evt.event_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "Date to be confirmed"}</span>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Users className="w-3.5 h-3.5 text-slate-400" />
                      <span>{evt.guest_count ? `${evt.guest_count} guests` : "Guests TBD"}</span>
                    </div>
                    <div className="flex items-center gap-1 font-semibold text-slate-100">
                      <CircleDollarSign className="w-3.5 h-3.5 text-amber-400" />
                      <span>{formatINR(evt.total_budget)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-500/20 px-2 py-0.5 rounded">
                  {evt.status}
                </span>
                <span className="text-xs text-amber-400 font-medium inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                  View Plan <ArrowUpRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Event Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-2xl p-6 sm:p-8 border border-slate-800 shadow-2xl glow-gold relative">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="mb-6">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-widest">
                New Celebration
              </span>
              <h2 className="text-xl font-bold text-white mt-1">Start Event Plan</h2>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Event Title
                </label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Priya & Rahul's Coastal Wedding"
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Celebration Type
                  </label>
                  <select
                    value={newEventType}
                    onChange={(e: any) => setNewEventType(e.target.value)}
                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-400"
                  >
                    <option value="wedding">Wedding</option>
                    <option value="birthday">Birthday</option>
                    <option value="community">Community / College</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Target Date
                  </label>
                  <input
                    type="date"
                    value={newEventDate}
                    onChange={(e) => setNewEventDate(e.target.value)}
                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-400"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Expected Guests
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={newGuestCount}
                    onChange={(e) => setNewGuestCount(e.target.value)}
                    placeholder="150"
                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-400"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Total Budget (₹ INR)
                  </label>
                  <input
                    type="number"
                    min="1000"
                    step="1000"
                    value={newTotalBudget}
                    onChange={(e) => setNewTotalBudget(e.target.value)}
                    placeholder="500000"
                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-400"
                  />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-semibold text-sm hover:brightness-110 shadow-lg shadow-amber-500/20 disabled:opacity-50"
                >
                  {createLoading ? "Creating..." : "Save Event"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
