import React from "react";
import { Check, Copy, Mail, X } from "lucide-react";
import { VendorInquiryDraft } from "../../lib/api";
import { formatCategoryLabel } from "../../lib/constants";

interface DraftMessageDialogProps {
  draftModalData: VendorInquiryDraft;
  copiedMessage: boolean;
  onCopyMessage: () => void;
  onClose: () => void;
}

export const DraftMessageDialog: React.FC<DraftMessageDialogProps> = ({
  draftModalData,
  copiedMessage,
  onCopyMessage,
  onClose,
}) => {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="draft-modal-title"
      className="fixed inset-0 z-60 flex items-center justify-center p-3 sm:p-6 bg-slate-950/75 backdrop-blur-xs animate-in fade-in"
    >
      <div className="w-full max-w-2xl max-h-[85dvh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border-2 border-amber-400 dark:border-amber-600 shadow-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-amber-500/10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500 text-white flex items-center justify-center">
              <Mail className="w-4 h-4" />
            </div>
            <div>
              <h3
                id="draft-modal-title"
                className="text-base font-bold text-slate-900 dark:text-white leading-tight"
              >
                Draft Vendor Inquiry: {formatCategoryLabel(draftModalData.vendor_category)}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Grounded communication asking for quotes & date availability
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close draft message dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 flex-1 overflow-y-auto space-y-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              Subject Line
            </span>
            <div className="p-2.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs sm:text-sm font-semibold text-slate-900 dark:text-white border border-slate-200 dark:border-slate-700">
              {draftModalData.subject}
            </div>
          </div>

          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
              Ready-to-Send Message Body
            </span>
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm text-slate-800 dark:text-slate-200 font-mono whitespace-pre-wrap leading-relaxed select-all">
              {draftModalData.full_message}
            </div>
          </div>

          {draftModalData.specific_questions.length > 0 && (
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                Checklist Questions Embedded
              </span>
              <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                {draftModalData.specific_questions.map((q, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-amber-600 font-bold">•</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/90 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            {draftModalData.is_template_fallback
              ? "Generated via standard template"
              : "Generated via Festiva Copilot"}
          </span>
          <div className="flex items-center gap-2">
            <button
              id="btn-copy-draft-message"
              type="button"
              onClick={onCopyMessage}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-xs transition cursor-pointer"
            >
              {copiedMessage ? (
                <>
                  <Check className="w-4 h-4 text-emerald-200" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Copy Message</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
