import { useState, useEffect } from "react";
import { 
  Orbit, History, Cpu, BookOpen, ShieldAlert, Activity, 
  FileText, Sparkles, Copy, Check, Download, X, Loader2
} from "lucide-react";
import { useNavigation } from "@/hooks/useNavigation";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Helper to render Markdown report dynamically
function parseMarkdown(md: string) {
  const lines = md.split("\n");
  let inCodeBlock = false;
  let codeBlockLines: string[] = [];

  return lines.map((line, idx) => {
    // Code block toggle
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        inCodeBlock = false;
        const code = codeBlockLines.join("\n");
        codeBlockLines = [];
        return (
          <pre key={idx} className="bg-void-950/80 border border-white/5 p-3 rounded-lg font-mono text-[10px] text-signal-400 overflow-x-auto my-2 whitespace-pre select-text select-all">
            {code}
          </pre>
        );
      } else {
        inCodeBlock = true;
        return null;
      }
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      return null;
    }

    // Headers
    if (line.startsWith("# ")) {
      return <h1 key={idx} className="text-base font-display font-bold text-white mt-4 mb-2">{line.slice(2)}</h1>;
    }
    if (line.startsWith("## ")) {
      return <h2 key={idx} className="text-xs font-display font-semibold text-signal-400 mt-4 mb-1.5 border-b border-white/5 pb-1 uppercase tracking-wider">{line.slice(3)}</h2>;
    }
    if (line.startsWith("### ")) {
      return <h3 key={idx} className="text-xs font-display font-semibold text-[#A78BFA] mt-3 mb-1">{line.slice(4)}</h3>;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      return (
        <blockquote key={idx} className="border-l-2 border-signal-400/60 bg-white/5 pl-3 py-1.5 my-2 rounded-r-lg text-slate-400 italic text-[11px]">
          {line.slice(2)}
        </blockquote>
      );
    }

    // Table rows
    if (line.startsWith("|")) {
      if (line.includes("---")) return null;
      const cells = line.split("|").map(c => c.trim()).filter((_, i, a) => i > 0 && i < a.length - 1);
      return (
        <div key={idx} className="grid grid-cols-4 gap-2 py-1 px-2 border-b border-white/5 hover:bg-white/5 text-[10px] font-mono text-slate-300">
          {cells.map((cell, cidx) => (
            <span key={cidx} className="truncate">{cell.replace(/`/g, "")}</span>
          ))}
        </div>
      );
    }

    // Unordered lists
    if (line.startsWith("- ")) {
      let content = line.slice(2);
      return (
        <li key={idx} className="list-disc list-inside text-[11px] text-slate-300 py-0.5 pl-2 leading-relaxed">
          {content.split("**").map((part, i) => {
            if (i % 2 === 1) return <strong key={i} className="text-white font-semibold">{part}</strong>;
            return part.split("`").map((subpart, j) => {
              if (j % 2 === 1) return <code key={j} className="bg-white/10 px-1 py-0.2 rounded font-mono text-[10px] text-signal-300">{subpart}</code>;
              return subpart;
            });
          })}
        </li>
      );
    }

    // Empty line
    if (!line.trim()) {
      return <div key={idx} className="h-2" />;
    }

    // Default text
    return (
      <p key={idx} className="text-[11px] text-slate-300 leading-relaxed my-1">
        {line.split("**").map((part, i) => {
          if (i % 2 === 1) return <strong key={i} className="text-white font-semibold">{part}</strong>;
          return part.split("`").map((subpart, j) => {
            if (j % 2 === 1) return <code key={j} className="bg-white/10 px-1 py-0.2 rounded font-mono text-[10px] text-signal-300">{subpart}</code>;
            return subpart;
          });
        })}
      </p>
    );
  }).filter(el => el !== null);
}

const getSkillIcon = (slug: string) => {
  switch (slug) {
    case "overview": return <FileText className="h-3.5 w-3.5 text-blue-400" />;
    case "architecture": return <Orbit className="h-3.5 w-3.5 text-purple-400" />;
    case "health": return <Activity className="h-3.5 w-3.5 text-emerald-400" />;
    case "dependencies": return <Cpu className="h-3.5 w-3.5 text-amber-400" />;
    case "timeline": return <History className="h-3.5 w-3.5 text-indigo-400" />;
    case "learning": return <BookOpen className="h-3.5 w-3.5 text-pink-400" />;
    case "readme": return <FileText className="h-3.5 w-3.5 text-teal-400" />;
    case "security": return <ShieldAlert className="h-3.5 w-3.5 text-red-400" />;
    case "performance": return <Sparkles className="h-3.5 w-3.5 text-yellow-400" />;
    default: return <Cpu className="h-3.5 w-3.5 text-slate-400" />;
  }
};

const skillsList = [
  { slug: "overview", name: "Overview" },
  { slug: "architecture", name: "Architecture" },
  { slug: "health", name: "Health" },
  { slug: "dependencies", name: "Dependencies" },
  { slug: "timeline", name: "Timeline" },
  { slug: "learning", name: "Learning" },
  { slug: "readme", name: "README" },
  { slug: "security", name: "Security" },
  { slug: "performance", name: "Performance" }
];

export function SkillsOverlay() {
  const { setShowSkillsPanel } = useNavigation();
  const [selectedSkillSlug, setSelectedSkillSlug] = useState<string>("overview");
  const [isLoading, setIsLoading] = useState(false);
  const [skillReportMarkdown, setSkillReportMarkdown] = useState<string>("");
  const [copied, setCopied] = useState(false);

  const runSkill = async () => {
    setIsLoading(true);
    setSkillReportMarkdown("");
    try {
      const execRes = await fetch(`${API}/api/skills/execute/${selectedSkillSlug}`, {
        method: "POST"
      });
      const execData = await execRes.json();
      
      if (execData.error) {
        setSkillReportMarkdown(`# Skill Run Failed\n\nError: ${execData.error}`);
        return;
      }
      
      const exportRes = await fetch(`${API}/api/skills/export/${selectedSkillSlug}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result: execData })
      });
      const exportData = await exportRes.json();
      setSkillReportMarkdown(exportData.markdown || "");
    } catch (err: any) {
      setSkillReportMarkdown(`# Skill Run Error\n\nFailed to connect to backend service:\n${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Clear report when switching tabs
  useEffect(() => {
    setSkillReportMarkdown("");
  }, [selectedSkillSlug]);

  const handleCopy = () => {
    if (!skillReportMarkdown) return;
    navigator.clipboard.writeText(skillReportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!skillReportMarkdown) return;
    const element = document.createElement("a");
    const file = new Blob([skillReportMarkdown], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = `repoverse-skill-${selectedSkillSlug}-report.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="absolute inset-x-4 top-20 bottom-4 z-30 panel-glass rounded-2xl flex flex-col overflow-hidden bg-void-950/85 backdrop-blur-md border border-white/10 shadow-2xl p-4 select-none pointer-events-auto">
      {/* Header and Close */}
      <div className="flex items-center justify-between pb-3 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <Cpu className="h-4.5 w-4.5 text-[#A78BFA] animate-pulse" />
          <span className="font-display font-semibold text-xs text-white">Skills Intelligence Console</span>
        </div>
        <button
          onClick={() => setShowSkillsPanel(false)}
          className="rounded-lg p-1 text-slate-400 hover:bg-white/5 hover:text-white transition-colors cursor-pointer"
          title="Close Skills Panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Horizontal Tabs: Run automatically when clicked */}
      <div className="flex items-center gap-1 py-3 overflow-x-auto shrink-0 scrollbar-none border-b border-white/5">
        {skillsList.map((skill) => {
          const isSelected = selectedSkillSlug === skill.slug;
          return (
            <button
              key={skill.slug}
              onClick={() => setSelectedSkillSlug(skill.slug)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-medium transition-all cursor-pointer whitespace-nowrap border ${
                isSelected 
                  ? "bg-[#7C3AED]/20 border-[#7C3AED]/40 text-[#A78BFA] shadow-md shadow-[#7C3AED]/5" 
                  : "bg-void-900/40 border-white/5 text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {getSkillIcon(skill.slug)}
              {skill.name}
            </button>
          );
        })}
      </div>

      {/* Content Pane */}
      <div className="flex-1 overflow-y-auto mt-3 pr-1 scrollbar-thin select-text">
        {isLoading ? (
          <div className="h-full flex flex-col items-center justify-center py-10 gap-3">
            <Loader2 className="h-6 w-6 animate-spin text-[#A78BFA]" />
            <div className="text-center">
              <span className="text-xs font-semibold text-white block">Executing Skill Run…</span>
              <span className="text-[10px] font-mono text-slate-500 mt-0.5 block">Parsing AST & synthesizing report payload</span>
            </div>
          </div>
        ) : skillReportMarkdown ? (
          <div className="space-y-4">
            {/* Quick Actions */}
            <div className="flex justify-end gap-2 border-b border-white/5 pb-2.5">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.2 text-[10px] text-slate-300 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
              >
                {copied ? (
                  <><Check className="h-3 w-3 text-emerald-400" /> Copied!</>
                ) : (
                  <><Copy className="h-3 w-3" /> Copy Markdown</>
                )}
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.2 text-[10px] text-slate-300 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
              >
                <Download className="h-3 w-3" />
                Download (.md)
              </button>
            </div>

            {/* Markdown Report Body */}
            <div className="markdown-body text-slate-300 space-y-3 pb-4 select-all text-xs">
              {parseMarkdown(skillReportMarkdown)}
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center py-10 gap-4">
            <span className="text-xs text-slate-500 font-mono">Ready to profile the codebase. Click Execute to begin analysis.</span>
            <button
              onClick={runSkill}
              className="px-6 py-2 bg-[#7C3AED] hover:bg-[#6D28D9] text-white rounded-lg text-[11px] font-semibold tracking-wide shadow-lg shadow-[#7C3AED]/20 transition-all cursor-pointer flex items-center gap-2"
            >
              <Cpu className="h-4 w-4" />
              Execute Skill Analysis
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
