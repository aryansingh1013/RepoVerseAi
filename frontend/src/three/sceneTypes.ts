/**
 * Canonical types for RepoVerse Solar System:
 * 
 * ⭐ Repository (Central Star)
 *       │
 *       ├── 🪐 Folder Planet
 *       │      ├── 🌙 File Moon
 *       │      └── 🌙 File Moon
 *       │
 *       └── 🌙 Root File Moon (e.g. README.md, package.json orbiting the Star)
 */

export type CelestialType = "repository" | "folder" | "file";

export type PlanetTextureType =
  | "rocky"
  | "cloudy"
  | "atmospheric"
  | "ocean"
  | "desert"
  | "icy"
  | "volcanic"
  | "crystalline"
  | "generic";

export interface FileMoon {
  id: string;
  parentId: string; // folder ID, or "repository-star" for root files
  name: string;
  path: string;
  extension: string;
  language: string;
  size: number;
  lines?: number;
  functions?: number;
  classes?: number;
  color: string;
  radius: number;
  orbitRadius: number;
  orbitSpeed: number;
  orbitPhase: number;
  inclination: number;
  direction: 1 | -1;
}

export interface FolderPlanet {
  id: string;
  name: string;
  path: string;
  fileCount: number;
  folderCount: number;
  size: number;
  languageBreakdown: Record<string, number>;
  primaryLanguage: string;
  color: string;
  atmosphereColor?: string;
  textureType: PlanetTextureType;
  radius: number;
  orbitRadius: number;
  orbitSpeed: number;
  orbitPhase: number;
  inclination: number;
  direction: 1 | -1;
  hasRings?: boolean;
  files: FileMoon[];
}

export interface RepositoryNode {
  id: string;
  name: string;
  owner?: string;
  description?: string;
  folderCount: number;
  fileCount: number;
  languages: string[];
  techStack?: string[];
  color: string;
  radius: number;
}

export interface RepositorySystemData {
  repository: RepositoryNode;
  folders: FolderPlanet[];
  rootFiles: FileMoon[];
}
