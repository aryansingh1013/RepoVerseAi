/**
 * Centralized motion configuration for the 3D universe.
 * PHASE 7.6–7.8: all orbital/self-rotation speeds live here — no magic
 * numbers scattered across components. All speeds are rad/second and are
 * applied via delta-time (frame-rate independent, see useFrame usage).
 *
 * Feel target: calm / cinematic / explorable — never arcade.
 */

// ─── Orbital speeds (rad/s), by body kind ──────────────────────────────────
export const ORBIT_SPEED = {
  star: 0.02,     // axial rotation of central repository star
  planet: 0.045,  // file planets orbiting central star
  moon: 0.12,     // symbols orbiting parent planet
} as const;

// Multiplier applied to per-object orbitSpeed data from the graph builder,
// so speeds remain calm and cinematic.
export const GLOBAL_ORBIT_SCALE = 0.35;

// ─── Self-rotation speeds (rad/s) ──────────────────────────────────────────
export const SELF_ROTATION = {
  star: 0.08,
  planet: 0.08,
  moon: 0.04,
} as const;

// ─── Camera / controls feel ────────────────────────────────────────────────
export const CAMERA = {
  dampingFactor: 0.06,
  rotateSpeed: 0.5,
  zoomSpeed: 0.7,
} as const;

// ─── Body sizing ───────────────────────────────────────────────────────────
// PHASE 7.3/7.5: normalized + clamped scales; moons must stay readable.
export const BODY_SCALE = {
  moonMultiplier: 3.0,
  moonMinScale: 0.28,   // floor so even tiny functions stay visible/clickable
  moonMaxScale: 0.65,   // never rival the parent planet
} as const;

// ─── Device tier detection (PHASE 9) ───────────────────────────────────────
export type DeviceTier = "low" | "mid" | "high";

let cachedTier: DeviceTier | null = null;

export function getDeviceTier(): DeviceTier {
  if (cachedTier) return cachedTier;
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
    if (!gl) { cachedTier = "low"; return cachedTier; }
    const dbg = gl.getExtension("WEBGL_debug_renderer_info");
    const renderer = dbg
      ? String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL))
      : "";
    const cores = navigator.hardwareConcurrency ?? 4;
    const memoryGB = (navigator as any).deviceMemory ?? 8;

    const isSoftware = /swiftshader|software|basic render/i.test(renderer);
    const isIntegrated = /intel|uhd|iris/i.test(renderer);
    const isDiscrete = /nvidia|geforce|rtx|gtx|radeon rx|apple m/i.test(renderer);

    if (isSoftware || cores <= 2) cachedTier = "low";
    else if (isDiscrete && cores >= 8) cachedTier = "high";
    else if (isIntegrated && cores >= 8) cachedTier = "mid";
    else cachedTier = isDiscrete ? "high" : "mid";
    void memoryGB;
  } catch {
    cachedTier = "mid";
  }
  return cachedTier;
}

// ─── Per-tier quality budgets (PHASE 8/9) ──────────────────────────────────
export interface QualityBudget {
  dprMax: number;
  starCounts: [number, number, number, number]; // 4 shell layers
  nebulaCount: number;
  focusTextureSize: number;
  orbitTextureSize: number;
}

export function getQualityBudget(): QualityBudget {
  const tier = getDeviceTier();
  if (tier === "low") {
    return { dprMax: 1, starCounts: [400, 500, 250, 12], nebulaCount: 1, focusTextureSize: 512, orbitTextureSize: 128 };
  }
  if (tier === "mid") {
    return { dprMax: 1.35, starCounts: [700, 1000, 450, 22], nebulaCount: 2, focusTextureSize: 512, orbitTextureSize: 256 };
  }
  return { dprMax: 1.75, starCounts: [900, 1400, 600, 30], nebulaCount: 3, focusTextureSize: 1024, orbitTextureSize: 256 };
}
