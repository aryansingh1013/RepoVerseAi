import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { positionsRegistry } from "./positionsRegistry";
import { useNavigation } from "@/hooks/useNavigation";
import type { SpaceObject } from "@/types";

interface FocusBodyProps {
  object: SpaceObject;
}

// ─── Procedural surface texture (same generator as OrbitingBody) ──────────

function useSurfaceTexture(color: string, seed: number, kind: string, size = 512): THREE.CanvasTexture {
  return useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;

    const hex = color.replace("#", "");
    const br = parseInt(hex.slice(0, 2), 16);
    const bg = parseInt(hex.slice(2, 4), 16);
    const bb = parseInt(hex.slice(4, 6), 16);

    let s = seed * 1000003 + 7;
    const rand = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };

    ctx.fillStyle = color;
    ctx.fillRect(0, 0, size, size);

    if (kind === "galaxy") {
      // Wireframe galaxy: swirling arms drawn as curves
      for (let arm = 0; arm < 3; arm++) {
        ctx.beginPath();
        const baseAngle = (arm / 3) * Math.PI * 2;
        for (let i = 0; i < 200; i++) {
          const t = i / 200;
          const angle = baseAngle + t * Math.PI * 2.5;
          const r = t * size * 0.45;
          const cx = size / 2 + Math.cos(angle) * r;
          const cy = size / 2 + Math.sin(angle) * r;
          i === 0 ? ctx.moveTo(cx, cy) : ctx.lineTo(cx, cy);
        }
        ctx.strokeStyle = `rgba(${Math.min(255,br+60)},${Math.min(255,bg+60)},${Math.min(255,bb+80)},0.25)`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      // Core glow
      const cg = ctx.createRadialGradient(size/2, size/2, 0, size/2, size/2, size * 0.3);
      cg.addColorStop(0, `rgba(255,255,220,0.4)`);
      cg.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = cg;
      ctx.fillRect(0, 0, size, size);
    } else if (kind === "star") {
      // Folder: animated plasma surface
      for (let i = 0; i < 1200; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const r = 3 + rand() * 22;
        const alpha = 0.03 + rand() * 0.15;
        const bright = rand() > 0.4;
        const gr = ctx.createRadialGradient(x, y, 0, x, y, r);
        gr.addColorStop(0, `rgba(${bright ? 255 : br},${bright ? 235 : bg},${bright ? 160 : bb},${alpha})`);
        gr.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gr;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (kind === "planet") {
      // File: rich terrain — bands, continent blobs, specular
      for (let i = 0; i < 8; i++) {
        const y = rand() * size;
        const h = 8 + rand() * 60;
        const dark = rand() > 0.5;
        ctx.fillStyle = `rgba(${dark ? br*0.45 : Math.min(255,br*1.5)},${dark ? bg*0.45 : Math.min(255,bg*1.5)},${dark ? bb*0.45 : Math.min(255,bb*1.5)},${0.08 + rand()*0.18})`;
        ctx.fillRect(0, y, size, h);
      }
      // Continent blobs
      for (let i = 0; i < 8; i++) {
        const cx = rand() * size;
        const cy = rand() * size;
        const rx = 20 + rand() * 80;
        const ry = 15 + rand() * 50;
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, rand() * Math.PI, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${Math.min(255,br+40)},${Math.min(255,bg+30)},${Math.min(255,bb+20)},0.12)`;
        ctx.fill();
      }
      // Craters
      for (let i = 0; i < 18; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const r = 4 + rand() * 22;
        const gr = ctx.createRadialGradient(x, y, 0, x, y, r);
        gr.addColorStop(0, `rgba(0,0,0,0.22)`);
        gr.addColorStop(0.5, `rgba(${br},${bg},${bb},0.06)`);
        gr.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gr;
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      }
      // Specular highlight
      const spec = ctx.createRadialGradient(size*0.32, size*0.28, 0, size*0.42, size*0.38, size*0.55);
      spec.addColorStop(0, "rgba(255,255,255,0.2)");
      spec.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = spec; ctx.fillRect(0, 0, size, size);
    } else {
      // Moon: grey cratered surface
      ctx.fillStyle = "#aaa"; ctx.fillRect(0, 0, size, size);
      for (let i = 0; i < 30; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const r = 3 + rand() * 20;
        ctx.fillStyle = `rgba(0,0,0,${0.12 + rand()*0.25})`;
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = `rgba(255,255,255,0.05)`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    return tex;
  }, [color, seed, kind, size]);
}

// ─── Bump / normal-esque roughness texture ─────────────────────────────────

function useBumpTexture(seed: number): THREE.CanvasTexture {
  return useMemo(() => {
    const size = 256;
    const canvas = document.createElement("canvas");
    canvas.width = size; canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    let s = seed * 999983;
    const rand = () => { s = (s * 16807) % 2147483647; return (s-1)/2147483646; };
    ctx.fillStyle = "#808080"; ctx.fillRect(0, 0, size, size);
    for (let i = 0; i < 600; i++) {
      const x = rand() * size; const y = rand() * size;
      const r = 2 + rand() * 12;
      const v = Math.floor(60 + rand() * 140);
      ctx.fillStyle = `rgba(${v},${v},${v},0.3)`;
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    }
    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    return tex;
  }, [seed]);
}

// ─── Atmosphere layers ─────────────────────────────────────────────────────

function AtmosphereLayers({ radius, color, atmosphereColor }: { radius: number; color: string; atmosphereColor?: string }) {
  return (
    <>
      {/* Inner atmosphere — the main color haze */}
      <mesh>
        <sphereGeometry args={[radius * 1.06, 32, 32]} />
        <meshBasicMaterial
          color={atmosphereColor ?? color}
          transparent opacity={0.08}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      {/* Outer fringe */}
      <mesh>
        <sphereGeometry args={[radius * 1.18, 24, 24]} />
        <meshBasicMaterial
          color={color}
          transparent opacity={0.04}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </>
  );
}

// ─── Ring system for focused planet ───────────────────────────────────────

function FocusRings({ radius, color }: { radius: number; color: string }) {
  const ringTex = useMemo(() => {
    const size = 512;
    const canvas = document.createElement("canvas");
    canvas.width = size; canvas.height = 1;
    const ctx = canvas.getContext("2d")!;
    const grad = ctx.createLinearGradient(0, 0, size, 0);
    grad.addColorStop(0,    "rgba(0,0,0,0)");
    grad.addColorStop(0.08, "rgba(255,255,255,0)");
    grad.addColorStop(0.18, "rgba(255,255,255,0.5)");
    grad.addColorStop(0.32, "rgba(255,255,255,0.15)");
    grad.addColorStop(0.45, "rgba(255,255,255,0.6)");
    grad.addColorStop(0.58, "rgba(255,255,255,0.1)");
    grad.addColorStop(0.7,  "rgba(255,255,255,0.45)");
    grad.addColorStop(0.84, "rgba(255,255,255,0.05)");
    grad.addColorStop(1,    "rgba(0,0,0,0)");
    ctx.fillStyle = grad; ctx.fillRect(0, 0, size, 1);
    const t = new THREE.CanvasTexture(canvas); t.needsUpdate = true; return t;
  }, []);

  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => { if (ref.current) ref.current.rotation.z += delta * 0.01; });

  return (
    <mesh ref={ref} rotation={[Math.PI / 2.3, 0.2, 0]}>
      <ringGeometry args={[radius * 1.35, radius * 2.4, 128]} />
      <meshBasicMaterial
        map={ringTex}
        color={color}
        side={THREE.DoubleSide}
        transparent opacity={0.6}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// ─── Galaxy wireframe disc ─────────────────────────────────────────────────

function GalaxyDisc({ color }: { color: string }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, delta) => { if (ref.current) ref.current.rotation.y += delta * 0.04; });

  const armPositions = useMemo(() => {
    const points: THREE.Vector3[] = [];
    for (let arm = 0; arm < 3; arm++) {
      const base = (arm / 3) * Math.PI * 2;
      for (let i = 0; i < 60; i++) {
        const t = i / 60;
        const angle = base + t * Math.PI * 2.5;
        const r = t * 2.8;
        points.push(new THREE.Vector3(Math.cos(angle) * r, (Math.random() - 0.5) * 0.1, Math.sin(angle) * r));
      }
    }
    return new THREE.BufferGeometry().setFromPoints(points);
  }, []);

  return (
    <group ref={ref}>
      {/* Outer disc glow */}
      <mesh>
        <torusGeometry args={[2.2, 0.35, 8, 64]} />
        <meshBasicMaterial color={color} transparent opacity={0.08} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      {/* Inner disc */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.6, 2.6, 64]} />
        <meshBasicMaterial color={color} transparent opacity={0.06} side={THREE.DoubleSide} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      {/* Spiral arm lines */}
      <line>
        {/* @ts-ignore */}
        <bufferGeometry attach="geometry" {...armPositions} />
        <lineBasicMaterial color={color} transparent opacity={0.25} depthWrite={false} />
      </line>
    </group>
  );
}

// ─── Main component ───────────────────────────────────────────────────────

/**
 * The focused object at the scene origin.
 * - galaxy   → icosahedron wireframe + swirling galactic disc overlay
 * - star     → large textured sphere with plasma surface + corona layers
 * - planet   → richly textured sphere with atmosphere, bump, optional rings
 * - moon     → grey cratered octahedron
 */
export function FocusBody({ object }: FocusBodyProps) {
  const meshRef   = useRef<THREE.Mesh>(null);
  const cloudRef  = useRef<THREE.Mesh>(null);
  const { goBack, hover, hoveredId, setMissionControlOpen } = useNavigation();
  const isHovered = hoveredId === object.id;

  const seed = useMemo(() => object.id.split("").reduce((a, c) => a + c.charCodeAt(0), 0), [object.id]);
  const surfaceTex = useSurfaceTexture(object.color, seed, object.kind, 512);
  const bumpTex    = useBumpTexture(seed);

  useFrame((_, delta) => {
    if (meshRef.current)  meshRef.current.rotation.y  += delta * (object.kind === "star" ? 0.15 : 0.06);
    if (cloudRef.current) cloudRef.current.rotation.y += delta * 0.1; // cloud layer drifts faster
    positionsRegistry.set(object.id, 0, 0, 0);
  });

  const canAscend  = object.parentId !== null;
  const baseRadius = 1.8 + object.scale * 1.5;

  return (
    <group
      onClick={(e) => { 
        e.stopPropagation(); 
        if (canAscend) {
          goBack(); 
        } else {
          setMissionControlOpen(true);
        }
      }}
      onPointerOver={(e) => { e.stopPropagation(); if (canAscend) hover(object.id); }}
      onPointerOut={() => hover(null)}
    >
      {/* ── Galaxy (repository) ── */}
      {object.kind === "galaxy" && (
        <>
          <mesh ref={meshRef}>
            <icosahedronGeometry args={[baseRadius + 0.4, 1]} />
            <meshStandardMaterial
              color={object.color}
              emissive={object.color}
              emissiveIntensity={isHovered ? 0.9 : 0.6}
              roughness={0.4} metalness={0.5}
              wireframe
            />
          </mesh>
          {/* Solid inner core */}
          <mesh>
            <sphereGeometry args={[baseRadius * 0.45, 24, 24]} />
            <meshStandardMaterial
              map={surfaceTex}
              color={object.color}
              emissive={object.color}
              emissiveIntensity={0.5}
              roughness={0.3} metalness={0.6}
            />
          </mesh>
          {/* Galactic disc overlay */}
          <GalaxyDisc color={object.color} />
        </>
      )}

      {/* ── Star (folder) ── */}
      {object.kind === "star" && (
        <>
          <mesh ref={meshRef}>
            <sphereGeometry args={[baseRadius, 48, 48]} />
            <meshStandardMaterial
              map={surfaceTex}
              color={object.color}
              emissive={object.color}
              emissiveIntensity={isHovered ? 1.1 : 0.78}
              roughness={0.2} metalness={0.05}
            />
          </mesh>
          {/* Solar flare / corona layers */}
          <mesh>
            <sphereGeometry args={[baseRadius * 1.12, 24, 24]} />
            <meshBasicMaterial color={object.color} transparent opacity={0.08} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <mesh>
            <sphereGeometry args={[baseRadius * 1.32, 18, 18]} />
            <meshBasicMaterial color={object.atmosphereColor ?? object.color} transparent opacity={0.04} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <mesh>
            <sphereGeometry args={[baseRadius * 1.65, 14, 14]} />
            <meshBasicMaterial color={object.color} transparent opacity={0.02} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
        </>
      )}

      {/* ── Planet (file) ── */}
      {object.kind === "planet" && (
        <>
          <mesh ref={meshRef}>
            <sphereGeometry args={[baseRadius, 48, 48]} />
            <meshStandardMaterial
              map={surfaceTex}
              bumpMap={bumpTex}
              bumpScale={0.04}
              color={object.color}
              emissive={object.color}
              emissiveIntensity={isHovered ? 0.4 : 0.12}
              roughness={object.roughness ?? 0.65}
              metalness={object.metalness ?? 0.15}
            />
          </mesh>
          {/* Wispy cloud layer */}
          <mesh ref={cloudRef}>
            <sphereGeometry args={[baseRadius * 1.025, 32, 32]} />
            <meshStandardMaterial
              color="#ffffff"
              transparent opacity={0.06}
              depthWrite={false}
            />
          </mesh>
          {/* Atmosphere */}
          <AtmosphereLayers radius={baseRadius} color={object.color} atmosphereColor={object.atmosphereColor} />
          {/* Rings if opted-in */}
          {object.hasRings && <FocusRings radius={baseRadius} color={object.color} />}
        </>
      )}

      {/* ── Moon (function/class) ── */}
      {object.kind === "moon" && (
        <mesh ref={meshRef}>
          <octahedronGeometry args={[baseRadius, 3]} />
          <meshStandardMaterial
            map={surfaceTex}
            bumpMap={bumpTex}
            bumpScale={0.02}
            color={object.color}
            emissive={object.color}
            emissiveIntensity={isHovered ? 0.35 : 0.05}
            roughness={0.92}
            metalness={0}
          />
        </mesh>
      )}

      {/* ── Corona / glow (all except moon) ── */}
      {object.kind !== "moon" && (
        <mesh>
          <sphereGeometry args={[baseRadius * 1.6, 24, 24]} />
          <meshBasicMaterial color={object.color} transparent opacity={0.05} depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>
      )}

      {/* ── Point light (illuminates children) ── */}
      <pointLight
        intensity={object.kind === "moon" ? 0.4 : object.kind === "star" ? 2.2 : 1.4}
        distance={object.kind === "star" ? 24 : 16}
        color={object.color}
      />

      {/* ── Back fill light so dark sides aren't pitch black ── */}
      {object.kind !== "moon" && (
        <pointLight intensity={0.15} distance={10} color="#aabbff" position={[-3, 2, -3]} />
      )}
    </group>
  );
}
