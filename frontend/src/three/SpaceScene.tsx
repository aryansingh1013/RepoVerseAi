import { Suspense, useMemo, useRef } from "react";
import { Canvas } from "@react-three/fiber";
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
    if (!focusObject) return 20;
    if (focusObject.kind === "moon") return 1.35;
    if (focusObject.kind === "planet") return 3.6;
    // Central Repository Star
    return 20;
  }, [focusObject]);

  // Subtle depth fog color
  const fogColor = "#030612";

  return (
    <Canvas
      camera={{ position: [0, 14, 22], fov: 48 }}
      dpr={[1, QUALITY.dprMax]}
      gl={{
        antialias: QUALITY.dprMax > 1,
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.15,
      }}
    >
      <color attach="background" args={["#030612"]} />
      <fog attach="fog" args={[fogColor, 35, 100]} />

      {/* ── Lighting ── */}
      {/* Soft fill ambient */}
      <ambientLight intensity={0.28} color="#94a3b8" />
      {/* Key directional light giving depth & sphere shading to planets */}
      <directionalLight position={[12, 18, 10]} intensity={0.65} color="#e2e8f0" />
      <directionalLight position={[-10, -12, -8]} intensity={0.15} color="#3b82f6" />

      <Suspense fallback={null}>
        {/* Secondary deep-space background (no galaxies, sparse stars) */}
        <StarField />

        {/* ── Unified Solar System: 1 Star -> File Planets -> Symbol Moons ── */}
        <RepositorySystem />
      </Suspense>

      <OrbitControls
        ref={controlsRef}
        enablePan
        enableZoom
        enableRotate
        minDistance={1.0}
        maxDistance={85}
        dampingFactor={CAMERA.dampingFactor}
        enableDamping
        rotateSpeed={CAMERA.rotateSpeed}
        zoomSpeed={CAMERA.zoomSpeed}
      />
      <CameraRig controlsRef={controlsRef} viewDistance={viewDistance} />
    </Canvas>
  );
}
