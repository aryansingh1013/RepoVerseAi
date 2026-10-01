import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import { useNavigation } from "@/hooks/useNavigation";
import { positionsRegistry } from "./positionsRegistry";
import { getMoonMaterial } from "./PlanetMaterial";
import { OrbitRing } from "./OrbitRing";
import type { SymbolMoon as SymbolMoonType } from "./sceneTypes";

interface SymbolMoonProps {
  moon: SymbolMoonType;
}

export function SymbolMoon({ moon }: SymbolMoonProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const [isHovered, setIsHovered] = useState(false);

  const {
    navigateTo,
    selectObject,
    selectedId,
    hover,
    isCut,
  } = useNavigation();

  const isSelected = selectedId === moon.id;
  const material = getMoonMaterial(moon.color);

  // Time-based orbit around parent planet
  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime() * moon.orbitSpeed * moon.direction + moon.orbitPhase;
    const x = Math.cos(t) * moon.orbitRadius;
    const zFlat = Math.sin(t) * moon.orbitRadius;
    const y = zFlat * Math.sin(moon.inclination);
    const z = zFlat * Math.cos(moon.inclination);

    if (groupRef.current) {
      groupRef.current.position.set(x, y, z);
    }

    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.15;
      // Record world position for CameraRig to fly to
      const worldPos = new THREE.Vector3();
      meshRef.current.getWorldPosition(worldPos);
      positionsRegistry.set(moon.id, worldPos.x, worldPos.y, worldPos.z);
    }
  });

  if (isCut(moon.id)) return null;

  const icon = moon.type === "class" ? "🔮" : moon.type === "method" ? "⚡" : "🌀";

  return (
    <>
      {/* Orbit track around parent planet */}
      <OrbitRing
        radius={moon.orbitRadius}
        inclination={moon.inclination}
        color={moon.color}
        opacity={0.08}
      />

      <group ref={groupRef}>
        <mesh
          ref={meshRef}
          material={material}
          onClick={(e) => {
            e.stopPropagation();
            selectObject(moon.id);
            navigateTo(moon.id);
          }}
          onPointerOver={(e) => {
            e.stopPropagation();
            setIsHovered(true);
            hover(moon.id);
          }}
          onPointerOut={() => {
            setIsHovered(false);
            hover(null);
          }}
        >
          {/* Solid 3D sphere geometry — NOT a particle */}
          <sphereGeometry args={[moon.radius, 32, 32]} />
        </mesh>

        {/* Selection indicator halo */}
        {isSelected && (
          <mesh rotation={[Math.PI / 2.5, 0, 0]}>
            <ringGeometry args={[moon.radius * 1.35, moon.radius * 1.55, 32]} />
            <meshBasicMaterial
              color="#38bdf8"
              side={THREE.DoubleSide}
              transparent
              opacity={0.85}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        )}

        {/* Interactive Floating Label on Hover */}
        {isHovered && (
          <Html distanceFactor={8} position={[0, moon.radius + 0.3, 0]} occlude>
            <div className="pointer-events-none whitespace-nowrap rounded-md bg-void-950/90 px-2 py-1 text-[11px] font-mono text-mist-100 border border-white/10 shadow-glow backdrop-blur-md">
              <span className="mr-1.5 opacity-80">{icon}</span>
              <span className="font-semibold">{moon.name}</span>
              <span className="ml-1.5 text-[9px] text-mist-400">L{moon.lineStart}</span>
            </div>
          </Html>
        )}
      </group>
    </>
  );
}
