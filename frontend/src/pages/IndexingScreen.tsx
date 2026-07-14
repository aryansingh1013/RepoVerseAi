import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Orbit, CheckCircle2, AlertCircle } from "lucide-react";

const API = "http://127.0.0.1:8000";

type StatusState = "cloning" | "indexing" | "ready" | "error";

const STATUS_LABELS: Record<StatusState, string> = {
  cloning: "Cloning repository from Git…",
  indexing: "Scanning & indexing your codebase…",
  ready: "Galaxy is ready for launch!",
  error: "Something went wrong.",
};

const STATUS_PROGRESS: Record<StatusState, number> = {
  cloning: 30,
  indexing: 65,
  ready: 100,
  error: 0,
};

// ─── Scanning dots animation ──────────────────────────────────────────────────
function Dot({ delay }: { delay: number }) {
  return (
    <motion.span
      animate={{ opacity: [0.2, 1, 0.2] }}
      transition={{ duration: 1.4, repeat: Infinity, delay }}
      className="inline-block h-2 w-2 rounded-full bg-[#A78BFA]"
    />
  );
}

// ─── Indexing Progress Screen ─────────────────────────────────────────────────
export function IndexingScreen() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<StatusState>("indexing");
  const [repoName, setRepoName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [progressVal, setProgressVal] = useState(20);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/workspace/status`);
        if (!res.ok) return;
        const data = await res.json();

        const st = data.status as StatusState;
        setStatus(st);
        setRepoName(data.repo_name || "");
        setErrorMsg(data.error_message || "");

        // Animate progress bar naturally
        const target = STATUS_PROGRESS[st] ?? 0;
        setProgressVal((prev) => {
          if (prev < target) return Math.min(prev + 3, target);
          return prev;
        });

        if (st === "ready") {
          clearInterval(interval);
          // Brief pause so user sees "Ready" before navigating
          setTimeout(() => navigate("/workspace"), 1200);
        } else if (st === "error") {
          clearInterval(interval);
        }
      } catch {
        // Backend offline
      }
    };

    poll();
    interval = setInterval(poll, 1000);
    return () => clearInterval(interval);
  }, [navigate]);

  const isError = status === "error";
  const isDone = status === "ready";

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#030308] flex flex-col items-center justify-center gap-8">
      {/* Subtle background gradient */}
      <div
        className="absolute inset-0 z-0"
        style={{ background: "radial-gradient(circle at 50% 50%, rgba(124,58,237,0.08) 0%, transparent 70%)" }}
      />

      <div className="relative z-10 flex flex-col items-center gap-8 w-full max-w-md px-6">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <Orbit className="h-7 w-7 text-[#A78BFA] animate-spin-slow" strokeWidth={1.5} />
          <span className="font-display text-xl font-semibold text-white">
            Repo<span className="text-[#A78BFA]">Verse</span> AI
          </span>
        </div>

        {/* Status icon */}
        <AnimatePresence mode="wait">
          {isDone ? (
            <motion.div
              key="done"
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center justify-center h-20 w-20 rounded-full bg-emerald-500/10 border border-emerald-500/30"
            >
              <CheckCircle2 className="h-10 w-10 text-emerald-400" />
            </motion.div>
          ) : isError ? (
            <motion.div
              key="error"
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center justify-center h-20 w-20 rounded-full bg-red-500/10 border border-red-500/30"
            >
              <AlertCircle className="h-10 w-10 text-red-400" />
            </motion.div>
          ) : (
            <motion.div
              key="scanning"
              className="relative flex items-center justify-center h-20 w-20"
            >
              <div className="absolute inset-0 rounded-full border-2 border-[#7C3AED]/30 animate-spin" />
              <div className="absolute inset-2 rounded-full border border-[#A78BFA]/20 animate-spin" style={{ animationDuration: "2s", animationDirection: "reverse" }} />
              <Orbit className="h-8 w-8 text-[#A78BFA] relative z-10" strokeWidth={1.5} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Status text */}
        <div className="text-center space-y-1.5">
          <p className="text-sm font-medium text-slate-200">
            {STATUS_LABELS[status]}
          </p>
          {repoName && !isError && (
            <p className="text-xs font-mono text-[#A78BFA]">{repoName}</p>
          )}
          {isError && errorMsg && (
            <p className="text-xs text-red-400 max-w-xs text-center">{errorMsg}</p>
          )}
          {!isDone && !isError && (
            <div className="flex items-center justify-center gap-1.5 pt-1">
              <Dot delay={0} />
              <Dot delay={0.25} />
              <Dot delay={0.5} />
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full space-y-2">
          <div className="h-1 w-full rounded-full bg-white/5 overflow-hidden">
            <motion.div
              className={`h-full rounded-full ${isError ? "bg-red-500" : "bg-gradient-to-r from-[#7C3AED] to-[#A78BFA]"}`}
              animate={{ width: `${isError ? 40 : progressVal}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-600 font-mono">
            <span>Clone</span>
            <span>Index</span>
            <span>Ready</span>
          </div>
        </div>

        {/* Agent steps (if available) */}
        <div className="w-full rounded-xl border border-white/5 bg-white/3 p-3 space-y-1.5 max-h-40 overflow-y-auto">
          <p className="text-[10px] font-mono text-slate-600 uppercase tracking-wider mb-2">
            System log
          </p>
          {[
            status === "cloning" && "→ git clone started…",
            (status === "indexing" || status === "ready") && "→ Directory walk complete",
            (status === "indexing" || status === "ready") && "→ Building code chunks",
            (status === "indexing" || status === "ready") && "→ Embedding into ChromaDB",
            (status === "indexing" || status === "ready") && "→ Building BM25 index",
            status === "ready" && "✓ Galaxy indexed and ready",
          ]
            .filter(Boolean)
            .map((line, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.15 }}
                className="text-[11px] font-mono text-slate-400"
              >
                {line as string}
              </motion.div>
            ))}
        </div>

        {/* Error retry */}
        {isError && (
          <button
            onClick={() => window.history.back()}
            className="text-sm text-[#A78BFA] underline underline-offset-2 hover:text-[#7C3AED] transition-colors"
          >
            ← Go back and try again
          </button>
        )}
      </div>
    </div>
  );
}
