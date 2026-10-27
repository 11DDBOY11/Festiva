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
  HelpCircle,
  Wand2,
} from "lucide-react";
import {
  EventItem,
  EventBrief,
  BriefParseResponse,
  createEvent,
  deleteEvent,
  listEvents,
  parseBrief,
} from "../lib/api";

export const EventsPage: React.FC = () => {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalTab, setModalTab] = useState<"ai" | "manual">("ai");
  const [createLoading, setCreateLoading] = useState(false);

  // AI Brief Intake State
  const [rawBriefText, setRawBriefText] = useState("");
  const [parsingBrief, setParsingBrief] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedResult, setParsedResult] = useState<BriefParseResponse | null>(null);

  // Editable Form State (synced from AI brief or manual)
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

  const handleParseBrief = async () => {
    if (!rawBriefText.trim()) return;
    setParsingBrief(true);
    setParseError(null);
    try {
      const res = await parseBrief(rawBriefText);
      setParsedResult(res);
      const b: EventBrief = res.brief;
      setNewTitle(b.title || "");
      setNewEventType(b.event_type);
      setNewEventDate(b.event_date || "");
      if (b.guest_count) setNewGuestCount(b.guest_count.toString());
      if (b.total_budget) setNewTotalBudget(b.total_budget.toString());
    } catch (err: any) {
      setParseError(err.message || "Failed to parse brief with AI.");
    } finally {
      setParsingBrief(false);
    }
  };

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
      resetModalState();
      await loadEvents();
    } catch (err: any) {
      alert(err.message || "Failed to create event");
    } finally {
      setCreateLoading(false);
    }
  };

  const resetModalState = () => {
    setRawBriefText("");
    setParsedResult(null);
    setParseError(null);
    setNewTitle("");
    setNewEventType("wedding");
    setNewEventDate("");
    setNewGuestCount("150");
    setNewTotalBudget("500000");
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
      {/* Top Header & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <span>Celebrations & Plans</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Mangaluru Copilot
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Budget-aware events powered by verified local vendors and deterministic rules.
          </p>
        </div>

        <button
          onClick={() => {
            resetModalState();
            setIsModalOpen(true);
          }}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-orange-500 text-slate-950 font-semibold text-sm hover:brightness-110 active:brightness-95 transition shadow-lg shadow-amber-500/20 cursor-pointer"
        >
          <Sparkles className="w-4 h-4 text-slate-950" />
          <span>New Celebration</span>
        </button>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
            Active Celebrations
          </div>
          <div className="text-2xl font-bold text-white">{events.length}</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
            Total Budget Managed
          </div>
          <div className="text-2xl font-bold text-amber-400">
            {formatINR(events.reduce((sum, e) => sum + (e.total_budget || 0), 0))}
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
            Estimated Total Guests
          </div>
          <div className="text-2xl font-bold text-white">
            {events.reduce((sum, e) => sum + (e.guest_count || 0), 0).toLocaleString()}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800">
          <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-400">Loading your Mangaluru celebrations...</p>
        </div>
      ) : events.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-dashed border-slate-800 max-w-lg mx-auto">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-400 flex items-center justify-center mx-auto mb-4 border border-amber-500/20">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-1">No Celebrations Yet</h3>
          <p className="text-sm text-slate-400 mb-6">
            Describe your event in plain English (e.g. 250 guests wedding in Kadri for 15 lakhs) or
            enter details directly.
          </p>
          <button
            onClick={() => {
              resetModalState();
              setIsModalOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium transition border border-slate-700"
          >
            <Plus className="w-4 h-4 text-amber-400" />
            <span>Create Your First Event</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {events.map((event) => (
            <div
              key={event.id}
              className="glass-panel rounded-2xl p-6 border border-slate-800/80 hover:border-slate-700 transition flex flex-col justify-between group shadow-sm hover:shadow-xl"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span
                    className={`text-xs font-semibold uppercase px-2.5 py-0.5 rounded-full border ${getEventTypeBadge(
                      event.event_type
                    )}`}
                  >
                    {event.event_type}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    v{event.current_version || 1}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-amber-300 transition mb-3 line-clamp-1">
                  {event.title}
                </h3>

                <div className="space-y-2 text-sm text-slate-300 mb-6">
                  <div className="flex items-center gap-2">
                    <CircleDollarSign className="w-4 h-4 text-amber-400 shrink-0" />
                    <span className="font-semibold text-slate-100">
                      {formatINR(event.total_budget)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>{event.guest_count ? `${event.guest_count} Guests` : "Guest count unset"}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
                    <span>{event.event_date ? event.event_date : "Date to be decided"}</span>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <span>{event.city || "Mangaluru"}</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between">
                <button
                  onClick={() => handleDelete(event.id, event.title)}
                  className="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg transition"
                  title="Delete celebration"
                >
                  <Trash2 className="w-4 h-4" />
                </button>

                <button
                  onClick={() => alert(`Phase 4 will open full plan view for "${event.title}".`)}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 transition"
                >
                  <span>Open Copilot</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Event Modal with AI Brief Parser */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="glass-panel w-full max-w-xl rounded-2xl p-6 sm:p-8 border border-slate-800 shadow-2xl glow-gold relative my-8">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="mb-5">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-widest">
                Event Intake
              </span>
              <h2 className="text-xl font-bold text-white mt-1">Start New Celebration</h2>
            </div>

            {/* Intake Tabs */}
            <div className="flex rounded-xl bg-slate-900/80 p-1 border border-slate-800 mb-6">
              <button
                type="button"
                onClick={() => setModalTab("ai")}
                className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-2 ${
                  modalTab === "ai"
                    ? "bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-semibold shadow-md"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Wand2 className="w-3.5 h-3.5" />
                <span>Plan with AI Brief</span>
              </button>
              <button
                type="button"
                onClick={() => setModalTab("manual")}
                className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all ${
                  modalTab === "manual"
                    ? "bg-slate-800 text-slate-100 font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Direct Manual Form
              </button>
            </div>

            {modalTab === "ai" && (
              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                    <span>Describe your celebration in plain text</span>
                    <span className="text-[11px] text-slate-500">FastAPI POST /briefs/parse</span>
                  </label>
                  <textarea
                    rows={3}
                    value={rawBriefText}
                    onChange={(e) => setRawBriefText(e.target.value)}
                    placeholder="e.g. Planning a wedding in Kadri, Mangaluru on Nov 20, 2026 for 250 guests with a budget of 15 lakhs. Need Mangalorean catering and floral decor."
                    className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-400 transition"
                  />
                </div>

                {/* Quick Samples */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-slate-500 text-[11px]">Quick samples:</span>
                  <button
                    type="button"
                    onClick={() =>
                      setRawBriefText(
                        "Planning a coastal wedding in Kadri, Mangaluru on 2026-11-20 for 250 guests with a budget of 15 lakhs. Need traditional catering and candid photography."
                      )
                    }
                    className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition text-[11px]"
                  >
                    Coastal Wedding (15L)
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setRawBriefText(
                        "Father's 50th birthday dinner in Bejai on 2026-12-15 with 60 family guests. Need coastal appetizers and cake."
                      )
                    }
                    className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition text-[11px]"
                  >
                    50th Bday (Missing Budget)
                  </button>
                </div>

                <button
                  type="button"
                  disabled={parsingBrief || !rawBriefText.trim()}
                  onClick={handleParseBrief}
                  className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-amber-400 font-semibold text-xs transition flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {parsingBrief ? (
                    <div className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Parse Brief & Detect Missing Fields</span>
                    </>
                  )}
                </button>

                {parseError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{parseError}</span>
                  </div>
                )}

                {/* Clarifying Questions Callout */}
                {parsedResult && parsedResult.clarifying_questions.length > 0 && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-amber-300">
                      <HelpCircle className="w-4 h-4 text-amber-400" />
                      <span>Clarifying Questions from Copilot:</span>
                    </div>
                    <ul className="space-y-1.5 pl-6 list-disc text-xs text-slate-300">
                      {parsedResult.clarifying_questions.map((q, idx) => (
                        <li key={idx} className="leading-relaxed">
                          {q}
                        </li>
                      ))}
                    </ul>
                    <p className="text-[11px] text-amber-400/80 pt-1">
                      Please confirm or fill in the details below before creating your plan:
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Event Form (Populated by AI or direct entry) */}
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Celebration Title
                </label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Priya & Rahul's Coastal Wedding"
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-400"
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
                    <option value="community">Community / Festival</option>
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

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading || !newTitle.trim()}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-semibold text-sm hover:brightness-110 shadow-lg shadow-amber-500/20 disabled:opacity-50 cursor-pointer"
                >
                  {createLoading ? "Creating..." : "Confirm & Create Event"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
