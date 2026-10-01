import * as THREE from "three";
import {
  getPlanetTexture,
  getPlanetBumpMap,
  getMoonTexture,
  getMoonBumpMap,
  getStarTexture,
} from "./PlanetTextures";
import type { PlanetTextureType } from "./sceneTypes";

const materialCache = new Map<string, THREE.MeshStandardMaterial>();

export function getPlanetMaterial(
  textureType: PlanetTextureType,
  colorHex: string,
  roughness = 0.65,
  metalness = 0.12
): THREE.MeshStandardMaterial {
  const key = `mat_planet_${textureType}_${colorHex}_${roughness}_${metalness}`;
  if (materialCache.has(key)) {
    return materialCache.get(key)!;
  }

  const map = getPlanetTexture(textureType, colorHex);
  const bumpMap = getPlanetBumpMap(textureType);

  const mat = new THREE.MeshStandardMaterial({
    map,
    bumpMap,
    bumpScale: 0.04,
    color: new THREE.Color(colorHex),
    roughness,
    metalness,
  });

  materialCache.set(key, mat);
  return mat;
}

export function getMoonMaterial(colorHex: string): THREE.MeshStandardMaterial {
  const key = `mat_moon_${colorHex}`;
  if (materialCache.has(key)) {
    return materialCache.get(key)!;
  }

  const map = getMoonTexture(colorHex);
  const bumpMap = getMoonBumpMap();

  const mat = new THREE.MeshStandardMaterial({
    map,
    bumpMap,
    bumpScale: 0.06,
    color: new THREE.Color(colorHex),
    roughness: 0.88,
    metalness: 0.04,
  });

  materialCache.set(key, mat);
  return mat;
}

export function getStarMaterial(colorHex = "#f59e0b"): THREE.MeshStandardMaterial {
  const key = `mat_star_${colorHex}`;
  if (materialCache.has(key)) {
    return materialCache.get(key)!;
  }

  const map = getStarTexture(colorHex);

  const mat = new THREE.MeshStandardMaterial({
    map,
    color: new THREE.Color(colorHex),
    emissive: new THREE.Color(colorHex),
    emissiveMap: map,
    emissiveIntensity: 1.35,
    roughness: 0.28,
    metalness: 0.0,
  });

  materialCache.set(key, mat);
  return mat;
}
