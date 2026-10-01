import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase, isSupabaseConfigured } from "@/lib/supabase";
import { API_BASE } from "@/lib/api";

export interface AuthUser {
  id: string;
  email: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  session: Session | null;
  loading: boolean;
  configured: boolean;
  signUp: (email: string, password: string) => Promise<{ error: string | null; needsConfirmation: boolean }>;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
  /** Current access token for attaching to backend calls. */
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const configured = isSupabaseConfigured;

  useEffect(() => {
    if (!configured) {
      setLoading(false);
      return;
    }

    // Initial session load
    supabase.auth
      .getSession()
      .then(({ data }) => setSession(data.session))
      .catch(() => setSession(null))
      .finally(() => setLoading(false));

    // Keep session fresh (token refresh, sign-out in another tab, etc.)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => subscription.unsubscribe();
  }, [configured]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user
        ? { id: session.user.id, email: session.user.email ?? null }
        : null,
      session,
      loading,
      configured,
      signUp: async (email, password) => {
        if (!configured) return { error: "Auth is not configured.", needsConfirmation: false };
        // Preferred: backend admin-backed registration (no confirmation email,
        // avoids Supabase's hourly email rate limit on free projects).
        try {
          const res = await fetch(`${API_BASE}/api/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });
          if (res.status === 409) {
            return { error: "An account with this email already exists. Please sign in.", needsConfirmation: false };
          }
          if (res.ok) {
            // Account created & pre-confirmed — sign straight in.
            const { error: inErr } = await supabase.auth.signInWithPassword({ email, password });
            return inErr ? { error: inErr.message, needsConfirmation: false } : { error: null, needsConfirmation: false };
          }
          // Backend unreachable/unconfigured — fall back to direct Supabase signup
          // (may hit the email rate limit and require inbox confirmation).
          const { error, data } = await supabase.auth.signUp({ email, password });
          if (error) return { error: error.message, needsConfirmation: false };
          return { error: null, needsConfirmation: !data.session };
        } catch {
          const { error, data } = await supabase.auth.signUp({ email, password });
          if (error) return { error: error.message, needsConfirmation: false };
          return { error: null, needsConfirmation: !data.session };
        }
      },
      signIn: async (email, password) => {
        if (!configured) return { error: "Auth is not configured." };
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        return { error: error?.message ?? null };
      },
      signOut: async () => {
        if (configured) await supabase.auth.signOut();
      },
      getAccessToken: async () => {
        if (!configured || !session) return null;
        const { data } = await supabase.auth.getSession();
        return data.session?.access_token ?? null;
      },
    }),
    [session, loading, configured]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
