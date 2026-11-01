import React from "react";
import { AlertCircle, HelpCircle, Sparkles, Wand2, X } from "lucide-react";
import { BriefParseResponse } from "../../lib/api";

interface CreateEventModalProps {
  onClose: () => void;
  modalTab: "ai" | "manual";
  setModalTab: (tab: "ai" | "manual") => void;
  rawBriefText: string;
  setRawBriefText: (text: string) => void;
  parsingBrief: boolean;
  parseError: string | null;
  parsedResult: BriefParseResponse | null;
  onParseBrief: () => void;
  newTitle: string;
  setNewTitle: (title: string) => void;
  newEventType: "wedding" | "birthday" | "community";
  setNewEventType: (type: "wedding" | "birthday" | "community") => void;
  newEventDate: string;
  setNewEventDate: (date: string) => void;
  newGuestCount: string;
  setNewGuestCount: (count: string) => void;
  newTotalBudget: string;
  setNewTotalBudget: (budget: string) => void;
  createLoading: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

export const CreateEventModal: React.FC<CreateEventModalProps> = ({
  onClose,
  modalTab,
  setModalTab,
  rawBriefText,
  setRawBriefText,
  parsingBrief,
  parseError,
  parsedResult,
  onParseBrief,
  newTitle,
  setNewTitle,
  newEventType,
  setNewEventType,
  newEventDate,
  setNewEventDate,
  newGuestCount,
  setNewGuestCount,
  newTotalBudget,
  setNewTotalBudget,
  createLoading,
  onSubmit,
}) => {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-event-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/70 backdrop-blur-sm overflow-y-auto"
    >
      <div className="glass-panel w-full max-w-lg rounded-2xl p-5 sm:p-7 border border-slate-200 dark:border-slate-800 shadow-2xl glow-gold relative my-4 sm:my-8 bg-white dark:bg-slate-900">
        <button
          onClick={onClose}
          aria-label="Close dialog"
          className="absolute top-4 right-4 sm:top-5 sm:right-5 text-slate-400 hover:text-slate-900 dark:hover:text-white p-1 rounded-lg transition cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="mb-4 sm:mb-5">
          <span className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-widest">
            Event Intake
          </span>
          <h2 id="create-event-modal-title" className="text-xl font-bold text-slate-900 dark:text-white mt-1">
            Start New Celebration
          </h2>
        </div>

        {/* Intake Tabs */}
        <div className="flex rounded-xl bg-slate-100 dark:bg-slate-800/80 p-1 border border-slate-200 dark:border-slate-700/80 mb-5">
          <button
            type="button"
            onClick={() => setModalTab("ai")}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              modalTab === "ai"
                ? "bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <Wand2 className="w-3.5 h-3.5" />
            <span>Plan with AI Brief</span>
          </button>
          <button
            type="button"
            onClick={() => setModalTab("manual")}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              modalTab === "manual"
                ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            Direct Manual Form
          </button>
        </div>

        {modalTab === "ai" && (
          <div className="space-y-3.5 mb-5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center justify-between">
                <span>Describe your celebration in plain text</span>
                <span className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">
                  Festiva AI Parser
                </span>
              </label>
              <textarea
                rows={3}
                value={rawBriefText}
                onChange={(e) => setRawBriefText(e.target.value)}
                placeholder="e.g. Planning a wedding in Kadri, Mangaluru on Nov 20, 2026 for 250 guests with a budget of 15 lakhs. Need Mangalorean catering and floral decor."
                className="w-full bg-slate-50 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition"
              />
            </div>

            {/* Quick Samples */}
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-slate-500 text-[11px] font-medium">Quick samples:</span>
              <button
                type="button"
                onClick={() =>
                  setRawBriefText(
                    "Planning a coastal wedding in Kadri, Mangaluru on 2026-11-20 for 250 guests with a budget of 15 lakhs. Need traditional catering and candid photography."
                  )
                }
                className="px-2 py-0.5 rounded-lg bg-slate-200/80 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-300 transition text-[11px]"
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
                className="px-2 py-0.5 rounded-lg bg-slate-200/80 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-300 transition text-[11px]"
              >
                50th Bday (Missing Budget)
              </button>
            </div>

            <button
              type="button"
              disabled={parsingBrief || !rawBriefText.trim()}
              onClick={onParseBrief}
              className="w-full py-2.5 rounded-xl bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 border border-slate-700 text-amber-400 font-semibold text-xs transition flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
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
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
                <span>{parseError}</span>
              </div>
            )}

            {/* Clarifying Questions Callout */}
            {parsedResult && parsedResult.clarifying_questions.length > 0 && (
              <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-300 dark:border-amber-500/30 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-900 dark:text-amber-300">
                  <HelpCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                  <span>Clarifying Questions from Copilot:</span>
                </div>
                <ul className="space-y-1.5 pl-6 list-disc text-xs text-slate-800 dark:text-slate-300">
                  {parsedResult.clarifying_questions.map((q, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {q}
                    </li>
                  ))}
                </ul>
                <p className="text-[11px] text-amber-800 dark:text-amber-400 font-medium pt-1">
                  Please confirm or fill in the parameters below before creating your plan:
                </p>
              </div>
            )}
          </div>
        )}

        {/* Structured Form */}
        <form onSubmit={onSubmit} className="space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Celebration Title
            </label>
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Priya's Coastal Beachside Wedding"
              className="w-full bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Celebration Type
              </label>
              <select
                id="new-event-type"
                value={newEventType}
                onChange={(e: any) => setNewEventType(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:border-amber-500"
              >
                <option value="wedding">Wedding</option>
                <option value="birthday">Birthday</option>
                <option value="community">Community / Festival</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Target Date
              </label>
              <input
                type="date"
                value={newEventDate}
                onChange={(e) => setNewEventDate(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Expected Guests
              </label>
              <input
                type="number"
                min="1"
                value={newGuestCount}
                onChange={(e) => setNewGuestCount(e.target.value)}
                placeholder="150"
                className="w-full bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Total Budget (₹ INR)
              </label>
              <input
                type="number"
                min="1000"
                step="1000"
                value={newTotalBudget}
                onChange={(e) => setNewTotalBudget(e.target.value)}
                placeholder="500000"
                className="w-full bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createLoading || !newTitle.trim()}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-bold text-sm hover:brightness-105 shadow-md shadow-amber-500/20 disabled:opacity-50 cursor-pointer"
            >
              {createLoading ? "Creating..." : "Confirm & Create Event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
