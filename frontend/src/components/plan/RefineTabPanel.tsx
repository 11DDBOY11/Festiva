import React from "react";
import {
  CheckCircle2,
  Loader2,
  Send,
  Sliders,
  Sparkles,
  XCircle,
} from "lucide-react";
import { ProposedChangeResponse } from "../../lib/api";
import { PlanDiffViewer } from "./PlanDiffViewer";

interface RefineTabPanelProps {
  actionSuccessMessage: string | null;
  proposalError: string | null;
  activeProposal: ProposedChangeResponse | null;
  applyingChange: boolean;
  onAcceptChange: () => void;
  onRejectChange: () => void;
  formatCurrency: (amt: number | null | undefined) => string;
  proposalPrompt: string;
  setProposalPrompt: (val: string) => void;
  proposing: boolean;
  onProposeChange: (prompt?: string) => void;
  chatHistory: Array<{ role: "user" | "assistant"; text: string }>;
  chatMessage: string;
  setChatMessage: (val: string) => void;
  streamingChat: boolean;
  onSendChatMessage: (e: React.FormEvent) => void;
}

export const RefineTabPanel: React.FC<RefineTabPanelProps> = ({
  actionSuccessMessage,
  proposalError,
  activeProposal,
  applyingChange,
  onAcceptChange,
  onRejectChange,
  formatCurrency,
  proposalPrompt,
  setProposalPrompt,
  proposing,
  onProposeChange,
  chatHistory,
  chatMessage,
  setChatMessage,
  streamingChat,
  onSendChatMessage,
}) => {
  return (
    <div className="space-y-6">
      {/* Success / Error Alerts */}
      {actionSuccessMessage && (
        <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-emerald-100 dark:bg-emerald-950/70 border-2 border-emerald-400 dark:border-emerald-600 text-emerald-900 dark:text-emerald-100 text-xs sm:text-sm font-semibold shadow-xs animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-700 dark:text-emerald-300 flex-shrink-0" />
          <span>{actionSuccessMessage}</span>
        </div>
      )}
      {proposalError && (
        <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-rose-100 dark:bg-rose-950/70 border-2 border-rose-400 dark:border-rose-600 text-rose-900 dark:text-rose-100 text-xs sm:text-sm font-semibold shadow-xs animate-in fade-in">
          <XCircle className="w-5 h-5 text-rose-700 dark:text-rose-300 flex-shrink-0" />
          <span>{proposalError}</span>
        </div>
      )}

      {/* ACTIVE DIFF VIEWER CARD */}
      {activeProposal && (
        <PlanDiffViewer
          activeProposal={activeProposal}
          applyingChange={applyingChange}
          onAcceptChange={onAcceptChange}
          onRejectChange={onRejectChange}
          formatCurrency={formatCurrency}
        />
      )}

      {/* Natural Language Refinement Input Box */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3 shadow-xs">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Propose Plan Modification
          </h3>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-300 font-medium">
          State desired adjustments in plain language. Festiva calculates the exact budget impacts and
          generates a structured proposal for your approval.
        </p>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">
            Try asking:
          </span>
          <button
            id="btn-suggest-reduce-decor"
            type="button"
            onClick={() => onProposeChange("reduce décor by ₹10,000")}
            disabled={proposing}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-amber-100 dark:bg-slate-800 dark:hover:bg-amber-950/60 text-slate-800 dark:text-slate-200 hover:text-amber-900 dark:hover:text-amber-200 transition border border-slate-200 dark:border-slate-700 cursor-pointer"
          >
            "reduce décor by ₹10,000"
          </button>
          <button
            type="button"
            onClick={() => onProposeChange("add ₹15,000 to catering")}
            disabled={proposing}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-amber-100 dark:bg-slate-800 dark:hover:bg-amber-950/60 text-slate-800 dark:text-slate-200 hover:text-amber-900 dark:hover:text-amber-200 transition border border-slate-200 dark:border-slate-700 cursor-pointer"
          >
            "add ₹15,000 to catering"
          </button>
          <button
            type="button"
            onClick={() => onProposeChange("cut photography by 5k")}
            disabled={proposing}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-amber-100 dark:bg-slate-800 dark:hover:bg-amber-950/60 text-slate-800 dark:text-slate-200 hover:text-amber-900 dark:hover:text-amber-200 transition border border-slate-200 dark:border-slate-700 cursor-pointer"
          >
            "cut photography by 5k"
          </button>
        </div>

        <div className="flex gap-2 pt-2">
          <input
            id="input-propose-prompt"
            type="text"
            value={proposalPrompt}
            onChange={(e) => setProposalPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onProposeChange();
              }
            }}
            placeholder="e.g. 'reduce décor by ₹10,000' or 'trim venue by 20000'"
            className="flex-1 px-4 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/40"
          />
          <button
            id="btn-propose-change"
            type="button"
            onClick={() => onProposeChange()}
            disabled={proposing || !proposalPrompt.trim()}
            className="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-sm disabled:opacity-50 transition flex items-center gap-1.5 cursor-pointer"
          >
            {proposing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Validating Math...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Propose Diff</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Streaming Copilot Conversation Assistant Drawer */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3 shadow-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Festiva Copilot Assistant
            </h3>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            Regional Advisory
          </span>
        </div>

        {/* Scrollable Conversation Stream */}
        <div
          role="region"
          aria-label="Chat conversation history"
          className="space-y-3 max-h-72 overflow-y-auto p-3 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80"
        >
          {chatHistory.map((msg, i) => (
            <div
              key={i}
              className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
            >
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1 px-1">
                {msg.role === "user" ? "You" : "Festiva Copilot"}
              </span>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-amber-600 text-white font-medium"
                    : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white shadow-xs"
                }`}
              >
                {msg.text || (
                  <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Thinking...</span>
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Chat Form - Docked at bottom of card */}
        <form onSubmit={onSendChatMessage} className="flex gap-2 pt-1 shrink-0">
          <input
            type="text"
            value={chatMessage}
            onChange={(e) => setChatMessage(e.target.value)}
            placeholder="Ask Copilot a question about vendors, budgets, or traditions..."
            disabled={streamingChat}
            className="flex-1 px-4 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/40 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={streamingChat || !chatMessage.trim()}
            className="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 disabled:opacity-50 transition flex items-center gap-1.5 cursor-pointer shadow-xs"
          >
            {streamingChat ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
