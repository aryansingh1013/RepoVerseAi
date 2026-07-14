/**
 * Central type contracts for RepoVerse AI.
 * Every mock data file must conform to these shapes so that swapping
 * mock JSON for real FastAPI responses later requires no component changes.
 */

export type SpaceObjectKind = "workspace" | "galaxy" | "star" | "planet" | "moon";

/** Maps directly to repository structure per the product's space metaphor. */
export const SPACE_OBJECT_LABELS: Record<SpaceObjectKind, string> = {
  workspace: "Universe",
  galaxy: "Repository",
  star: "Folder",
  planet: "File",
  moon: "Class / Function",
};

export interface Vector3Tuple {
  x: number;
  y: number;
  z: number;
}

export interface SpaceObject {
  id: string;
  kind: SpaceObjectKind;
  name: string;
  parentId: string | null;
  position: Vector3Tuple;
  scale: number;
  color: string;
  orbitRadius?: number;
  orbitSpeed?: number;
  inclination?: number;
  direction?: 1 | -1;
  roughness?: number;
  metalness?: number;
  fileCount?: number;
  hasRings?: boolean;
  atmosphereColor?: string;
  /** Real relative file path for /api/file calls (planets only) */
  filePath?: string;
  /** File language extension (planets only) */
  language?: string;
  /** Constellation/folder name this belongs to (stars only) */
  description?: string;
  /** Symbol type (moons only) */
  symbolType?: "function" | "class";
  /** Source line number (moons only) */
  symbolLine?: number;
  /** Symbol docstring summary (moons only) */
  symbolSummary?: string;
}

export interface RepositoryStat {
  label: string;
  value: string;
}

export interface CodePreviewLine {
  line: number;
  content: string;
}

export interface ObjectDetails {
  id: string;
  name: string;
  type: SpaceObjectKind;
  description: string;
  language?: string;
  dependencies: string[];
  summary: string;
  stats: RepositoryStat[];
  codePreview: CodePreviewLine[];
  /** Parsed symbols (classes/functions) from /api/file */
  symbols?: Array<{
    name: string;
    type: "function" | "class";
    start_line: number;
    end_line: number;
    summary: string;
    details: string;
  }>;
}

export interface Workspace {
  id: string;
  name: string;
  repositoryCount: number;
}

export interface RepositorySummary {
  id: string;
  name: string;
  description: string;
  language: string;
  updatedAt: string;
  starCount: number;
}

export interface RecentFile {
  id: string;
  name: string;
  path: string;
  openedAt: string;
}

export interface Bookmark {
  id: string;
  name: string;
  path: string;
}

export type SystemStatusLevel = "online" | "degraded" | "offline";

export interface SystemStatus {
  label: string;
  level: SystemStatusLevel;
  detail: string;
}

export interface Citation {
  file: string;
  lines?: [number, number];
  content?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  steps?: string[];
  isStreaming?: boolean;
  citations?: Citation[];
  confidence?: number;
  goal?: string;
  tasks?: any[];
  trace?: string;
  reflection?: string;
}
