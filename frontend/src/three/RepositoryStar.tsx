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
      meshRef.current.rotation.y += delta * 0.08;
    }

    // Subtle gentle breathing pulse on the corona glow
    if (coronaRef.current) {
      const pulse = 1.0 + Math.sin(clock.getElapsedTime() * 1.5) * 0.05;
      const baseScale = repository.radius * 4.6;
      coronaRef.current.scale.set(baseScale * pulse, baseScale * pulse, 1);
    }
  });

  if (isCut(repository.id)) return null;

  return (
    <group position={[0, 0, 0]}>
      {/* Central Omnidirectional Light illuminating the solar system */}
      <pointLight
        position={[0, 0, 0]}
        intensity={2.8}
        distance={75}
        color={repository.color}
      />
      <pointLight
        position={[0, 0, 0]}
        intensity={1.0}
        distance={35}
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
          opacity={0.85}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </sprite>

      {/* Faint Outer Corona Shell */}
      <mesh scale={1.12}>
        <sphereGeometry args={[repository.radius, 32, 32]} />
        <meshBasicMaterial
          color={repository.color}
          transparent
          opacity={0.15}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Selection indicator ring */}
      {isSelected && (
        <mesh rotation={[Math.PI / 2.4, 0, 0]}>
          <ringGeometry args={[repository.radius * 1.5, repository.radius * 1.65, 64]} />
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
        <Html distanceFactor={14} position={[0, repository.radius + 0.9, 0]} occlude>
          <div className="pointer-events-none whitespace-nowrap rounded-lg bg-void-950/95 px-3 py-2 text-xs font-mono text-mist-100 border border-amber-500/30 shadow-2xl backdrop-blur-md">
            <div className="flex items-center gap-1.5 font-bold text-amber-400">
              <span>⭐</span>
              <span>{repository.name}</span>
            </div>
            <div className="text-[10px] text-mist-400 mt-0.5">
              Central Star • {repository.fileCount} file planets
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}
