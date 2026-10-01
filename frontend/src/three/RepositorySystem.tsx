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

    // Star is large, majestic solar center
    const repository: RepositoryNode = {
      id: rootNode?.id || "repository-star",
      name: repoName,
      description: repositories[0]?.description || "Repository central star",
      fileCount: 0,
      languages: [],
      color: "#f59e0b", // Radiant warm solar amber
      radius: 2.8,
    };

    // 2. Extract all file planets from spaceGraph
    const planetNodes = spaceGraph.filter((o) => o.kind === "planet");
    const moonNodes = spaceGraph.filter((o) => o.kind === "moon");

    repository.fileCount = planetNodes.length;

    // Spacious planetary bands around the central star
    const planetsPerTrack = planetNodes.length > 24 ? 3 : planetNodes.length > 12 ? 2 : 1;
    const baseOrbitRadius = 8.2;
    const trackSpacing = 4.2;

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
      const angleOffset = (slotIndex * (2 * Math.PI)) / planetsPerTrack + trackIndex * 0.85;

      // Keplerian orbit speed (further bodies orbit slightly slower)
      const orbitSpeed = 0.038 / Math.sqrt(orbitRadius / baseOrbitRadius);

      // Extract moons that belong to this planet
      const relatedMoons = moonNodes.filter(
        (m) => m.parentId === p.id || m.parentId === filePath
      );

      // Sizing formula: Planets are substantial worlds (1.05 to 1.75 radius)
      const fileBytes = (p as any).size_bytes || (p as any).size || 1500;
      const normalizedSize = Math.min(fileBytes / 30000, 1.0);
      const normalizedSymbols = Math.min(relatedMoons.length / 8, 1.0);
      const radius = Math.min(
        Math.max(1.05 + normalizedSize * 0.45 + normalizedSymbols * 0.25, 1.05),
        1.75
      );

      // Moons are clearly smaller (0.16 to 0.24 radius) — a 5x to 7x ratio vs parent planet!
      const moons: SymbolMoonType[] = relatedMoons.map((m, mIdx) => {
        const symbolLines =
          (m as any).symbolEndLine && (m as any).symbolLine
            ? (m as any).symbolEndLine - (m as any).symbolLine + 1
            : 15;
        const moonRadius = Math.min(
          Math.max(0.16 + Math.min(symbolLines / 150, 1.0) * 0.08, 0.16),
          0.24
        );

        // Orbit radius around parent planet (clear separated orbits)
        const mOrbitRadius = radius * 1.85 + mIdx * 0.8;
        const mOrbitSpeed = 0.14 / (1 + mIdx * 0.15);
        const mPhase = (mIdx * (2 * Math.PI)) / Math.max(1, relatedMoons.length) + (mIdx * 0.5);

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
          inclination: ((mIdx % 3) - 1) * 0.22,
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
        hasRings: Boolean(p.hasRings || index % 4 === 0),
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
