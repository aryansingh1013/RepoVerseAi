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
  ChatMessage,
  ObjectDetails,
  RepositorySummary,
  RecentFile,
  Bookmark,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const WS_BASE = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000";


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

// ─── Build Space Graph from Backend Scan ─────────────────────────────────────

function buildSpaceGraphFromScan(scanData: any, theme: ThemeColors): SpaceObject[] {
  const graph: SpaceObject[] = [];
  if (!scanData) return graph;

  const repoName = scanData.galaxy || "Repository";
  const galaxyId = "galaxy-root";

  // 1. Repository node (galaxy core)
  graph.push({
    id: galaxyId,
    kind: "galaxy",
    name: repoName,
    parentId: null,
    position: { x: 0, y: 0, z: 0 },
    scale: 1.0,
    color: theme.galaxy_accent,
    atmosphereColor: "#3a1a7d",
  });

  if (!scanData.constellations || scanData.constellations.length === 0) return graph;

  // 2. Flatten all stars, keeping track of their constellation
  const allStars: Array<{ star: any; constellationName: string }> = [];
  scanData.constellations.forEach((c: any) => {
    if (c.stars) {
      c.stars.forEach((s: any) => {
        allStars.push({ star: s, constellationName: c.name });
      });
    }
  });

  // 3. Stars (folders)
  allStars.forEach(({ star, constellationName }, starIndex) => {
    const starId = `star-${star.path || star.name}`;
    const fileCount = star.planets ? star.planets.length : 0;
    const totalStars = allStars.length;
    // Spread stars out wider
    const orbitRadius = 9.0 + starIndex * 4.5;
    const orbitSpeed = 0.012 + 0.04 / (starIndex + 1);
    const angle = (starIndex * (2 * Math.PI)) / Math.max(1, totalStars);

    const starColor = getConstellationColor(constellationName, theme);

    // Stars (Folders): Scale depends on number of files it contains
    const starScale = 0.8 + Math.min(fileCount / 12, 1.0) * 0.7;

    graph.push({
      id: starId,
      kind: "star",
      name: star.name === "core" ? repoName : `${star.name}/`,
      parentId: galaxyId,
      // Store constellation name for display
      description: constellationName,
      position: {
        x: orbitRadius * Math.cos(angle),
        y: (Math.random() - 0.5) * 0.8,
        z: orbitRadius * Math.sin(angle),
      },
      fileCount,
      scale: starScale,
      color: starColor,
      atmosphereColor: starColor + "80",
      orbitRadius,
      orbitSpeed,
      inclination: (Math.random() - 0.5) * 0.4,
      direction: Math.random() > 0.5 ? 1 : -1,
    });

    // 4. Planets (files) orbiting each star
    if (star.planets) {
      star.planets.forEach((planet: any, planetIndex: number) => {
        const planetId = `planet-${planet.path}`;
        // Spread planets out wider
        const pOrbitRadius = 2.5 + planetIndex * 1.5;
        const pOrbitSpeed = 0.1 + 0.2 / (planetIndex + 1);
        const pAngle = (planetIndex * (2 * Math.PI)) / Math.max(1, star.planets.length);
        const lang = planet.language || "text";

        // Planets (Files): Scale depends on file size in bytes
        const fileBytes = planet.size_bytes || 1000;
        const planetScale = 0.15 + Math.min(fileBytes / 20000, 1.0) * 0.25;

        graph.push({
          id: planetId,
          kind: "planet",
          name: planet.name,
          parentId: starId,
          // Store real file path for API calls
          filePath: planet.path,
          language: lang,
          position: {
            x: pOrbitRadius * Math.cos(pAngle),
            y: (Math.random() - 0.5) * 0.3,
            z: pOrbitRadius * Math.sin(pAngle),
          },
          scale: planetScale,
          color: getLanguageColor(lang, theme),
          atmosphereColor: getLanguageAtmosphereColor(lang),
          orbitRadius: pOrbitRadius,
          orbitSpeed: pOrbitSpeed,
          inclination: (Math.random() - 0.5) * 0.3,
          direction: Math.random() > 0.5 ? 1 : -1,
          roughness: 0.55,
          metalness: 0.15,
          hasRings: planetIndex % 4 === 0,
        });
      });
    }
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
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  input: string;
  setInput: (val: string) => void;
  isStreaming: boolean;
  agentSteps: string[];
  activeStep: string;
  submitMessage: () => void;
  selectedMessageId: string | null;
  setSelectedMessageId: (id: string | null) => void;

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
  const [spaceGraph, setSpaceGraph] = useState<SpaceObject[]>([]);
  const [themeColors, setThemeColors] = useState<ThemeColors>(DEFAULT_THEME);
  const [isScanning, setIsScanning] = useState(false);

  const rootId = useMemo(
    () => spaceGraph.find((o) => o.parentId === null)?.id ?? "galaxy-root",
    [spaceGraph]
  );

  const [focusId, setFocusId] = useState("galaxy-root");
  const [displayedId, setDisplayedId] = useState("galaxy-root");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // AI Chat / Mission Control
  const [isMissionControlOpen, setMissionControlOpen] = useState(false);
  const [showSkillsPanel, setShowSkillsPanel] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentSteps, setAgentSteps] = useState<string[]>([]);
  const [activeStep, setActiveStep] = useState("");
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

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

  // ── Sync focusId / displayedId with rootId on graph load
  useEffect(() => {
    setFocusId(rootId);
    setDisplayedId(rootId);
  }, [rootId]);

  // ── Fetch theme from backend on startup
  useEffect(() => {
    fetch(`${API_BASE}/api/theme`)
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
        const res = await fetch(`${API_BASE}/api/workspace/status`);
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
    setIsScanning(true);
    try {
      const [scanRes, summaryRes] = await Promise.all([
        fetch(`${API_BASE}/api/scan`),
        fetch(`${API_BASE}/api/summary`),
      ]);

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
      setIsScanning(false);
    }
  }, [themeColors, workspaceStatus.repo_name]);

  // ── Fetch file details when a planet/star/moon is selected
  useEffect(() => {
    if (!displayedId) return;

    const object = spaceGraph.find((o) => o.id === displayedId);
    if (!object) return;

    const isPlanet = object.kind === "planet";
    const isMoon = object.kind === "moon";

    if (isPlanet || isMoon) {
      // It's a file or a symbol inside a file — fetch parent file content and symbols
      let filePath = "";
      let planetName = "";
      let planetId = "";

      if (isPlanet) {
        filePath = (object as any).filePath || object.id.replace("planet-", "");
        planetName = object.name;
        planetId = object.id;
      } else {
        const parentPlanet = spaceGraph.find(o => o.id === object.parentId);
        if (parentPlanet) {
          filePath = (parentPlanet as any).filePath || parentPlanet.id.replace("planet-", "");
          planetName = parentPlanet.name;
          planetId = parentPlanet.id;
        } else {
          filePath = object.id.replace("moon-", "").split("-")[0];
          planetName = filePath.split("/").pop() || "File";
          planetId = `planet-${filePath}`;
        }
      }

      const fetchFile = async () => {
        try {
          const res = await fetch(
            `${API_BASE}/api/file?path=${encodeURIComponent(filePath)}`
          );
          if (!res.ok) return;
          const data = await res.json();

          setActiveFileContent(data.content);

          const lines = data.content ? data.content.split("\n").length : 0;
          const functions = (data.symbols || []).filter((s: any) => s.type === "function").length;
          const classes = (data.symbols || []).filter((s: any) => s.type === "class").length;

          const previewLines = (data.content || "")
            .split("\n")
            .slice(0, 25)
            .map((line: string, i: number) => ({ line: i + 1, content: line }));

          if (isPlanet) {
            setActiveFileDetails({
              id: displayedId,
              name: object.name,
              type: "planet",
              description: `${filePath}`,
              language: data.language || (object as any).language || "text",
              dependencies: data.imports || [],
              summary: `${classes} class${classes !== 1 ? "es" : ""}, ${functions} function${functions !== 1 ? "s" : ""}, ${lines} lines`,
              stats: [
                { label: "Lines", value: String(lines) },
                { label: "Functions", value: String(functions) },
                { label: "Classes", value: String(classes) },
                { label: "Imports", value: String((data.imports || []).length) },
              ],
              codePreview: previewLines,
              symbols: data.symbols || [],
            });
          } else {
            // It's a moon (symbol)
            setActiveFileDetails({
              id: object.id,
              name: object.name,
              type: "moon",
              description: `Symbol in file: ${filePath}`,
              language: data.language || "text",
              dependencies: [],
              summary: (object as any).symbolSummary || `Line ${(object as any).symbolLine || "?"}`,
              stats: [
                { label: "Start Line", value: String((object as any).symbolLine || 1) },
                { label: "Symbol Type", value: String((object as any).symbolType || "definition") },
                { label: "File Lines", value: String(lines) },
              ],
              codePreview: previewLines,
              symbols: [],
              parentPlanetId: planetId,
              parentPlanetName: planetName,
              parentPlanetPath: filePath
            } as any);
          }

          // Inject moons (symbols) into the spaceGraph
          if (isPlanet && data.symbols && data.symbols.length > 0) {
            setSpaceGraph((prev) => {
              const cleaned = prev.filter(
                (o) => !(o.kind === "moon" && o.parentId === displayedId)
              );
              const moons: SpaceObject[] = data.symbols
                .slice(0, 10)
                .map((sym: any, idx: number) => {
                  // Spread moons out wider from the parent planet
                  const mOrbit = 0.8 + idx * 0.45;
                  const mAngle = (idx * (2 * Math.PI)) / Math.max(1, Math.min(10, data.symbols.length));

                  // Calculate symbol length in lines
                  const symbolLines = (sym.end_line && sym.start_line)
                    ? (sym.end_line - sym.start_line + 1)
                    : 10;
                  
                  // Scale moon proportionally, keeping them much smaller than planets
                  const moonScale = 0.04 + Math.min(symbolLines / 150, 1.0) * 0.06;

                  return {
                    id: `moon-${filePath}-${sym.name}`,
                    kind: "moon" as const,
                    name: sym.type === "class" ? `class ${sym.name}` : `${sym.name}()`,
                    parentId: displayedId,
                    symbolType: sym.type,
                    symbolLine: sym.start_line,
                    symbolSummary: sym.summary || "",
                    position: {
                      x: mOrbit * Math.cos(mAngle),
                      y: 0,
                      z: mOrbit * Math.sin(mAngle),
                    },
                    scale: moonScale,
                    color: sym.type === "class" ? "#c084fc" : "#FBBF24",
                    orbitRadius: mOrbit,
                    orbitSpeed: 0.3 + 0.12 / (idx + 1),
                    inclination: (Math.random() - 0.5) * 0.5,
                    direction: idx % 2 === 0 ? 1 : -1,
                  };
                });
              return [...cleaned, ...moons];
            });
          }
        } catch (e) {
          console.error("Failed to fetch file/symbol details:", e);
        }
      };

      fetchFile();
    } else {
      // Star, galaxy — clear file details
      setActiveFileContent(null);
      setActiveFileDetails({
        id: object.id,
        name: object.name,
        type: object.kind,
        description:
          object.kind === "galaxy"
            ? "Repository root — the galaxy core"
            : object.kind === "star"
            ? `Folder containing ${object.fileCount ?? 0} files`
            : `${(object as any).symbolType || "symbol"} — line ${(object as any).symbolLine || "?"}`,
        language: undefined,
        dependencies: [],
        summary:
          object.kind === "star"
            ? `This folder contains ${object.fileCount ?? 0} files spread across the codebase.`
            : object.kind === "galaxy"
            ? `The galaxy core — root of the entire repository.`
            : `${(object as any).symbolSummary || "Code symbol"}`,
        stats:
          object.kind === "star"
            ? [{ label: "Files", value: String(object.fileCount ?? 0) }]
            : [],
        codePreview: [],
        symbols: [],
      });
    }
  }, [displayedId, spaceGraph]);

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

  // ── WebSocket Chat
  const submitMessage = useCallback(() => {
    if (!input.trim()) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      text: input,
    };

    setMessages((prev) => [...prev, userMsg]);
    const query = input;
    setInput("");
    setAgentSteps([]);
    setIsStreaming(true);

    const ws = new WebSocket(`${WS_BASE}/ws/chat`);
    const assistantId = `a-${Date.now()}`;
    setSelectedMessageId(assistantId);

    ws.onopen = () => ws.send(query);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "step") {
        setActiveStep(msg.content);
        setAgentSteps((prev) => [...prev, msg.content]);
      } else if (msg.type === "response") {
        setMessages((prev) => {
          const exists = prev.some((m) => m.id === assistantId);
          if (!exists) {
            return [...prev, { id: assistantId, role: "assistant", text: msg.content, steps: [] }];
          }
          return prev.map((m) => (m.id === assistantId ? { ...m, text: msg.content } : m));
        });
      } else if (msg.type === "citations") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, citations: msg.content } : m))
        );
      } else if (msg.type === "confidence") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, confidence: msg.content } : m))
        );
      } else if (msg.type === "reasoning_trace") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, trace: msg.content } : m))
        );
      } else if (msg.type === "goal_metadata") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, goal: msg.content } : m))
        );
      } else if (msg.type === "tasks_metadata") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, tasks: msg.content } : m))
        );
      } else if (msg.type === "reflection_status") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, reflection: msg.content } : m))
        );
      } else if (msg.type === "done") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m))
        );
        setIsStreaming(false);
        setActiveStep("");
        ws.close();
      } else if (msg.type === "error") {
        setMessages((prev) => [
          ...prev,
          { id: `err-${Date.now()}`, role: "assistant", text: `⚠️ ${msg.content}` },
        ]);
        setIsStreaming(false);
        setActiveStep("");
        ws.close();
      }
    };

    ws.onclose = () => { setIsStreaming(false); setActiveStep(""); };
    ws.onerror = () => { setIsStreaming(false); setActiveStep(""); };
  }, [input]);

  // ── Workspace Actions
  const triggerSelectWorkspace = useCallback(async (path: string) => {
    try {
      await fetch(`${API_BASE}/api/workspace/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
    } catch (e) {
      console.error("Select workspace error:", e);
    }
  }, []);

  const triggerCloneWorkspace = useCallback(async (url: string) => {
    try {
      await fetch(`${API_BASE}/api/clone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url }),
      });
    } catch (e) {
      console.error("Clone workspace error:", e);
    }
  }, []);

  const triggerIndexWorkspace = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/api/index`, { method: "POST" });
      setTimeout(refreshScan, 2000);
    } catch (e) {
      console.error("Index error:", e);
    }
  }, [refreshScan]);

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
      messages,
      setMessages,
      input,
      setInput,
      isStreaming,
      agentSteps,
      activeStep,
      submitMessage,
      selectedMessageId,
      setSelectedMessageId,
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
      isMissionControlOpen, showSkillsPanel, messages, input, isStreaming, agentSteps, activeStep,
      submitMessage, selectedMessageId, activeFileContent, activeFileDetails,
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
