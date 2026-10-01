import {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
  createElement,
} from "react";
import type {
  SpaceObject,
  ObjectDetails,
  RepositorySummary,
  RecentFile,
  Bookmark,
} from "@/types";

import { apiFetch, wsUrl } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { positionsRegistry } from "@/three/positionsRegistry";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:7860";
const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:7860";


// ─── Theme Colors (from /api/theme) ──────────────────────────────────────────

export interface ThemeColors {
  universe_bg: string;
  galaxy_accent: string;
  star_color: string;
  planet_color: string;
  moon_color: string;
  constellation_colors: Record<string, string>;
  glass_bg: string;
  glass_border: string;
  neon_shadow: string;
}

const DEFAULT_THEME: ThemeColors = {
  universe_bg: "radial-gradient(circle at center, #0B0B1E 0%, #030308 100%)",
  galaxy_accent: "#7C3AED",
  star_color: "#A78BFA",
  planet_color: "#60A5FA",
  moon_color: "#FBBF24",
  constellation_colors: {
    Auth: "#3B82F6",
    Database: "#10B981",
    Core: "#F59E0B",
    Api: "#EC4899",
    Rag: "#8B5CF6",
    Agent: "#EF4444",
    Default: "#6B7280",
  },
  glass_bg: "rgba(15, 23, 42, 0.45)",
  glass_border: "rgba(255, 255, 255, 0.08)",
  neon_shadow: "0 0 10px rgba(124, 58, 237, 0.5)",
};

// ─── Language Color Helpers (themed) ─────────────────────────────────────────

function getLanguageColor(lang: string, theme: ThemeColors): string {
  switch (lang.toLowerCase()) {
    case "py": return "#4d8fdd";
    case "js": case "jsx": return "#f7df1e";
    case "ts": case "tsx": return "#3178c6";
    case "html": return "#e34c26";
    case "css": return "#563d7c";
    case "json": return "#854d0e";
    case "md": return "#e2e8f0";
    default: return theme.planet_color;
  }
}

function getLanguageAtmosphereColor(lang: string): string {
  switch (lang.toLowerCase()) {
    case "py": return "#1a4fff";
    case "js": case "jsx": return "#b59b00";
    case "ts": case "tsx": return "#0055ff";
    case "html": return "#ff2200";
    case "css": return "#31115c";
    case "json": return "#a16207";
    default: return "#475569";
  }
}

function getConstellationColor(constellationName: string, theme: ThemeColors): string {
  const key = constellationName.charAt(0).toUpperCase() + constellationName.slice(1).toLowerCase();
  return theme.constellation_colors[key] || theme.constellation_colors["Default"] || theme.star_color;
}

import { getFolderVisualIdentity, getFileVisualIdentity } from "@/three/PlanetTextures";

// ─── Build Space Graph from Backend Scan ─────────────────────────────────────

function buildSpaceGraphFromScan(scanData: any, _theme: ThemeColors): SpaceObject[] {
  const graph: SpaceObject[] = [];
  if (!scanData) return graph;

  const repoName = scanData.galaxy || "Repository";
  const starId = "repository-star";

  // 1. Gather all files across all constellations and stars
  interface RawFile {
    name: string;
    path: string;
    size_bytes?: number;
    lines?: number;
    language?: string;
    moons?: any[];
  }

  const rawFiles: RawFile[] = [];

  if (scanData.constellations && Array.isArray(scanData.constellations)) {
    scanData.constellations.forEach((c: any) => {
      if (c.stars && Array.isArray(c.stars)) {
        c.stars.forEach((s: any) => {
          if (s.planets && Array.isArray(s.planets)) {
            s.planets.forEach((p: any) => {
              rawFiles.push({
                name: p.name,
                path: (p.path || p.name).replace(/\\/g, "/"),
                size_bytes: p.size_bytes || 1000,
                lines: p.lines || 25,
                language: p.language || p.name.split(".").pop() || "text",
                moons: p.moons || [],
              });
            });
          }
        });
      }
    });
  }

  // 2. Separate into Top-Level Folders and Root-Level Files
  // Top-level folders are the first directory component in relative paths: e.g. "backend/api/auth.py" -> "backend"
  const folderBuckets = new Map<string, RawFile[]>();
  const rootFiles: RawFile[] = [];

  rawFiles.forEach((file) => {
    const parts = file.path.split("/").filter(Boolean);
    if (parts.length > 1) {
      const topFolder = parts[0];
      if (!folderBuckets.has(topFolder)) {
        folderBuckets.set(topFolder, []);
      }
      folderBuckets.get(topFolder)!.push(file);
    } else {
      rootFiles.push(file);
    }
  });

  // 3. Exactly ONE Central Star representing the currently selected repository
  graph.push({
    id: starId,
    kind: "star",
    name: repoName,
    parentId: null,
    position: { x: 0, y: 0, z: 0 },
    scale: 1.0,
    color: "#f59e0b",
    atmosphereColor: "#fbbf24",
    fileCount: rawFiles.length,
    description: "Repository Central Star",
  });

  // 4. Folder Planets (folders orbit the central repository star in separated tracks)
  const folderNames = Array.from(folderBuckets.keys()).sort();
  const totalFolders = folderNames.length;
  const planetsPerTrack = totalFolders > 8 ? 3 : totalFolders > 4 ? 2 : 1;
  const baseOrbitRadius = 8.5;
  const trackSpacing = 4.8;

  folderNames.forEach((folderName, index) => {
    const filesInFolder = folderBuckets.get(folderName)!;
    const folderId = `folder-${folderName}`;
    const visual = getFolderVisualIdentity(folderName);

    const trackIndex = Math.floor(index / planetsPerTrack);
    const slotIndex = index % planetsPerTrack;
    const orbitRadius = baseOrbitRadius + trackIndex * trackSpacing;
    const pAngle = (slotIndex * (2 * Math.PI)) / planetsPerTrack + trackIndex * 0.95;
    const orbitSpeed = 0.032 / Math.sqrt(orbitRadius / baseOrbitRadius);

    // Aggregate folder metrics
    const totalBytes = filesInFolder.reduce((sum, f) => sum + (f.size_bytes || 1000), 0);
    const normalizedFiles = Math.min(filesInFolder.length / 25, 1.0);
    const normalizedSize = Math.min(totalBytes / 150000, 1.0);
    const folderScale = Math.min(Math.max(1.15 + normalizedFiles * 0.45 + normalizedSize * 0.25, 1.15), 1.85);

    // Compute language breakdown for folder
    const langCounts: Record<string, number> = {};
    filesInFolder.forEach((f) => {
      const l = f.language || "text";
      langCounts[l] = (langCounts[l] || 0) + 1;
    });

    graph.push({
      id: folderId,
      kind: "folder",
      name: folderName,
      parentId: starId,
      filePath: folderName,
      description: `${filesInFolder.length} files • ${folderName}/`,
      language: filesInFolder[0]?.language || "folder",
      position: {
        x: orbitRadius * Math.cos(pAngle),
        y: 0,
        z: orbitRadius * Math.sin(pAngle),
      },
      scale: folderScale,
      color: visual.color,
      atmosphereColor: visual.atmosphereColor,
      orbitRadius,
      orbitSpeed,
      inclination: ((index % 5) - 2) * 0.03,
      direction: index % 2 === 0 ? 1 : -1,
      roughness: 0.65,
      metalness: 0.12,
      fileCount: filesInFolder.length,
      hasRings: index % 3 === 0,
    });

    // 5. File Moons orbiting their parent folder planet
    filesInFolder.forEach((file, fIdx) => {
      const fileId = `file-${file.path}`;
      const ext = file.name.includes(".") ? file.name.split(".").pop() || "" : "";
      const fileVisual = getFileVisualIdentity(file.path, file.language);

      const mOrbitRadius = folderScale * 1.75 + fIdx * 0.75;
      const mOrbitSpeed = 0.12 / (1 + fIdx * 0.12);
      const mPhase = (fIdx * (2 * Math.PI)) / Math.max(1, filesInFolder.length) + fIdx * 0.45;

      graph.push({
        id: fileId,
        kind: "file",
        name: file.name,
        parentId: folderId,
        filePath: file.path,
        description: file.path,
        language: file.language || ext || "text",
        position: { x: 0, y: 0, z: 0 },
        scale: 0.22,
        color: fileVisual.color,
        atmosphereColor: fileVisual.atmosphereColor,
        orbitRadius: mOrbitRadius,
        orbitSpeed: mOrbitSpeed,
        inclination: ((fIdx % 3) - 1) * 0.18,
        direction: fIdx % 2 === 0 ? 1 : -1,
      });
    });
  });

  // 6. Root-Level Files (files with no parent folder, e.g. README.md, package.json)
  rootFiles.forEach((file, rIdx) => {
    const fileId = `file-${file.path}`;
    const ext = file.name.includes(".") ? file.name.split(".").pop() || "" : "";
    const fileVisual = getFileVisualIdentity(file.path, file.language);

    const starOrbitRadius = 3.6 + rIdx * 0.7;
    const starOrbitSpeed = 0.07 / (1 + rIdx * 0.08);

    graph.push({
      id: fileId,
      kind: "file",
      name: file.name,
      parentId: starId,
      filePath: file.path,
      description: file.path,
      language: file.language || ext || "text",
      position: { x: 0, y: 0, z: 0 },
      scale: 0.22,
      color: fileVisual.color,
      atmosphereColor: fileVisual.atmosphereColor,
      orbitRadius: starOrbitRadius,
      orbitSpeed: starOrbitSpeed,
      inclination: ((rIdx % 4) - 1.5) * 0.12,
      direction: rIdx % 2 === 0 ? 1 : -1,
    });
  });

  return graph;
}

// ─── Context Interface ────────────────────────────────────────────────────────

interface NavigationContextValue {
  // 3D Scene / Space Graph
  spaceGraph: SpaceObject[];
  focusId: string;
  breadcrumbs: SpaceObject[];
  displayedId: string;
  hoveredId: string | null;
  isTransitioning: boolean;
  navigateTo: (id: string) => void;
  goBack: () => void;
  jumpTo: (id: string) => void;
  hover: (id: string | null) => void;
  reportArrived: () => void;
  refreshScan: () => Promise<void>;
  isScanning: boolean;

  // Theme
  themeColors: ThemeColors;

  // AI Orb / Mission Control
  isMissionControlOpen: boolean;
  setMissionControlOpen: (open: boolean) => void;
  showSkillsPanel: boolean;
  setShowSkillsPanel: (open: boolean) => void;
  // Chat state lives in hooks/useChat.tsx (ChatProvider) — see PHASE 12 isolation.
  /** Persistent selection (highlight) — distinct from focus/navigation. */
  selectedId: string | null;
  selectObject: (id: string | null) => void;
  /** Cut: body ids hidden from the universe view (view-state only). */
  cutIds: Set<string>;
  cutObject: (id: string) => void;
  restoreAll: () => void;
  isCut: (id: string) => boolean;

  // Active File Details
  activeFileContent: string | null;
  activeFileDetails: ObjectDetails | null;

  // Workspace status
  workspaceStatus: {
    status: string;
    repo_name: string;
    error_message: string;
    current_path?: string;
  };
  triggerSelectWorkspace: (path: string) => Promise<void>;
  triggerCloneWorkspace: (url: string) => Promise<void>;
  triggerIndexWorkspace: () => Promise<void>;
  repositories: RepositorySummary[];
  recentFiles: RecentFile[];
  bookmarks: Bookmark[];
}

const NavigationContext = createContext<NavigationContextValue | null>(null);

// ─── Provider ────────────────────────────────────────────────────────────────

export function NavigationProvider({ children }: { children: ReactNode }) {
  const { getAccessToken } = useAuth();
  const [spaceGraph, setSpaceGraph] = useState<SpaceObject[]>([]);
  const [themeColors, setThemeColors] = useState<ThemeColors>(DEFAULT_THEME);
  const [isScanning, setIsScanning] = useState(false);

  const rootId = useMemo(
    () => spaceGraph.find((o) => o.parentId === null)?.id ?? "repository-star",
    [spaceGraph]
  );

  const [focusId, setFocusId] = useState("repository-star");
  const [displayedId, setDisplayedId] = useState("repository-star");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Mission Control / Skills panel (chat state lives in useChat — PHASE 12
  // isolation: streaming updates must not re-render the 3D universe)
  const [isMissionControlOpen, setMissionControlOpen] = useState(false);
  const [showSkillsPanel, setShowSkillsPanel] = useState(false);

  // File Details
  const [activeFileContent, setActiveFileContent] = useState<string | null>(null);
  const [activeFileDetails, setActiveFileDetails] = useState<ObjectDetails | null>(null);

  // Workspace Status
  const [workspaceStatus, setWorkspaceStatus] = useState<{
    status: string;
    repo_name: string;
    error_message: string;
    current_path?: string;
  }>({ status: "ready", repo_name: "", error_message: "" });

  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [recentFiles, setRecentFiles] = useState<RecentFile[]>([]);
  const [bookmarks] = useState<Bookmark[]>([]);

  // PHASE 21 — monotonically increasing call id for stale-response guards
  const refreshScanSeq = useRef(0);

  // ── Sync focusId / displayedId with rootId on graph load
  useEffect(() => {
    setFocusId(rootId);
    setDisplayedId(rootId);
  }, [rootId]);

  // ── Fetch theme from backend on startup
  useEffect(() => {
    apiFetch(`/api/theme`)
      .then((r) => r.json())
      .then((data) => {
        if (data?.palette) {
          const p = data.palette;
          setThemeColors({
            universe_bg: p.universe_bg || DEFAULT_THEME.universe_bg,
            galaxy_accent: p.galaxy_accent || DEFAULT_THEME.galaxy_accent,
            star_color: p.star_color || DEFAULT_THEME.star_color,
            planet_color: p.planet_color || DEFAULT_THEME.planet_color,
            moon_color: p.moon_color || DEFAULT_THEME.moon_color,
            constellation_colors: p.constellation_colors || DEFAULT_THEME.constellation_colors,
            glass_bg: p.glass_bg || DEFAULT_THEME.glass_bg,
            glass_border: p.glass_border || DEFAULT_THEME.glass_border,
            neon_shadow: p.neon_shadow || DEFAULT_THEME.neon_shadow,
          });
        }
      })
      .catch(() => {
        // Backend offline — use defaults silently
      });
  }, []);

  // ── Poll workspace status every 3s
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await apiFetch(`/api/workspace/status`);
        if (res.ok) {
          const data = await res.json();
          setWorkspaceStatus(data);
        }
      } catch {
        // Silently fail
      }
    };
    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, []);

  // ── Fetch workspace scan tree and build 3D graph
  const refreshScan = useCallback(async () => {
    // PHASE 21 — stale-response guard: overlapping calls (manual refresh +
    // post-index refresh) must not apply out-of-order results.
    const callId = ++refreshScanSeq.current;
    setIsScanning(true);
    try {
      const [scanRes, summaryRes] = await Promise.all([
        apiFetch(`/api/scan`),
        apiFetch(`/api/summary`),
      ]);

      if (callId !== refreshScanSeq.current) return; // a newer call superseded this one

      if (scanRes.ok) {
        const scanData = await scanRes.json();
        const graph = buildSpaceGraphFromScan(scanData, themeColors);
        if (graph.length > 0) {
          setSpaceGraph(graph);
        }
      }

      if (summaryRes.ok) {
        const summary = await summaryRes.json();
        const repoName =
          summary.title?.replace("Galaxy: ", "") || workspaceStatus.repo_name || "active-repo";
        setRepositories([
          {
            id: "repo-active",
            name: repoName,
            description: summary.readme_summary || "Active Repository",
            language: summary.tech_stack?.join(" / ") || "Multi",
            updatedAt: "Active Now",
            starCount: summary.file_metrics?.total_files || 0,
          },
        ]);
        if (summary.entry_points?.length > 0) {
          setRecentFiles(
            summary.entry_points.map((p: string, idx: number) => ({
              id: `rf-${idx}`,
              name: p.split("/").pop() || p,
              path: p,
              openedAt: "Entry Point",
            }))
          );
        }
      }
    } catch (e) {
      console.error("Backend scan failed:", e);
    } finally {
      if (callId === refreshScanSeq.current) setIsScanning(false);
    }
  }, [themeColors, workspaceStatus.repo_name]);

  // ── Fetch details when a folder planet/file moon/repository star is selected
  useEffect(() => {
    if (!displayedId) return;

    const object = spaceGraph.find((o) => o.id === displayedId);
    if (!object) return;

    const isFolder = object.kind === "folder" || object.kind === "planet";
    const isFile = object.kind === "file" || object.kind === "moon";

    if (isFolder) {
      // 🪐 Folder Planet Selected
      setActiveFileContent(null);
      const childFiles = spaceGraph.filter(
        (o) => (o.kind === "file" || o.kind === "moon") && o.parentId === object.id
      );

      // Compute folder metrics and language breakdown
      const langCounts: Record<string, number> = {};
      childFiles.forEach((cf) => {
        const lang = cf.language || "text";
        langCounts[lang] = (langCounts[lang] || 0) + 1;
      });

      const totalFilesCount = childFiles.length;
      const languagesBreakdown = Object.entries(langCounts)
        .map(([language, count]) => ({
          language,
          percentage: totalFilesCount > 0 ? Math.round((count / totalFilesCount) * 100) : 0,
        }))
        .sort((a, b) => b.percentage - a.percentage);

      const topFiles = childFiles.slice(0, 8).map((cf) => cf.name);

      setActiveFileDetails({
        id: object.id,
        name: object.name,
        type: "folder",
        description: `${object.name}/`,
        language: languagesBreakdown[0]?.language,
        dependencies: [],
        summary: `Contains ${totalFilesCount} file${totalFilesCount !== 1 ? "s" : ""} across ${languagesBreakdown.map((l) => `${l.language} (${l.percentage}%)`).join(", ") || "various types"}.`,
        fileCount: totalFilesCount,
        folderCount: (object as any).folderCount || 0,
        languagesBreakdown,
        topFiles,
        stats: [
          { label: "Files", value: String(totalFilesCount) },
          { label: "Primary Language", value: languagesBreakdown[0]?.language || "None" },
          { label: "Track Radius", value: `${(object.orbitRadius || 0).toFixed(1)} AU` },
        ],
        codePreview: [],
        symbols: [],
      });
    } else if (isFile) {
      // 🌙 File Moon Selected
      const filePath = (object as any).filePath || object.name;
      const parentFolder = spaceGraph.find((o) => o.id === object.parentId);

      const fetchFile = async () => {
        try {
          const res = await apiFetch(`/api/file?path=${encodeURIComponent(filePath)}`);
          if (!res.ok) return;
          const data = await res.json();

          setActiveFileContent(data.content);

          const lines = data.content ? data.content.split("\n").length : 0;
          const symbols = data.symbols || [];
          const functions = symbols.filter((s: any) => s.type === "function").length;
          const classes = symbols.filter((s: any) => s.type === "class").length;
          const imports = data.imports || [];

          const previewLines = (data.content || "")
            .split("\n")
            .slice(0, 30)
            .map((line: string, i: number) => ({ line: i + 1, content: line }));

          setActiveFileDetails({
            id: object.id,
            name: object.name,
            type: "file",
            description: filePath,
            language: data.language || (object as any).language || "text",
            dependencies: imports,
            summary: `${classes} class${classes !== 1 ? "es" : ""}, ${functions} function${functions !== 1 ? "s" : ""}, ${lines} lines, ${imports.length} imports`,
            stats: [
              { label: "Lines", value: String(lines) },
              { label: "Functions", value: String(functions) },
              { label: "Classes", value: String(classes) },
              { label: "Imports", value: String(imports.length) },
            ],
            codePreview: previewLines,
            symbols,
            parentFolderId: parentFolder?.id,
            parentFolderName: parentFolder?.name,
          });
        } catch (e) {
          console.error("Failed to fetch file details:", e);
        }
      };

      fetchFile();
    } else {
      // ⭐ Repository Central Star Selected
      setActiveFileContent(null);
      const folderPlanets = spaceGraph.filter((o) => o.kind === "folder" || o.kind === "planet");
      const fileMoons = spaceGraph.filter((o) => o.kind === "file" || o.kind === "moon");

      setActiveFileDetails({
        id: object.id,
        name: object.name,
        type: "star",
        description: "Repository Central Star",
        language: repositories[0]?.language,
        dependencies: [],
        summary:
          repositories[0]?.description ||
          `Repository solar system: ${folderPlanets.length} folder planets and ${fileMoons.length} files.`,
        stats: [
          { label: "Folders", value: String(folderPlanets.length) },
          { label: "Total Files", value: String(fileMoons.length) },
          { label: "Language", value: repositories[0]?.language || "Multi" },
        ],
        codePreview: [],
        symbols: [],
      });
    }
  }, [displayedId, spaceGraph, repositories]);

  // ── Breadcrumb chain
  const getAncestorChain = useCallback(
    (id: string): SpaceObject[] => {
      const chain: SpaceObject[] = [];
      let current = spaceGraph.find((o) => o.id === id);
      while (current) {
        chain.unshift(current);
        current = current.parentId
          ? spaceGraph.find((o) => o.id === current!.parentId)
          : undefined;
      }
      return chain;
    },
    [spaceGraph]
  );

  const breadcrumbs = useMemo(
    () => getAncestorChain(focusId),
    [focusId, getAncestorChain]
  );

  const navigateTo = useCallback(
    (id: string) => {
      if (id === focusId) return;
      setFocusId(id);
      setDisplayedId(id);
      setIsTransitioning(true);
    },
    [focusId]
  );

  const goBack = useCallback(() => {
    const current = spaceGraph.find((o) => o.id === focusId);
    if (current?.parentId) navigateTo(current.parentId);
  }, [focusId, spaceGraph, navigateTo]);

  const jumpTo = useCallback(
    (id: string) => navigateTo(id),
    [navigateTo]
  );

  const reportArrived = useCallback(() => {
    setIsTransitioning(false);
    setDisplayedId(focusId);
  }, [focusId]);

  // ── WebSocket Chat — moved to hooks/useChat.tsx (PHASE 12 isolation).
  // submitMessage previously lived here and re-rendered the universe per
  // streaming frame; it now lives in the dedicated ChatProvider.

  // ── Workspace Actions
  const triggerSelectWorkspace = useCallback(async (path: string) => {
    try {
      await apiFetch(`/api/workspace/select`, {
        method: "POST",
        body: JSON.stringify({ path }),
      });
    } catch (e) {
      console.error("Select workspace error:", e);
    }
  }, []);

  const triggerCloneWorkspace = useCallback(async (url: string) => {
    try {
      await apiFetch(`/api/clone`, {
        method: "POST",
        body: JSON.stringify({ repo_url: url }),
      });
    } catch (e) {
      console.error("Clone workspace error:", e);
    }
  }, []);

  const triggerIndexWorkspace = useCallback(async () => {
    try {
      await apiFetch(`/api/index`, { method: "POST" });
      setTimeout(refreshScan, 2000);
    } catch (e) {
      console.error("Index error:", e);
    }
  }, [refreshScan]);

  // ── Selection (persistent highlight — distinct from focus/navigation) ────
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectObject = useCallback((id: string | null) => {
    setSelectedId((prev) => (prev === id ? null : id));
  }, []);

  // ── Cut (PHASE 15/16) — hides a body from the universe (view-state only,
  // never mutates the repository or the spaceGraph itself).
  const [cutIds, setCutIds] = useState<Set<string>>(new Set());
  const cutObject = useCallback((id: string) => {
    const target = spaceGraph.find((o) => o.id === id);
    const fallbackId = target?.parentId || rootId;

    // 1. Mark as cut
    setCutIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });

    // 2. Clear from selection and position registry
    setSelectedId((prev) => (prev === id ? null : prev));
    positionsRegistry.clear(id);

    // 3. Smoothly navigate camera & display back to parent or root star
    if (focusId === id || displayedId === id) {
      setFocusId(fallbackId);
      setDisplayedId(fallbackId);
      setIsTransitioning(true);
    }
  }, [spaceGraph, rootId, focusId, displayedId]);

  const restoreAll = useCallback(() => setCutIds(new Set()), []);
  const isCut = useCallback((id: string) => cutIds.has(id), [cutIds]);

  const value = useMemo(
    () => ({
      spaceGraph,
      focusId,
      breadcrumbs,
      displayedId,
      hoveredId,
      isTransitioning,
      navigateTo,
      goBack,
      jumpTo,
      hover: setHoveredId,
      reportArrived,
      refreshScan,
      isScanning,
      themeColors,
      isMissionControlOpen,
      setMissionControlOpen,
      showSkillsPanel,
      setShowSkillsPanel,
      selectedId,
      selectObject,
      cutIds,
      cutObject,
      restoreAll,
      isCut,
      activeFileContent,
      activeFileDetails,
      workspaceStatus,
      triggerSelectWorkspace,
      triggerCloneWorkspace,
      triggerIndexWorkspace,
      repositories,
      recentFiles,
      bookmarks,
    }),
    [
      spaceGraph, focusId, breadcrumbs, displayedId, hoveredId, isTransitioning,
      navigateTo, goBack, jumpTo, reportArrived, refreshScan, isScanning, themeColors,
      isMissionControlOpen, showSkillsPanel, selectedId, selectObject, cutIds, cutObject,
      restoreAll, isCut, activeFileContent, activeFileDetails,
      workspaceStatus, triggerSelectWorkspace, triggerCloneWorkspace, triggerIndexWorkspace,
      repositories, recentFiles, bookmarks,
    ]
  );

  return createElement(NavigationContext.Provider, { value }, children);
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useNavigation() {
  const ctx = useContext(NavigationContext);
  if (!ctx) throw new Error("useNavigation must be used within a NavigationProvider");
  return ctx;
}
