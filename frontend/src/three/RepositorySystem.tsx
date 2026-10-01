import { useMemo } from "react";
import { useNavigation } from "@/hooks/useNavigation";
import { RepositoryStar } from "./RepositoryStar";
import { FilePlanet } from "./FilePlanet";
import { getLanguageVisualIdentity } from "./PlanetTextures";
import type {
  RepositorySystemData,
  RepositoryNode,
  FilePlanet as FilePlanetType,
  SymbolMoon as SymbolMoonType,
} from "./sceneTypes";

export function RepositorySystem() {
  const { spaceGraph, workspaceStatus, repositories } = useNavigation();

  const systemData: RepositorySystemData = useMemo(() => {
    // 1. Find Central Star (Repository Root)
    const rootNode =
      spaceGraph.find((o) => o.parentId === null) ||
      spaceGraph.find((o) => o.kind === "star" || o.kind === "galaxy");

    const repoName =
      repositories[0]?.name ||
      workspaceStatus.repo_name ||
      rootNode?.name ||
      "Repository";

    const repository: RepositoryNode = {
      id: rootNode?.id || "repository-root",
      name: repoName,
      description: repositories[0]?.description || "Repository central star",
      fileCount: 0,
      languages: [],
      color: "#f59e0b", // Radiant warm solar amber
      radius: 1.75,
    };

    // 2. Extract all file planets from spaceGraph
    const planetNodes = spaceGraph.filter((o) => o.kind === "planet");
    const moonNodes = spaceGraph.filter((o) => o.kind === "moon");

    repository.fileCount = planetNodes.length;

    // Determine orbital layout parameters
    // Spread planets across distinct separated orbital radii
    const planetsPerTrack = planetNodes.length > 24 ? 3 : planetNodes.length > 12 ? 2 : 1;
    const baseOrbitRadius = 4.8;
    const trackSpacing = 2.1;

    const languagesSet = new Set<string>();

    const planets: FilePlanetType[] = planetNodes.map((p, index) => {
      const filePath = p.filePath || (p as any).path || p.id.replace("planet-", "");
      const lang = p.language || filePath.split(".").pop() || "text";
      languagesSet.add(lang);

      const visual = getLanguageVisualIdentity(filePath, lang);

      // Directory metadata (folder is metadata only, NOT a celestial body)
      const dirParts = filePath.split("/");
      const directory = dirParts.length > 1 ? dirParts.slice(0, -1).join("/") : "";

      // Orbital placement: concentric separated bands
      const trackIndex = Math.floor(index / planetsPerTrack);
      const slotIndex = index % planetsPerTrack;
      const orbitRadius = baseOrbitRadius + trackIndex * trackSpacing;

      // Golden ratio angle offset + slot distribution so planets never cluster
      const angleOffset = (slotIndex * (2 * Math.PI)) / planetsPerTrack + trackIndex * 0.75;

      // Keplerian orbit speed (further bodies orbit slightly slower)
      const orbitSpeed = 0.045 / Math.sqrt(orbitRadius / baseOrbitRadius);

      // Extract moons that belong to this planet
      const relatedMoons = moonNodes.filter(
        (m) => m.parentId === p.id || m.parentId === filePath
      );

      // Sizing formula: normalize and clamp (Section 8)
      const fileBytes = (p as any).size_bytes || (p as any).size || 1500;
      const normalizedSize = Math.min(fileBytes / 30000, 1.0);
      const normalizedSymbols = Math.min(relatedMoons.length / 8, 1.0);
      const radius = Math.min(
        Math.max(0.38 + normalizedSize * 0.28 + normalizedSymbols * 0.12, 0.38),
        0.82
      );

      // Map moons
      const moons: SymbolMoonType[] = relatedMoons.map((m, mIdx) => {
        const symbolLines =
          (m as any).symbolEndLine && (m as any).symbolLine
            ? (m as any).symbolEndLine - (m as any).symbolLine + 1
            : 15;
        const moonRadius = Math.min(
          Math.max(0.14 + Math.min(symbolLines / 150, 1.0) * 0.06, 0.14),
          0.22
        );

        const mOrbitRadius = radius * 1.6 + mIdx * 0.42;
        const mOrbitSpeed = 0.12 / (1 + mIdx * 0.15);
        const mPhase = (mIdx * (2 * Math.PI)) / Math.max(1, relatedMoons.length);

        return {
          id: m.id,
          planetId: p.id,
          name: m.name,
          type: (m.symbolType as any) || "function",
          lineStart: m.symbolLine || 1,
          lineEnd: (m as any).symbolEndLine || m.symbolLine || 1,
          summary: m.symbolSummary || "",
          radius: moonRadius,
          orbitRadius: mOrbitRadius,
          orbitSpeed: mOrbitSpeed,
          orbitPhase: mPhase,
          inclination: ((mIdx % 3) - 1) * 0.18,
          direction: mIdx % 2 === 0 ? 1 : -1,
          color: m.symbolType === "class" ? "#c084fc" : (m.symbolType as string) === "method" ? "#38bdf8" : "#fbbf24",
        };
      });

      return {
        id: p.id,
        path: filePath,
        name: p.name,
        directory,
        language: lang,
        size: fileBytes,
        color: visual.color,
        atmosphereColor: visual.atmosphereColor,
        textureType: visual.textureType,
        radius,
        orbitRadius,
        orbitSpeed,
        orbitPhase: angleOffset,
        inclination: ((index % 7) - 3) * 0.035, // subtle natural orbital tilt
        direction: index % 2 === 0 ? 1 : -1,
        hasRings: Boolean(p.hasRings || index % 5 === 0),
        moons,
      };
    });

    repository.languages = Array.from(languagesSet);

    return { repository, planets };
  }, [spaceGraph, workspaceStatus.repo_name, repositories]);

  return (
    <group>
      {/* 1. Exactly ONE central star representing the repository */}
      <RepositoryStar repository={systemData.repository} />

      {/* 2. File Planets orbiting the central star */}
      {systemData.planets.map((planet) => (
        <FilePlanet key={planet.id} planet={planet} />
      ))}
    </group>
  );
}
