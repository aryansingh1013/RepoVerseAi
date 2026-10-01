import { supabase } from "@/lib/supabase";

/**
 * Central API helpers — every backend call goes through here so the
 * Supabase JWT is attached automatically when a session exists.
 *
 * Note on WebSockets: browsers cannot set custom headers on WebSocket,
 * so if the backend later enforces auth on /ws/chat, pass the token as
 * a query param (see wsUrl below) and validate server-side.
 */

export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:7860";
export const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:7860";

/** Attach the current Supabase JWT (if any) to fetch headers. */
export async function authHeaders(): Promise<Record<string, string>> {
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

/** Authenticated fetch wrapper — JSON-preserving, throws nothing (callers check res.ok). */
export async function apiFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const auth = await authHeaders();
  Object.entries(auth).forEach(([k, v]) => headers.set(k, v));
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

/** WebSocket URL with token as query param (header-based auth is impossible on WS). */
export function wsUrl(path: string, token: string | null): string {
  const base = WS_BASE.startsWith("ws") ? WS_BASE : WS_BASE.replace(/^http/, "ws");
  return token ? `${base}${path}?token=${encodeURIComponent(token)}` : `${base}${path}`;
}
