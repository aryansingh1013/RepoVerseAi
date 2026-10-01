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

// ─── Deterministic Visual Identity Mapping ───────────────────────────────────

export interface LanguageVisualIdentity {
  color: string;
  atmosphereColor: string;
  textureType: PlanetTextureType;
}

export function getLanguageVisualIdentity(path: string, language?: string): LanguageVisualIdentity {
  const ext = (language || path.split(".").pop() || "").toLowerCase().replace(/^\./, "");

  switch (ext) {
    case "py":
    case "pyw":
    case "python":
      return {
        color: "#2563eb", // Python blue
        atmosphereColor: "#60a5fa",
        textureType: "python",
      };

    case "js":
    case "mjs":
    case "cjs":
    case "javascript":
      return {
        color: "#f59e0b", // Warm amber / orange
        atmosphereColor: "#fbbf24",
        textureType: "javascript",
      };

    case "ts":
    case "typescript":
      return {
        color: "#3178c6", // TypeScript blue/cyan
        atmosphereColor: "#38bdf8",
        textureType: "typescript",
      };

    case "tsx":
    case "jsx":
    case "react":
      return {
        color: "#06b6d4", // Electric cyan
        atmosphereColor: "#22d3ee",
        textureType: "react",
      };

    case "c":
    case "cpp":
    case "cc":
    case "cxx":
    case "h":
    case "hpp":
      return {
        color: "#ea580c", // Red/orange
        atmosphereColor: "#fb923c",
        textureType: "cpp",
      };

    case "java":
    case "jar":
    case "kt":
    case "kotlin":
      return {
        color: "#dc2626", // Crimson red
        atmosphereColor: "#f87171",
        textureType: "java",
      };

    case "css":
    case "scss":
    case "sass":
    case "less":
      return {
        color: "#9333ea", // Purple
        atmosphereColor: "#c084fc",
        textureType: "css",
      };

    case "html":
    case "htm":
      return {
        color: "#e11d48", // HTML orange / warm coral
        atmosphereColor: "#fb7185",
        textureType: "html",
      };

    case "json":
    case "yaml":
    case "yml":
    case "toml":
      return {
        color: "#d97706", // Amber
        atmosphereColor: "#fde047",
        textureType: "json",
      };

    case "md":
    case "markdown":
    case "txt":
      return {
        color: "#64748b", // Neutral slate gray
        atmosphereColor: "#94a3b8",
        textureType: "markdown",
      };

    case "sql":
    case "prisma":
      return {
        color: "#059669", // Emerald green
        atmosphereColor: "#34d399",
        textureType: "sql",
      };

    default:
      return {
        color: "#64748b", // Neutral gray
        atmosphereColor: "#94a3b8",
        textureType: "generic",
      };
  }
}

// ─── Simple Deterministic Pseudo-Random ──────────────────────────────────────

function createPRNG(seed: number) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// ─── Procedural Planet Surface Generator ─────────────────────────────────────

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
    const rand = createPRNG(baseColorHex.length * 37 + size);

    const baseRGB = hexToRgb(baseColorHex);

    // 1. Fill base tone
    ctx.fillStyle = baseColorHex;
    ctx.fillRect(0, 0, size, size);

    if (textureType === "javascript" || textureType === "typescript") {
      // Atmospheric Jupiter-style horizontal banding
      const bandCount = 14;
      for (let i = 0; i < bandCount; i++) {
        const y = (i / bandCount) * size;
        const h = size / bandCount + (rand() - 0.5) * 4;
        const lightnessMod = (rand() - 0.5) * 0.35;
        const color = shadeRgb(baseRGB, lightnessMod);
        ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, 0.6)`;
        ctx.fillRect(0, y, size, h);
      }
    } else if (textureType === "python") {
      // Cloudy oceanic / atmospheric noise
      for (let i = 0; i < 40; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const rad = 15 + rand() * 45;
        const shade = rand() > 0.5 ? 0.25 : -0.25;
        const color = shadeRgb(baseRGB, shade);
        const grad = ctx.createRadialGradient(x, y, 2, x, y, rad);
        grad.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, 0.5)`);
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (textureType === "react") {
      // Cybernetic aura with subtle horizontal flow
      for (let i = 0; i < 20; i++) {
        const y = rand() * size;
        const grad = ctx.createLinearGradient(0, y, size, y);
        grad.addColorStop(0, "rgba(34, 211, 238, 0.1)");
        grad.addColorStop(0.5, "rgba(255, 255, 255, 0.4)");
        grad.addColorStop(1, "rgba(6, 182, 212, 0.1)");
        ctx.fillStyle = grad;
        ctx.fillRect(0, y, size, 3 + rand() * 6);
      }
    } else if (textureType === "css") {
      // Crystalline fractal / noise surface
      for (let i = 0; i < 35; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const rad = 10 + rand() * 25;
        ctx.fillStyle = rand() > 0.5 ? "rgba(236, 72, 153, 0.25)" : "rgba(147, 51, 234, 0.35)";
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (textureType === "json" || textureType === "markdown") {
      // Rocky cratered moon/asteroid surface
      for (let i = 0; i < 50; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const rad = 4 + rand() * 12;
        const grad = ctx.createRadialGradient(x, y, 1, x, y, rad);
        grad.addColorStop(0, "rgba(0, 0, 0, 0.45)");
        grad.addColorStop(0.8, "rgba(255, 255, 255, 0.15)");
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.fill();
      }
    } else {
      // Generic subtle planetary marbling
      for (let i = 0; i < 25; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const rad = 20 + rand() * 30;
        const grad = ctx.createRadialGradient(x, y, 3, x, y, rad);
        const col = shadeRgb(baseRGB, (rand() - 0.5) * 0.3);
        grad.addColorStop(0, `rgba(${col.r}, ${col.g}, ${col.b}, 0.4)`);
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Polar ice caps for terrestrial bodies
    const capGrad = ctx.createLinearGradient(0, 0, 0, size);
    capGrad.addColorStop(0, "rgba(255, 255, 255, 0.45)");
    capGrad.addColorStop(0.08, "rgba(255, 255, 255, 0)");
    capGrad.addColorStop(0.92, "rgba(255, 255, 255, 0)");
    capGrad.addColorStop(1, "rgba(255, 255, 255, 0.45)");
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

    // Medium gray base (neutral relief)
    ctx.fillStyle = "#808080";
    ctx.fillRect(0, 0, size, size);

    // Add crater/ridge variations
    const features = textureType === "markdown" || textureType === "json" ? 40 : 20;
    for (let i = 0; i < features; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 3 + rand() * 12;
      const grad = ctx.createRadialGradient(x, y, 1, x, y, r);
      grad.addColorStop(0, "#404040"); // Pit
      grad.addColorStop(0.7, "#c0c0c0"); // Rim ridge
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
    const rand = createPRNG(size * 29);

    ctx.fillStyle = colorHex;
    ctx.fillRect(0, 0, size, size);

    // Stark craters
    for (let i = 0; i < 30; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 2 + rand() * 9;
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

    // Warm solar base
    ctx.fillStyle = colorHex;
    ctx.fillRect(0, 0, size, size);

    // Plasma granulation convection cells
    for (let i = 0; i < 60; i++) {
      const x = rand() * size;
      const y = rand() * size;
      const r = 10 + rand() * 30;
      const grad = ctx.createRadialGradient(x, y, 2, x, y, r);
      grad.addColorStop(0, "#fffbeb"); // Bright hot core
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
