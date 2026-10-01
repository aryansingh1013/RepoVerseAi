import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { getQualityBudget } from "./motionConfig";

const BUDGET = getQualityBudget();

// ─── Utility ──────────────────────────────────────────────────────────────────

function seededRand(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// ─── Regular star shell ────────────────────────────────────────────────────

interface LayerConfig {
  count: number;
  radius: number;
  size: number;
  opacity: number;
  driftSpeed: number;
  color: string;
}

function useShellPositions(count: number, radius: number) {
  return useMemo(() => {
    const rand = seededRand(count * 7919 + radius * 31);
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = radius * (0.7 + rand() * 0.3);
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      arr[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, [count, radius]);
}

function StarLayer({ count, radius, size, opacity, driftSpeed, color }: LayerConfig) {
  const pointsRef = useRef<THREE.Points>(null);
  const positions = useShellPositions(count, radius);

  useFrame((_, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * driftSpeed;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={size}
        color={color}
        transparent
        opacity={opacity}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

// ─── Subtle Nebula Cloud ───────────────────────────────────────────────────

function NebulaCloud({
  seed,
  center,
  radius,
  color,
  count,
  opacity,
}: {
  seed: number;
  center: [number, number, number];
  radius: number;
  color: string;
  count: number;
  opacity: number;
}) {
  const pointsRef = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const rand = seededRand(seed * 4099 + 17);
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = Math.pow(rand(), 1.8) * radius;
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      arr[i * 3]     = center[0] + r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = center[1] + r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = center[2] + r * Math.cos(phi);
    }
    return arr;
  }, [seed, center, radius, count]);

  useFrame((_, delta) => {
    if (pointsRef.current) pointsRef.current.rotation.y += delta * 0.0004;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.25}
        color={color}
        transparent
        opacity={opacity}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Occasional Shooting Star ─────────────────────────────────────────────

function ShootingStar() {
  const meshRef = useRef<THREE.Mesh>(null);
  const trailRef = useRef<THREE.Mesh>(null);
  const state = useRef({
    active: false,
    progress: 0,
    start: new THREE.Vector3(),
    end: new THREE.Vector3(),
    nextSpawn: 6 + Math.random() * 10,
  });

  useFrame((_, delta) => {
    const s = state.current;
    s.nextSpawn -= delta;

    if (!s.active && s.nextSpawn <= 0) {
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1) * 0.4;
      const r = 50;
      s.start.set(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta) * 0.5 + 20,
        r * Math.cos(phi)
      );
      const dir = new THREE.Vector3(
        (Math.random() - 0.5) * 0.4,
        -0.6 - Math.random() * 0.3,
        (Math.random() - 0.5) * 0.4
      ).normalize();
      s.end.copy(s.start).addScaledVector(dir, 20 + Math.random() * 15);
      s.progress = 0;
      s.active = true;
      s.nextSpawn = 8 + Math.random() * 15;
    }

    if (s.active && meshRef.current && trailRef.current) {
      s.progress = Math.min(1, s.progress + delta * 0.8);
      const pos = new THREE.Vector3().lerpVectors(s.start, s.end, s.progress);
      meshRef.current.position.copy(pos);
      trailRef.current.position.copy(pos);

      const fade = 1 - Math.abs(s.progress - 0.5) * 2;
      (meshRef.current.material as THREE.MeshBasicMaterial).opacity = fade * 0.8;
      (trailRef.current.material as THREE.MeshBasicMaterial).opacity = fade * 0.25;

      if (s.progress >= 1) s.active = false;
    }
  });

  return (
    <group>
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.06, 6, 6]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0} depthWrite={false} />
      </mesh>
      <mesh ref={trailRef}>
        <sphereGeometry args={[0.16, 6, 6]} />
        <meshBasicMaterial color="#aaccff" transparent opacity={0} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

// ─── Export Clean Secondary Space Background ─────────────────────────────────

export function StarField() {
  return (
    <>
      {/* Distant shell layers for deep parallax depth */}
      <StarLayer count={BUDGET.starCounts[0]} radius={85} size={0.045} opacity={0.45} driftSpeed={0.002} color="#8fa3d1" />
      <StarLayer count={BUDGET.starCounts[1]} radius={120} size={0.065} opacity={0.65} driftSpeed={0.005} color="#c9d6f5" />
      <StarLayer count={BUDGET.starCounts[2]} radius={160} size={0.08} opacity={0.8}  driftSpeed={0.009} color="#ffffff"  />

      {/* Very subtle deep-space nebula clouds far behind the solar system */}
      <NebulaCloud seed={11} center={[ 36, 12, -28]} radius={18} color="#2563eb" count={120} opacity={0.025} />
      <NebulaCloud seed={22} center={[-32, -8,  34]} radius={16} color="#7c3aed" count={100} opacity={0.02} />

      {/* Life & motion */}
      <ShootingStar />
    </>
  );
}
