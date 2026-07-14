import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type * as THREE from "three";
import { useSelectedObject } from "@/hooks/useSelectedObject";
import type { SpaceObject } from "@/types";

interface GalaxyCoreProps {
  object: SpaceObject;
}

/** The repository root, rendered as a slowly rotating glowing core. */
export function GalaxyCore({ object }: GalaxyCoreProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const { selectedId, hoveredId, select, hover } = useSelectedObject();

  const isSelected = selectedId === object.id;
  const isHovered = hoveredId === object.id;

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.08;
    }
  });

  return (
    <group>
      <mesh
        ref={meshRef}
        position={[object.position.x, object.position.y, object.position.z]}
        onClick={(e) => {
          e.stopPropagation();
          select(object.id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          hover(object.id);
        }}
        onPointerOut={() => hover(null)}
      >
        <icosahedronGeometry args={[0.9 * object.scale + 0.6, 1]} />
        <meshStandardMaterial
          color={object.color}
          emissive={object.color}
          emissiveIntensity={isSelected ? 0.9 : isHovered ? 0.6 : 0.35}
          roughness={0.35}
          metalness={0.4}
          wireframe
        />
      </mesh>
      <pointLight position={[object.position.x, object.position.y, object.position.z]} intensity={1.2} distance={12} color={object.color} />
    </group>
  );
}
