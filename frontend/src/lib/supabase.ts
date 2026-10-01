import { createClient } from "@supabase/supabase-js";

/**
 * Supabase client for RepoVerse AI frontend.
 *
 * Only the PUBLIC (anon/publishable) key lives here. It is designed to be
 * public — all authorization is enforced by Postgres Row Level Security and
 * verified again server-side by backend/auth. Never place the service-role
 * (secret) key in frontend code.
 *
 * Configure via frontend/.env.local:
 *   VITE_SUPABASE_URL=https://<project>.supabase.co
 *   VITE_SUPABASE_ANON_KEY=<publishable-key>
 */

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    "[RepoVerse] Supabase auth disabled: missing VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY. " +
      "Add them to frontend/.env.local and restart the dev server."
  );
}

export const supabase = createClient(
  supabaseUrl ?? "http://localhost:54321",
  supabaseAnonKey ?? "public-anon-key-placeholder",
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storageKey: "repoverse-auth",
    },
  }
);

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);
