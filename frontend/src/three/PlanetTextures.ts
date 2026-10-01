import * as THREE from "three";
import type { PlanetTextureType } from "./sceneTypes";

// ─── Procedural Texture Cache ────────────────────────────────────────────────
// Reuses generated canvas textures to prevent memory leaks and redundant rendering
const textureCache = new Map<string, THREE.CanvasTexture>();

export function getCachedTexture(key: string, generator: () => HTMLCanvasElement): THREE.CanvasTexture {
  if (textureCache.has(key)) {
    return textureCache.get(key)!;
  }
  const canvas = generator();
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  textureCache.set(key, texture);
  return texture;
}

// ─── Simple Deterministic Pseudo-Random ──────────────────────────────────────

function createPRNG(seed: number) {
  let s = Math.abs(seed) % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function stringToSeed(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) || 42;
}

// ─── Deterministic Folder Planet Visual Identity (Section 9 & 10) ────────────

export interface FolderVisualIdentity {
  color: string;
  atmosphereColor: string;
  textureType: PlanetTextureType;
}

const CURATED_PALETTE: FolderVisualIdentity[] = [
  { color: "#2563eb", atmosphereColor: "#60a5fa", textureType: "cloudy" },      // Blue
  { color: "#06b6d4", atmosphereColor: "#22d3ee", textureType: "atmospheric" }, // Cyan
  { color: "#9333ea", atmosphereColor: "#c084fc", textureType: "icy" },         // Purple
  { color: "#ea580c", atmosphereColor: "#f97316", textureType: "desert" },      // Orange
  { color: "#10b981", atmosphereColor: "#34d399", textureType: "rocky" },       // Emerald
  { color: "#e11d48", atmosphereColor: "#fb7185", textureType: "volcanic" },    // Crimson
  { color: "#059669", atmosphereColor: "#10b981", textureType: "ocean" },       // Deep teal
  { color: "#7c3aed", atmosphereColor: "#a78bfa", textureType: "crystalline" }, // Violet
  { color: "#d97706", atmosphereColor: "#fbbf24", textureType: "desert" },      // Amber
];

export function getFolderVisualIdentity(folderName: string): FolderVisualIdentity {
  const norm = folderName.toLowerCase().replace(/[^a-z0-9]/g, "");

  // Curated prominent assignments for standard repository folders
  if (norm.includes("back") || norm.includes("server") || norm === "api") {
    return { color: "#2563eb", atmosphereColor: "#60a5fa", textureType: "cloudy" };
  }
  if (norm.includes("front") || norm.includes("client") || norm === "ui" || norm === "web") {
    return { color: "#06b6d4", atmosphereColor: "#22d3ee", textureType: "atmospheric" };
  }
  if (norm.includes("doc")) {
    return { color: "#9333ea", atmosphereColor: "#c084fc", textureType: "icy" };
  }
  if (norm.includes("script") || norm === "bin" || norm === "tools") {
    return { color: "#ea580c", atmosphereColor: "#f97316", textureType: "desert" };
  }
  if (norm.includes("test") || norm.includes("spec")) {
    return { color: "#10b981", atmosphereColor: "#34d399", textureType: "rocky" };
  }
  if (norm.includes("supa") || norm.includes("db") || norm.includes("data") || norm.includes("sql")) {
    return { color: "#059669", atmosphereColor: "#10b981", textureType: "volcanic" };
  }
  if (norm.includes("agent") || norm.includes("ai") || norm === "core" || norm === "models") {
    return { color: "#7c3aed", atmosphereColor: "#a78bfa", textureType: "crystalline" };
  }

  // Stable hash into curated celestial palette
  const seed = stringToSeed(folderName);
  return CURATED_PALETTE[seed % CURATED_PALETTE.length];
}

// ─── Deterministic File Moon Visual Identity (Section 13) ─────────────────────

export interface FileVisualIdentity {
  color: string;
  atmosphereColor: string;
}

export function getFileVisualIdentity(filePath: string, language?: string): FileVisualIdentity {
  const ext = (language || filePath.split(".").pop() || "").toLowerCase().replace(/^\./, "");

  switch (ext) {
    case "py":
    case "pyw":
    case "python":
      return { color: "#3b82f6", atmosphereColor: "#60a5fa" }; // Python blue

    case "ts":
    case "typescript":
      return { color: "#2563eb", atmosphereColor: "#60a5fa" }; // TypeScript cobalt

    case "tsx":
    case "jsx":
    case "react":
      return { color: "#06b6d4", atmosphereColor: "#22d3ee" }; // React cyan

    case "js":
    case "mjs":
    case "cjs":
    case "javascript":
      return { color: "#f59e0b", atmosphereColor: "#fbbf24" }; // JavaScript yellow/amber

    case "md":
    case "markdown":
    case "txt":
      return { color: "#94a3b8", atmosphereColor: "#cbd5e1" }; // Markdown slate gray

    case "json":
    case "yaml":
    case "yml":
    case "toml":
      return { color: "#d97706", atmosphereColor: "#fbbf24" }; // Amber

    case "css":
    case "scss":
    case "sass":
    case "less":
      return { color: "#a855f7", atmosphereColor: "#c084fc" }; // Purple

    case "c":
    case "cpp":
    case "cc":
    case "h":
    case "hpp":
      return { color: "#ea580c", atmosphereColor: "#fb923c" }; // Red/orange

    case "html":
    case "htm":
      return { color: "#e11d48", atmosphereColor: "#fb7185" }; // Coral/orange

    case "sql":
    case "prisma":
      return { color: "#10b981", atmosphereColor: "#34d399" }; // Emerald

    default:
      return { color: "#64748b", atmosphereColor: "#94a3b8" }; // Neutral slate
  }
}

// ─── Procedural Planet Surface Generator (Section 10) ─────────────────────────

export function getPlanetTexture(
  textureType: PlanetTextureType,
  baseColorHex: string,
  size = 256
): THREE.CanvasTexture {
  const key = `planet_tex_${textureType}_${baseColorHex}_${size}`;
  return getCachedTexture(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const rand = createPRNG(stringToSeed(baseColorHex) + size * 13);
    const baseRGB = hexToRgb(baseColorHex);

    // Base surface fill
    ctx.fillStyle = baseColorHex;
    ctx.fillRect(0, 0, size, size);

    if (textureType === "atmospheric" || textureType === "ocean") {
      // Atmospheric Jupiter-like subtle banding & circulation swirls
      const bandCount = 12;
      for (let i = 0; i < bandCount; i++) {
        const y = (i / bandCount) * size;
        const h = size / bandCount + (rand() - 0.5) * 6;
        const shade = (rand() - 0.5) * 0.35;
        const col = shadeRgb(baseRGB, shade);
        ctx.fillStyle = `rgba(${col.r}, ${col.g}, ${col.b}, 0.55)`;
        ctx.fillRect(0, y, size, h);
      }
    } else if (textureType === "cloudy") {
      // Cloudy oceanic / cumulus planetary noise
      for (let i = 0; i < 40; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const rad = 15 + rand() * 45;
        const shade = rand() > 0.5 ? 0.3 : -0.25;
        const col = shadeRgb(baseRGB, shade);
        const grad = ctx.createRadialGradient(x, y, 2, x, y, rad);
        grad.addColorStop(0, `rgba(${col.r}, ${col.g}, ${col.b}, 0.5)`);
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (textureType === "crystalline") {
      // Radiant polygonal / crystalline facets
      for (let i = 0; i < 30; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const rad = 12 + rand() * 30;
        ctx.fillStyle = rand() > 0.5 ? "rgba(255, 255, 255, 0.22)" : "rgba(124, 58, 237, 0.3)";
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (textureType === "desert" || textureType === "volcanic") {
      // Dune striations & tectonic fissure veins
      for (let i = 0; i < 25; i++) {
        const y = rand() * size;
        const h = 4 + rand() * 12;
        ctx.fillStyle = rand() > 0.5 ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 200, 100, 0.25)";
        ctx.fillRect(0, y, size, h);
      }
    } else {
      // Rocky / Icy cratered terrain
      for (let i = 0; i < 45; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const rad = 4 + rand() * 16;
        const grad = ctx.createRadialGradient(x, y, 1, x, y, rad);
        grad.addColorStop(0, "rgba(0, 0, 0, 0.45)");
        grad.addColorStop(0.75, "rgba(255, 255, 255, 0.2)");
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Polar ice caps
    const capGrad = ctx.createLinearGradient(0, 0, 0, size);
    capGrad.addColorStop(0, "rgba(255, 255, 255, 0.4)");
    capGrad.addColorStop(0.07, "rgba(255, 255, 255, 0)");
    capGrad.addColorStop(0.93, "rgba(255, 255, 255, 0)");
    capGrad.addColorStop(1, "rgba(255, 255, 255, 0.4)");
    ctx.fillStyle = capGrad;
    ctx.fillRect(0, 0, size, size);

    return canvas;
  });
}

// ─── Procedural Bump Map Generator ──────────────────────────────────────────

export function getPlanetBumpMap(textureType: PlanetTextureType, size = 128): THREE.CanvasTexture {
  const key = `planet_bump_${textureType}_${size}`;
  return getCachedTexture(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const rand = createPRNG(size * 17);

    ctx.fillStyle = "#808080";
    ctx.fillRect(0, 0, size, size);

    const features = 25;
    for (let i = 0; i < features; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 3 + rand() * 14;
      const grad = ctx.createRadialGradient(x, y, 1, x, y, r);
      grad.addColorStop(0, "#404040");
      grad.addColorStop(0.7, "#c0c0c0");
      grad.addColorStop(1, "#808080");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    return canvas;
  });
}

// ─── Procedural Moon Texture & Bump Map ───────────────────────────────────────

export function getMoonTexture(colorHex: string, size = 128): THREE.CanvasTexture {
  const key = `moon_tex_${colorHex}_${size}`;
  return getCachedTexture(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const rand = createPRNG(stringToSeed(colorHex) + size * 29);

    ctx.fillStyle = colorHex;
    ctx.fillRect(0, 0, size, size);

    // Stark craters
    for (let i = 0; i < 30; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 2 + rand() * 10;
      const grad = ctx.createRadialGradient(x, y, 1, x, y, r);
      grad.addColorStop(0, "rgba(0, 0, 0, 0.55)");
      grad.addColorStop(0.75, "rgba(255, 255, 255, 0.2)");
      grad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    return canvas;
  });
}

export function getMoonBumpMap(size = 128): THREE.CanvasTexture {
  const key = `moon_bump_${size}`;
  return getCachedTexture(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const rand = createPRNG(size * 53);

    ctx.fillStyle = "#808080";
    ctx.fillRect(0, 0, size, size);

    for (let i = 0; i < 35; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 2 + rand() * 10;
      const grad = ctx.createRadialGradient(x, y, 1, x, y, r);
      grad.addColorStop(0, "#202020");
      grad.addColorStop(0.8, "#e0e0e0");
      grad.addColorStop(1, "#808080");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    return canvas;
  });
}

// ─── Central Repository Star Textures ────────────────────────────────────────

export function getStarTexture(colorHex = "#f59e0b", size = 256): THREE.CanvasTexture {
  const key = `star_plasma_${colorHex}_${size}`;
  return getCachedTexture(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const rand = createPRNG(size * 71);

    ctx.fillStyle = colorHex;
    ctx.fillRect(0, 0, size, size);

    // Plasma granulation convection cells
    for (let i = 0; i < 60; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 10 + rand() * 30;
      const grad = ctx.createRadialGradient(x, y, 2, x, y, r);
      grad.addColorStop(0, "#fffbeb");
      grad.addColorStop(0.4, "#fbbf24");
      grad.addColorStop(1, "rgba(217, 119, 6, 0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    return canvas;
  });
}

export function getStarCoronaTexture(colorHex = "#fbbf24", size = 256): THREE.CanvasTexture {
  const key = `star_corona_${colorHex}_${size}`;
  return getCachedTexture(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const c = size / 2;

    const grad = ctx.createRadialGradient(c, c, 4, c, c, c);
    grad.addColorStop(0, "#ffffff");
    grad.addColorStop(0.2, colorHex);
    grad.addColorStop(0.55, "rgba(245, 158, 11, 0.35)");
    grad.addColorStop(1, "rgba(0, 0, 0, 0)");

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);
    return canvas;
  });
}

export function getRingTexture(colorHex: string, size = 256): THREE.CanvasTexture {
  const key = `ring_tex_${colorHex}_${size}`;
  return getCachedTexture(key, () => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const c = size / 2;

    const grad = ctx.createRadialGradient(c, c, c * 0.45, c, c, c);
    grad.addColorStop(0, "rgba(0,0,0,0)");
    grad.addColorStop(0.15, "rgba(255,255,255,0.7)");
    grad.addColorStop(0.45, colorHex);
    grad.addColorStop(0.55, "rgba(0,0,0,0.85)"); // Cassini division gap
    grad.addColorStop(0.65, colorHex);
    grad.addColorStop(0.85, "rgba(255,255,255,0.4)");
    grad.addColorStop(1, "rgba(0,0,0,0)");

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);
    return canvas;
  });
}

// ─── Color Math Helpers ──────────────────────────────────────────────────────

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  let clean = hex.replace("#", "");
  if (clean.length === 3) {
    clean = clean.split("").map((c) => c + c).join("");
  }
  const num = parseInt(clean, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

function shadeRgb(rgb: { r: number; g: number; b: number }, factor: number): { r: number; g: number; b: number } {
  return {
    r: Math.min(255, Math.max(0, Math.round(rgb.r + (255 - rgb.r) * factor))),
    g: Math.min(255, Math.max(0, Math.round(rgb.g + (255 - rgb.g) * factor))),
    b: Math.min(255, Math.max(0, Math.round(rgb.b + (255 - rgb.b) * factor))),
  };
}
