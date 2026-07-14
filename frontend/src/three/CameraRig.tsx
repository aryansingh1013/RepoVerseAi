import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { positionsRegistry } from "./positionsRegistry";
import { useNavigation } from "@/hooks/useNavigation";

const ARRIVAL_EPSILON = 0.05;
/** How quickly the camera eases toward its target — lower = more cinematic drift. */
const EASE_FACTOR = 2.2;

interface CameraRigProps {
  controlsRef: React.RefObject<OrbitControlsImpl>;
  /** Distance the camera should sit back from whatever's focused. */
  viewDistance: number;
}

/**
 * Every frame, eases the OrbitControls target (and the camera itself) toward
 * the current focus object's live position from the positions registry.
 * This is what turns clicks into "flights" instead of instant cuts.
 */
export function CameraRig({ controlsRef, viewDistance }: CameraRigProps) {
  const { camera } = useThree();
  const { focusId, reportArrived } = useNavigation();
  const desiredCamPos = useRef(new THREE.Vector3());
  const hasReportedArrival = useRef(false);

  useFrame((_, delta) => {
    const target = positionsRegistry.get(focusId) ?? new THREE.Vector3(0, 0, 0);
    const controls = controlsRef.current;
    if (!controls) return;

    // Ease the orbit target toward the focused object.
    controls.target.lerp(target, Math.min(1, delta * EASE_FACTOR));

    // Keep the camera at a consistent viewing distance/angle from the target,
    // easing its position rather than snapping — this is the "fly" feeling.
    const offset = camera.position.clone().sub(controls.target);
    const currentDistance = offset.length();
    const distanceDelta = viewDistance - currentDistance;
    if (Math.abs(distanceDelta) > 0.01) {
      offset.setLength(currentDistance + distanceDelta * Math.min(1, delta * EASE_FACTOR));
      desiredCamPos.current.copy(controls.target).add(offset);
      camera.position.lerp(desiredCamPos.current, Math.min(1, delta * EASE_FACTOR));
    }

    controls.update();

    const distanceToTarget = controls.target.distanceTo(target);
    if (distanceToTarget < ARRIVAL_EPSILON) {
      if (!hasReportedArrival.current) {
        hasReportedArrival.current = true;
        reportArrived();
      }
    } else {
      hasReportedArrival.current = false;
    }
  });

  return null;
}
