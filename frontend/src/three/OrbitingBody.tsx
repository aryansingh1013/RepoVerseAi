import { useRef, useState, useMemo, type ReactNode } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import { useNavigation } from "@/hooks/useNavigation";
import { positionsRegistry } from "./positionsRegistry";
import type { SpaceObject } from "@/types";

interface OrbitingBodyProps {
  object: SpaceObject;
  children?: ReactNode;
}

// ─── Procedural texture generators ────────────────────────────────────────

/**
 * Creates a canvas-based procedural texture: layered Perlin-like noise
 * painted in the object's own color family, so each body has unique surface
 * detail without loading any image files.
 */
function usePlanetTexture(color: string, seed: number, kind: string): THREE.CanvasTexture {
  return useMemo(() => {
    const size = 256;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;

    // Parse base color
    const hex = color.replace("#", "");
    const br = parseInt(hex.slice(0, 2), 16);
    const bg = parseInt(hex.slice(2, 4), 16);
    const bb = parseInt(hex.slice(4, 6), 16);

    // Seeded pseudo-random
    let s = seed * 1000003 + 7;
    const rand = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };

    // Base fill
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, size, size);

    if (kind === "star") {
      // Folder/star: swirling plasma
      for (let i = 0; i < 800; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const r2 = 3 + rand() * 18;
        const alpha = 0.04 + rand() * 0.12;
        const bright = rand() > 0.5;
        const gr = ctx.createRadialGradient(x, y, 0, x, y, r2);
        gr.addColorStop(0, `rgba(${bright ? 255 : br},${bright ? 240 : bg},${bright ? 180 : bb},${alpha})`);
        gr.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gr;
        ctx.beginPath();
        ctx.arc(x, y, r2, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (kind === "planet") {
      // File/planet: terrain with bands + craters
      // Horizontal bands
      for (let i = 0; i < 6; i++) {
        const y = rand() * size;
        const h = 4 + rand() * 28;
        const alpha = 0.06 + rand() * 0.14;
        const dark = rand() > 0.5;
        ctx.fillStyle = `rgba(${dark ? br * 0.5 : Math.min(255, br * 1.4)},${dark ? bg * 0.5 : Math.min(255, bg * 1.4)},${dark ? bb * 0.5 : Math.min(255, bb * 1.4)},${alpha})`;
        ctx.fillRect(0, y, size, h);
      }
      // Craters/spots
      for (let i = 0; i < 14; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const r2 = 3 + rand() * 14;
        const gr = ctx.createRadialGradient(x, y, 0, x, y, r2);
        gr.addColorStop(0, `rgba(0,0,0,0.18)`);
        gr.addColorStop(0.6, `rgba(${br},${bg},${bb},0.05)`);
        gr.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gr;
        ctx.beginPath();
        ctx.arc(x, y, r2, 0, Math.PI * 2);
        ctx.fill();
      }
      // Specular highlight
      const spec = ctx.createRadialGradient(size * 0.35, size * 0.3, 0, size * 0.4, size * 0.4, size * 0.5);
      spec.addColorStop(0, "rgba(255,255,255,0.15)");
      spec.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = spec;
      ctx.fillRect(0, 0, size, size);
    } else {
      // Moon: beautiful cratered surface using its own color family (purple/yellow)!
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, size, size);
      for (let i = 0; i < 20; i++) {
        const x = rand() * size;
        const y = rand() * size;
        const r2 = 2 + rand() * 10;
        ctx.fillStyle = `rgba(0,0,0,${0.15 + rand() * 0.25})`;
        ctx.beginPath();
        ctx.arc(x, y, r2, 0, Math.PI * 2);
        ctx.fill();
      }
      // Specular glow highlight
      const spec = ctx.createRadialGradient(size * 0.35, size * 0.3, 0, size * 0.4, size * 0.4, size * 0.5);
      spec.addColorStop(0, "rgba(255,255,255,0.22)");
      spec.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = spec;
      ctx.fillRect(0, 0, size, size);
    }

    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    return tex;
  }, [color, seed, kind]);
}

// ─── Orbit path ring (the dashed line the planet travels along) ───────────

function OrbitPath({ radius, inclination }: { radius: number; inclination: number }) {
  const geometry = useMemo(() => {
    const points: THREE.Vector3[] = [];
    const SEGMENTS = 128;
    for (let i = 0; i <= SEGMENTS; i++) {
      const angle = (i / SEGMENTS) * Math.PI * 2;
      const x = Math.cos(angle) * radius;
      const zFlat = Math.sin(angle) * radius;
      const y = zFlat * Math.sin(inclination);
      const z = zFlat * Math.cos(inclination);
      points.push(new THREE.Vector3(x, y, z));
    }
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [radius, inclination]);

  return (
    <line>
      {/* @ts-ignore — primitive line type */}
      <bufferGeometry attach="geometry" {...geometry} />
      <lineBasicMaterial color="#ffffff" transparent opacity={0.06} depthWrite={false} />
    </line>
  );
}

// ─── Saturn-style ring system ─────────────────────────────────────────────

function RingSystem({ color, scale }: { color: string; scale: number }) {
  const mesh = useRef<THREE.Mesh>(null);

  // Rotate ring slightly differently from planet
  useFrame((_, delta) => {
    if (mesh.current) mesh.current.rotation.z += delta * 0.02;
  });

  const ringTexture = useMemo(() => {
    const size = 256;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = 1;
    const ctx = canvas.getContext("2d")!;
    const grad = ctx.createLinearGradient(0, 0, size, 0);
    grad.addColorStop(0,    "rgba(0,0,0,0)");
    grad.addColorStop(0.15, `rgba(255,255,255,0.0)`);
    grad.addColorStop(0.22, `rgba(255,255,255,0.4)`);
    grad.addColorStop(0.38, `rgba(255,255,255,0.15)`);
    grad.addColorStop(0.5,  `rgba(255,255,255,0.55)`);
    grad.addColorStop(0.65, `rgba(255,255,255,0.1)`);
    grad.addColorStop(0.78, `rgba(255,255,255,0.35)`);
    grad.addColorStop(0.88, `rgba(255,255,255,0.05)`);
    grad.addColorStop(1,    "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, 1);
    const t = new THREE.CanvasTexture(canvas);
    t.needsUpdate = true;
    return t;
  }, []);

  const innerR = scale * 0.9;
  const outerR = scale * 1.8;

  return (
    <mesh ref={mesh} rotation={[Math.PI / 2.2, 0.15, 0]}>
      <ringGeometry args={[innerR, outerR, 64]} />
      <meshBasicMaterial
        map={ringTexture}
        color={color}
        side={THREE.DoubleSide}
        transparent
        opacity={0.55}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// ─── Atmosphere glow shell ────────────────────────────────────────────────

function AtmosphereGlow({ radius, color }: { radius: number; color: string }) {
  return (
    <mesh>
      <sphereGeometry args={[radius * 1.18, 24, 24]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.07}
        side={THREE.BackSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// ─── Main component ───────────────────────────────────────────────────────

/**
 * Renders one orbiting body. Visual differences by kind:
 * - star   (folder): icosahedron, plasma texture, size driven by fileCount
 * - planet (file):   sphere with procedural terrain texture, optional rings
 * - moon   (fn):     octahedron, cratered grey
 *
 * Each body gets its own inclination and phase, plus a faint orbital path.
 */
export function OrbitingBody({ object, children }: OrbitingBodyProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef  = useRef<THREE.Mesh>(null);
  const [labelVisible, setLabelVisible] = useState(false);
  const { hoveredId, hover, navigateTo } = useNavigation();

  const isHovered = hoveredId === object.id;
  const angleOffset = useRef(Math.random() * Math.PI * 2).current;
  const seedVal = useRef(Math.floor(Math.random() * 99999)).current;

  const radius      = object.orbitRadius ?? 2;
  const speed       = (object.orbitSpeed ?? 0.1) * (object.direction ?? 1);
  const inclination = object.inclination ?? 0;

  // Folders (stars) scale with fileCount so busier folders look bigger
  const fileCountScale = object.kind === "star" && object.fileCount
    ? 0.8 + Math.min(object.fileCount / 12, 1) * 0.7
    : object.scale;

  // Scale hierarchy: Sun (FocusBody) >> Star (Folder) >> Planet (File) >> Moon (Symbol)
  // Scale hierarchy: Sun (FocusBody) >> Star (Folder) >> Planet (File) >> Moon (Symbol)
  let meshScale = 
    object.kind === "star"   ? fileCountScale * 1.6 :
    object.kind === "planet" ? object.scale * 0.8 :
                               object.scale * 3.0; // Increased from 1.8 to 3.0 to make moons much bigger!

  const isRed = 
    object.color?.toLowerCase() === '#ef4444' || 
    object.color?.toLowerCase() === '#e34c26' || 
    object.color?.toLowerCase() === '#ff2255' || 
    object.color?.toLowerCase() === '#ff0000';

  if (isRed) {
    if (object.kind === "planet") {
      meshScale = object.scale * 1.2; // Boosted from 0.8 to 1.2
    } else if (object.kind === "star") {
      meshScale = fileCountScale * 2.2; // Boosted from 1.6 to 2.2
    } else if (object.kind === "moon") {
      meshScale = object.scale * 4.0; // Boosted from 3.0 to 4.0
    }
  }

  // Geometry radius feeds atmosphere and rings
  const geoRadius =
    object.kind === "moon"   ? 0.32 :
    object.kind === "star"   ? 0.6  :
                               0.45;
  const physicalRadius = geoRadius * meshScale;

  // Procedural texture
  const texture = usePlanetTexture(object.color, seedVal, object.kind);

  // Self-rotation speed (stars spin fast like young suns, moons are tidally locked)
  const selfRotSpeed =
    object.kind === "star"   ? 0.4 :
    object.kind === "planet" ? 0.12 :
                               0.0;

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime() * speed + angleOffset;
    const x = Math.cos(t) * radius;
    const zFlat = Math.sin(t) * radius;
    const y = zFlat * Math.sin(inclination);
    const z = zFlat * Math.cos(inclination);

    if (groupRef.current) groupRef.current.position.set(x, y, z);
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * selfRotSpeed;
      
      // Calculate and store world position instead of local coordinates
      const worldPos = new THREE.Vector3();
      meshRef.current.getWorldPosition(worldPos);
      positionsRegistry.set(object.id, worldPos.x, worldPos.y, worldPos.z);
    }
  });

  const emissiveIntensity =
    object.kind === "star"   ? (isHovered ? 1.1 : 0.8) :
    isHovered                ? 0.55 :
    object.kind === "moon"   ? 0.05 :
                               0.18;

  return (
    <group ref={groupRef}>
      {/* ── Faint orbital path ── */}
      <OrbitPath radius={radius} inclination={inclination} />

      {/* ── Main body ── */}
      <mesh
        ref={meshRef}
        scale={meshScale}
        onClick={(e) => { e.stopPropagation(); navigateTo(object.id); }}
        onPointerOver={(e) => { e.stopPropagation(); hover(object.id); setLabelVisible(true); }}
        onPointerOut={() => { hover(null); setLabelVisible(false); }}
      >
        {object.kind === "star"   && <icosahedronGeometry args={[geoRadius, 2]} />}
        {object.kind === "planet" && <sphereGeometry args={[geoRadius, 32, 32]} />}
        {object.kind === "moon"   && <octahedronGeometry args={[geoRadius, 1]} />}

        <meshStandardMaterial
          map={texture}
          color={object.color}
          emissive={object.color}
          emissiveIntensity={emissiveIntensity}
          roughness={object.roughness ?? (object.kind === "star" ? 0.25 : object.kind === "moon" ? 0.95 : 0.55)}
          metalness={object.metalness ?? (object.kind === "star" ? 0.1 : 0.2)}
        />
      </mesh>

      {/* ── Atmosphere glow (planets) ── */}
      {object.kind === "planet" && object.atmosphereColor && (
        <AtmosphereGlow radius={physicalRadius} color={object.atmosphereColor} />
      )}

      {/* ── Star corona ── */}
      {object.kind === "star" && (
        <>
          <mesh scale={meshScale * 1.05}>
            <sphereGeometry args={[geoRadius * 0.95, 16, 16]} />
            <meshBasicMaterial color={object.color} transparent opacity={0.1} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <mesh scale={meshScale * 1.18}>
            <sphereGeometry args={[geoRadius * 0.9, 12, 12]} />
            <meshBasicMaterial color={object.atmosphereColor ?? object.color} transparent opacity={0.04} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <pointLight intensity={1.2} distance={12} color={object.color} />
        </>
      )}

      {/* ── Ring system (opted-in per file/planet) ── */}
      {object.hasRings && object.kind === "planet" && (
        <RingSystem color={object.color} scale={physicalRadius} />
      )}

      {/* ── Label ── */}
      {(labelVisible || isHovered) && (
        <Html distanceFactor={10} position={[0, physicalRadius + 0.4, 0]} occlude>
          <div className="pointer-events-none whitespace-nowrap rounded-md bg-void-900/90 px-2 py-1 text-xs font-mono text-mist-100 border border-white/10 shadow-glow">
            <span className="opacity-50 mr-1">
              {object.kind === "star" ? "📁" : object.kind === "planet" ? "📄" : "⚙️"}
            </span>
            {object.name}
            {object.kind === "star" && object.fileCount != null && (
              <span className="ml-1.5 opacity-50 text-[10px]">{object.fileCount} files</span>
            )}
          </div>
        </Html>
      )}

      {/* ── Nested Orbits (Planets in Stars, Moons in Planets) ── */}
      {children}
    </group>
  );
}
