import { useMemo } from "react";
import { useNavigation } from "@/hooks/useNavigation";
import { RepositoryStar } from "./RepositoryStar";
import { FolderPlanet } from "./FolderPlanet";
import { getFolderVisualIdentity, getFileVisualIdentity } from "./PlanetTextures";
import type {
  RepositorySystemData,
  RepositoryNode,
  FolderPlanet as FolderPlanetType,
  FileMoon as FileMoonType,
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

    // 2. Extract Folder Planets and File Moons
    const folderNodes = spaceGraph.filter((o) => o.kind === "folder" || o.kind === "planet");
    const fileNodes = spaceGraph.filter((o) => o.kind === "file" || o.kind === "moon");

    // Star is large, majestic solar center
    const repository: RepositoryNode = {
      id: rootNode?.id || "repository-star",
      name: repoName,
      description: repositories[0]?.description || "Repository central star",
      folderCount: folderNodes.length,
      fileCount: fileNodes.length,
      languages: [],
      color: "#f59e0b", // Radiant warm solar amber
      radius: 2.8,
    };

    // Calculate folder planets layout
    const totalFolders = Math.max(1, folderNodes.length);
    const planetsPerTrack = totalFolders > 8 ? 3 : totalFolders > 4 ? 2 : 1;
    const baseOrbitRadius = 8.5;
    const trackSpacing = 4.8;

    const languagesSet = new Set<string>();

    // 3. Map folders to FolderPlanets
    const folders: FolderPlanetType[] = folderNodes.map((folderNode, index) => {
      const folderName = folderNode.name;
      const folderPath = (folderNode as any).path || (folderNode as any).filePath || folderName;

      // Deterministic folder visual identity
      const visual = getFolderVisualIdentity(folderName);

      // Orbital placement in separated concentric bands
      const trackIndex = Math.floor(index / planetsPerTrack);
      const slotIndex = index % planetsPerTrack;
      const orbitRadius = baseOrbitRadius + trackIndex * trackSpacing;

      // Golden ratio angle offset so folder planets never visually align or collide
      const angleOffset =
        (slotIndex * (2 * Math.PI)) / planetsPerTrack + trackIndex * 0.95;

      // Calm Keplerian orbit speed
      const orbitSpeed = 0.032 / Math.sqrt(orbitRadius / baseOrbitRadius);

      // Extract file moons that belong to this folder
      const childFiles = fileNodes.filter(
        (f) =>
          f.parentId === folderNode.id ||
          f.parentId === folderPath ||
          (f as any).folder === folderName
      );

      // Sizing formula: normalize folder size
      const totalBytes =
        (folderNode as any).size_bytes ||
        (folderNode as any).size ||
        childFiles.reduce((acc, f) => acc + ((f as any).size || 1500), 0);
      const normalizedFiles = Math.min(childFiles.length / 25, 1.0);
      const normalizedSize = Math.min(totalBytes / 150000, 1.0);
      const radius = Math.min(
        Math.max(1.15 + normalizedFiles * 0.45 + normalizedSize * 0.25, 1.15),
        1.85
      );

      // Child file moons orbiting around this folder planet
      const files: FileMoonType[] = childFiles.map((fileNode, fIdx) => {
        const filePath = (fileNode as any).filePath || (fileNode as any).path || fileNode.name;
        const fileName = fileNode.name || filePath.split("/").pop() || "file";
        const ext = fileName.includes(".") ? fileName.split(".").pop() || "" : "";
        const lang = (fileNode as any).language || ext || "text";
        languagesSet.add(lang);

        const fileVisual = getFileVisualIdentity(filePath, lang);

        // Moons size & orbit around parent planet
        const fileLines = (fileNode as any).lines || 20;
        const moonRadius = Math.min(
          Math.max(0.18 + Math.min(fileLines / 200, 1.0) * 0.08, 0.18),
          0.26
        );

        // Orbit radius around parent folder planet
        const mOrbitRadius = radius * 1.75 + fIdx * 0.75;
        const mOrbitSpeed = 0.12 / (1 + fIdx * 0.12);
        const mPhase =
          (fIdx * (2 * Math.PI)) / Math.max(1, childFiles.length) + fIdx * 0.45;

        return {
          id: fileNode.id,
          parentId: folderNode.id,
          name: fileName,
          path: filePath,
          extension: ext,
          language: lang,
          size: (fileNode as any).size || 1500,
          lines: (fileNode as any).lines,
          functions: (fileNode as any).functions || 0,
          classes: (fileNode as any).classes || 0,
          color: fileVisual.color,
          radius: moonRadius,
          orbitRadius: mOrbitRadius,
          orbitSpeed: mOrbitSpeed,
          orbitPhase: mPhase,
          inclination: ((fIdx % 3) - 1) * 0.18,
          direction: fIdx % 2 === 0 ? 1 : -1,
        };
      });

      return {
        id: folderNode.id,
        name: folderName,
        path: folderPath,
        fileCount: childFiles.length,
        folderCount: (folderNode as any).folderCount || 0,
        size: totalBytes,
        languageBreakdown: (folderNode as any).languageBreakdown || {},
        primaryLanguage: (folderNode as any).primaryLanguage || (childFiles[0]?.language || "text"),
        color: visual.color,
        atmosphereColor: visual.atmosphereColor,
        textureType: visual.textureType,
        radius,
        orbitRadius,
        orbitSpeed,
        orbitPhase: angleOffset,
        inclination: ((index % 5) - 2) * 0.03,
        direction: index % 2 === 0 ? 1 : -1,
        hasRings: Boolean(folderNode.hasRings || index % 3 === 0),
        files,
      };
    });

    // 4. Root-level files (files that do NOT belong to any folder planet, e.g. README.md)
    const rootFileNodes = fileNodes.filter(
      (f) =>
        f.parentId === "repository-star" ||
        f.parentId === rootNode?.id ||
        !f.parentId ||
        f.parentId === ""
    );

    const rootFiles: FileMoonType[] = rootFileNodes.map((rf, rIdx) => {
      const filePath = (rf as any).filePath || (rf as any).path || rf.name;
      const fileName = rf.name || filePath.split("/").pop() || "file";
      const ext = fileName.includes(".") ? fileName.split(".").pop() || "" : "";
      const lang = (rf as any).language || ext || "text";
      languagesSet.add(lang);

      const fileVisual = getFileVisualIdentity(filePath, lang);

      // Root files orbit close to the central star (orbit radius 4.2 to 5.8)
      const starOrbitRadius = repository.radius * 1.55 + rIdx * 0.75;
      const starOrbitSpeed = 0.07 / (1 + rIdx * 0.08);
      const starPhase = (rIdx * (2 * Math.PI)) / Math.max(1, rootFileNodes.length);

      return {
        id: rf.id,
        parentId: repository.id,
        name: fileName,
        path: filePath,
        extension: ext,
        language: lang,
        size: (rf as any).size || 2000,
        lines: (rf as any).lines,
        functions: (rf as any).functions || 0,
        classes: (rf as any).classes || 0,
        color: fileVisual.color,
        radius: 0.22,
        orbitRadius: starOrbitRadius,
        orbitSpeed: starOrbitSpeed,
        orbitPhase: starPhase,
        inclination: ((rIdx % 4) - 1.5) * 0.12,
        direction: rIdx % 2 === 0 ? 1 : -1,
      };
    });

    repository.languages = Array.from(languagesSet);

    return { repository, folders, rootFiles };
  }, [spaceGraph, workspaceStatus.repo_name, repositories]);

  return (
    <group>
      {/* 1. Exactly ONE central star representing the repository (with root file moons) */}
      <RepositoryStar
        repository={systemData.repository}
        rootFiles={systemData.rootFiles}
      />

      {/* 2. Folder Planets orbiting the central star (each holding its File Moons) */}
      {systemData.folders.map((folder) => (
        <FolderPlanet key={folder.id} planet={folder} />
      ))}
    </group>
  );
}
