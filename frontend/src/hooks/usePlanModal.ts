import React, { useEffect, useRef, useState } from "react";
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

export type PlanTab = "budget" | "timeline" | "run_of_show" | "vendors" | "refine";

interface UsePlanModalProps {
  initialPlan: PlanSchema;
  eventId?: string;
  onClose: () => void;
  onPlanUpdated?: () => void;
}

export function usePlanModal({
  initialPlan,
  eventId,
  onClose,
  onPlanUpdated,
}: UsePlanModalProps) {
  const [currentPlan, setCurrentPlan] = useState<PlanSchema>(initialPlan);
  const [activeTab, setActiveTab] = useState<PlanTab>("budget");

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

  // Escape key handler for accessible modal dismissal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (draftModalData) {
          setDraftModalData(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [draftModalData, onClose]);

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
      setProposalError(err.message || "Failed to preview plan updates.");
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

  return {
    currentPlan,
    setCurrentPlan,
    activeTab,
    setActiveTab,
    versions,
    selectedVersionNum,
    versionLoading,
    handleSelectVersion,
    proposalPrompt,
    setProposalPrompt,
    proposing,
    proposalError,
    setProposalError,
    activeProposal,
    setActiveProposal,
    actionSuccessMessage,
    setActionSuccessMessage,
    applyingChange,
    handleProposeChange,
    handleAcceptChange,
    handleRejectChange,
    chatMessage,
    setChatMessage,
    chatHistory,
    streamingChat,
    handleSendChatMessage,
    exportingPdf,
    handleExportPdf,
    draftModalData,
    setDraftModalData,
    draftingCategory,
    copiedMessage,
    handleDraftVendorInquiry,
    handleCopyMessage,
    formatCurrency,
    formatDate,
    tabRefs,
  };
}
