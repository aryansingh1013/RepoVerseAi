import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Orbit, Settings, RefreshCw, LogOut, Cpu } from "lucide-react";
import { useNavigation } from "@/hooks/useNavigation";

export function TopNavbar() {
  const navigate = useNavigate();
  const { 
    workspaceStatus, 
    triggerIndexWorkspace, 
    isScanning,
    showSkillsPanel,
    setShowSkillsPanel
  } = useNavigation();
  const [showSettings, setShowSettings] = useState(false);

  return (
    <header className="w-full pointer-events-auto panel-glass rounded-xl flex items-center justify-between px-5 py-2.5 shadow-2xl relative select-none">
      {/* Brand logo & active folder */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate("/")}>
          <Orbit className="h-5 w-5 text-signal-400 animate-spin-slow" strokeWidth={1.5} />
          <span className="font-display font-semibold tracking-wide text-mist-100">RepoVerse</span>
        </div>
        <div className="h-4 w-px bg-white/10 mx-1" />
        <span className="text-xs font-mono text-mist-400 bg-void-950/50 px-2.5 py-1 rounded border border-white/5 max-w-[200px] truncate" title={workspaceStatus.current_path}>
          {workspaceStatus.repo_name || "local-orbit"}
        </span>
      </div>

      {/* Navigation tabs */}
      <nav className="flex items-center gap-1.5">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-mist-300 hover:bg-void-700/60 hover:text-mist-100 transition-colors cursor-pointer"
        >
          <LogOut className="h-3.5 w-3.5" />
          Change Workspace
        </button>

        <button
          onClick={() => setShowSkillsPanel(!showSkillsPanel)}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs transition-colors cursor-pointer ${
            showSkillsPanel 
              ? "bg-[#7C3AED]/20 text-[#A78BFA] border border-[#7C3AED]/30" 
              : "text-mist-300 hover:bg-void-700/60 hover:text-mist-100"
          }`}
        >
          <Cpu className="h-3.5 w-3.5" />
          Agent Skills
        </button>

        <button
          disabled={isScanning}
          onClick={() => triggerIndexWorkspace()}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-signal-400 border border-signal-400/20 bg-signal-500/5 hover:bg-signal-500/10 hover:text-signal-300 transition-all font-medium cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isScanning ? "animate-spin" : ""}`} />
          {isScanning ? "Scanning..." : "Re-Index 🚀"}
        </button>
      </nav>

      {/* Settings & actions */}
      <div className="flex items-center gap-3">
        <button 
          onClick={() => setShowSettings(!showSettings)}
          className="rounded-lg p-2 text-mist-400 hover:bg-white/5 hover:text-mist-100 transition-colors cursor-pointer"
          aria-label="Settings"
        >
          <Settings className="h-4 w-4" />
        </button>

        {showSettings && (
          <div className="absolute top-16 right-0 panel-glass rounded-xl p-4 w-64 shadow-2xl z-30 flex flex-col gap-3 text-xs bg-void-900 border border-white/10">
            <h3 className="font-display font-semibold text-mist-100">Settings Configuration</h3>
            <div className="space-y-2">
              <div>
                <label className="text-mist-500 block mb-1">Workspace Path:</label>
                <div className="font-mono text-[10px] bg-void-950 p-2 rounded border border-white/5 break-all">
                  {workspaceStatus.current_path || "Unknown"}
                </div>
              </div>
              <div>
                <label className="text-mist-500 block mb-1">Indexing Status:</label>
                <div className="capitalize font-medium text-signal-400">
                  {workspaceStatus.status}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

