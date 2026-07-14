import { useMemo, useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

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
      const r = radius * (0.6 + rand() * 0.4);
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
      <pointsMaterial size={size} color={color} transparent opacity={opacity} sizeAttenuation depthWrite={false} />
    </points>
  );
}

// ─── Milky Way Spiral Arms ─────────────────────────────────────────────────

function SpiralArm({ armIndex, totalArms }: { armIndex: number; totalArms: number }) {
  const groupRef = useRef<THREE.Group>(null);
  const COUNT = 800;

  const { positions, colors } = useMemo(() => {
    const rand = seededRand(armIndex * 1337 + 42);
    const pos = new Float32Array(COUNT * 3);
    const col = new Float32Array(COUNT * 3);
    const baseAngle = (armIndex / totalArms) * Math.PI * 2;

    for (let i = 0; i < COUNT; i++) {
      const t = rand();                        // 0..1 along the arm
      const spiral = baseAngle + t * Math.PI * 1.8; // how much it wraps
      const r = 12 + t * 48;                  // distance from center
      const spread = (rand() - 0.5) * (3 + t * 12); // arm width grows outward
      const vertSpread = (rand() - 0.5) * (1 + t * 4);

      pos[i * 3]     = Math.cos(spiral) * r + (rand() - 0.5) * spread;
      pos[i * 3 + 1] = vertSpread;
      pos[i * 3 + 2] = Math.sin(spiral) * r + (rand() - 0.5) * spread;

      // Core is bluer/whiter, outer arm is warmer/dimmer
      const warmth = t;
      col[i * 3]     = 0.7 + warmth * 0.3;
      col[i * 3 + 1] = 0.75 + (1 - warmth) * 0.1;
      col[i * 3 + 2] = 1.0 - warmth * 0.4;
    }
    return { positions: pos, colors: col };
  }, [armIndex, totalArms]);

  useFrame((_, delta) => {
    if (groupRef.current) groupRef.current.rotation.y += delta * 0.001;
  });

  return (
    <group ref={groupRef}>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="attributes-color"    args={[colors, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={0.06}
          vertexColors
          transparent
          opacity={0.55}
          sizeAttenuation
          depthWrite={false}
        />
      </points>
    </group>
  );
}

// ─── Nebula Cloud ──────────────────────────────────────────────────────────

interface NebulaProps {
  seed: number;
  center: [number, number, number];
  radius: number;
  color: string;
  count: number;
  opacity: number;
}

function NebulaCloud({ seed, center, radius, color, count, opacity }: NebulaProps) {
  const positions = useMemo(() => {
    const rand = seededRand(seed);
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = radius * Math.pow(rand(), 0.5);
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      arr[i * 3]     = center[0] + r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = center[1] + r * Math.sin(phi) * Math.sin(theta) * 0.4;
      arr[i * 3 + 2] = center[2] + r * Math.cos(phi);
    }
    return arr;
  }, [seed, center, radius, count]);

  const pointsRef = useRef<THREE.Points>(null);
  useFrame((_, delta) => {
    if (pointsRef.current) pointsRef.current.rotation.y += delta * 0.0005;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.35}
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

// ─── Shooting Star ─────────────────────────────────────────────────────────

function ShootingStar() {
  const meshRef = useRef<THREE.Mesh>(null);
  const trailRef = useRef<THREE.Mesh>(null);
  const state = useRef({
    active: false,
    progress: 0,
    start: new THREE.Vector3(),
    end: new THREE.Vector3(),
    nextSpawn: 4 + Math.random() * 8,
  });

  useFrame((_, delta) => {
    const s = state.current;
    s.nextSpawn -= delta;

    if (!s.active && s.nextSpawn <= 0) {
      // Spawn from a random point on a far sphere
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1) * 0.4; // mostly equatorial
      const r = 35;
      s.start.set(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta) * 0.5 + 15,
        r * Math.cos(phi),
      );
      const dir = new THREE.Vector3(
        (Math.random() - 0.5) * 0.4,
        -0.6 - Math.random() * 0.3,
        (Math.random() - 0.5) * 0.4,
      ).normalize();
      s.end.copy(s.start).addScaledVector(dir, 18 + Math.random() * 12);
      s.progress = 0;
      s.active = true;
      s.nextSpawn = 5 + Math.random() * 12;
    }

    if (s.active && meshRef.current && trailRef.current) {
      s.progress = Math.min(1, s.progress + delta * 0.9);
      const pos = new THREE.Vector3().lerpVectors(s.start, s.end, s.progress);
      meshRef.current.position.copy(pos);
      trailRef.current.position.copy(pos);

      const fade = 1 - Math.abs(s.progress - 0.5) * 2;
      (meshRef.current.material as THREE.MeshBasicMaterial).opacity = fade * 0.9;
      (trailRef.current.material as THREE.MeshBasicMaterial).opacity = fade * 0.3;

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
        <sphereGeometry args={[0.18, 6, 6]} />
        <meshBasicMaterial color="#aaccff" transparent opacity={0} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

// ─── Galactic Core Glow ────────────────────────────────────────────────────

function GalacticCore() {
  const ref = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const rand = seededRand(99991);
    const arr = new Float32Array(300 * 3);
    for (let i = 0; i < 300; i++) {
      const r = Math.pow(rand(), 2) * 8;
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      arr[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.15;
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, []);

  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.002;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.25}
        color="#fffbe8"
        transparent
        opacity={0.18}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Export ────────────────────────────────────────────────────────────────

/**
 * Full starfield: distant shell layers for parallax depth, Milky Way spiral
 * arms, three nebula clouds in different hues, a galactic core glow, and
 * periodic shooting stars for life and motion.
 */
export function StarField() {
  return (
    <>
      {/* ── Distant shell layers (parallax depth) ── */}
      <StarLayer count={900}  radius={60} size={0.05} opacity={0.5}  driftSpeed={0.003} color="#8fa3d1" />
      <StarLayer count={1400} radius={40} size={0.07} opacity={0.7}  driftSpeed={0.008} color="#c9d6f5" />
      <StarLayer count={600}  radius={22} size={0.09} opacity={0.9}  driftSpeed={0.015} color="#ffffff"  />
      <StarLayer count={30}   radius={70} size={0.6}  opacity={0.12} driftSpeed={0.001} color="#b8c6ff" />

      {/* ── Milky Way spiral arms ── */}
      <SpiralArm armIndex={0} totalArms={2} />
      <SpiralArm armIndex={1} totalArms={2} />

      {/* ── Galactic core density bulge ── */}
      <GalacticCore />

      {/* ── Nebula clouds (additive blended) ── */}
      <NebulaCloud seed={11} center={[ 28, 6, -18]} radius={14} color="#3a1fff" count={220} opacity={0.04} />
      <NebulaCloud seed={22} center={[-24, -4,  22]} radius={12} color="#ff2266" count={180} opacity={0.035} />
      <NebulaCloud seed={33} center={[ 10, 8,   32]} radius={10} color="#00ccaa" count={150} opacity={0.03} />

      {/* ── Shooting stars ── */}
      <ShootingStar />
      <ShootingStar />
    </>
  );
}
