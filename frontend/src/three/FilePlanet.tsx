import { useRef, useState, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import { useNavigation } from "@/hooks/useNavigation";
import { positionsRegistry } from "./positionsRegistry";
import { getPlanetMaterial } from "./PlanetMaterial";
import { getRingTexture } from "./PlanetTextures";
import { OrbitRing } from "./OrbitRing";
import { SymbolMoon } from "./SymbolMoon";
import type { FilePlanet as FilePlanetType } from "./sceneTypes";

interface FilePlanetProps {
  planet: FilePlanetType;
}

// ─── Saturn-Style Ring System ────────────────────────────────────────────────

function PlanetRingSystem({ radius, color }: { radius: number; color: string }) {
  const ringMesh = useRef<THREE.Mesh>(null);
  const ringTexture = useMemo(() => getRingTexture(color, 256), [color]);

  useFrame((_, delta) => {
    if (ringMesh.current) {
      ringMesh.current.rotation.z += delta * 0.03;
    }
  });

  return (
    <mesh ref={ringMesh} rotation={[Math.PI / 2.3, 0.15, 0]}>
      <ringGeometry args={[radius * 1.35, radius * 2.1, 64]} />
      <meshBasicMaterial
        map={ringTexture}
        color={color}
        side={THREE.DoubleSide}
        transparent
        opacity={0.8}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

// ─── Atmosphere Rim Glow ─────────────────────────────────────────────────────

function AtmosphereRim({
  radius,
  color,
  atmosphereColor,
}: {
  radius: number;
  color: string;
  atmosphereColor?: string;
}) {
  return (
    <>
      <mesh>
        <sphereGeometry args={[radius * 1.08, 32, 32]} />
        <meshBasicMaterial
          color={atmosphereColor || color}
          transparent
          opacity={0.12}
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

// ─── Main FilePlanet Component ───────────────────────────────────────────────

export function FilePlanet({ planet }: FilePlanetProps) {
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

  const isSelected = selectedId === planet.id;
  const material = getPlanetMaterial(planet.textureType, planet.color);

  // Time-based orbital motion around central star (calm & cinematic)
  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime() * planet.orbitSpeed * planet.direction + planet.orbitPhase;
    const x = Math.cos(t) * planet.orbitRadius;
    const zFlat = Math.sin(t) * planet.orbitRadius;
    const y = zFlat * Math.sin(planet.inclination);
    const z = zFlat * Math.cos(planet.inclination);

    if (groupRef.current) {
      groupRef.current.position.set(x, y, z);
    }

    if (meshRef.current) {
      // Axial self-rotation
      meshRef.current.rotation.y += delta * 0.12;

      // Register live world position for CameraRig to fly to
      const worldPos = new THREE.Vector3();
      meshRef.current.getWorldPosition(worldPos);
      positionsRegistry.set(planet.id, worldPos.x, worldPos.y, worldPos.z);
    }
  });

  if (isCut(planet.id)) return null;

  return (
    <>
      {/* Orbital track ring around central star */}
      <OrbitRing
        radius={planet.orbitRadius}
        inclination={planet.inclination}
        color={planet.color}
        opacity={0.14}
      />

      {/* Planet entity group */}
      <group ref={groupRef}>
        <mesh
          ref={meshRef}
          material={material}
          onClick={(e) => {
            e.stopPropagation();
            selectObject(planet.id);
            navigateTo(planet.id);
          }}
          onPointerOver={(e) => {
            e.stopPropagation();
            setIsHovered(true);
            hover(planet.id);
          }}
          onPointerOut={() => {
            setIsHovered(false);
            hover(null);
          }}
        >
          {/* Solid 3D spherical body */}
          <sphereGeometry args={[planet.radius, 40, 40]} />
        </mesh>

        {/* Selection indicator ring */}
        {isSelected && (
          <mesh rotation={[Math.PI / 2.3, 0.2, 0]}>
            <ringGeometry args={[planet.radius * 1.45, planet.radius * 1.68, 64]} />
            <meshBasicMaterial
              color="#38bdf8"
              transparent
              opacity={0.85}
              side={THREE.DoubleSide}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        )}

        {/* Atmospheric halo */}
        <AtmosphereRim
          radius={planet.radius}
          color={planet.color}
          atmosphereColor={planet.atmosphereColor}
        />

        {/* Optional planetary rings */}
        {planet.hasRings && (
          <PlanetRingSystem radius={planet.radius} color={planet.color} />
        )}

        {/* Floating Label on Hover */}
        {isHovered && (
          <Html distanceFactor={10} position={[0, planet.radius + 0.5, 0]} occlude>
            <div className="pointer-events-none whitespace-nowrap rounded-md bg-void-950/90 px-2.5 py-1.5 text-xs font-mono text-mist-100 border border-white/10 shadow-glow backdrop-blur-md">
              <span className="mr-1.5 text-signal-400">📄</span>
              <span className="font-semibold text-mist-100">{planet.name}</span>
              <span className="ml-2 text-[10px] text-mist-400 font-mono">
                {planet.directory !== "." && planet.directory !== "" ? `${planet.directory}/` : ""}
              </span>
              {planet.moons.length > 0 && (
                <span className="ml-2 text-[10px] text-amber-400 font-medium">
                  {planet.moons.length} moon{planet.moons.length > 1 ? "s" : ""}
                </span>
              )}
            </div>
          </Html>
        )}

        {/* Moons orbiting this parent file planet */}
        {planet.moons.map((moon) => (
          <SymbolMoon key={moon.id} moon={moon} />
        ))}
      </group>
    </>
  );
}
