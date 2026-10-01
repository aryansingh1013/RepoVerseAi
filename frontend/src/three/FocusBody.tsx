import { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { positionsRegistry } from "./positionsRegistry";
import { useNavigation } from "@/hooks/useNavigation";
import { SELF_ROTATION } from "./motionConfig";
import {
  makePlanetTexture,
  makePlanetBumpMap,
  makeMoonTexture,
  makeMoonBumpMap,
  makeStarTexture,
  makeGlowTexture,
  makeGalaxyDiscTexture,
  makeRingTexture,
} from "./textures";
import type { SpaceObject } from "@/types";

interface FocusBodyProps {
  object: SpaceObject;
}

// ─── Atmosphere layers ─────────────────────────────────────────────────────

function AtmosphereLayers({ radius, color, atmosphereColor }: { radius: number; color: string; atmosphereColor?: string }) {
  return (
    <>
      {/* Inner atmosphere — the main color haze */}
      <mesh>
        <sphereGeometry args={[radius * 1.06, 48, 48]} />
        <meshBasicMaterial
          color={atmosphereColor ?? color}
          transparent opacity={0.1}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      {/* Outer fringe */}
      <mesh>
        <sphereGeometry args={[radius * 1.18, 32, 32]} />
        <meshBasicMaterial
          color={color}
          transparent opacity={0.05}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </>
  );
}

// ─── Ring system for focused planet ───────────────────────────────────────

function FocusRings({ radius, color, seed }: { radius: number; color: string; seed: number }) {
  const ringTex = useMemo(() => makeRingTexture(color, seed, 512), [color, seed]);

  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => { if (ref.current) ref.current.rotation.z += delta * 0.01; });

  return (
    <mesh ref={ref} rotation={[Math.PI / 2.3, 0.2, 0]}>
      <ringGeometry args={[radius * 1.4, radius * 2.5, 128]} />
      <meshBasicMaterial
        map={ringTex}
        color={color}
        side={THREE.DoubleSide}
        transparent opacity={0.9}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// ─── Galaxy — layered spiral disc with glow core ───────────────────────────

function GalaxyDisc({ color, seed }: { color: string; seed: number }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    // PHASE 7.7 — calm galaxy disc rotation (rad/s, delta-based)
    if (ref.current) ref.current.rotation.z += delta * SELF_ROTATION.galaxy;
  });

  const discTex = useMemo(() => makeGalaxyDiscTexture(color, seed, 1024), [color, seed]);
  const glowTex = useMemo(() => makeGlowTexture("#fff9e8", color, 256), [color, seed]);

  // PHASE 24 — dispose galaxy disc textures on unmount
  useEffect(() => {
    return () => { discTex.dispose(); glowTex.dispose(); };
  }, [discTex, glowTex]);

  return (
    <group ref={ref} rotation={[Math.PI / 2.4, 0, 0]}>
      {/* Textured spiral disc */}
      <mesh>
        <circleGeometry args={[3.2, 96]} />
        <meshBasicMaterial
          map={discTex}
          color={color}
          transparent
          opacity={0.9}
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      {/* Faint counter-rotating halo disc */}
      <mesh rotation={[0, 0, Math.PI / 5]}>
        <ringGeometry args={[2.2, 4.2, 96]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.05}
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      {/* Hot core glow sprite */}
      <sprite scale={[7.5, 7.5, 1]}>
        <spriteMaterial
          map={glowTex}
          color={color}
          transparent
          opacity={0.75}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </sprite>
    </group>
  );
}

// ─── Main component ───────────────────────────────────────────────────────

/**
 * The focused object at the scene origin.
 * - galaxy → glowing core + textured multi-arm spiral disc
 * - star   → plasma-granulated sun with corona glow layers
 * - planet → noise-terrain sphere, cloud layer, atmosphere, optional rings
 * - moon   → heavily cratered sphere with strong relief lighting
 */
export function FocusBody({ object }: FocusBodyProps) {
  const meshRef   = useRef<THREE.Mesh>(null);
  const cloudRef  = useRef<THREE.Mesh>(null);
  const glowRef   = useRef<THREE.Sprite>(null);
  const { goBack, hover, hoveredId, setMissionControlOpen } = useNavigation();
  const isHovered = hoveredId === object.id;

  const seed = useMemo(() => object.id.split("").reduce((a, c) => a + c.charCodeAt(0), 0), [object.id]);

  // Per-kind procedural textures from the shared engine
  const { map, bumpMap, bumpScale, glowTex } = useMemo(() => {
    switch (object.kind) {
      case "star":
        return {
          map: makeStarTexture(object.color, seed, 512),
          bumpMap: null,
          bumpScale: 0,
          glowTex: makeGlowTexture("#fff8e0", object.color, 512),
        };
      case "planet":
        return {
          map: makePlanetTexture(object.color, seed, 1024),
          bumpMap: makePlanetBumpMap(object.color, seed, 256),
          bumpScale: 0.05,
          glowTex: makeGlowTexture(object.color, "#02030a", 256),
        };
      case "moon":
        return {
          map: makeMoonTexture(object.color, seed, 512),
          bumpMap: makeMoonBumpMap(seed, 256),
          bumpScale: 0.06,
          glowTex: makeGlowTexture(object.color, "#02030a", 256),
        };
      default: // galaxy
        return {
          map: null,
          bumpMap: null,
          bumpScale: 0,
          glowTex: makeGlowTexture("#fff9e8", object.color, 512),
        };
    }
  }, [object.kind, object.color, seed]);

  useFrame((_, delta) => {
    // PHASE 7.7 — rotation speeds from central motion config (rad/s, delta-based)
    const spin = object.kind === "star" ? SELF_ROTATION.star : SELF_ROTATION.planet;
    if (meshRef.current)  meshRef.current.rotation.y  += delta * spin;
    if (cloudRef.current) cloudRef.current.rotation.y += delta * SELF_ROTATION.moon * 3; // cloud drift
    if (glowRef.current) {
      // Corona pulse for stars/galaxies
      const pulse = 1 + Math.sin(performance.now() * 0.0012) * 0.04;
      const s = (object.kind === "star" ? 5.4 : 4.2) * pulse * (isHovered ? 1.1 : 1);
      glowRef.current.scale.set(s, s, 1);
    }
    positionsRegistry.set(object.id, 0, 0, 0);
  });

  // PHASE 24 — dispose per-kind focus textures on unmount
  useEffect(() => {
    return () => {
      map?.dispose();
      bumpMap?.dispose();
      glowTex?.dispose();
    };
  }, [map, bumpMap, glowTex]);

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
          {/* Swirling spiral disc + core */}
          <GalaxyDisc color={object.color} seed={seed} />
          {/* Small molten core sphere under the glow */}
          <mesh>
            <sphereGeometry args={[baseRadius * 0.22, 32, 32]} />
            <meshStandardMaterial
              color="#fff4d6"
              emissive={object.color}
              emissiveIntensity={1.4}
              roughness={0.3} metalness={0}
            />
          </mesh>
          {/* Core glow sprite (pulsing) */}
          <sprite ref={glowRef} scale={[4.2, 4.2, 1]}>
            <spriteMaterial
              map={glowTex}
              color={object.color}
              transparent
              opacity={0.8}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </sprite>
        </>
      )}

      {/* ── Star (folder) — the focused sun ── */}
      {object.kind === "star" && (
        <>
          <mesh ref={meshRef}>
            <sphereGeometry args={[baseRadius, 64, 64]} />
            <meshStandardMaterial
              map={map ?? undefined}
              color={object.color}
              emissive={object.color}
              emissiveMap={map ?? undefined}
              emissiveIntensity={isHovered ? 1.15 : 0.85}
              roughness={0.4} metalness={0}
            />
          </mesh>
          {/* Pulsing corona glow sprite */}
          <sprite ref={glowRef} scale={[5.4, 5.4, 1]}>
            <spriteMaterial
              map={glowTex}
              color={object.color}
              transparent
              opacity={0.85}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </sprite>
          {/* Prominence shells */}
          <mesh>
            <sphereGeometry args={[baseRadius * 1.08, 32, 32]} />
            <meshBasicMaterial color={object.color} transparent opacity={0.1} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <mesh>
            <sphereGeometry args={[baseRadius * 1.25, 24, 24]} />
            <meshBasicMaterial color={object.atmosphereColor ?? object.color} transparent opacity={0.04} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
          <mesh>
            <sphereGeometry args={[baseRadius * 1.55, 16, 16]} />
            <meshBasicMaterial color={object.color} transparent opacity={0.02} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
        </>
      )}

      {/* ── Planet (file) ── */}
      {object.kind === "planet" && (
        <>
          <mesh ref={meshRef}>
            <sphereGeometry args={[baseRadius, 64, 64]} />
            <meshStandardMaterial
              map={map ?? undefined}
              bumpMap={bumpMap ?? undefined}
              bumpScale={bumpScale}
              color={object.color}
              emissive={object.color}
              emissiveIntensity={isHovered ? 0.35 : 0.1}
              roughness={object.roughness ?? 0.7}
              metalness={object.metalness ?? 0.1}
            />
          </mesh>
          {/* Wispy cloud layer */}
          <mesh ref={cloudRef}>
            <sphereGeometry args={[baseRadius * 1.03, 48, 48]} />
            <meshStandardMaterial
              color="#ffffff"
              transparent opacity={0.07}
              depthWrite={false}
              roughness={1}
            />
          </mesh>
          {/* Atmosphere */}
          <AtmosphereLayers radius={baseRadius} color={object.color} atmosphereColor={object.atmosphereColor} />
          {/* Soft halo behind the planet */}
          <sprite scale={[baseRadius * 3.2, baseRadius * 3.2, 1]}>
            <spriteMaterial
              map={glowTex}
              color={object.color}
              transparent
              opacity={0.16}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </sprite>
          {/* Rings if opted-in */}
          {object.hasRings && <FocusRings radius={baseRadius} color={object.color} seed={seed} />}
        </>
      )}

      {/* ── Moon (function/class) — cratered sphere with relief ── */}
      {object.kind === "moon" && (
        <>
          <mesh ref={meshRef}>
            <sphereGeometry args={[baseRadius, 64, 64]} />
            <meshStandardMaterial
              map={map ?? undefined}
              bumpMap={bumpMap ?? undefined}
              bumpScale={bumpScale}
              color={object.color}
              emissive={object.color}
              emissiveIntensity={isHovered ? 0.25 : 0.04}
              roughness={0.95}
              metalness={0}
            />
          </mesh>
          <sprite scale={[baseRadius * 2.4, baseRadius * 2.4, 1]}>
            <spriteMaterial
              map={glowTex}
              color={object.color}
              transparent
              opacity={0.12}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </sprite>
        </>
      )}

      {/* ── Point light (illuminates children) ── */}
      <pointLight
        intensity={object.kind === "moon" ? 0.4 : object.kind === "star" ? 2.4 : 1.4}
        distance={object.kind === "star" ? 26 : 16}
        color={object.color}
      />

      {/* ── Back fill light so dark sides aren't pitch black ── */}
      {object.kind !== "moon" && (
        <pointLight intensity={0.15} distance={10} color="#aabbff" position={[-3, 2, -3]} />
      )}
    </group>
  );
}
