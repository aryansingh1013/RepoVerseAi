import * as THREE from "three";

/**
 * Procedural texture engine for the RepoVerse universe.
 * All textures are canvas-generated (no image assets) with layered
 * value-noise so every body has rich, unique surface detail.
 */

// ─── Seeded PRNG (mulberry32) ──────────────────────────────────────────────

export function seededRand(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ─── Color helpers ─────────────────────────────────────────────────────────

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16) || 0,
    parseInt(h.slice(2, 4), 16) || 0,
    parseInt(h.slice(4, 6), 16) || 0,
  ];
}

/** rgb string like "128,90,200" with optional multiplier & offset */
function rgbStr([r, g, b]: [number, number, number], m = 1, o = 0, a = 1): string {
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v * m + o)));
  return `rgba(${c(r)},${c(g)},${c(b)},${a})`;
}

// ─── Value noise (tiled, multi-octave) ─────────────────────────────────────

/**
 * Tileable multi-octave value noise returned as a Float32 field [0..1].
 * Grid vertices are interpolated bilinearly; wrapping keeps the texture
 * seamless when mapped onto a sphere.
 */
export function noiseField(
  size: number,
  seed: number,
  octaves = 4,
  baseFreq = 4
): Float32Array {
  const field = new Float32Array(size * size);
  let amp = 1;
  let total = 0;
  for (let o = 0; o < octaves; o++) {
    const freq = baseFreq * Math.pow(2, o);
    const grid: number[] = [];
    const gr = seededRand(seed * 7919 + o * 131 + 17);
    for (let i = 0; i < freq * freq; i++) grid.push(gr());
    const stride = size / freq;
    for (let y = 0; y < size; y++) {
      const gy = y / stride;
      const y0 = Math.floor(gy) % freq;
      const y1 = (y0 + 1) % freq;
      const fy = gy - Math.floor(gy);
      const sy = fy * fy * (3 - 2 * fy); // smoothstep
      for (let x = 0; x < size; x++) {
        const gx = x / stride;
        const x0 = Math.floor(gx) % freq;
        const x1 = (x0 + 1) % freq;
        const fx = gx - Math.floor(gx);
        const sx = fx * fx * (3 - 2 * fx);
        const v00 = grid[y0 * freq + x0];
        const v10 = grid[y0 * freq + x1];
        const v01 = grid[y1 * freq + x0];
        const v11 = grid[y1 * freq + x1];
        const top = v00 + (v10 - v00) * sx;
        const bot = v01 + (v11 - v01) * sx;
        field[y * size + x] += (top + (bot - top) * sy) * amp;
      }
    }
    total += amp;
    amp *= 0.55;
  }
  // Normalize to 0..1
  for (let i = 0; i < field.length; i++) field[i] /= total;
  return field;
}

function makeCanvas(size: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  return [canvas, canvas.getContext("2d")!];
}

function toTexture(canvas: HTMLCanvasElement): THREE.CanvasTexture {
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.needsUpdate = true;
  return tex;
}

// ─── Planet (file) — banded terrain, continents, polar caps, craters ───────

export function makePlanetTexture(color: string, seed: number, size = 512): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const [br, bg, bb] = hexToRgb(color);
  const rand = seededRand(seed);

  // Height field drives everything: bands, land, ice, ocean shading
  const height = noiseField(size, seed, 5, 5);
  const detail = noiseField(size, seed * 3 + 11, 4, 16);

  const img = ctx.createImageData(size, size);
  const d = img.data;

  for (let y = 0; y < size; y++) {
    // Latitude for bands + polar caps; use abs so poles mirror
    const lat = Math.abs((y / size) * 2 - 1); // 0 equator → 1 pole
    // Warm band stripes (gas-giant style) modulated by noise
    const bandPhase = Math.sin((y / size) * Math.PI * 7 + height[(y * size + (size >> 1)) % (size * size)] * 9);
    for (let x = 0; x < size; x++) {
      const i = y * size + x;
      const h = height[i];
      const dtl = detail[i];

      // Base: color ramp from dark lowlands to bright highlands
      let r = br * (0.45 + h * 0.9);
      let g = bg * (0.45 + h * 0.9);
      let b = bb * (0.5 + h * 0.95);

      // Continental tint — landmasses slightly warmer/lighter
      if (h > 0.56) {
        const t = Math.min(1, (h - 0.56) * 5);
        r += t * 26; g += t * 22; b += t * 12;
      }
      // Deep ocean/lowland — darker, bluer
      if (h < 0.42) {
        const t = Math.min(1, (0.42 - h) * 6);
        r -= t * 18; g -= t * 10; b += t * 6;
      }

      // Gas-giant band overlay
      const band = bandPhase * 0.5 + 0.5;
      const bandMix = 0.18 * band * (1 - lat * 0.6);
      r += bandMix * 34; g += bandMix * 22; b -= bandMix * 10;

      // Polar ice caps with noisy edge
      const capEdge = 0.78 + dtl * 0.14;
      if (lat > capEdge) {
        const t = Math.min(1, (lat - capEdge) * 9);
        r += (235 - r) * t * 0.85;
        g += (242 - g) * t * 0.85;
        b += (255 - b) * t * 0.85;
      }

      // Fine grain
      const grain = (dtl - 0.5) * 26;
      d[i * 4]     = Math.max(0, Math.min(255, r + grain));
      d[i * 4 + 1] = Math.max(0, Math.min(255, g + grain));
      d[i * 4 + 2] = Math.max(0, Math.min(255, b + grain));
      d[i * 4 + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);

  // Impact craters (subtle, lit from upper-left)
  const craters = 6 + Math.floor(rand() * 8);
  for (let i = 0; i < craters; i++) {
    const x = rand() * size;
    const y = size * 0.15 + rand() * size * 0.7;
    const r = 4 + rand() * 16;
    const g1 = ctx.createRadialGradient(x - r * 0.25, y - r * 0.25, 0, x, y, r);
    g1.addColorStop(0, "rgba(255,255,255,0.10)");
    g1.addColorStop(0.55, "rgba(0,0,0,0.16)");
    g1.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g1;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }

  return toTexture(canvas);
}

/** Planet bump/roughness map — bright = high. Matches makePlanetTexture noise. */
export function makePlanetBumpMap(color: string, seed: number, size = 256): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const height = noiseField(size, seed, 5, 5);
  const img = ctx.createImageData(size, size);
  const d = img.data;
  for (let i = 0; i < size * size; i++) {
    const v = Math.max(0, Math.min(255, Math.round(height[i] * 255)));
    d[i * 4] = v; d[i * 4 + 1] = v; d[i * 4 + 2] = v; d[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return toTexture(canvas);
}

// ─── Moon (function/class) — grey cratered regolith ────────────────────────

export function makeMoonTexture(color: string, seed: number, size = 512): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const [mr, mg, mb] = hexToRgb(color);
  const rand = seededRand(seed);

  // Rolling terrain noise
  const rough = noiseField(size, seed, 5, 6);
  const img = ctx.createImageData(size, size);
  const d = img.data;

  for (let i = 0; i < size * size; i++) {
    // Marè (dark patches) via low-frequency noise
    const mare = rough[i] < 0.42;
    let shade = 0.62 + rough[i] * 0.5;
    if (mare) shade *= 0.55;
    d[i * 4]     = Math.min(255, mr * shade + 40);
    d[i * 4 + 1] = Math.min(255, mg * shade + 40);
    d[i * 4 + 2] = Math.min(255, mb * shade + 40);
    d[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);

  // Craters: dark bowl + bright rim, varied sizes, some ray systems
  const craters = 26 + Math.floor(rand() * 18);
  for (let i = 0; i < craters; i++) {
    const x = rand() * size;
    const y = rand() * size;
    const r = 3 + rand() * rand() * 26; // bias small
    // Bowl
    const bowl = ctx.createRadialGradient(x, y, 0, x, y, r);
    bowl.addColorStop(0, "rgba(0,0,0,0.34)");
    bowl.addColorStop(0.7, "rgba(0,0,0,0.18)");
    bowl.addColorStop(0.92, "rgba(255,255,255,0.16)"); // rim catchlight
    bowl.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = bowl;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
    // Ray system for a few big craters
    if (r > 16 && rand() > 0.5) {
      const rays = 5 + Math.floor(rand() * 6);
      ctx.strokeStyle = "rgba(255,255,255,0.07)";
      ctx.lineWidth = 1 + rand() * 2;
      for (let k = 0; k < rays; k++) {
        const a = rand() * Math.PI * 2;
        const len = r * (1.6 + rand() * 2.2);
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len);
        ctx.stroke();
      }
    }
  }

  return toTexture(canvas);
}

/** Moon bump map — heavy cratering for strong relief lighting. */
export function makeMoonBumpMap(seed: number, size = 256): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const rand = seededRand(seed * 13 + 5);
  const rough = noiseField(size, seed, 4, 6);
  ctx.fillStyle = "#808080";
  ctx.fillRect(0, 0, size, size);
  // Noise roughness
  const img = ctx.getImageData(0, 0, size, size);
  for (let i = 0; i < size * size; i++) {
    const v = Math.min(255, rough[i] * 190 + 60);
    img.data[i * 4] = Math.round((img.data[i * 4] + v) / 2);
    img.data[i * 4 + 1] = Math.round((img.data[i * 4 + 1] + v) / 2);
    img.data[i * 4 + 2] = Math.round((img.data[i * 4 + 2] + v) / 2);
  }
  ctx.putImageData(img, 0, 0);
  for (let i = 0; i < 60; i++) {
    const x = rand() * size;
    const y = rand() * size;
    const r = 2 + rand() * rand() * 20;
    // Dark bowl, bright rim = strong bump relief
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, "rgba(0,0,0,0.75)");
    g.addColorStop(0.72, "rgba(0,0,0,0.35)");
    g.addColorStop(0.88, "rgba(255,255,255,0.55)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  return toTexture(canvas);
}

// ─── Star / Sun (folder) — plasma granulation + sunspots ───────────────────

export function makeStarTexture(color: string, seed: number, size = 512): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const [sr, sg, sb] = hexToRgb(color);
  const rand = seededRand(seed);

  const cells = noiseField(size, seed, 4, 24); // granulation
  const blotch = noiseField(size, seed * 7 + 3, 3, 6); // large convection cells

  const img = ctx.createImageData(size, size);
  const d = img.data;
  for (let i = 0; i < size * size; i++) {
    // Hot bright granules over slightly darker convective background
    const granule = Math.pow(cells[i], 1.6);
    const cell = 0.75 + blotch[i] * 0.5;
    let r = (255 * granule + sr * 0.9) * cell * 0.62;
    let g = (235 * granule + sg * 0.9) * cell * 0.62;
    let b = (170 * granule + sb * 0.9) * cell * 0.62;
    d[i * 4]     = Math.min(255, Math.max(0, Math.round(r)));
    d[i * 4 + 1] = Math.min(255, Math.max(0, Math.round(g)));
    d[i * 4 + 2] = Math.min(255, Math.max(0, Math.round(b)));
    d[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);

  // Sunspots — dark umbra with penumbral fringe
  const spots = 5 + Math.floor(rand() * 6);
  for (let i = 0; i < spots; i++) {
    const x = rand() * size;
    const y = size * 0.2 + rand() * size * 0.6;
    const r = 6 + rand() * 20;
    const sp = ctx.createRadialGradient(x, y, 0, x, y, r);
    sp.addColorStop(0, "rgba(30,10,0,0.55)");
    sp.addColorStop(0.45, "rgba(60,20,0,0.28)");
    sp.addColorStop(0.75, "rgba(255,200,80,0.12)");
    sp.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = sp;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }

  return toTexture(canvas);
}

/**
 * Soft radial glow sprite used for sun coronas, nebulae, and star halos.
 * Returns an RGBA canvas texture with smooth falloff.
 */
export function makeGlowTexture(
  innerColor: string,
  outerColor: string,
  size = 256
): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const [r1, g1, b1] = hexToRgb(innerColor);
  const [r2, g2, b2] = hexToRgb(outerColor);
  const c = size / 2;
  const img = ctx.createImageData(size, size);
  const d = img.data;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dist = Math.sqrt((x - c) ** 2 + (y - c) ** 2) / c; // 0 center → 1 edge
      const i = y * size + x;
      // Smooth exponential-ish falloff with a hot core
      const core = Math.max(0, 1 - dist / 0.18) ** 2;
      const halo = Math.max(0, 1 - dist) ** 2.6;
      const a = Math.min(1, core * 0.9 + halo * 0.55);
      const t = Math.min(1, dist * 1.4);
      d[i * 4]     = Math.round(r1 + (r2 - r1) * t);
      d[i * 4 + 1] = Math.round(g1 + (g2 - g1) * t);
      d[i * 4 + 2] = Math.round(b1 + (b2 - b1) * t);
      d[i * 4 + 3] = Math.round(a * 255);
    }
  }
  ctx.putImageData(img, 0, 0);
  return toTexture(canvas);
}

/**
 * Turbulent nebula sprite — value noise shaped by a radial falloff, with
 * darker dust lanes. Used for the big soft background clouds.
 */
export function makeNebulaTexture(color: string, seed: number, size = 256): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const [r, g, b] = hexToRgb(color);
  const n1 = noiseField(size, seed, 4, 6);
  const n2 = noiseField(size, seed * 5 + 9, 3, 14);
  const c = size / 2;
  const img = ctx.createImageData(size, size);
  const d = img.data;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dist = Math.sqrt((x - c) ** 2 + (y - c) ** 2) / c;
      const i = y * size + x;
      const cloud = n1[i] * 0.7 + n2[i] * 0.3;
      const shape = Math.max(0, 1 - dist) ** 2.2;
      const a = Math.max(0, (cloud - 0.32) * 1.9) * shape;
      // Dust lanes darken dense areas slightly toward deep blue
      d[i * 4]     = Math.round(r * (0.75 + cloud * 0.5));
      d[i * 4 + 1] = Math.round(g * (0.75 + cloud * 0.5));
      d[i * 4 + 2] = Math.round(Math.min(255, b * (0.8 + cloud * 0.5) + 20));
      d[i * 4 + 3] = Math.round(Math.min(255, a * 255));
    }
  }
  ctx.putImageData(img, 0, 0);
  return toTexture(canvas);
}

// ─── Galaxy — multi-color spiral disc for the repository core ──────────────

/**
 * Galaxy spiral-arm disc texture: bright core, dust-laned arms in the
 * galaxy's own hue plus young blue-white star clusters. Mapped onto a
 * horizontal disc mesh.
 */
export function makeGalaxyDiscTexture(color: string, seed: number, size = 1024): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  const [gr, gg, gb] = hexToRgb(color);
  const rand = seededRand(seed);

  ctx.clearRect(0, 0, size, size);
  const c = size / 2;

  // ── Core bulge: layered radial gradients (white-hot center) ──
  const coreLayers: Array<[number, string]> = [
    [0.05, "rgba(255,255,240,0.95)"],
    [0.12, `rgba(${Math.min(255, gr + 150)},${Math.min(255, gg + 140)},220,0.55)`],
    [0.22, `rgba(${Math.min(255, gr + 80)},${Math.min(255, gg + 90)},200,0.30)`],
    [0.38, rgbStr([gr, gg, gb], 1, 0, 0.16)],
  ];
  for (const [r, col] of coreLayers) {
    const g = ctx.createRadialGradient(c, c, 0, c, c, size * r);
    g.addColorStop(0, col);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
  }

  // ── Spiral arms: two per half (4 arms), drawn as soft blobs along a log spiral ──
  const arms = 4;
  for (let arm = 0; arm < arms; arm++) {
    const baseAngle = (arm / arms) * Math.PI * 2;
    for (let step = 0; step < 130; step++) {
      const t = step / 130;
      const angle = baseAngle + t * Math.PI * 2.1;
      const r = (0.08 + t * 0.42) * size;
      const x = c + Math.cos(angle) * r;
      const y = c + Math.sin(angle) * r;
      // Blob size grows outward; color cools from core-warm to arm hue
      const br = size * (0.012 + t * 0.045);
      const warm = Math.max(0, 1 - t * 1.8);
      const rr = Math.round(gr * (0.8 + warm * 0.4) + warm * 60);
      const gcol = Math.round(gg * (0.8 + warm * 0.4) + warm * 55);
      const bcol = Math.round(Math.min(255, gb * 0.9 + (1 - warm) * 90 + 30));
      const alpha = 0.05 + (1 - Math.abs(t - 0.55)) * 0.06;
      const g = ctx.createRadialGradient(x, y, 0, x, y, br);
      g.addColorStop(0, `rgba(${rr},${gcol},${bcol},${alpha})`);
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, br, 0, Math.PI * 2);
      ctx.fill();

      // Star clusters sprinkled along arms
      if (rand() > 0.86) {
        ctx.fillStyle = `rgba(255,255,255,${0.25 + rand() * 0.4})`;
        ctx.beginPath();
        ctx.arc(x + (rand() - 0.5) * br * 2.2, y + (rand() - 0.5) * br * 2.2, 0.8 + rand() * 1.6, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  // ── Dust lanes: dark wisps hugging the arms ──
  ctx.globalCompositeOperation = "destination-out";
  for (let i = 0; i < 340; i++) {
    const arm = Math.floor(rand() * arms);
    const t = rand();
    const angle = (arm / arms) * Math.PI * 2 + t * Math.PI * 2.1 + 0.12;
    const r = (0.1 + t * 0.4) * size;
    const x = c + Math.cos(angle) * r + (rand() - 0.5) * 26;
    const y = c + Math.sin(angle) * r + (rand() - 0.5) * 26;
    const rr = 3 + rand() * 15;
    const g = ctx.createRadialGradient(x, y, 0, x, y, rr);
    g.addColorStop(0, "rgba(0,0,0,0.5)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, rr, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalCompositeOperation = "source-over";

  return toTexture(canvas);
}

// ─── Ring system (Saturn-style) ────────────────────────────────────────────

/** 1D radial ring banding texture with Cassini-style gaps and color variation. */
export function makeRingTexture(color: string, seed: number, size = 512): THREE.CanvasTexture {
  const [canvas, ctx] = makeCanvas(size);
  canvas.height = 8;
  const [rr, rg, rb] = hexToRgb(color);
  const rand = seededRand(seed);

  const img = ctx.createImageData(size, 8);
  const d = img.data;
  // Band structure: per-pixel density from layered noise + gaps
  const density = noiseField(size, seed, 3, 40);
  for (let x = 0; x < size; x++) {
    const t = x / size; // 0 inner → 1 outer
    // Major gaps (Cassini division etc.)
    let gap = 1;
    for (const [gt, gw, gd] of [[0.30, 0.045, 0.15], [0.62, 0.03, 0.35], [0.85, 0.02, 0.4]] as const) {
      const dd = Math.abs(t - gt);
      if (dd < gw) gap = Math.min(gap, gd + (dd / gw) * 0.85);
    }
    // Fade in/out at edges
    const edge = Math.min(1, t / 0.08) * Math.min(1, (1 - t) / 0.08);
    const dens = (0.35 + density[x] * 0.65) * gap * edge;
    for (let y = 0; y < 8; y++) {
      const i = y * size + x;
      const shade = 0.6 + density[x] * 0.55;
      d[i * 4]     = Math.min(255, Math.round(rr * shade + 40 * shade));
      d[i * 4 + 1] = Math.min(255, Math.round(rg * shade + 38 * shade));
      d[i * 4 + 2] = Math.min(255, Math.round(rb * shade + 30 * shade));
      d[i * 4 + 3] = Math.round(Math.min(1, dens * 1.15) * 255);
    }
  }
  ctx.putImageData(img, 0, 0);
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.needsUpdate = true;
  return tex;
}
