import type { SystemStatus } from "@/types";

export const mockSystemStatus: SystemStatus[] = [
  { label: "Repository", level: "online", detail: "Synced 3m ago" },
  { label: "Backend", level: "online", detail: "FastAPI · mock" },
  { label: "AI Engine", level: "online", detail: "Idle" },
  { label: "Index", level: "degraded", detail: "Rebuilding (62%)" },
  { label: "Connection", level: "online", detail: "42ms" },
];
