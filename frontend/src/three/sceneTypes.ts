/**
 * Canonical types for the RepoVerse Solar System visualization.
 * 
 * Hierarchy:
 * Repository (Central Star)
 *   ↓
 * FilePlanets (Source files orbiting the central star)
 *   ↓
 * SymbolMoons (Functions / Classes / Methods orbiting parent file planet)
 */

export type CelestialType = "repository" | "planet" | "moon";

export type PlanetTextureType =
  | "python"
  | "javascript"
  | "typescript"
  | "react"
  | "css"
  | "html"
  | "json"
  | "markdown"
  | "sql"
  | "cpp"
  | "java"
  | "generic";

export interface SymbolMoon {
  id: string;
  planetId: string;
  name: string;
  type: "function" | "class" | "method";
  lineStart: number;
  lineEnd: number;
  summary?: string;
  details?: string;
  parameters?: string[];
  radius: number;
  orbitRadius: number;
  orbitSpeed: number;
  orbitPhase: number;
  inclination: number;
  direction: 1 | -1;
  color: string;
}

export interface FilePlanet {
  id: string;
  path: string;
  name: string;
  directory: string;
  language: string;
  size: number;
  lines?: number;
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
  moons: SymbolMoon[];
  imports?: string[];
  functionsCount?: number;
  classesCount?: number;
}

export interface RepositoryNode {
  id: string;
  name: string;
  owner?: string;
  description?: string;
  fileCount: number;
  languages: string[];
  techStack?: string[];
  color: string;
  radius: number;
}

export interface RepositorySystemData {
  repository: RepositoryNode;
  planets: FilePlanet[];
}
