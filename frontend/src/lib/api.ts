/**
 * API client with automatic token rotation, silent refresh, and session expiration handling.
 */

const BASE_URL = "/api";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface EventItem {
  id: string;
  owner_id: string;
  title: string;
  event_type: "wedding" | "birthday" | "community";
  event_date: string | null;
  city: string | null;
  guest_count: number | null;
  total_budget: number | null;
  currency: string;
  current_version: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

// In-memory + LocalStorage tokens
let accessToken: string | null = localStorage.getItem("festiva_access_token");
let refreshToken: string | null = localStorage.getItem("festiva_refresh_token");
let refreshPromise: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem("festiva_access_token", access);
  localStorage.setItem("festiva_refresh_token", refresh);
  window.dispatchEvent(new Event("festiva_auth_change"));
}

export function clearTokens(): void {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem("festiva_access_token");
  localStorage.removeItem("festiva_refresh_token");
  window.dispatchEvent(new Event("festiva_auth_change"));
}

/**
 * Perform silent token refresh with rotation.
 * Concurrent requests share the same in-flight refresh promise.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshToken) {
    clearTokens();
    return null;
  }

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) {
        clearTokens();
        return null;
      }

      const data: TokenResponse = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      clearTokens();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Fetch wrapper that attaches Bearer token, intercepts 401s,
 * triggers silent refresh rotation, and replays the request once.
 */
export async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  let token = accessToken;

  // Set authorization header
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  headers.set("Content-Type", "application/json");

  let res = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });

  // If 401, attempt silent refresh once
  if (res.status === 401 && refreshToken) {
    token = await refreshAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
      res = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });
    }
  }

  return res;
}

// ---------------------------------------------------------------------------
// Auth API Endpoints
// ---------------------------------------------------------------------------

export async function register(name: string, email: string, password: string): Promise<User> {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Registration failed");
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Invalid email or password");
  }
  const data: TokenResponse = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function getCurrentUser(): Promise<User | null> {
  if (!accessToken) return null;
  const res = await fetchWithAuth("/auth/me");
  if (!res.ok) {
    clearTokens();
    return null;
  }
  return res.json();
}

export function logout(): void {
  clearTokens();
}

// ---------------------------------------------------------------------------
// Events API Endpoints
// ---------------------------------------------------------------------------

export async function listEvents(): Promise<EventItem[]> {
  const res = await fetchWithAuth("/events/");
  if (!res.ok) {
    throw new Error("Failed to fetch events");
  }
  return res.json();
}

export async function createEvent(payload: {
  title: string;
  event_type: string;
  event_date?: string | null;
  city?: string | null;
  guest_count?: number | null;
  total_budget?: number | null;
  currency?: string;
}): Promise<EventItem> {
  const res = await fetchWithAuth("/events/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create event");
  }
  return res.json();
}

export async function deleteEvent(id: string): Promise<void> {
  const res = await fetchWithAuth(`/events/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("Failed to delete event");
  }
}

// ---------------------------------------------------------------------------
// Brief Parser API Endpoints
// ---------------------------------------------------------------------------

export interface EventBrief {
  title: string;
  event_type: "wedding" | "birthday" | "community";
  event_date: string | null;
  city: string;
  guest_count: number | null;
  total_budget: number | null;
  currency: string;
  theme?: string | null;
  dietary_preferences?: string[];
  priorities?: string[];
  constraints?: string[];
  raw_brief?: string | null;
  missing_fields: string[];
  clarifying_questions: string[];
}

export interface BriefParseResponse {
  brief: EventBrief;
  clarifying_questions: string[];
  needs_clarification: boolean;
}

export async function parseBrief(rawText: string): Promise<BriefParseResponse> {
  const res = await fetchWithAuth("/briefs/parse", {
    method: "POST",
    body: JSON.stringify({ raw_text: rawText }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to parse celebration brief");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Plan Version API Endpoints & Types
// ---------------------------------------------------------------------------

export interface BudgetCategoryAllocation {
  category: string;
  share_pct: number;
  allocated_amount: number;
  per_guest_cost?: number | null;
  notes?: string;
}

export interface BudgetBreakdown {
  total_budget: number;
  currency: string;
  categories: BudgetCategoryAllocation[];
}

export interface TimelineItem {
  phase: string;
  days_before_event: number;
  target_date: string | null;
  task: string;
  category: string;
  owner: string;
  priority: "high" | "medium" | "low";
}

export interface ChecklistQuestion {
  category: string;
  item: string;
  questions_to_ask_vendor: string[];
  due_phase: string;
}

export interface RunOfShowSlot {
  time_slot: string;
  activity: string;
  location: string;
  lead_person: string;
  notes: string;
}

export interface VendorRecommendation {
  category: string;
  vendor_id?: string | null;
  vendor_name: string;
  estimated_price_low?: number | null;
  estimated_price_high?: number | null;
  price_unit?: string | null;
  is_grounded: boolean;
  price_status: "confirmed" | "to confirm";
  questions_to_ask: string[];
  budget_impact: number;
  reason: string;
  is_sample?: boolean;
}

export interface PlanSchema {
  version: number;
  title: string;
  event_type: "wedding" | "birthday" | "community";
  event_date: string | null;
  guest_count: number | null;
  total_budget: number;
  currency: string;
  summary: string;
  budget: BudgetBreakdown;
  timeline: TimelineItem[];
  checklist: ChecklistQuestion[];
  run_of_show: RunOfShowSlot[];
  vendor_shortlist: VendorRecommendation[];
  meta: {
    city?: string;
    theme?: string;
    menu_ideas?: string[];
    dietary_preferences?: string[];
    priorities?: string[];
    compressed_timeline?: boolean;
    timeline_warning?: string;
  };
}

export interface PlanVersionResponse {
  id: string;
  event_id: string;
  version: number;
  created_by: string;
  change_summary: string | null;
  created_at: string;
  plan: PlanSchema;
}

export async function getEventPlan(
  eventId: string,
  version?: number
): Promise<PlanVersionResponse> {
  const query = version ? `?version=${version}` : "";
  const res = await fetchWithAuth(`/events/${eventId}/plan${query}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load event plan");
  }
  return res.json();
}

export interface PlanVersionSummary {
  id: string;
  version: number;
  created_by: string;
  change_summary?: string | null;
  created_at: string;
  total_budget?: number | null;
}

export interface CategoryDelta {
  category: string;
  old_amount: number;
  new_amount: number;
  delta: number;
  old_share_pct?: number | null;
  new_share_pct?: number | null;
}

export interface TimelineDelta {
  task: string;
  action: string;
  old_date?: string | null;
  new_date?: string | null;
  reason?: string | null;
}

export interface PlanDiff {
  prompt: string;
  summary: string;
  category_changes: CategoryDelta[];
  timeline_changes: TimelineDelta[];
  old_total_budget: number;
  new_total_budget: number;
  budget_impact: number;
}

export interface ProposedChangeResponse {
  id: string;
  event_id: string;
  base_version: number;
  diff: PlanDiff;
  budget_impact: number;
  status: "pending" | "applied" | "rejected";
  created_at: string;
}

export async function getPlanVersions(eventId: string): Promise<PlanVersionSummary[]> {
  const res = await fetchWithAuth(`/events/${eventId}/versions`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load plan versions");
  }
  return res.json();
}

export async function proposePlanChange(
  eventId: string,
  prompt: string,
  baseVersion: number
): Promise<ProposedChangeResponse> {
  const res = await fetchWithAuth(`/events/${eventId}/changes/propose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, base_version: baseVersion }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to propose plan change");
  }
  return res.json();
}

export async function acceptPlanChange(
  eventId: string,
  changeId: string,
  baseVersion?: number
): Promise<PlanVersionResponse> {
  const res = await fetchWithAuth(`/events/${eventId}/changes/${changeId}/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ base_version: baseVersion }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to accept plan change");
  }
  return res.json();
}

export async function rejectPlanChange(
  eventId: string,
  changeId: string
): Promise<ProposedChangeResponse> {
  const res = await fetchWithAuth(`/events/${eventId}/changes/${changeId}/reject`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to reject plan change");
  }
  return res.json();
}

export function streamPlanChat(
  eventId: string,
  message: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (err: Error) => void
): () => void {
  const controller = new AbortController();
  const token = getAccessToken();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/events/${eventId}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Chat stream request failed");
      }

      const reader = res.body?.getReader();
      if (!reader) {
        throw new Error("No readable stream response");
      }

      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const payload = trimmed.replace(/^data:\s*/, "");
          if (payload === "[DONE]") {
            onDone();
            return;
          }
          try {
            const parsed = JSON.parse(payload);
            if (parsed.content) onChunk(parsed.content);
          } catch {
            if (payload) onChunk(payload);
          }
        }
      }
      onDone();
    } catch (err: unknown) {
      if ((err as Error)?.name !== "AbortError") {
        onError(err instanceof Error ? err : new Error(String(err)));
      }
    }
  })();

  return () => controller.abort();
}

