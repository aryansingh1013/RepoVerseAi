import { useRef, useState, useMemo, useEffect, type ReactNode } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import { useNavigation } from "@/hooks/useNavigation";
import { positionsRegistry } from "./positionsRegistry";
import { ORBIT_SPEED, GLOBAL_ORBIT_SCALE, SELF_ROTATION, BODY_SCALE } from "./motionConfig";
import {
  makePlanetTexture,
  makePlanetBumpMap,
  makeMoonTexture,
  makeMoonBumpMap,
  makeStarTexture,
  makeGlowTexture,
  makeRingTexture,
} from "./textures";
import type { SpaceObject } from "@/types";

interface OrbitingBodyProps {
  object: SpaceObject;
  children?: ReactNode;
}

// ─── Procedural texture hooks (shared engine, see textures.ts) ────────────

function useBodyTextures(color: string, seed: number, kind: string) {
  return useMemo(() => {
    if (kind === "planet") {
      return {
        map: makePlanetTexture(color, seed, 256),
        bumpMap: makePlanetBumpMap(color, seed, 128),
        bumpScale: 0.03,
        glow: makeGlowTexture(color, "#02030a", 128),
      };
    }
    if (kind === "moon") {
      return {
        map: makeMoonTexture(color, seed, 256),
        bumpMap: makeMoonBumpMap(seed, 128),
        bumpScale: 0.05,
        glow: makeGlowTexture(color, "#02030a", 128),
      };
    }
    // star
    return {
      map: makeStarTexture(color, seed, 256),
      bumpMap: null,
      bumpScale: 0,
      glow: makeGlowTexture("#fff8e0", color, 256),
    };
  }, [color, seed, kind]);
}

// ─── Selection ring (PHASE 7.11 — visible selection state, not color-only) ──

function SelectionRing({ radius, color }: { radius: number; color: string }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => { if (ref.current) ref.current.rotation.z += delta * 0.3; });
  return (
    <mesh ref={ref} rotation={[Math.PI / 2.6, 0.2, 0]}>
      <ringGeometry args={[radius * 1.5, radius * 1.72, 64]} />
      <meshBasicMaterial
        color="#7dd3fc"
        transparent
        opacity={0.75}
        side={THREE.DoubleSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// ─── Orbit path ring (the faint line the planet travels along) ─────────────

function OrbitPath({ radius, inclination, color }: { radius: number; inclination: number; color: string }) {
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
      <lineBasicMaterial color={color} transparent opacity={0.09} depthWrite={false} />
    </line>
  );
}

// ─── Saturn-style ring system ─────────────────────────────────────────────

function RingSystem({ color, seed, scale }: { color: string; seed: number; scale: number }) {
  const mesh = useRef<THREE.Mesh>(null);

  // Rotate ring slightly differently from planet
  useFrame((_, delta) => {
    if (mesh.current) mesh.current.rotation.z += delta * 0.02;
  });

  const ringTexture = useMemo(() => makeRingTexture(color, seed, 256), [color, seed]);

  const innerR = scale * 1.25;
  const outerR = scale * 2.1;

  return (
    <mesh ref={mesh} rotation={[Math.PI / 2.2, 0.15, 0]}>
      <ringGeometry args={[innerR, outerR, 96]} />
      <meshBasicMaterial
        map={ringTexture}
        color={color}
        side={THREE.DoubleSide}
        transparent
        opacity={0.85}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// ─── Atmosphere glow shell (two-layer rim) ────────────────────────────────

function AtmosphereGlow({ radius, color, atmosphereColor }: { radius: number; color: string; atmosphereColor?: string }) {
  return (
    <>
      <mesh>
        <sphereGeometry args={[radius * 1.09, 32, 32]} />
        <meshBasicMaterial
          color={atmosphereColor ?? color}
          transparent
          opacity={0.1}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[radius * 1.2, 24, 24]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.05}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </>
  );
}

// ─── Main component ───────────────────────────────────────────────────────

/**
 * Renders one orbiting body. Visual differences by kind:
 * - star   (folder): plasma-textured sun with corona glow sprite + light
 * - planet (file):   sphere with procedural terrain, ice caps, atmosphere, optional rings
 * - moon   (fn):     cratered sphere with strong relief bump lighting
 *
 * Each body gets its own inclination and phase, plus a faint orbital path.
 */
export function OrbitingBody({ object, children }: OrbitingBodyProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef  = useRef<THREE.Mesh>(null);
  const [labelVisible, setLabelVisible] = useState(false);
  const { hoveredId, hover, navigateTo, selectedId, selectObject, isCut } = useNavigation();

  const isHovered = hoveredId === object.id;
  const isSelected = selectedId === object.id;
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
  // PHASE 7.5: moons get a floor (readable/clickable) and a cap (never rival
  // the parent planet).
  let meshScale =
    object.kind === "star"   ? fileCountScale * 1.6 :
    object.kind === "planet" ? object.scale * 0.8 :
    Math.min(
      Math.max(object.scale * BODY_SCALE.moonMultiplier, BODY_SCALE.moonMinScale),
      BODY_SCALE.moonMaxScale
    );

  const isRed =
    object.color?.toLowerCase() === '#ef4444' ||
    object.color?.toLowerCase() === '#e34c26' ||
    object.color?.toLowerCase() === '#ff2255' ||
    object.color?.toLowerCase() === '#ff0000';

  if (isRed) {
    if (object.kind === "planet") {
      meshScale = object.scale * 1.2;
    } else if (object.kind === "star") {
      meshScale = fileCountScale * 2.2;
    } else if (object.kind === "moon") {
      meshScale = object.scale * 4.0;
    }
  }

  // Geometry radius feeds atmosphere and rings
  const geoRadius =
    object.kind === "moon"   ? 0.32 :
    object.kind === "star"   ? 0.6  :
                               0.45;
  const physicalRadius = geoRadius * meshScale;

  // Procedural textures (per kind)
  const { map, bumpMap, bumpScale, glow } = useBodyTextures(object.color, seedVal, object.kind);

  // PHASE 24 — dispose GPU textures when this body unmounts (navigation /
  // cut). Textures are per-body (seeded), so they are never shared.
  useEffect(() => {
    return () => {
      map?.dispose();
      bumpMap?.dispose();
      glow?.dispose();
    };
  }, [map, bumpMap, glow]);

  // Self-rotation speed (stars spin fast like young suns, moons are tidally locked)
  // PHASE 7.7 — speeds come from the central motion config.
  const selfRotSpeed =
    object.kind === "star"   ? SELF_ROTATION.star :
    object.kind === "planet" ? SELF_ROTATION.planet :
                               SELF_ROTATION.moon;

  useFrame(({ clock }, delta) => {
    // PHASE 7.6/7.8 — time-based orbit: data speed × global cinematic scale ×
    // delta. Frame-rate independent; never angle += constant.
    const speed = (object.orbitSpeed ?? ORBIT_SPEED[object.kind as keyof typeof ORBIT_SPEED] ?? 0.1) * GLOBAL_ORBIT_SCALE;
    const t = clock.getElapsedTime() * speed * (object.direction ?? 1) + angleOffset;
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
    object.kind === "star"   ? (isHovered ? 1.2 : 0.9) :
    isHovered                ? 0.55 :
    object.kind === "moon"   ? 0.05 :
                               0.16;

  // All bodies are spheres now — moons included (octahedron read as "dots")
  const segments = object.kind === "moon" ? 32 : 40;

  // PHASE 15 — Cut: a cut body is removed from the universe view entirely
  // (children are nested inside this group, so they disappear with it).
  if (isCut(object.id)) return null;

  return (
    <group ref={groupRef}>
      {/* ── Faint orbital path ── */}
      <OrbitPath radius={radius} inclination={inclination} color={object.color} />

      {/* ── Main body ── */}
      <mesh
        ref={meshRef}
        scale={meshScale}
        onClick={(e) => {
          e.stopPropagation();
          selectObject(object.id);   // persistent highlight + info (PHASE 7.10)
          navigateTo(object.id);     // camera focus flight
        }}
        onPointerOver={(e) => { e.stopPropagation(); hover(object.id); setLabelVisible(true); }}
        onPointerOut={() => { hover(null); setLabelVisible(false); }}
      >
        <sphereGeometry args={[geoRadius, segments, segments]} />

        <meshStandardMaterial
          map={map}
          bumpMap={bumpMap ?? undefined}
          bumpScale={bumpScale}
          color={object.color}
          emissive={object.color}
          emissiveMap={object.kind === "star" ? map : undefined}
          emissiveIntensity={emissiveIntensity}
          roughness={object.roughness ?? (object.kind === "star" ? 0.35 : object.kind === "moon" ? 0.95 : 0.6)}
          metalness={object.metalness ?? (object.kind === "star" ? 0 : object.kind === "moon" ? 0.02 : 0.15)}
        />
      </mesh>

      {/* ── Selection ring (PHASE 7.11 — explicit selected state) ── */}
      {isSelected && <SelectionRing radius={physicalRadius} color={object.color} />}

      {/* ── Soft glow sprite behind every body (corona for stars, halo for planets) ── */}
      <sprite scale={[physicalRadius * (object.kind === "star" ? 5.2 : 2.6), physicalRadius * (object.kind === "star" ? 5.2 : 2.6), 1]}>
        <spriteMaterial
          map={glow}
          color={object.color}
          transparent
          opacity={object.kind === "star" ? (isHovered ? 0.85 : 0.65) : 0.22}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </sprite>

      {/* ── Atmosphere rim (planets) ── */}
      {object.kind === "planet" && (
        <AtmosphereGlow
          radius={physicalRadius}
          color={object.color}
          atmosphereColor={object.atmosphereColor}
        />
      )}

      {/* ── Star extra corona layers ── */}
      {object.kind === "star" && (
        <>
          <mesh scale={meshScale * 1.06}>
            <sphereGeometry args={[geoRadius * 0.95, 24, 24]} />
            <meshBasicMaterial color={object.color} transparent opacity={0.12} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <mesh scale={meshScale * 1.2}>
            <sphereGeometry args={[geoRadius * 0.9, 16, 16]} />
            <meshBasicMaterial color={object.atmosphereColor ?? object.color} transparent opacity={0.05} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <pointLight intensity={1.4} distance={14} color={object.color} />
        </>
      )}

      {/* ── Ring system (opted-in per file/planet) ── */}
      {object.hasRings && object.kind === "planet" && (
        <RingSystem color={object.color} seed={seedVal} scale={physicalRadius} />
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
