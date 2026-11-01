import React, { useEffect, useState } from "react";
import {
  BriefParseResponse,
  createEvent,
  deleteEvent,
  EventBrief,
  EventItem,
  getEventPlan,
  listEvents,
  parseBrief,
  PlanSchema,
} from "../lib/api";
import { formatINR } from "../lib/formatters";

export function useEvents() {
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

  // Editable Form State
  const [newTitle, setNewTitle] = useState("");
  const [newEventType, setNewEventType] = useState<"wedding" | "birthday" | "community">("wedding");
  const [newEventDate, setNewEventDate] = useState("");
  const [newGuestCount, setNewGuestCount] = useState<string>("150");
  const [newTotalBudget, setNewTotalBudget] = useState<string>("500000");

  // Plan View State
  const [selectedPlan, setSelectedPlan] = useState<PlanSchema | null>(null);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [loadingPlanEventId, setLoadingPlanEventId] = useState<string | null>(null);

  const handleViewPlan = async (eventId: string) => {
    try {
      setLoadingPlanEventId(eventId);
      setSelectedEventId(eventId);
      const res = await getEventPlan(eventId);
      setSelectedPlan(res.plan);
    } catch (err: any) {
      setError(err.message || "Failed to load event plan");
    } finally {
      setLoadingPlanEventId(null);
    }
  };

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listEvents();
      setEvents(data);
      return data;
    } catch (err: any) {
      setError(err.message || "Failed to load events");
      return [];
    } finally {
      setLoading(false);
    }
  };

  // Escape key handler for accessible modal dismissal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isModalOpen) {
        setIsModalOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isModalOpen]);

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await listEvents();
        setEvents(data);

        // Auto-open demo event if triggered from landing page
        if (sessionStorage.getItem("festiva_auto_open_demo") === "true") {
          sessionStorage.removeItem("festiva_auto_open_demo");
          let birthdayEvent = data.find(
            (e) => e.event_type === "birthday" || e.title.toLowerCase().includes("birthday")
          );
          if (!birthdayEvent) {
            try {
              birthdayEvent = await createEvent({
                title: "21st Birthday Party - Mangaluru Coastal Celebration",
                event_type: "birthday",
                event_date: "2026-11-20",
                guest_count: 80,
                total_budget: 75000,
                city: "Mangaluru",
              });
              const refreshed = await listEvents();
              setEvents(refreshed);
            } catch (createErr) {
              console.error("Failed to auto-create demo event:", createErr);
            }
          }
          if (birthdayEvent) {
            handleViewPlan(birthdayEvent.id);
          }
        } else if (sessionStorage.getItem("festiva_auto_open_create") === "true") {
          sessionStorage.removeItem("festiva_auto_open_create");
          setIsModalOpen(true);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load events");
      } finally {
        setLoading(false);
      }
    };

    init();
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

  const handleDelete = async (id: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"?`)) return;
    try {
      await deleteEvent(id);
      setEvents((prev) => prev.filter((e) => e.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete event");
    }
  };


  // Next Upcoming Event calculation
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const upcomingEvents = events
    .filter((e) => e.event_date && new Date(e.event_date) >= today)
    .sort((a, b) => new Date(a.event_date!).getTime() - new Date(b.event_date!).getTime());

  const nextEvent = upcomingEvents.length > 0 ? upcomingEvents[0] : null;
  const daysUntilNext = nextEvent
    ? Math.max(
        0,
        Math.ceil(
          (new Date(nextEvent.event_date!).getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
        )
      )
    : null;

  const activeEventsCount = events.filter((e) => e.status !== "draft").length;

  const getEventTypeBadge = (type: string) => {
    switch (type) {
      case "wedding":
        return "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-500/10 dark:text-rose-300 dark:border-rose-500/20";
      case "birthday":
        return "bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/20";
      case "community":
        return "bg-blue-100 text-blue-900 border-blue-300 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/20";
      default:
        return "bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-500/10 dark:text-slate-300 dark:border-slate-500/20";
    }
  };

  return {
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
  };
}
