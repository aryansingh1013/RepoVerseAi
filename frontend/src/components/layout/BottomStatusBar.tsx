import { mockSystemStatus } from "@/data/mockStatus";
import type { SystemStatusLevel } from "@/types";
import { clsx } from "@/utils/clsx";

const levelColor: Record<SystemStatusLevel, string> = {
  online: "bg-emerald-400",
  degraded: "bg-ember-400",
  offline: "bg-red-400",
};

export function BottomStatusBar() {
  return (
    <footer className="h-8 shrink-0 panel-glass flex items-center gap-5 px-4 text-[11px] text-mist-400 font-mono z-20">
      {mockSystemStatus.map((status) => (
        <div key={status.label} className="flex items-center gap-1.5">
          <span
            className={clsx("h-1.5 w-1.5 rounded-full", levelColor[status.level], status.level === "online" && "animate-pulse-slow")}
          />
          <span className="text-mist-300">{status.label}</span>
          <span className="text-mist-500">· {status.detail}</span>
        </div>
      ))}
    </footer>
  );
}
