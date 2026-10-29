import React, { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  DollarSign,
  Download,
  ExternalLink,
  HelpCircle,
  History,
  Loader2,
  Mail,
  MapPin,
  Send,
  Sliders,
  Sparkles,
  Store,
  Utensils,
  X,
  XCircle,
} from "lucide-react";
import {
  acceptPlanChange,
  draftVendorMessage,
  exportPlanPdf,
  getEventPlan,
  getPlanVersions,
  PlanSchema,
  PlanVersionSummary,
  proposePlanChange,
  ProposedChangeResponse,
  rejectPlanChange,
  streamPlanChat,
  VendorInquiryDraft,
} from "../lib/api";
import { formatCategoryLabel } from "../lib/constants";

interface PlanViewModalProps {
  plan: PlanSchema;
  eventId?: string;
  onClose: () => void;
  onPlanUpdated?: () => void;
}

export const PlanViewModal: React.FC<PlanViewModalProps> = ({
  plan: initialPlan,
  eventId,
  onClose,
  onPlanUpdated,
}) => {
  const [currentPlan, setCurrentPlan] = useState<PlanSchema>(initialPlan);
  const [activeTab, setActiveTab] = useState<
    "budget" | "timeline" | "run_of_show" | "vendors" | "refine"
  >("budget");

  // Versioning state
  const [versions, setVersions] = useState<PlanVersionSummary[]>([]);
  const [selectedVersionNum, setSelectedVersionNum] = useState<number>(initialPlan.version);
  const [versionLoading, setVersionLoading] = useState(false);

  // Proposal & Diff state
  const [proposalPrompt, setProposalPrompt] = useState("");
  const [proposing, setProposing] = useState(false);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const [activeProposal, setActiveProposal] = useState<ProposedChangeResponse | null>(null);
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);
  const [applyingChange, setApplyingChange] = useState(false);

  // Streaming Chat state
  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState<Array<{ role: "user" | "assistant"; text: string }>>([
    {
      role: "assistant",
      text: "Namaskara! I am your Festiva Copilot. You can ask me to adjust budget allocations (e.g. 'reduce décor by ₹10,000'), suggest Mangalorean menus, or refine timeline milestones.",
    },
  ]);
  const [streamingChat, setStreamingChat] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  const handleExportPdf = async () => {
    if (!eventId) return;
    setExportingPdf(true);
    try {
      const blob = await exportPlanPdf(eventId, currentPlan.version);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Festiva_Plan_${eventId}_v${currentPlan.version}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(err.message || "Failed to download plan PDF");
    } finally {
      setExportingPdf(false);
    }
  };

  // Vendor inquiry drafting state
  const [draftModalData, setDraftModalData] = useState<VendorInquiryDraft | null>(null);
  const [draftingCategory, setDraftingCategory] = useState<string | null>(null);
  const [copiedMessage, setCopiedMessage] = useState(false);

  const handleDraftVendorInquiry = async (category: string, vendorName?: string) => {
    if (!eventId) return;
    setDraftingCategory(category);
    try {
      const res = await draftVendorMessage(eventId, {
        vendor_category: category,
        vendor_name: vendorName,
      });
      setDraftModalData(res);
      setCopiedMessage(false);
    } catch (err: any) {
      alert(err.message || "Failed to draft vendor message");
    } finally {
      setDraftingCategory(null);
    }
  };

  const handleCopyMessage = () => {
    if (!draftModalData) return;
    navigator.clipboard.writeText(draftModalData.full_message);
    setCopiedMessage(true);
    setTimeout(() => setCopiedMessage(false), 2500);
  };

  // Prevent page behind modal from scrolling while modal is open
  useEffect(() => {
    const originalStyle = window.getComputedStyle(document.body).overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = originalStyle;
    };
  }, []);

  // Scroll active tab button smoothly into view on mobile / narrow viewports
  const tabRefs = useRef<{ [key: string]: HTMLButtonElement | null }>({});
  useEffect(() => {
    if (tabRefs.current[activeTab]) {
      tabRefs.current[activeTab]?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "center",
      });
    }
  }, [activeTab]);

  // Load versions list
  useEffect(() => {
    if (!eventId) return;
    getPlanVersions(eventId)
      .then((data) => setVersions(data))
      .catch((err) => console.error("Failed to load versions:", err));
  }, [eventId, currentPlan.version]);

  const handleSelectVersion = async (vNum: number) => {
    if (!eventId || vNum === currentPlan.version) return;
    setVersionLoading(true);
    try {
      const res = await getEventPlan(eventId, vNum);
      setCurrentPlan(res.plan);
      setSelectedVersionNum(vNum);
    } catch (err: any) {
      alert(err.message || "Failed to switch plan version");
    } finally {
      setVersionLoading(false);
    }
  };

  const handleProposeChange = async (customPrompt?: string) => {
    if (!eventId) return;
    const promptToUse = (customPrompt || proposalPrompt).trim();
    if (!promptToUse) return;

    setProposing(true);
    setProposalError(null);
    setActionSuccessMessage(null);

    try {
      const res = await proposePlanChange(eventId, promptToUse, currentPlan.version);
      setActiveProposal(res);
      setProposalPrompt("");
      setActiveTab("refine");
    } catch (err: any) {
      setProposalError(err.message || "Failed to compute modification diff.");
    } finally {
      setProposing(false);
    }
  };

  const handleAcceptChange = async () => {
    if (!eventId || !activeProposal) return;
    setApplyingChange(true);
    setProposalError(null);

    try {
      const updatedVersion = await acceptPlanChange(
        eventId,
        activeProposal.id,
        currentPlan.version
      );
      setCurrentPlan(updatedVersion.plan);
      setSelectedVersionNum(updatedVersion.version);
      setActionSuccessMessage(
        `Successfully applied change and generated Plan v${updatedVersion.version}!`
      );
      setActiveProposal(null);
      if (onPlanUpdated) onPlanUpdated();
    } catch (err: any) {
      setProposalError(err.message || "Failed to apply proposed change.");
    } finally {
      setApplyingChange(false);
    }
  };

  const handleRejectChange = async () => {
    if (!eventId || !activeProposal) return;
    try {
      await rejectPlanChange(eventId, activeProposal.id);
      setActiveProposal(null);
      setActionSuccessMessage("Proposed changes were discarded. Plan remains unchanged.");
    } catch (err: any) {
      setProposalError(err.message || "Failed to reject change.");
    }
  };

  const handleSendChatMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventId || !chatMessage.trim() || streamingChat) return;

    const userText = chatMessage.trim();
    setChatMessage("");
    setChatHistory((prev) => [...prev, { role: "user", text: userText }]);

    // Append placeholder for assistant response
    setChatHistory((prev) => [...prev, { role: "assistant", text: "" }]);
    setStreamingChat(true);

    streamPlanChat(
      eventId,
      userText,
      (chunk) => {
        setChatHistory((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
            updated[lastIdx] = {
              ...updated[lastIdx],
              text: updated[lastIdx].text + chunk,
            };
          }
          return updated;
        });
      },
      () => {
        setStreamingChat(false);
      },
      (err) => {
        console.error("Stream error:", err);
        setStreamingChat(false);
      }
    );
  };

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
  // Determine display name using vendor sample flag instead of regex
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
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Event Plan Modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-5xl h-[90dvh] max-h-[90dvh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        {/* Fixed Compact Header */}
        <div className="shrink-0 px-4 py-3 sm:px-6 sm:py-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/95">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-1">
                {/* Version Selector Pill */}
                {versions.length > 1 ? (
                  <div className="flex items-center gap-1 bg-amber-500/10 border border-amber-500/30 rounded-full px-2.5 py-0.5 text-xs font-semibold text-amber-700 dark:text-amber-300">
                    <History className="w-3.5 h-3.5" />
                    <span>Plan:</span>
                    <select
                      value={selectedVersionNum}
                      onChange={(e) => handleSelectVersion(Number(e.target.value))}
                      className="bg-transparent text-amber-700 dark:text-amber-300 font-bold focus:outline-none cursor-pointer"
                    >
                      {versions.map((v) => (
                        <option key={v.version} value={v.version} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                          v{v.version} {v.version === currentPlan.version ? "(Current)" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                    Plan v{currentPlan.version}
                  </span>
                )}

                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700">
                  {currentPlan.event_type}
                </span>
                {currentPlan.guest_count && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-200/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300">
                    {currentPlan.guest_count} guests
                  </span>
                )}
                {currentPlan.event_date && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-200/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300">
                    {formatDate(currentPlan.event_date)}
                  </span>
                )}
              </div>
              <h2 className="text-lg sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white truncate flex items-center gap-2">
                <span className="truncate">{currentPlan.title}</span>
                {versionLoading && <Loader2 className="w-4 h-4 animate-spin text-amber-600 shrink-0" />}
              </h2>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                id="btn-header-export-pdf"
                type="button"
                onClick={handleExportPdf}
                disabled={exportingPdf}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 transition shadow-2xs cursor-pointer disabled:opacity-50"
                title="Export this plan as a printable PDF"
              >
                {exportingPdf ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-600" />
                ) : (
                  <Download className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                )}
                <span className="hidden sm:inline">Export PDF</span>
                <span className="sm:hidden">PDF</span>
              </button>
              <button
                id="btn-header-suggest-changes"
                type="button"
                onClick={() => {
                  setActiveTab("refine");
                  setTimeout(() => {
                    document.getElementById("input-propose-prompt")?.focus();
                  }, 100);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-500/15 hover:bg-amber-500/25 text-amber-900 dark:text-amber-200 border border-amber-400/60 dark:border-amber-700 transition shadow-2xs cursor-pointer"
                title="Suggest changes or modifications to AI"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                <span className="hidden sm:inline">Suggestions / Changes</span>
                <span className="sm:hidden">Suggest</span>
              </button>
              <button
                id="btn-close-modal-x"
                onClick={onClose}
                aria-label="Close modal"
                className="p-2 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-200/80 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* ONE Scrollable Body in between Header and Footer */}
        <div
          id="plan-modal-scrollable-body"
          className="flex-1 min-h-0 overflow-y-auto bg-slate-50/60 dark:bg-slate-950/50"
        >
          {/* Top Overview Section: Metrics, Venue Card, Summary, Advisory & Curated Menu */}
          <div className="p-4 sm:p-6 space-y-4">
            {/* Top Metric Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total Budget</span>
                <div className="text-lg sm:text-xl font-bold text-amber-600 dark:text-amber-400 mt-0.5">
                  {formatCurrency(currentPlan.total_budget)}
                </div>
              </div>
              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Budget Breakdown</span>
                <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                  {currentPlan.budget?.categories?.length || 0} Categories
                </div>
              </div>
              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Milestones</span>
                <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                  {currentPlan.timeline?.length || 0} Tasks
                </div>
              </div>
              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Plan Iterations</span>
                <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                  Version {currentPlan.version} of {Math.max(versions.length, currentPlan.version)}
                </div>
              </div>
            </div>

            {/* Dedicated Venue & Location Showcase Card (Single Instance) */}
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
                  onClick={() => {
                    setActiveTab("refine");
                    setProposalPrompt("Change venue to an outdoor lawn or beachside hall in Mangaluru");
                    setTimeout(() => {
                      document.getElementById("input-propose-prompt")?.focus();
                    }, 100);
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-xs transition cursor-pointer"
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
                  <span className="font-bold block text-xs sm:text-sm text-amber-900 dark:text-amber-200">Compressed Timeline Advisory</span>
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

          {/* Sticky Tab Bar inside the scrollable container */}
          <div className="sticky top-0 z-20 px-3 sm:px-6 py-2.5 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-y-2 border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="flex items-center gap-2 p-1.5 rounded-2xl bg-slate-100 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 overflow-x-auto no-scrollbar">
              <button
                id="tab-btn-budget"
                ref={(el) => {
                  tabRefs.current["budget"] = el;
                }}
                onClick={() => setActiveTab("budget")}
                className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
                  activeTab === "budget"
                    ? "bg-amber-600 text-white shadow-md shadow-amber-600/30 scale-[1.02] border border-amber-500"
                    : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
                }`}
              >
                <DollarSign className="w-4 h-4" />
                <span>Budget Table</span>
              </button>

              <button
                id="tab-btn-timeline"
                ref={(el) => {
                  tabRefs.current["timeline"] = el;
                }}
                onClick={() => setActiveTab("timeline")}
                className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
                  activeTab === "timeline"
                    ? "bg-amber-600 text-white shadow-md shadow-amber-600/30 scale-[1.02] border border-amber-500"
                    : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
                }`}
              >
                <Calendar className="w-4 h-4" />
                <span>Timeline & Tasks</span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    activeTab === "timeline"
                      ? "bg-white/25 text-white"
                      : "bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200"
                  }`}
                >
                  {currentPlan.timeline?.length || 0}
                </span>
              </button>

              <button
                id="tab-btn-run-of-show"
                ref={(el) => {
                  tabRefs.current["run_of_show"] = el;
                }}
                onClick={() => setActiveTab("run_of_show")}
                className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
                  activeTab === "run_of_show"
                    ? "bg-amber-600 text-white shadow-md shadow-amber-600/30 scale-[1.02] border border-amber-500"
                    : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
                }`}
              >
                <Clock className="w-4 h-4" />
                <span>Run-of-Show</span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    activeTab === "run_of_show"
                      ? "bg-white/25 text-white"
                      : "bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200"
                  }`}
                >
                  {currentPlan.run_of_show?.length || 0}
                </span>
              </button>

              <button
                id="tab-btn-vendors"
                ref={(el) => {
                  tabRefs.current["vendors"] = el;
                }}
                onClick={() => setActiveTab("vendors")}
                className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
                  activeTab === "vendors"
                    ? "bg-amber-600 text-white shadow-md shadow-amber-600/30 scale-[1.02] border border-amber-500"
                    : "text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-white/80 dark:hover:bg-slate-800/80 border border-transparent"
                }`}
              >
                <Store className="w-4 h-4" />
                <span>Vendors & Checklist</span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    activeTab === "vendors"
                      ? "bg-white/25 text-white"
                      : "bg-slate-300 dark:bg-slate-700 text-slate-800 dark:text-slate-200"
                  }`}
                >
                  {currentPlan.vendor_shortlist?.length || 0}
                </span>
              </button>

              <button
                id="tab-btn-refine"
                ref={(el) => {
                  tabRefs.current["refine"] = el;
                }}
                onClick={() => setActiveTab("refine")}
                className={`flex items-center gap-2 py-2 px-3.5 text-xs sm:text-sm font-bold rounded-xl transition-all whitespace-nowrap shrink-0 cursor-pointer ${
                  activeTab === "refine"
                    ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30 scale-[1.02] border border-emerald-500"
                    : "bg-amber-500/15 text-amber-900 dark:text-amber-200 hover:bg-amber-500/25 border border-amber-400/60 dark:border-amber-700"
                }`}
              >
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span>Suggestions / Changes</span>
                {activeProposal && (
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                )}
              </button>
            </div>
          </div>

          {/* Tab Content Panels (with pb-16 to ensure bottom-most item scrolls fully into view) */}
          <div className="p-4 sm:p-6 pb-16 space-y-4">
          {/* TAB 1: BUDGET TABLE */}
          {activeTab === "budget" && (
            <div className="space-y-4">
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
                <table className="w-full text-left text-xs sm:text-sm">
                  <thead className="bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-200 border-b border-slate-200 dark:border-slate-700 font-bold uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-3 sm:px-4 font-bold">Category</th>
                      <th className="py-3 px-3 sm:px-4 font-bold text-right">Share (%)</th>
                      <th className="py-3 px-3 sm:px-4 font-bold text-right">Allocated Amount</th>
                      <th className="py-3 px-3 sm:px-4 font-bold text-right hidden sm:table-cell">
                        Per Guest
                      </th>
                      <th className="py-3 px-3 sm:px-4 font-bold hidden md:table-cell">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {currentPlan.budget?.categories?.map((cat, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                        <td className="py-3 px-3 sm:px-4 font-bold text-slate-900 dark:text-white">
                          {formatCategoryLabel(cat.category)}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-right font-mono text-slate-600 dark:text-slate-300 font-medium">
                          {Number(cat.share_pct).toFixed(1)}%
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-right font-bold text-slate-900 dark:text-white text-sm">
                          {formatCurrency(Number(cat.allocated_amount))}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-right font-mono text-slate-600 dark:text-slate-300 hidden sm:table-cell">
                          {cat.per_guest_cost ? formatCurrency(Number(cat.per_guest_cost)) : "—"}
                        </td>
                        <td className="py-3 px-3 sm:px-4 text-xs text-slate-600 dark:text-slate-400 hidden md:table-cell">
                          {cat.notes || "Standard tier allocation"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-100/90 dark:bg-slate-800/90 font-bold border-t-2 border-slate-200 dark:border-slate-700">
                    <tr>
                      <td className="py-3.5 px-3 sm:px-4 text-slate-900 dark:text-white">Total Budget</td>
                      <td className="py-3.5 px-3 sm:px-4 text-right text-slate-700 dark:text-slate-300">100.0%</td>
                      <td className="py-3.5 px-3 sm:px-4 text-right text-amber-600 dark:text-amber-400 text-base font-bold">
                        {formatCurrency(currentPlan.total_budget)}
                      </td>
                      <td className="py-3.5 px-3 sm:px-4 text-right text-slate-700 dark:text-slate-300 hidden sm:table-cell font-mono">
                        {currentPlan.guest_count && currentPlan.total_budget
                          ? formatCurrency(currentPlan.total_budget / currentPlan.guest_count)
                          : "—"}
                      </td>
                      <td className="py-3.5 px-3 sm:px-4 text-xs text-slate-500 dark:text-slate-400 hidden md:table-cell font-normal">
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
              {currentPlan.timeline?.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start justify-between gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs hover:border-amber-400/60 transition-colors"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700">
                        {item.phase}
                      </span>
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                        {formatCategoryLabel(item.category)}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                          item.priority === "high"
                            ? "bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800"
                            : "bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-800"
                        }`}
                      >
                        {item.priority}
                      </span>
                    </div>
                    <p className="text-sm sm:text-base font-bold text-slate-900 dark:text-white leading-snug">{item.task}</p>
                    <p className="text-xs font-medium text-slate-600 dark:text-slate-400">Owner: {item.owner}</p>
                  </div>

                  <div className="text-right flex-shrink-0 pt-0.5">
                    <span className="text-xs font-bold text-amber-600 dark:text-amber-400 block font-mono">
                      {item.target_date ? formatDate(item.target_date) : "TBD"}
                    </span>
                    <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                      T{item.days_before_event < 0 ? item.days_before_event : `-${item.days_before_event}`}d
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: RUN OF SHOW */}
          {activeTab === "run_of_show" && (
            <div className="space-y-3">
              {currentPlan.run_of_show?.map((slot, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-4 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs hover:border-amber-400/60 transition-colors"
                >
                  <div className="w-28 flex-shrink-0 text-left">
                    <span className="text-xs font-mono font-bold text-amber-600 dark:text-amber-400 block">
                      {slot.time_slot}
                    </span>
                    <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">{slot.location}</span>
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-sm text-slate-900 dark:text-white">{slot.activity}</h4>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                        {slot.lead_person}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal">{slot.notes}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: VENDORS & CHECKLIST */}
          {activeTab === "vendors" && (
            <div className="space-y-6">
              {/* Grounded Vendor Directory Recommendations */}
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5 mb-3">
                  <Store className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  Grounded Mangaluru Vendor Shortlist
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {currentPlan.vendor_shortlist?.map((v, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-2 shadow-xs hover:border-amber-400/60 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 block">
                            {formatCategoryLabel(v.category)}
                          </span>
                          <h4 className="font-bold text-sm text-slate-900 dark:text-white">{v.vendor_name}</h4>
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
                          onClick={() => handleDraftVendorInquiry(v.category, v.vendor_name)}
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
                  ))}
                </div>
              </div>

              {/* Vendor Category Questions Checklist */}
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5 mb-3">
                  <HelpCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  Vendor Category Checklist & Negotiation Questions
                </h3>
                <div className="space-y-3">
                  {currentPlan.checklist?.map((chk, idx) => (
                    <div key={idx} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-2">
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
                            onClick={() => handleDraftVendorInquiry(chk.category)}
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
              </div>
            </div>
          )}

          {/* TAB 5: PHASE 5 REFINE & DIFF VIEWER */}
          {activeTab === "refine" && (
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
                <div className="p-5 rounded-2xl border-2 border-amber-500 bg-amber-50/70 dark:bg-amber-950/40 space-y-4 shadow-xl">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200 dark:border-amber-800/80 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-200 dark:bg-amber-900/80 text-amber-950 dark:text-amber-100 border border-amber-400 dark:border-amber-700">
                        Proposed Change (Pending Review)
                      </span>
                      <span className="text-xs text-slate-700 dark:text-slate-300 font-bold font-mono">
                        Base: v{activeProposal.base_version} → Target: v{activeProposal.base_version + 1}
                      </span>
                    </div>

                    {/* Net Budget Impact Pill */}
                    <div
                      className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
                        activeProposal.budget_impact < 0
                          ? "bg-emerald-200 dark:bg-emerald-900/70 text-emerald-950 dark:text-emerald-100 border border-emerald-400 dark:border-emerald-700"
                          : activeProposal.budget_impact > 0
                          ? "bg-rose-200 dark:bg-rose-900/70 text-rose-950 dark:text-rose-100 border border-rose-400 dark:border-rose-700"
                          : "bg-blue-200 dark:bg-blue-900/70 text-blue-950 dark:text-blue-100 border border-blue-400 dark:border-blue-700"
                      }`}
                    >
                      <span>
                        Net Impact: {activeProposal.budget_impact < 0 ? "−" : "+"}
                        {formatCurrency(Math.abs(activeProposal.budget_impact))}
                        {activeProposal.budget_impact < 0 ? " (Savings)" : " (Increase)"}
                      </span>
                    </div>
                  </div>

                  {/* Summary */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
                      Change Summary
                    </h4>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white bg-white dark:bg-slate-900 p-3.5 rounded-xl border border-amber-300 dark:border-amber-800 shadow-xs">
                      {activeProposal.diff.summary}
                    </p>
                  </div>

                  {/* Structured Delta Table */}
                  {activeProposal.diff.category_changes.length > 0 && (
                    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
                      <table className="w-full text-left text-xs sm:text-sm">
                        <thead className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-bold border-b border-slate-200 dark:border-slate-700">
                          <tr>
                            <th className="py-2.5 px-3 font-bold">Category</th>
                            <th className="py-2.5 px-3 font-bold text-right">Current Allocation</th>
                            <th className="py-2.5 px-3 font-bold text-center"></th>
                            <th className="py-2.5 px-3 font-bold text-right">Proposed Allocation</th>
                            <th className="py-2.5 px-3 font-bold text-right">Net Change</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                          {activeProposal.diff.category_changes.map((delta, idx) => (
                            <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                              <td className="py-3 px-3 font-bold text-slate-900 dark:text-white">
                                {formatCategoryLabel(delta.category)}
                              </td>
                              <td className="py-3 px-3 text-right font-mono text-slate-600 dark:text-slate-400 line-through">
                                {formatCurrency(delta.old_amount)}
                              </td>
                              <td className="py-3 px-3 text-center text-slate-400">
                                <ArrowRight className="w-3.5 h-3.5 mx-auto text-slate-400" />
                              </td>
                              <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                                {formatCurrency(delta.new_amount)}
                              </td>
                              <td className="py-3 px-3 text-right font-mono font-bold">
                                <span
                                  className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold ${
                                    delta.delta < 0
                                      ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800"
                                      : "bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800"
                                  }`}
                                >
                                  {delta.delta < 0 ? "−" : "+"}
                                  {formatCurrency(Math.abs(delta.delta))}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot className="bg-slate-100 dark:bg-slate-800/90 font-bold border-t-2 border-slate-200 dark:border-slate-700">
                          <tr>
                            <td className="py-3 px-3 text-slate-900 dark:text-white">Total Event Budget</td>
                            <td className="py-3 px-3 text-right text-slate-600 dark:text-slate-400 line-through font-mono">
                              {formatCurrency(activeProposal.diff.old_total_budget)}
                            </td>
                            <td className="py-3 px-3 text-center text-slate-400">
                              <ArrowRight className="w-3.5 h-3.5 mx-auto text-slate-400" />
                            </td>
                            <td className="py-3 px-3 text-right text-amber-600 dark:text-amber-400 font-mono font-bold text-sm">
                              {formatCurrency(activeProposal.diff.new_total_budget)}
                            </td>
                            <td className="py-3 px-3 text-right text-amber-600 dark:text-amber-400 font-mono font-bold">
                              {activeProposal.diff.budget_impact < 0 ? "−" : "+"}
                              {formatCurrency(Math.abs(activeProposal.diff.budget_impact))}
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  )}

                  {/* Accept / Reject Action Bar */}
                  <div className="pt-2 flex items-center justify-end gap-3">
                    <button
                      id="btn-reject-change"
                      type="button"
                      onClick={handleRejectChange}
                      disabled={applyingChange}
                      className="px-4 py-2.5 rounded-xl text-xs sm:text-sm font-bold border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-slate-800 transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <X className="w-4 h-4" />
                      Discard Proposal
                    </button>
                    <button
                      id="btn-accept-change"
                      type="button"
                      onClick={handleAcceptChange}
                      disabled={applyingChange}
                      className="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/30 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 transition"
                    >
                      {applyingChange ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Applying & Creating Version...</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4" />
                          <span>Accept Changes (Creates Plan v{activeProposal.base_version + 1})</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
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
                  State desired adjustments in plain language. Festiva's deterministic diff engine computes
                  the exact budget impacts and generates a structured proposal for your approval.
                </p>

                {/* Suggestion Chips */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">Try asking:</span>
                  <button
                    id="btn-suggest-reduce-decor"
                    type="button"
                    onClick={() => handleProposeChange("reduce décor by ₹10,000")}
                    disabled={proposing}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-amber-100 dark:bg-slate-800 dark:hover:bg-amber-950/60 text-slate-800 dark:text-slate-200 hover:text-amber-900 dark:hover:text-amber-200 transition border border-slate-200 dark:border-slate-700 cursor-pointer"
                  >
                    "reduce décor by ₹10,000"
                  </button>
                  <button
                    type="button"
                    onClick={() => handleProposeChange("add ₹15,000 to catering")}
                    disabled={proposing}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-amber-100 dark:bg-slate-800 dark:hover:bg-amber-950/60 text-slate-800 dark:text-slate-200 hover:text-amber-900 dark:hover:text-amber-200 transition border border-slate-200 dark:border-slate-700 cursor-pointer"
                  >
                    "add ₹15,000 to catering"
                  </button>
                  <button
                    type="button"
                    onClick={() => handleProposeChange("cut photography by 5k")}
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
                        handleProposeChange();
                      }
                    }}
                    placeholder="e.g. 'reduce décor by ₹10,000' or 'trim venue by 20000'"
                    className="flex-1 px-4 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/40"
                  />
                  <button
                    id="btn-propose-change"
                    type="button"
                    onClick={() => handleProposeChange()}
                    disabled={proposing || !proposalPrompt.trim()}
                    className="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-sm disabled:opacity-50 transition flex items-center gap-1.5 cursor-pointer"
                  >
                    {proposing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Calculating Diff...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        <span>Propose Change</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Streaming AI Copilot Chat */}
              <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3 shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      Copilot Conversational Assistant
                    </h3>
                  </div>
                  <span className="text-[11px] text-slate-600 dark:text-slate-400 font-mono font-bold">
                    Plan Context: v{currentPlan.version}
                  </span>
                </div>

                {/* Message Scroll Area */}
                <div className="h-48 overflow-y-auto rounded-xl bg-slate-50 dark:bg-slate-950/60 p-3 space-y-2.5 text-xs sm:text-sm border border-slate-200 dark:border-slate-800">
                  {chatHistory.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex flex-col ${
                        msg.role === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      <div
                        className={`max-w-[85%] rounded-xl px-4 py-2.5 ${
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
                <form onSubmit={handleSendChatMessage} className="flex gap-2 pt-1 shrink-0">
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
          )}
          </div>
        </div>

        {/* Modal Fixed Footer */}
        <div className="shrink-0 p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">
            <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="hidden sm:inline">Deterministic budget & timeline • Grounded in Mangaluru dataset</span>
            <span className="sm:hidden text-[11px]">Deterministic Mangaluru plan</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              id="btn-footer-export-pdf"
              type="button"
              onClick={handleExportPdf}
              disabled={exportingPdf}
              className="px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 transition shadow-xs cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
            >
              {exportingPdf ? (
                <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
              ) : (
                <Download className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              )}
              <span>Export PDF</span>
            </button>
            <button
              id="btn-close-plan"
              onClick={onClose}
              className="px-5 py-2 rounded-xl text-xs sm:text-sm font-bold bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 transition shadow-xs cursor-pointer"
            >
              Close Plan
            </button>
          </div>
        </div>

        {/* Vendor Inquiry Draft Modal Dialog */}
        {draftModalData && (
          <div className="fixed inset-0 z-60 flex items-center justify-center p-3 sm:p-6 bg-slate-950/75 backdrop-blur-xs animate-in fade-in">
            <div className="w-full max-w-2xl max-h-[85dvh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border-2 border-amber-400 dark:border-amber-600 shadow-2xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-amber-500/10">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-amber-500 text-white flex items-center justify-center">
                    <Mail className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white leading-tight">
                      Draft Vendor Inquiry: {formatCategoryLabel(draftModalData.vendor_category)}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Grounded communication asking for quotes & date availability
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setDraftModalData(null)}
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
                    ? "Generated via deterministic fallback template"
                    : "Generated via Festiva Copilot"}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    id="btn-copy-draft-message"
                    type="button"
                    onClick={handleCopyMessage}
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
                    onClick={() => setDraftModalData(null)}
                    className="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
