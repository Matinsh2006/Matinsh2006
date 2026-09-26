import * as THREE from "three";

export const METALS = {
  rose: { color: "#f0b39a" },
  gold: { color: "#f2cf85" },
  steel: { color: "#d3d7db" },
  black: { color: "#3a393c", metalness: 0.75, roughness: 0.3 },
  titanium: { color: "#a9a8a5", roughness: 0.3 },
};

const FINISH_ROUGHNESS = { polished: 0.11, satin: 0.22, brushed: 0.32 };

export function metalMaterial(metal = "rose", finish = "polished") {
  const preset = METALS[metal] || METALS.rose;
  const roughness = preset.roughness ?? FINISH_ROUGHNESS[finish] ?? 0.15;
  const material = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(preset.color),
    metalness: preset.metalness ?? 1,
    roughness: finish === "polished" ? roughness : Math.max(roughness, FINISH_ROUGHNESS[finish]),
    envMapIntensity: 1.2,
  });
  if (finish === "brushed") {
    material.anisotropy = 0.55;
  }
  return material;
}

export function glassMaterial(strength = 1.6, opacity = 0.16) {
  // A thin, mostly transparent layer that mainly shows reflections — much
  // cheaper than real transmission and keeps the dial perfectly readable.
  return new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    roughness: 0.03,
    metalness: 0,
    envMapIntensity: strength,
    clearcoat: 1,
    clearcoatRoughness: 0.02,
    transparent: true,
    opacity,
    depthWrite: false,
  });
}

export function lumeMaterial(color = "#f4f1e6") {
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    roughness: 0.45,
    metalness: 0,
    emissive: new THREE.Color("#c9f5d9"),
    emissiveIntensity: 0.06,
  });
}

export function gemMaterial() {
  return new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    metalness: 0,
    roughness: 0,
    ior: 2.4,
    specularIntensity: 1,
    clearcoat: 1,
    clearcoatRoughness: 0,
    envMapIntensity: 3.2,
    flatShading: true,
  });
}

export function leatherMaterial(color = "#5a3322") {
  return new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(color),
    roughness: 0.62,
    metalness: 0,
    sheen: 0.4,
    sheenRoughness: 0.6,
    sheenColor: new THREE.Color("#ffffff"),
    envMapIntensity: 0.8,
  });
}

export function rubberMaterial(color = "#141516") {
  return new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(color),
    roughness: 0.55,
    metalness: 0,
    clearcoat: 0.25,
    clearcoatRoughness: 0.5,
    envMapIntensity: 0.9,
  });
}
