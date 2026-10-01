import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import { StarField } from "./StarField";
import { RepositorySystem } from "./RepositorySystem";
import { CameraRig } from "./CameraRig";
import { useSelectionKeyboard } from "./SelectionManager";
import { CAMERA, getQualityBudget } from "./motionConfig";
import { useNavigation } from "@/hooks/useNavigation";

const QUALITY = getQualityBudget();

// ─── Swirling Cosmic Stardust Particles ───────────────────────────────────────

function CosmicStardust() {
  const pointsRef = useRef<THREE.Points>(null);
  const COUNT = 350;

  const positions = useMemo(() => {
    const pos = new Float32Array(COUNT * 3);
    for (let i = 0; i < COUNT; i++) {
      const radius = 6 + Math.random() * 32;
      const angle = Math.random() * Math.PI * 2;
      pos[i * 3]     = Math.cos(angle) * radius;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 6;
      pos[i * 3 + 2] = Math.sin(angle) * radius;
    }
    return pos;
  }, []);

  useFrame((_, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.008;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        color="#93c5fd"
        transparent
        opacity={0.4}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Master SpaceScene ────────────────────────────────────────────────────────

export function SpaceScene() {
  const { focusId, spaceGraph } = useNavigation();
  const controlsRef = useRef<OrbitControlsImpl>(null);

  // Enable Escape key to return to central star overview
  useSelectionKeyboard();

  const focusObject = useMemo(
    () => spaceGraph.find((o) => o.id === focusId),
    [spaceGraph, focusId]
  );

  // Dynamic zoom distance depending on focused celestial body
  const viewDistance = useMemo(() => {
    if (!focusObject) return 24;
    if (focusObject.kind === "moon") return 1.4;
    if (focusObject.kind === "planet") return 4.5;
    // Central Repository Star
    return 24;
  }, [focusObject]);

  // Subtle depth fog color
  const fogColor = "#030612";

  return (
    <Canvas
      camera={{ position: [0, 16, 26], fov: 48 }}
      dpr={[1, QUALITY.dprMax]}
      gl={{
        antialias: QUALITY.dprMax > 1,
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.15,
      }}
    >
      <color attach="background" args={["#030612"]} />
      <fog attach="fog" args={[fogColor, 40, 120]} />

      {/* ── Lighting ── */}
      {/* Soft fill ambient */}
      <ambientLight intensity={0.25} color="#94a3b8" />
      {/* Key directional light giving depth & sphere shading to planets */}
      <directionalLight position={[14, 20, 12]} intensity={0.7} color="#e2e8f0" />
      <directionalLight position={[-12, -14, -10]} intensity={0.15} color="#3b82f6" />

      <Suspense fallback={null}>
        {/* Secondary deep-space background (sparse stars & nebulae) */}
        <StarField />

        {/* Ambient cosmic stardust particles drifting through the solar system */}
        <CosmicStardust />

        {/* ── Unified Solar System: 1 Star -> File Planets -> Symbol Moons ── */}
        <RepositorySystem />
      </Suspense>

      <OrbitControls
        ref={controlsRef}
        enablePan
        enableZoom
        enableRotate
        minDistance={1.0}
        maxDistance={95}
        dampingFactor={CAMERA.dampingFactor}
        enableDamping
        rotateSpeed={CAMERA.rotateSpeed}
        zoomSpeed={CAMERA.zoomSpeed}
      />
      <CameraRig controlsRef={controlsRef} viewDistance={viewDistance} />
    </Canvas>
  );
}
