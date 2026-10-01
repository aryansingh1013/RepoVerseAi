import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";
import { useNavigation } from "@/hooks/useNavigation";
import { positionsRegistry } from "./positionsRegistry";
import { getPlanetMaterial } from "./PlanetMaterial";
import { getRingTexture } from "./PlanetTextures";
import { OrbitRing } from "./OrbitRing";
import { FileMoon } from "./FileMoon";
import type { FolderPlanet as FolderPlanetType } from "./sceneTypes";

interface FolderPlanetProps {
  planet: FolderPlanetType;
}

// ─── Saturn-Style Ring System for Folders ────────────────────────────────────

function FolderRingSystem({ radius, color }: { radius: number; color: string }) {
  const ringMesh = useRef<THREE.Mesh>(null);
  const ringTexture = getRingTexture(color, 256);

  useFrame((_, delta) => {
    if (ringMesh.current) {
      ringMesh.current.rotation.z += delta * 0.025;
    }
  });

  return (
    <mesh ref={ringMesh} rotation={[Math.PI / 2.3, 0.15, 0]}>
      <ringGeometry args={[radius * 1.35, radius * 2.2, 64]} />
      <meshBasicMaterial
        map={ringTexture}
        color={color}
        side={THREE.DoubleSide}
        transparent
        opacity={0.85}
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
      {/* Inner atmospheric haze */}
      <mesh>
        <sphereGeometry args={[radius * 1.07, 36, 36]} />
        <meshBasicMaterial
          color={atmosphereColor || color}
          transparent
          opacity={0.18}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      {/* Outer fringe halo */}
      <mesh>
        <sphereGeometry args={[radius * 1.18, 28, 28]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.06}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </>
  );
}

// ─── Main FolderPlanet Component ─────────────────────────────────────────────

export function FolderPlanet({ planet }: FolderPlanetProps) {
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

  // Time-based orbital motion around central repository star (calm & cinematic)
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
      meshRef.current.rotation.y += delta * 0.08;

      // Register live world position for CameraRig to fly to
      const worldPos = new THREE.Vector3();
      meshRef.current.getWorldPosition(worldPos);
      positionsRegistry.set(planet.id, worldPos.x, worldPos.y, worldPos.z);
    }
  });

  if (isCut(planet.id)) return null;

  return (
    <>
      {/* Planetary orbital path ring around central repository star */}
      <OrbitRing
        radius={planet.orbitRadius}
        inclination={planet.inclination}
        color={planet.color}
        opacity={0.16}
      />

      {/* Planet entity group (holds the folder planet body and its orbiting file moons) */}
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
          {/* Substantial, solid 3D spherical folder planet body */}
          <sphereGeometry args={[planet.radius, 44, 44]} />
        </mesh>

        {/* Selection indicator ring */}
        {isSelected && (
          <mesh rotation={[Math.PI / 2.3, 0.2, 0]}>
            <ringGeometry args={[planet.radius * 1.35, planet.radius * 1.55, 64]} />
            <meshBasicMaterial
              color="#38bdf8"
              transparent
              opacity={0.88}
              side={THREE.DoubleSide}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        )}

        {/* Atmospheric halo glow */}
        <AtmosphereRim
          radius={planet.radius}
          color={planet.color}
          atmosphereColor={planet.atmosphereColor}
        />

        {/* Optional planetary rings */}
        {planet.hasRings && (
          <FolderRingSystem radius={planet.radius} color={planet.color} />
        )}

        {/* Floating Label on Hover */}
        {isHovered && (
          <Html distanceFactor={14} position={[0, planet.radius + 0.9, 0]} occlude>
            <div className="pointer-events-none whitespace-nowrap rounded-lg bg-void-950/95 px-3 py-2 text-xs font-mono text-mist-100 border border-white/10 shadow-glow backdrop-blur-md">
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-signal-400">🪐</span>
                <span className="text-mist-100">{planet.name}/</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[10px] text-mist-400">
                <span>{planet.fileCount} file{planet.fileCount !== 1 ? "s" : ""}</span>
                {planet.primaryLanguage && (
                  <span className="text-signal-400 font-medium">
                    • {planet.primaryLanguage}
                  </span>
                )}
              </div>
            </div>
          </Html>
        )}

        {/* File Moons orbiting this parent folder planet */}
        {planet.files.map((file) => (
          <FileMoon key={file.id} moon={file} />
        ))}
      </group>
    </>
  );
}
