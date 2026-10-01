import { useMemo } from "react";
import * as THREE from "three";

interface OrbitRingProps {
  radius: number;
  inclination?: number;
  color?: string;
  opacity?: number;
}

/**
 * Faint Keplerian orbital path rendered on the ecliptic plane.
 */
export function OrbitRing({
  radius,
  inclination = 0,
  color = "#60a5fa",
  opacity = 0.12,
}: OrbitRingProps) {
  const geometry = useMemo(() => {
    const points: THREE.Vector3[] = [];
    const SEGMENTS = 128;
    for (let i = 0; i <= SEGMENTS; i++) {
      const angle = (i / SEGMENTS) * Math.PI * 2;
      const x = Math.cos(angle) * radius;
      const zFlat = Math.sin(angle) * radius;
      const y = zFlat * Math.sin(inclination);
      const z = zFlat * Math.cos(inclination);
      points.push(new THREE.Vector3(x, y, z));
    }
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [radius, inclination]);

  return (
    <line>
      {/* @ts-ignore line bufferGeometry */}
      <bufferGeometry attach="geometry" {...geometry} />
      <lineBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        depthWrite={false}
      />
    </line>
  );
}
