import React from "react";
import { PlanSchema } from "../lib/api";
import { usePlanModal } from "../hooks/usePlanModal";
import { PlanModalHeader } from "./plan/PlanModalHeader";
import { PlanVenueCard } from "./plan/PlanVenueCard";
import { PlanTabNav } from "./plan/PlanTabNav";
import { BudgetTabPanel } from "./plan/BudgetTabPanel";
import { TimelineTabPanel } from "./plan/TimelineTabPanel";
import { RunOfShowTabPanel } from "./plan/RunOfShowTabPanel";
import { VendorsTabPanel } from "./plan/VendorsTabPanel";
import { RefineTabPanel } from "./plan/RefineTabPanel";
import { PlanModalFooter } from "./plan/PlanModalFooter";
import { DraftMessageDialog } from "./plan/DraftMessageDialog";

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
  const {
    currentPlan,
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
    activeProposal,
    actionSuccessMessage,
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
  } = usePlanModal({
    initialPlan,
    eventId,
    onClose,
    onPlanUpdated,
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Event Plan Modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-5xl h-[90dvh] max-h-[90dvh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        {/* Fixed Compact Header */}
        <PlanModalHeader
          currentPlan={currentPlan}
          versions={versions}
          selectedVersionNum={selectedVersionNum}
          versionLoading={versionLoading}
          exportingPdf={exportingPdf}
          onSelectVersion={handleSelectVersion}
          onExportPdf={handleExportPdf}
          onSuggestChanges={() => {
            setActiveTab("refine");
            setTimeout(() => {
              document.getElementById("input-propose-prompt")?.focus();
            }, 100);
          }}
          onClose={onClose}
          formatDate={formatDate}
        />

        {/* ONE Scrollable Body in between Header and Footer */}
        <div
          id="plan-modal-scrollable-body"
          className="flex-1 min-h-0 overflow-y-auto bg-slate-50/60 dark:bg-slate-950/50"
        >
          {/* Top Overview Section: Metrics, Venue Card, Summary, Advisory & Curated Menu */}
          <div className="p-4 sm:p-6 space-y-4">
            <PlanVenueCard
              currentPlan={currentPlan}
              formatCurrency={formatCurrency}
              onChangeVenue={() => {
                setActiveTab("refine");
                setProposalPrompt("Change venue to an outdoor lawn or beachside hall in Mangaluru");
                setTimeout(() => {
                  document.getElementById("input-propose-prompt")?.focus();
                }, 100);
              }}
            />
          </div>

          {/* Sticky Tab Bar inside the scrollable container */}
          <PlanTabNav
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            currentPlan={currentPlan}
            hasActiveProposal={Boolean(activeProposal)}
            tabRefs={tabRefs}
          />

          {/* Tab Content Panels (with pb-16 to ensure bottom-most item scrolls fully into view) */}
          <div className="p-4 sm:p-6 pb-16 space-y-4">
            {activeTab === "budget" && (
              <BudgetTabPanel currentPlan={currentPlan} formatCurrency={formatCurrency} />
            )}

            {activeTab === "timeline" && (
              <TimelineTabPanel currentPlan={currentPlan} formatDate={formatDate} />
            )}

            {activeTab === "run_of_show" && (
              <RunOfShowTabPanel currentPlan={currentPlan} />
            )}

            {activeTab === "vendors" && (
              <VendorsTabPanel
                currentPlan={currentPlan}
                formatCurrency={formatCurrency}
                draftingCategory={draftingCategory}
                onDraftVendorInquiry={handleDraftVendorInquiry}
              />
            )}

            {activeTab === "refine" && (
              <RefineTabPanel
                actionSuccessMessage={actionSuccessMessage}
                proposalError={proposalError}
                activeProposal={activeProposal}
                applyingChange={applyingChange}
                onAcceptChange={handleAcceptChange}
                onRejectChange={handleRejectChange}
                formatCurrency={formatCurrency}
                proposalPrompt={proposalPrompt}
                setProposalPrompt={setProposalPrompt}
                proposing={proposing}
                onProposeChange={handleProposeChange}
                chatHistory={chatHistory}
                chatMessage={chatMessage}
                setChatMessage={setChatMessage}
                streamingChat={streamingChat}
                onSendChatMessage={handleSendChatMessage}
              />
            )}
          </div>
        </div>

        {/* Modal Fixed Footer */}
        <PlanModalFooter
          exportingPdf={exportingPdf}
          onExportPdf={handleExportPdf}
          onClose={onClose}
        />

        {/* Vendor Inquiry Draft Modal Dialog */}
        {draftModalData && (
          <DraftMessageDialog
            draftModalData={draftModalData}
            copiedMessage={copiedMessage}
            onCopyMessage={handleCopyMessage}
            onClose={() => setDraftModalData(null)}
          />
        )}
      </div>
    </div>
  );
};
