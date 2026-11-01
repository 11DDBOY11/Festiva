import React from "react";
import { AlertCircle, Plus, Sparkles } from "lucide-react";
import { useEvents } from "../hooks/useEvents";
import { EventsHeader } from "../components/events/EventsHeader";
import { EventCard } from "../components/events/EventCard";
import { CreateEventModal } from "../components/events/CreateEventModal";
import { PlanViewModal } from "../components/PlanViewModal";

export const EventsPage: React.FC = () => {
  const {
    events,
    loading,
    error,
    loadEvents,
    handleDelete,
    selectedPlan,
    setSelectedPlan,
    selectedEventId,
    setSelectedEventId,
    loadingPlanEventId,
    handleViewPlan,
    isModalOpen,
    setIsModalOpen,
    modalTab,
    setModalTab,
    createLoading,
    rawBriefText,
    setRawBriefText,
    parsingBrief,
    parseError,
    parsedResult,
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
    handleParseBrief,
    handleCreate,
    resetModalState,
    formatINR,
    nextEvent,
    daysUntilNext,
    activeEventsCount,
    getEventTypeBadge,
  } = useEvents();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      {/* Top Header & Action */}
      <EventsHeader
        events={events}
        nextEvent={nextEvent}
        daysUntilNext={daysUntilNext}
        activeEventsCount={activeEventsCount}
        formatINR={formatINR}
        onOpenCreateModal={() => {
          resetModalState();
          setIsModalOpen(true);
        }}
      />

      {/* Main Content Area */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-300 text-sm flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-rose-600 dark:text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-slate-200 dark:border-slate-800">
          <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-600 dark:text-slate-400">Loading your Mangaluru celebrations...</p>
        </div>
      ) : events.length === 0 ? (
        <div className="glass-panel rounded-2xl p-8 sm:p-12 text-center border border-dashed border-slate-300 dark:border-slate-800 max-w-lg mx-auto">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mx-auto mb-4 border border-amber-500/30">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-1">No Celebrations Yet</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
            Describe your event in plain English or enter details directly to start your plan.
          </p>
          <button
            onClick={() => {
              resetModalState();
              setIsModalOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white text-sm font-semibold transition"
          >
            <Plus className="w-4 h-4 text-amber-400" />
            <span>Create Your First Event</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {events.map((event) => (
            <EventCard
              key={event.id}
              event={event}
              loadingPlanEventId={loadingPlanEventId}
              onViewPlan={handleViewPlan}
              onDelete={handleDelete}
              formatINR={formatINR}
              getEventTypeBadge={getEventTypeBadge}
            />
          ))}
        </div>
      )}

      {/* Create Event Modal with AI Brief Parser */}
      {isModalOpen && (
        <CreateEventModal
          onClose={() => setIsModalOpen(false)}
          modalTab={modalTab}
          setModalTab={setModalTab}
          rawBriefText={rawBriefText}
          setRawBriefText={setRawBriefText}
          parsingBrief={parsingBrief}
          parseError={parseError}
          parsedResult={parsedResult}
          onParseBrief={handleParseBrief}
          newTitle={newTitle}
          setNewTitle={setNewTitle}
          newEventType={newEventType}
          setNewEventType={setNewEventType}
          newEventDate={newEventDate}
          setNewEventDate={setNewEventDate}
          newGuestCount={newGuestCount}
          setNewGuestCount={setNewGuestCount}
          newTotalBudget={newTotalBudget}
          setNewTotalBudget={setNewTotalBudget}
          createLoading={createLoading}
          onSubmit={handleCreate}
        />
      )}

      {/* Full Plan View Modal with Phase 5 Refinement & Diff Viewer */}
      {selectedPlan && (
        <PlanViewModal
          plan={selectedPlan}
          eventId={selectedEventId || undefined}
          onClose={() => {
            setSelectedPlan(null);
            setSelectedEventId(null);
          }}
          onPlanUpdated={loadEvents}
        />
      )}
    </div>
  );
};
