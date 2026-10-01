import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Rocket, Mail, Lock, Loader2, AlertCircle, CheckCircle2, Orbit } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function AuthPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const redirectTarget =
    (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      if (mode === "signup") {
        const res = await signUp(email, password);
        if (res.error) {
          setError(res.error);
        } else if (res.needsConfirmation) {
          setNotice("Check your inbox — we sent you a confirmation link. After confirming, sign in here.");
        } else {
          navigate(redirectTarget, { replace: true });
        }
      } else {
        const res = await signIn(email, password);
        if (res.error) {
          setError(res.error);
        } else {
          navigate(redirectTarget, { replace: true });
        }
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#030308] text-white px-4"
         style={{ background: "radial-gradient(circle at center, #0B0B1E 0%, #030308 100%)" }}>
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-violet-600 to-indigo-800 flex items-center justify-center shadow-[0_0_30px_rgba(124,58,237,0.5)] mb-4">
            <Rocket className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-wide">RepoVerse AI</h1>
          <p className="text-sm text-slate-400 mt-1">Your repository universe awaits</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-white/10 bg-slate-900/50 backdrop-blur-xl p-8 shadow-[0_0_40px_rgba(124,58,237,0.15)]">
          <div className="flex gap-2 mb-6 p-1 rounded-xl bg-slate-800/60">
            {(["signin", "signup"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setError(null); setNotice(null); }}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                  mode === m
                    ? "bg-violet-600 shadow-[0_0_15px_rgba(124,58,237,0.4)]"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {m === "signin" ? "Sign In" : "Create Account"}
              </button>
            ))}
          </div>

          {error && (
            <div className="flex items-start gap-2 mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-300">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {notice && (
            <div className="flex items-start gap-2 mb-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-sm text-emerald-300">
              <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{notice}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="explorer@galaxy.dev"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-800/70 border border-white/10 text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/50"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-800/70 border border-white/10 text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/50"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={busy}
              className="w-full py-2.5 rounded-lg font-semibold text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_20px_rgba(124,58,237,0.35)] flex items-center justify-center gap-2"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Orbit className="w-4 h-4" />}
              {busy ? "Connecting..." : mode === "signin" ? "Launch" : "Create Account & Launch"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          Powered by Supabase Auth · Your data stays in your universe
        </p>
      </div>
    </div>
  );
}
