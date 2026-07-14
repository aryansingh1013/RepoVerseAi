import * as THREE from "three";

/**
 * Every orbiting body writes its current world position here each frame.
 * The camera rig reads from it to know where to fly, without requiring
 * React state updates on every animation tick (which would be far too
 * expensive at 60fps). Plain mutable module state is the right tool here —
 * this is intentionally outside React's render cycle.
 */
class PositionsRegistry {
  private positions = new Map<string, THREE.Vector3>();

  set(id: string, x: number, y: number, z: number) {
    const existing = this.positions.get(id);
    if (existing) {
      existing.set(x, y, z);
    } else {
      this.positions.set(id, new THREE.Vector3(x, y, z));
    }
  }

  get(id: string | null): THREE.Vector3 | null {
    if (!id) return null;
    return this.positions.get(id) ?? null;
  }

  clear(id: string) {
    this.positions.delete(id);
  }
}

export const positionsRegistry = new PositionsRegistry();
