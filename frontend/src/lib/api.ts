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
