import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { FolderOpen, Github, Orbit, ChevronRight, Loader2, AlertCircle, Sparkles } from "lucide-react";

const API = "http://127.0.0.1:8000";

// ─── Starfield background canvas ─────────────────────────────────────────────
function Starfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    let animFrame: number;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    // Generate random stars
    const STAR_COUNT = 280;
    const stars = Array.from({ length: STAR_COUNT }, () => ({
      x: Math.random(),
      y: Math.random(),
      r: Math.random() * 1.4 + 0.3,
      speed: Math.random() * 0.00012 + 0.00003,
      opacity: Math.random() * 0.7 + 0.3,
      twinkle: Math.random() * Math.PI * 2,
    }));

    // A few colored nebula blobs
    const nebulae = [
      { x: 0.2, y: 0.3, r: 280, color: "rgba(124,58,237,0.06)" },
      { x: 0.75, y: 0.6, r: 220, color: "rgba(59,130,246,0.05)" },
      { x: 0.5, y: 0.85, r: 180, color: "rgba(236,72,153,0.04)" },
    ];

    let t = 0;
    const draw = () => {
      t += 1;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Nebulae
      nebulae.forEach((n) => {
        const grad = ctx.createRadialGradient(
          n.x * canvas.width, n.y * canvas.height, 0,
          n.x * canvas.width, n.y * canvas.height, n.r
        );
        grad.addColorStop(0, n.color);
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(n.x * canvas.width, n.y * canvas.height, n.r, 0, Math.PI * 2);
        ctx.fill();
      });

      // Stars
      stars.forEach((s) => {
        s.twinkle += s.speed * 40;
        const alpha = s.opacity * (0.6 + 0.4 * Math.sin(s.twinkle));
        ctx.beginPath();
        ctx.arc(s.x * canvas.width, s.y * canvas.height, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(200,210,255,${alpha})`;
        ctx.fill();
      });

      animFrame = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animFrame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 z-0" />;
}

// ─── Mode Tabs ────────────────────────────────────────────────────────────────
type Mode = "local" | "git";

// ─── Main Landing Page ────────────────────────────────────────────────────────
export function LandingPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("local");
  const [gitUrl, setGitUrl] = useState("");
  const [manualPath, setManualPath] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Check backend is alive
  useEffect(() => {
    fetch(`${API}/api/workspace/status`)
      .then((r) => r.ok ? setBackendOnline(true) : setBackendOnline(false))
      .catch(() => setBackendOnline(false));
  }, []);

  // ── Open local folder via OS dialog
  const handleBrowse = async () => {
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/api/workspace/browse`);
      const data = await res.json();
      if (data.status === "success" && data.path) {
        setManualPath(data.path);
      } else if (data.status === "cancelled") {
        setError("Folder selection cancelled.");
      }
    } catch {
      setError("Could not open folder dialog. Is the backend running?");
    } finally {
      setIsLoading(false);
    }
  };

  // ── Submit local path
  const handleLocalSubmit = async () => {
    const path = manualPath.trim();
    if (!path) { setError("Please select or enter a folder path."); return; }
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/api/workspace/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to set workspace.");
      }
      navigate("/workspace");
    } catch (e: any) {
      setError(e.message || "Failed to open local project.");
    } finally {
      setIsLoading(false);
    }
  };

  // ── Submit git URL
  const handleGitSubmit = async () => {
    const url = gitUrl.trim();
    if (!url) { setError("Please enter a Git repository URL."); return; }
    if (!url.startsWith("http") && !url.startsWith("git@")) {
      setError("Please enter a valid Git URL (https:// or git@...).");
      return;
    }
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/api/clone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start clone.");
      }
      navigate("/workspace");
    } catch (e: any) {
      setError(e.message || "Failed to clone repository.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = mode === "local" ? handleLocalSubmit : handleGitSubmit;

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#030308] flex flex-col items-center justify-center">
      {/* Animated starfield */}
      <Starfield />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-8 px-4 w-full max-w-lg">

        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="flex flex-col items-center gap-3"
        >
          <div className="relative flex items-center justify-center h-20 w-20">
            <div className="absolute inset-0 rounded-full bg-[#7C3AED]/20 animate-pulse" />
            <div className="absolute inset-2 rounded-full bg-[#7C3AED]/10 border border-[#7C3AED]/30" />
            <Orbit className="h-9 w-9 text-[#A78BFA] relative z-10 animate-spin-slow" strokeWidth={1.5} />
            {/* Outer rings */}
            <span className="absolute -inset-1 rounded-full border border-[#7C3AED]/20 animate-ping opacity-40 pointer-events-none" />
          </div>
          <div className="text-center">
            <h1 className="font-display text-4xl font-bold tracking-tight text-white">
              Repo<span className="text-[#A78BFA]">Verse</span>
              <span className="text-[#7C3AED] ml-1">AI</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1 tracking-wide">
              Explore your codebase as an interactive galaxy
            </p>
          </div>
        </motion.div>

        {/* Backend status pill */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className={`flex items-center gap-1.5 text-xs px-3 py-1 rounded-full border ${
            backendOnline === null
              ? "border-white/10 text-slate-500 bg-white/5"
              : backendOnline
              ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
              : "border-red-500/30 text-red-400 bg-red-500/10"
          }`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${
            backendOnline === null ? "bg-slate-500" :
            backendOnline ? "bg-emerald-400 animate-pulse" : "bg-red-400"
          }`} />
          {backendOnline === null ? "Connecting to AI engine…" :
           backendOnline ? "AI Engine Online · Port 8000" : "Backend offline — start the server first"}
        </motion.div>

        {/* Main Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="w-full rounded-2xl border border-white/10 overflow-hidden"
          style={{ background: "rgba(11,11,30,0.85)", backdropFilter: "blur(20px)" }}
        >
          {/* Tab switcher */}
          <div className="flex border-b border-white/5">
            {(["local", "git"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(""); }}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-medium transition-all ${
                  mode === m
                    ? "text-[#A78BFA] border-b-2 border-[#7C3AED] bg-[#7C3AED]/5"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {m === "local" ? <FolderOpen className="h-4 w-4" /> : <Github className="h-4 w-4" />}
                {m === "local" ? "Local Project" : "Clone from Git"}
              </button>
            ))}
          </div>

          {/* Form body */}
          <div className="p-6 space-y-4">
            <AnimatePresence mode="wait">
              {mode === "local" ? (
                <motion.div
                  key="local"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-3"
                >
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Select a local folder on your computer. RepoVerse AI will scan and index it, then visualize every file and folder as a planet and star in your private galaxy.
                  </p>

                  {/* OS dialog button */}
                  <button
                    onClick={handleBrowse}
                    disabled={isLoading || !backendOnline}
                    className="w-full flex items-center justify-center gap-2 rounded-lg border border-[#7C3AED]/40 bg-[#7C3AED]/10 py-2.5 text-sm text-[#A78BFA] hover:bg-[#7C3AED]/20 transition-all disabled:opacity-40 cursor-pointer"
                  >
                    {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderOpen className="h-4 w-4" />}
                    Browse Folder…
                  </button>

                  {/* Or type path manually */}
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                      <span className="text-slate-600 text-xs font-mono">path/</span>
                    </div>
                    <input
                      type="text"
                      value={manualPath}
                      onChange={(e) => setManualPath(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                      placeholder="or type absolute path, e.g. C:\Projects\my-app"
                      className="w-full rounded-lg border border-white/8 bg-white/5 pl-12 pr-3 py-2.5 text-xs text-slate-300 placeholder:text-slate-600 outline-none focus:border-[#7C3AED]/50 font-mono"
                    />
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="git"
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-3"
                >
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Paste any public GitHub/GitLab URL. RepoVerse will clone it automatically, then index and visualize the full codebase as a 3D galaxy.
                  </p>
                  <input
                    type="text"
                    value={gitUrl}
                    onChange={(e) => setGitUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    placeholder="https://github.com/user/repo"
                    className="w-full rounded-lg border border-white/8 bg-white/5 px-3 py-2.5 text-xs text-slate-300 placeholder:text-slate-600 outline-none focus:border-[#7C3AED]/50 font-mono"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400"
                >
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Launch button */}
            <button
              onClick={handleSubmit}
              disabled={isLoading || !backendOnline || (mode === "local" ? !manualPath.trim() : !gitUrl.trim())}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#7C3AED] py-3 text-sm font-semibold text-white hover:bg-[#6D28D9] active:scale-[0.98] transition-all disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-lg shadow-[#7C3AED]/25"
            >
              {isLoading ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Launching…</>
              ) : (
                <><Sparkles className="h-4 w-4" /> Launch Galaxy <ChevronRight className="h-4 w-4" /></>
              )}
            </button>
          </div>
        </motion.div>

        {/* Footer hint */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-[11px] text-slate-600 text-center"
        >
          Universe → Galaxy → Constellation → Star (Folder) → Planet (File) → Moon (Function)
        </motion.p>
      </div>
    </div>
  );
}
