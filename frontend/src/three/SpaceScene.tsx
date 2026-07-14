import { Suspense, useMemo, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import { StarField } from "./StarField";
import { FocusBody } from "./FocusBody";
import { OrbitingBody } from "./OrbitingBody";
import { CameraRig } from "./CameraRig";
import { useNavigation } from "@/hooks/useNavigation";

/** A faint volumetric nebula billboard — cheap additive-blended plane. */
function NebulaVolume({ position, color, size, opacity }: {
  position: [number, number, number];
  color: string;
  size: number;
  opacity: number;
}) {
  return (
    <mesh position={position} rotation={[0.3, 0.8, 0.2]}>
      <planeGeometry args={[size, size]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        side={THREE.DoubleSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

/** Animated particle dust that drifts slowly around the focused body. */
function LocalDust() {
  const positions = useMemo(() => {
    const arr = new Float32Array(200 * 3);
    for (let i = 0; i < 200; i++) {
      arr[i * 3]     = (Math.random() - 0.5) * 14;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 8;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 14;
    }
    return arr;
  }, []);

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#8899cc"
        transparent
        opacity={0.35}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export function SpaceScene() {
  const { focusId, spaceGraph } = useNavigation();
  const controlsRef = useRef<OrbitControlsImpl>(null);

  // Retrieve different celestial bodies from flat graph
  const galaxyCore = useMemo(() => spaceGraph.find(o => o.kind === "galaxy"), [spaceGraph]);
  const stars = useMemo(() => spaceGraph.filter(o => o.kind === "star"), [spaceGraph]);
  const planets = useMemo(() => spaceGraph.filter(o => o.kind === "planet"), [spaceGraph]);
  const moons = useMemo(() => spaceGraph.filter(o => o.kind === "moon"), [spaceGraph]);

  const focusObject = useMemo(() => spaceGraph.find((o) => o.id === focusId), [spaceGraph, focusId]);

  // Adjust zoom distance dynamically depending on object depth
  const viewDistance = useMemo(() => {
    if (!focusObject) return 15;
    if (focusObject.kind === "galaxy") return 15;
    if (focusObject.kind === "star") return 5.5;
    if (focusObject.kind === "planet") return 2.2;
    if (focusObject.kind === "moon") return 0.85;
    return 15;
  }, [focusObject]);

  // Tint the fog color toward the focused object's color for a localized haze
  const fogColor = focusObject
    ? `#${parseInt(focusObject.color.slice(1), 16).toString(16).padStart(6, "0")}`
    : "#05070d";

  if (!galaxyCore) {
    return (
      <Canvas camera={{ position: [8, 5, 10], fov: 50 }}>
        <color attach="background" args={["#04060c"]} />
        <ambientLight intensity={0.2} />
      </Canvas>
    );
  }

  return (
    <Canvas
      camera={{ position: [8, 5, 10], fov: 50 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.1 }}
    >
      <color attach="background" args={["#04060c"]} />
      {/* Soft depth fog — tinted toward focused body's hue */}
      <fog attach="fog" args={[fogColor, 25, 60]} />

      {/* ── Lighting ── */}
      <ambientLight intensity={0.18} color="#b8c8ff" />
      <directionalLight position={[6, 8, 4]} intensity={0.6} color="#ccd8ff" />
      <directionalLight position={[-4, -6, -2]} intensity={0.12} color="#ff8844" />
      <pointLight position={[-10, 4, -8]} intensity={0.25} color="#4466ff" distance={30} />
      <pointLight position={[10, -3, 6]} intensity={0.15} color="#ffaa44" distance={25} />

      <Suspense fallback={null}>
        {/* ── Background ── */}
        <StarField />

        {/* ── Nebula volumes in background ── */}
        <NebulaVolume position={[ 18, 4, -12]} color="#2233ff" size={22} opacity={0.025} />
        <NebulaVolume position={[-16, -3,  18]} color="#ff2255" size={18} opacity={0.020} />
        <NebulaVolume position={[  8, 12, -20]} color="#00ccaa" size={16} opacity={0.018} />

        {/* Local dust particles near focus */}
        <LocalDust />

        {/* ── 3D Universe Hierarchy ── */}
        {/* Core Galaxy (Root Repository) */}
        <FocusBody object={galaxyCore} />

        {/* Stars (Folders) orbiting the core */}
        {stars.map((star) => {
          const starPlanets = planets.filter((p) => p.parentId === star.id);
          return (
            <OrbitingBody key={star.id} object={star}>
              {/* Planets (Files) orbiting their parent star folder */}
              {starPlanets.map((planet) => {
                const planetMoons = moons.filter((m) => m.parentId === planet.id);
                return (
                  <OrbitingBody key={planet.id} object={planet}>
                    {/* Moons (Symbols) orbiting their parent planet file */}
                    {planetMoons.map((moon) => (
                      <OrbitingBody key={moon.id} object={moon} />
                    ))}
                  </OrbitingBody>
                );
              })}
            </OrbitingBody>
          );
        })}
      </Suspense>

      <OrbitControls
        ref={controlsRef}
        enablePan
        enableZoom
        enableRotate
        minDistance={1.2}
        maxDistance={65}
        dampingFactor={0.08}
        enableDamping
        rotateSpeed={0.6}
        zoomSpeed={0.8}
      />
      <CameraRig controlsRef={controlsRef} viewDistance={viewDistance} />
    </Canvas>
  );
}
