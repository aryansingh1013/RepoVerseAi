import { useEffect, useState } from "react";
import type { SystemStatusLevel } from "@/types";
import { clsx } from "@/utils/clsx";
import { apiFetch } from "@/lib/api";
import { useNavigation } from "@/hooks/useNavigation";

interface StatusRow {
  label: string;
  level: SystemStatusLevel;
  detail: string;
}

interface LlmStatusResponse {
  llm: {
    connected: boolean;
    model_available: boolean;
    model: string;
    error: string | null;
  };
  workspace: { path: string; exists: boolean; repo_name: string };
  index: { chunks: number; indexed: boolean };
}

const levelColor: Record<SystemStatusLevel, string> = {
  online: "bg-emerald-400",
  degraded: "bg-ember-400",
  offline: "bg-red-400",
};

export function BottomStatusBar() {
  const { workspaceStatus } = useNavigation();
  const [rows, setRows] = useState<StatusRow[]>([
    { label: "Backend", level: "degraded", detail: "checking…" },
    { label: "Repository", level: "degraded", detail: "checking…" },
    { label: "AI Engine", level: "degraded", detail: "checking…" },
  ]);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      const start = performance.now();
      try {
        const res = await apiFetch(`/api/llm/status`);
        const ms = Math.round(performance.now() - start);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: LlmStatusResponse = await res.json();
        if (cancelled) return;

        const next: StatusRow[] = [
          {
            label: "Repository",
            level: data.workspace.exists ? "online" : "offline",
            detail: data.workspace.exists
              ? data.workspace.repo_name || "active"
              : "path missing",
          },
          {
            label: "Backend",
            level: "online",
            detail: `FastAPI · ${ms}ms`,
          },
          {
            label: "AI Engine",
            level:
              data.llm.connected && data.llm.model_available
                ? "online"
                : data.llm.connected
                ? "degraded"
                : "offline",
            detail:
              data.llm.connected && data.llm.model_available
                ? `${data.llm.model} ready`
                : data.llm.error
                ? data.llm.error.length > 48
                  ? `${data.llm.error.slice(0, 48)}…`
                  : data.llm.error
                : "unavailable",
          },
          {
            label: "Index",
            level: data.index.chunks > 0 ? "online" : "degraded",
            detail: data.index.chunks > 0 ? `${data.index.chunks} chunks` : "not indexed",
          },
          {
            label: "Workspace",
            level:
              workspaceStatus.status === "ready"
                ? "online"
                : workspaceStatus.status === "error"
                ? "offline"
                : "degraded",
            detail:
              workspaceStatus.status === "error"
                ? workspaceStatus.error_message.slice(0, 40)
                : workspaceStatus.status,
          },
        ];
        setRows(next);
      } catch {
        if (cancelled) return;
        setRows([
          { label: "Backend", level: "offline", detail: "unreachable" },
          { label: "Repository", level: "offline", detail: "unknown" },
          { label: "AI Engine", level: "offline", detail: "unknown" },
        ]);
      }
    };

    poll();
    const interval = setInterval(poll, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [workspaceStatus.status, workspaceStatus.error_message]);

  return (
    <footer className="h-8 shrink-0 panel-glass flex items-center gap-5 px-4 text-[11px] text-mist-400 font-mono z-20 overflow-x-auto scrollbar-none">
      {rows.map((status) => (
        <div key={status.label} className="flex items-center gap-1.5 whitespace-nowrap">
          <span
            className={clsx(
              "h-1.5 w-1.5 rounded-full",
              levelColor[status.level],
              status.level === "online" && "animate-pulse-slow"
            )}
          />
          <span className="text-mist-300">{status.label}</span>
          <span className="text-mist-500">· {status.detail}</span>
        </div>
      ))}
    </footer>
  );
}
