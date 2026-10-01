import { useRef, useState, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import { useNavigation } from "@/hooks/useNavigation";
import { positionsRegistry } from "./positionsRegistry";
import { getStarMaterial } from "./PlanetMaterial";
import { getStarCoronaTexture } from "./PlanetTextures";
import type { RepositoryNode } from "./sceneTypes";

interface RepositoryStarProps {
  repository: RepositoryNode;
}

// ─── Solar Flare / Prominence Particles ──────────────────────────────────────

function SolarFlares({ radius, color }: { radius: number; color: string }) {
  const pointsRef = useRef<THREE.Points>(null);
  const COUNT = 160;

  const [positions, speeds] = useMemo(() => {
    const pos = new Float32Array(COUNT * 3);
    const spd = new Float32Array(COUNT);
    for (let i = 0; i < COUNT; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = radius * (1.05 + Math.random() * 0.45);
      pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
      spd[i] = 0.2 + Math.random() * 0.5;
    }
    return [pos, spd];
  }, [radius]);

  useFrame(({ clock }, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.05;
      pointsRef.current.rotation.z += delta * 0.02;
      // Pulse scale
      const pulse = 1.0 + Math.sin(clock.getElapsedTime() * 2) * 0.04;
      pointsRef.current.scale.set(pulse, pulse, pulse);
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.18}
        color={color}
        transparent
        opacity={0.8}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

// ─── Central Repository Star ─────────────────────────────────────────────────

export function RepositoryStar({ repository }: RepositoryStarProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const coronaRef = useRef<THREE.Sprite>(null);
  const [isHovered, setIsHovered] = useState(false);

  const {
    navigateTo,
    selectObject,
    selectedId,
    hover,
    isCut,
  } = useNavigation();

  const isSelected = selectedId === repository.id;
  const material = useMemo(() => getStarMaterial(repository.color), [repository.color]);
  const coronaTex = useMemo(() => getStarCoronaTexture(repository.color, 256), [repository.color]);

  // Keep (0, 0, 0) registered for CameraRig
  useFrame(({ clock }, delta) => {
    positionsRegistry.set(repository.id, 0, 0, 0);

    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.06;
    }

    // Subtle gentle breathing pulse on the corona glow
    if (coronaRef.current) {
      const pulse = 1.0 + Math.sin(clock.getElapsedTime() * 1.5) * 0.06;
      const baseScale = repository.radius * 4.8;
      coronaRef.current.scale.set(baseScale * pulse, baseScale * pulse, 1);
    }
  });

  if (isCut(repository.id)) return null;

  return (
    <group position={[0, 0, 0]}>
      {/* Central Omnidirectional Solar Light illuminating planets & moons */}
      <pointLight
        position={[0, 0, 0]}
        intensity={3.8}
        distance={95}
        color={repository.color}
      />
      <pointLight
        position={[0, 0, 0]}
        intensity={1.4}
        distance={45}
        color="#ffffff"
      />

      {/* Main Solar Sphere */}
      <mesh
        ref={meshRef}
        material={material}
        onClick={(e) => {
          e.stopPropagation();
          selectObject(repository.id);
          navigateTo(repository.id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setIsHovered(true);
          hover(repository.id);
        }}
        onPointerOut={() => {
          setIsHovered(false);
          hover(null);
        }}
      >
        <sphereGeometry args={[repository.radius, 48, 48]} />
      </mesh>

      {/* Corona Glow Sprite */}
      <sprite ref={coronaRef} position={[0, 0, 0]}>
        <spriteMaterial
          map={coronaTex}
          color={repository.color}
          transparent
          opacity={0.88}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </sprite>

      {/* Solar Prominence / Flare Particles */}
      <SolarFlares radius={repository.radius} color="#ffedd5" />

      {/* Outer Corona Atmosphere Shell */}
      <mesh scale={1.14}>
        <sphereGeometry args={[repository.radius, 32, 32]} />
        <meshBasicMaterial
          color={repository.color}
          transparent
          opacity={0.16}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Selection indicator ring */}
      {isSelected && (
        <mesh rotation={[Math.PI / 2.4, 0, 0]}>
          <ringGeometry args={[repository.radius * 1.4, repository.radius * 1.55, 64]} />
          <meshBasicMaterial
            color="#38bdf8"
            transparent
            opacity={0.9}
            side={THREE.DoubleSide}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      )}

      {/* Floating Label on Hover */}
      {isHovered && (
        <Html distanceFactor={16} position={[0, repository.radius + 1.2, 0]} occlude>
          <div className="pointer-events-none whitespace-nowrap rounded-xl bg-void-950/95 px-3.5 py-2.5 text-xs font-mono text-mist-100 border border-amber-500/30 shadow-2xl backdrop-blur-md">
            <div className="flex items-center gap-2 font-bold text-amber-400 text-sm">
              <span>⭐</span>
              <span>{repository.name}</span>
            </div>
            <div className="text-[11px] text-mist-400 mt-1 font-mono">
              Central Star • {repository.fileCount} File Planets
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}
