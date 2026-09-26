import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import {
  braceletCurve,
  extrudeSide,
  flutes,
  frameOnCurve,
  gearShape,
  roundedRectShape,
  strapGeometry,
  sweepZ,
} from "./geometry.js";
import {
  gemMaterial,
  glassMaterial,
  leatherMaterial,
  lumeMaterial,
  metalMaterial,
  rubberMaterial,
} from "./materials.js";
import {
  DIALS,
  createCasebackTexture,
  createCotesTexture,
  createDialTexture,
  createInsertTexture,
  createPerlageTexture,
  createSmartScreenTexture,
  createStrapTexture,
} from "./textures.js";

const TAU = Math.PI * 2;

export const DEFAULTS = {
  style: "presidential", // presidential | diver | chrono | classic | smart
  metal: "rose",
  dial: "chocolate",
  numerals: "persian", // persian | roman | none
  indices: "none", // baton | dot | diamond | none
  bezel: "fluted", // fluted | smooth | diver | tachy | diamond
  bezelColor: "#0b0c10",
  bezelInk: "#e9e6dd",
  strap: "president", // president | oyster | leather | rubber | mesh
  strapColor: "#5a3322",
  handStyle: "baton", // baton | dauphine | sword
  secondsColor: null,
  size: 1,
  brand: "SANIYEH",
  brandFa: "ثانیه",
  origin: "TEHRAN",
  date: new Date(),
  time: null, // {h, m, s}; null = live time
  movement: true,
  quality: "high",
};

const smooth = (t) => t * t * (3 - 2 * t);
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const clamp01 = (v) => Math.min(1, Math.max(0, v));

function handShape(kind, length, width, tail) {
  const shape = new THREE.Shape();
  const w = width / 2;
  if (kind === "dauphine") {
    shape.moveTo(0, -tail);
    shape.lineTo(w, length * 0.12);
    shape.lineTo(0, length);
    shape.lineTo(-w, length * 0.12);
  } else if (kind === "sword") {
    shape.moveTo(-w * 0.35, -tail);
    shape.lineTo(w * 0.35, -tail);
    shape.lineTo(w, length * 0.62);
    shape.lineTo(0, length);
    shape.lineTo(-w, length * 0.62);
  } else {
    shape.moveTo(-w, -tail);
    shape.lineTo(w, -tail);
    shape.lineTo(w, length - width * 1.1);
    shape.lineTo(0, length);
    shape.lineTo(-w, length - width * 1.1);
  }
  shape.closePath();
  return shape;
}

function extrudeFlat(shape, depth, bevel = 0.006) {
  return new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: bevel > 0,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 2,
    curveSegments: 24,
  });
}

function hourAngle(hours) {
  // clockwise from 12 o'clock (three.js rotates counter-clockwise)
  return -(hours / 12) * TAU;
}

export function createWatch(options = {}) {
  const o = { ...DEFAULTS, ...options };
  if (o.style === "smart") return createSmartwatch(o);

  const root = new THREE.Group();
  root.name = "watch";
  const head = new THREE.Group(); // everything except the bracelet
  root.add(head);
  const parts = [];
  const lowQuality = o.quality === "low";
  const palette = DIALS[o.dial] || DIALS.chocolate;

  const polished = metalMaterial(o.metal, "polished");
  const brushed = metalMaterial(o.metal, "brushed");
  const satin = metalMaterial(o.metal, "satin");

  function addPart(name, object, explode, { rot = [0, 0, 0], delay = 0, parent = head } = {}) {
    parent.add(object);
    parts.push({
      name,
      object,
      basePos: object.position.clone(),
      baseRot: object.rotation.clone(),
      explode: new THREE.Vector3(...explode),
      rot: new THREE.Vector3(...rot),
      delay,
      phase: parts.length * 1.7,
    });
    return object;
  }

  // ------------------------------------------------------------------ case
  const caseGroup = new THREE.Group();
  const caseProfile = [
    { r: 1.35, z: -0.45 },
    { r: 1.84, z: -0.45 },
    { r: 1.93, z: -0.42 },
    { r: 1.985, z: -0.35 },
    { r: 2.0, z: -0.26 },
    { r: 2.0, z: 0.16 },
    { r: 1.985, z: 0.25 },
    { r: 1.95, z: 0.305 },
    { r: 1.88, z: 0.335 },
    { r: 1.5, z: 0.335 },
    { r: 1.5, z: -0.3 },
    { r: 1.35, z: -0.45 },
  ];
  caseGroup.add(new THREE.Mesh(sweepZ(caseProfile, { segments: lowQuality ? 96 : 160 }), polished));

  const lugShape = new THREE.Shape();
  lugShape.moveTo(1.5, 0.27);
  lugShape.bezierCurveTo(1.95, 0.27, 2.2, 0.12, 2.42, -0.06);
  lugShape.quadraticCurveTo(2.52, -0.2, 2.42, -0.35);
  lugShape.bezierCurveTo(2.2, -0.41, 1.9, -0.43, 1.5, -0.43);
  lugShape.closePath();
  const lugGeometry = extrudeSide(lugShape, 0.28, 0.045);
  for (const x of [1.05, -1.33]) {
    const top = new THREE.Mesh(lugGeometry, polished);
    top.position.x = x;
    caseGroup.add(top);
    const bottom = new THREE.Mesh(lugGeometry, polished);
    bottom.position.x = -x;
    bottom.rotation.z = Math.PI;
    caseGroup.add(bottom);
  }
  // Crown tube
  const tube = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.16, 32), polished);
  tube.rotation.z = Math.PI / 2;
  tube.position.set(2.04, 0, -0.07);
  caseGroup.add(tube);
  if (o.style === "chrono") {
    for (const angle of [Math.PI / 5.2, -Math.PI / 5.2]) {
      const pusher = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 0.34, 32), polished);
      pusher.rotation.z = Math.PI / 2 - angle;
      pusher.position.set(Math.cos(angle) * 2.08, Math.sin(angle) * 2.08, -0.07);
      caseGroup.add(pusher);
    }
  }
  addPart("case", caseGroup, [0, 0, 0]);

  // -------------------------------------------------------------- caseback
  const backGroup = new THREE.Group();
  const backProfile = [
    { r: 0, z: -0.7 },
    { r: 0.95, z: -0.7 },
    { r: 1.45, z: -0.67 },
    { r: 1.78, z: -0.6 },
    { r: 1.86, z: -0.52 },
    { r: 1.84, z: -0.45 },
    { r: 1.5, z: -0.45 },
    { r: 1.4, z: -0.48 },
    { r: 0, z: -0.48 },
  ];
  backGroup.add(new THREE.Mesh(sweepZ(backProfile, { segments: 96 }), satin));
  const backDecal = new THREE.Mesh(
    new THREE.CircleGeometry(1.44, 96),
    new THREE.MeshPhysicalMaterial({
      map: createCasebackTexture({ brand: o.brand, metal: o.metal }),
      metalness: 1,
      roughness: 0.3,
    })
  );
  backDecal.rotation.x = Math.PI;
  backDecal.position.z = -0.702;
  backGroup.add(backDecal);
  addPart("caseback", backGroup, [0, 0, -2.3], { rot: [0.25, 0, 0.4], delay: 0.46 });

  // -------------------------------------------------------------- movement
  const spinners = [];
  let balance = null;
  if (o.movement) {
    const movement = new THREE.Group();
    const perlage = createPerlageTexture(lowQuality ? 512 : 1024);
    perlage.repeat.set(1.4, 1.4);
    const plate = new THREE.Mesh(
      new THREE.CylinderGeometry(1.5, 1.5, 0.08, 96),
      new THREE.MeshPhysicalMaterial({ map: perlage, metalness: 1, roughness: 0.42, color: "#fbf7f1", envMapIntensity: 1.6 })
    );
    plate.rotation.x = Math.PI / 2;
    plate.position.z = -0.26;
    movement.add(plate);

    const bridgeMaterial = new THREE.MeshPhysicalMaterial({
      map: createCotesTexture(lowQuality ? 512 : 1024, "#e6c9a1"),
      metalness: 1,
      roughness: 0.3,
      color: "#fff0dc",
      envMapIntensity: 1.6,
    });
    const bridge = new THREE.Shape();
    bridge.absarc(0, 0, 1.42, -Math.PI * 0.62, Math.PI * 0.12, false);
    bridge.absarc(0.25, -0.2, 0.62, Math.PI * 0.2, -Math.PI * 0.75, true);
    bridge.closePath();
    const bridgeMesh = new THREE.Mesh(extrudeFlat(bridge, 0.06, 0.012), bridgeMaterial);
    bridgeMesh.position.z = -0.22;
    movement.add(bridgeMesh);
    const cock = new THREE.Shape();
    cock.absarc(-0.62, -0.72, 0.5, Math.PI * 0.1, Math.PI * 1.25, false);
    cock.absarc(-0.25, -0.35, 0.16, Math.PI * 1.1, Math.PI * 0.2, true);
    cock.closePath();
    const cockMesh = new THREE.Mesh(extrudeFlat(cock, 0.05, 0.01), bridgeMaterial);
    cockMesh.position.z = -0.17;
    movement.add(cockMesh);

    const gearMaterial = new THREE.MeshPhysicalMaterial({ color: "#f7d58f", metalness: 1, roughness: 0.28, envMapIntensity: 1.8 });
    const jewelMaterial = new THREE.MeshPhysicalMaterial({
      color: "#b3122f",
      roughness: 0.05,
      metalness: 0,
      clearcoat: 1,
      envMapIntensity: 2,
    });
    const gears = [
      { teeth: 64, radius: 0.56, x: 0.5, y: 0.52, speed: 0.12 },
      { teeth: 44, radius: 0.36, x: -0.34, y: 0.72, speed: -0.3 },
      { teeth: 36, radius: 0.28, x: -0.72, y: 0.14, speed: 0.6 },
      { teeth: 15, radius: 0.19, x: -0.18, y: -0.22, speed: -1.6 },
      { teeth: 30, radius: 0.24, x: 0.62, y: -0.28, speed: 0.9 },
    ];
    for (const spec of gears) {
      const gear = new THREE.Mesh(
        extrudeFlat(gearShape({ teeth: spec.teeth, radius: spec.radius, toothDepth: spec.radius * 0.09, hole: 0.035, spokes: spec.radius > 0.25 ? 5 : 0 }), 0.03, 0.004),
        gearMaterial
      );
      gear.position.set(spec.x, spec.y, -0.15);
      movement.add(gear);
      const jewel = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 12), jewelMaterial);
      jewel.position.set(spec.x, spec.y, -0.11);
      movement.add(jewel);
      spinners.push({ object: gear, speed: spec.speed });
    }

    balance = new THREE.Group();
    const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.035, 12, 64), gearMaterial);
    balance.add(wheel);
    for (let i = 0; i < 3; i++) {
      const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.68, 0.03, 0.02), gearMaterial);
      spoke.rotation.z = (i / 3) * Math.PI;
      balance.add(spoke);
    }
    const spiralPoints = [];
    for (let i = 0; i <= 360; i++) {
      const t = i / 360;
      const a = t * TAU * 9;
      const r = 0.05 + t * 0.22;
      spiralPoints.push(new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, 0.03));
    }
    const hairspring = new THREE.Mesh(
      new THREE.TubeGeometry(new THREE.CatmullRomCurve3(spiralPoints), 360, 0.004, 4, false),
      new THREE.MeshStandardMaterial({ color: "#aeb6c4", metalness: 1, roughness: 0.25 })
    );
    balance.add(hairspring);
    balance.position.set(-0.62, -0.72, -0.08);
    movement.add(balance);
    const balanceJewel = new THREE.Mesh(new THREE.SphereGeometry(0.04, 16, 12), jewelMaterial);
    balanceJewel.position.set(-0.62, -0.72, -0.1);
    movement.add(balanceJewel);
    addPart("movement", movement, [0, 0, 0.95], { rot: [0, 0, -0.25], delay: 0.36 });

    const rotorShape = new THREE.Shape();
    rotorShape.absarc(0, 0, 1.42, Math.PI * 0.05, Math.PI * 0.95, false);
    rotorShape.absarc(0, 0, 0.18, Math.PI * 0.95, Math.PI * 0.05, true);
    rotorShape.closePath();
    const rotor = new THREE.Mesh(
      extrudeFlat(rotorShape, 0.05, 0.01),
      new THREE.MeshPhysicalMaterial({ map: createCotesTexture(512, "#f0d3ae"), metalness: 1, roughness: 0.18, color: "#ffe9d0" })
    );
    const rotorPivot = new THREE.Group();
    rotorPivot.position.z = -0.4;
    rotorPivot.add(rotor);
    addPart("rotor", rotorPivot, [0, 0, -1.25], { rot: [0, 0, 0.6], delay: 0.42 });
    spinners.push({ object: rotor, speed: 0.35 });
  }

  // ------------------------------------------------------------------ dial
  const dialGroup = new THREE.Group();
  const dialTexture = createDialTexture({
    dial: o.dial,
    metal: o.metal,
    style: o.style,
    numerals: o.numerals,
    brand: o.brand,
    brandFa: o.brandFa,
    origin: o.origin,
    date: o.date,
    size: lowQuality ? 1024 : 2048,
  });
  const dialMaterial = new THREE.MeshPhysicalMaterial({
    map: dialTexture,
    metalness: palette.light ? 0.05 : 0.3,
    roughness: 0.46,
    clearcoat: 0.15,
    clearcoatRoughness: 0.3,
    envMapIntensity: palette.light ? 1.35 : 0.55,
  });
  if (o.dial === "mop") {
    dialMaterial.iridescence = 1;
    dialMaterial.iridescenceIOR = 1.5;
    dialMaterial.iridescenceThicknessRange = [160, 520];
    dialMaterial.metalness = 0.05;
    dialMaterial.roughness = 0.22;
  }
  const dialMesh = new THREE.Mesh(new THREE.CircleGeometry(1.6, 160), dialMaterial);
  dialGroup.add(dialMesh);
  dialGroup.position.z = 0.345;

  const skipHours = new Set(o.style === "chrono" ? [3, 6, 9] : o.style === "presidential" ? [0, 3] : [3]);
  if (o.indices === "baton") {
    const baton = new RoundedBoxGeometry(0.075, 0.27, 0.045, 2, 0.018);
    for (let h = 0; h < 12; h++) {
      if (skipHours.has(h) && h !== 0) continue;
      const a = (h / 12) * TAU;
      const offsets = h === 0 ? [-0.055, 0.055] : [0];
      for (const off of offsets) {
        const marker = new THREE.Mesh(baton, polished);
        const r = 1.28;
        marker.position.set(Math.sin(a) * r + Math.cos(a) * off, Math.cos(a) * r - Math.sin(a) * off, 0.022);
        marker.rotation.z = -a;
        dialGroup.add(marker);
      }
    }
  } else if (o.indices === "dot") {
    const lume = lumeMaterial();
    const rim = new THREE.CylinderGeometry(0.12, 0.12, 0.04, 32);
    rim.rotateX(Math.PI / 2);
    const dot = new THREE.CylinderGeometry(0.098, 0.098, 0.05, 32);
    dot.rotateX(Math.PI / 2);
    const bar = new RoundedBoxGeometry(0.16, 0.36, 0.045, 2, 0.02);
    const barLume = new RoundedBoxGeometry(0.12, 0.32, 0.05, 2, 0.02);
    for (let h = 0; h < 12; h++) {
      if (h === 3) continue;
      const a = (h / 12) * TAU;
      const r = h % 3 === 0 ? 1.24 : 1.3;
      const group = new THREE.Group();
      if (h % 3 === 0) {
        group.add(new THREE.Mesh(bar, polished), new THREE.Mesh(barLume, lume));
      } else {
        group.add(new THREE.Mesh(rim, polished), new THREE.Mesh(dot, lume));
      }
      group.position.set(Math.sin(a) * r, Math.cos(a) * r, 0.022);
      group.rotation.z = -a;
      dialGroup.add(group);
    }
  } else if (o.indices === "diamond") {
    const gem = new THREE.CylinderGeometry(0.075, 0.001, 0.075, 8, 1);
    gem.rotateX(-Math.PI / 2);
    const gemMat = gemMaterial();
    for (let h = 0; h < 12; h++) {
      if (skipHours.has(h)) continue;
      const a = (h / 12) * TAU;
      const setting = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.02, 24).rotateX(Math.PI / 2), polished);
      const stone = new THREE.Mesh(gem, gemMat);
      stone.position.z = 0.05;
      const group = new THREE.Group();
      group.add(setting, stone);
      group.position.set(Math.sin(a) * 1.3, Math.cos(a) * 1.3, 0.012);
      dialGroup.add(group);
    }
  }
  const subHands = [];
  if (o.style === "chrono") {
    const subShape = handShape("baton", 0.26, 0.03, 0.05);
    const subGeo = extrudeFlat(subShape, 0.01, 0.003);
    const subMat = new THREE.MeshStandardMaterial({ color: o.secondsColor || (palette.light ? "#1c1c1c" : "#f2f2f2"), metalness: 0.6, roughness: 0.3 });
    for (const [x, y, rate] of [[0.704, 0, 1 / 60], [-0.704, 0, 1], [0, -0.704, 1 / 3600]]) {
      const hand = new THREE.Mesh(subGeo, subMat);
      hand.position.set(x, y, 0.03);
      dialGroup.add(hand);
      subHands.push({ hand, rate });
    }
  }
  addPart("dial", dialGroup, [0, 0, 1.75], { rot: [0, 0, 0.35], delay: 0.28 });

  // ----------------------------------------------------------------- hands
  const handMaterial = metalMaterial(o.metal, "satin");
  const lume = lumeMaterial();
  const kind = o.handStyle;
  function buildHand(length, width, tail, depthZ, withLume = true) {
    const group = new THREE.Group();
    group.add(new THREE.Mesh(extrudeFlat(handShape(kind, length, width, tail), 0.016), handMaterial));
    if (withLume && o.style !== "classic") {
      const insert = handShape(kind, length * 0.72, width * 0.52, -length * 0.22);
      const mesh = new THREE.Mesh(extrudeFlat(insert, 0.01, 0.002), lume);
      mesh.position.z = 0.02;
      group.add(mesh);
    }
    group.position.z = depthZ;
    return group;
  }
  const hourHand = buildHand(0.92, o.handStyle === "sword" ? 0.2 : 0.12, 0.18, 0.4);
  const minuteHand = buildHand(1.38, o.handStyle === "sword" ? 0.16 : 0.1, 0.2, 0.43);
  const secondHand = new THREE.Group();
  const secondColor = o.secondsColor ? new THREE.MeshStandardMaterial({ color: o.secondsColor, metalness: 0.3, roughness: 0.35 }) : handMaterial;
  const needle = new THREE.Mesh(extrudeFlat(roundedRectShape(0.024, 1.84, 0.01), 0.008, 0.002), secondColor);
  needle.position.y = 0.55;
  secondHand.add(needle);
  const weight = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.012, 32).rotateX(Math.PI / 2), secondColor);
  weight.position.y = -0.26;
  secondHand.add(weight);
  if (o.style === "diver") {
    const lumeDot = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.016, 32).rotateX(Math.PI / 2), lume);
    lumeDot.position.y = 1.08;
    secondHand.add(lumeDot);
  }
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.04, 32).rotateX(Math.PI / 2), polished);
  cap.position.z = 0.02;
  secondHand.add(cap);
  secondHand.position.z = 0.455;
  addPart("hourHand", hourHand, [0, 0, 2.2], { rot: [0, 0, 0.9], delay: 0.2 });
  addPart("minuteHand", minuteHand, [0, 0, 2.55], { rot: [0, 0, -0.7], delay: 0.15 });
  addPart("secondHand", secondHand, [0, 0, 2.9], { rot: [0, 0, 1.2], delay: 0.1 });

  // ----------------------------------------------------------------- bezel
  const bezelGroup = new THREE.Group();
  if (o.bezel === "fluted") {
    const profile = [
      { r: 1.58, z: 0.33 },
      { r: 1.99, z: 0.33 },
      { r: 2.005, z: 0.36 },
      { r: 1.975, z: 0.43, w: 1 },
      { r: 1.75, z: 0.55, w: 1 },
      { r: 1.67, z: 0.565 },
      { r: 1.61, z: 0.54 },
      { r: 1.58, z: 0.47 },
      { r: 1.58, z: 0.33 },
    ];
    bezelGroup.add(new THREE.Mesh(sweepZ(profile, { segments: lowQuality ? 360 : 576, modulate: flutes(72, 0.055, 1.2) }), polished));
  } else if (o.bezel === "diver" || o.bezel === "tachy") {
    const profile = [
      { r: 1.58, z: 0.33 },
      { r: 2.03, z: 0.33 },
      { r: 2.05, z: 0.36, w: o.bezel === "diver" ? 1 : 0 },
      { r: 2.05, z: 0.47, w: o.bezel === "diver" ? 1 : 0 },
      { r: 2.0, z: 0.505 },
      { r: 1.95, z: 0.505 },
      { r: 1.95, z: 0.49 },
      { r: 1.63, z: 0.49 },
      { r: 1.6, z: 0.47 },
      { r: 1.58, z: 0.4 },
      { r: 1.58, z: 0.33 },
    ];
    bezelGroup.add(new THREE.Mesh(sweepZ(profile, { segments: 480, modulate: flutes(120, 0.025, 1) }), polished));
    const insert = new THREE.Mesh(
      new THREE.RingGeometry(1.625, 1.955, 160, 1),
      new THREE.MeshPhysicalMaterial({
        map: createInsertTexture({ kind: o.bezel === "diver" ? "diver" : "tachy", color: o.bezelColor, ink: o.bezelInk }),
        roughness: 0.18,
        metalness: 0.1,
        clearcoat: 1,
        clearcoatRoughness: 0.06,
      })
    );
    insert.position.z = 0.492;
    bezelGroup.add(insert);
  } else {
    const profile = [
      { r: 1.58, z: 0.33 },
      { r: 1.99, z: 0.33 },
      { r: 2.005, z: 0.37 },
      { r: 1.95, z: 0.47 },
      { r: 1.8, z: 0.535 },
      { r: 1.66, z: 0.55 },
      { r: 1.6, z: 0.52 },
      { r: 1.58, z: 0.45 },
      { r: 1.58, z: 0.33 },
    ];
    bezelGroup.add(new THREE.Mesh(sweepZ(profile, { segments: 256 }), polished));
    if (o.bezel === "diamond") {
      const count = 44;
      const stone = new THREE.CylinderGeometry(0.085, 0.001, 0.08, 8, 1);
      stone.rotateX(-Math.PI / 2);
      const gems = new THREE.InstancedMesh(stone, gemMaterial(), count);
      const m = new THREE.Matrix4();
      const q = new THREE.Quaternion();
      const tilt = new THREE.Quaternion();
      for (let i = 0; i < count; i++) {
        const a = (i / count) * TAU;
        tilt.setFromEuler(new THREE.Euler(Math.sin(a) * -0.35, Math.cos(a) * 0.35, 0));
        q.copy(tilt);
        m.compose(new THREE.Vector3(Math.cos(a) * 1.8, Math.sin(a) * 1.8, 0.55), q, new THREE.Vector3(1, 1, 1));
        gems.setMatrixAt(i, m);
      }
      bezelGroup.add(gems);
    }
  }
  addPart("bezel", bezelGroup, [0, 0, 3.35], { rot: [0.12, -0.1, -0.5], delay: 0.07 });

  // --------------------------------------------------------------- crystal
  const crystalGroup = new THREE.Group();
  const crystalGeometry = new THREE.CylinderGeometry(1.61, 1.61, 0.06, 128, 1);
  crystalGeometry.rotateX(Math.PI / 2);
  const crystal = new THREE.Mesh(crystalGeometry, glassMaterial());
  crystal.renderOrder = 2;
  crystalGroup.add(crystal);
  const glintUniforms = { uSweep: { value: -2 }, uStrength: { value: 0 } };
  const glint = new THREE.Mesh(
    new THREE.CircleGeometry(1.6, 96),
    new THREE.ShaderMaterial({
      uniforms: glintUniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
      fragmentShader:
        "varying vec2 vUv; uniform float uSweep; uniform float uStrength;" +
        "void main(){ vec2 p = vUv*2.0-1.0; float d = dot(p, normalize(vec2(0.75,0.66)));" +
        "float band = exp(-pow((d-uSweep)*4.0,2.0)) + 0.35*exp(-pow((d-uSweep+0.28)*9.0,2.0));" +
        "float edge = smoothstep(1.0,0.82,length(p));" +
        "gl_FragColor = vec4(vec3(1.0,0.93,0.86)*band*edge*uStrength*0.42, 1.0); }",
    })
  );
  glint.position.z = 0.035;
  glint.renderOrder = 3;
  crystalGroup.add(glint);
  crystalGroup.position.z = 0.565;
  addPart("crystal", crystalGroup, [1.9, 0.55, 4.1], { rot: [0.35, 0.6, 0.2], delay: 0 });

  // ----------------------------------------------------------------- crown
  const crownProfile = [
    { r: 0.0, z: 0.0 },
    { r: 0.23, z: 0.0 },
    { r: 0.27, z: 0.035 },
    { r: 0.28, z: 0.06, w: 1 },
    { r: 0.28, z: 0.27, w: 1 },
    { r: 0.255, z: 0.31 },
    { r: 0.14, z: 0.335 },
    { r: 0.0, z: 0.34 },
  ];
  const crownGeometry = sweepZ(crownProfile, { segments: 120, modulate: flutes(26, 0.028, 1.4) });
  crownGeometry.rotateY(Math.PI / 2);
  const crown = new THREE.Mesh(crownGeometry, polished);
  crown.position.set(2.06, 0, -0.07);
  addPart("crown", crown, [1.35, 0, 0.25], { rot: [0.9, 0, 0], delay: 0.3 });

  // -------------------------------------------------------------- bracelet
  const bracelet = buildBand(o, { polished, brushed });
  root.add(bracelet);
  parts.push({
    name: "bracelet",
    object: bracelet,
    basePos: bracelet.position.clone(),
    baseRot: bracelet.rotation.clone(),
    explode: new THREE.Vector3(0, 0, -0.35),
    rot: new THREE.Vector3(0, 0, 0),
    delay: 0.4,
    phase: 0,
  });

  root.scale.setScalar(o.size);

  // --------------------------------------------------------------- runtime
  let explodeAmount = 0;
  function setExplode(amount, time = 0) {
    explodeAmount = amount;
    for (const part of parts) {
      const local = easeInOut(clamp01((amount - part.delay) / (1 - part.delay)));
      const float = Math.sin(time * 0.9 + part.phase) * 0.06 * local;
      part.object.position.set(
        part.basePos.x + part.explode.x * local,
        part.basePos.y + part.explode.y * local + float,
        part.basePos.z + part.explode.z * local
      );
      part.object.rotation.set(
        part.baseRot.x + part.rot.x * local,
        part.baseRot.y + part.rot.y * local,
        part.baseRot.z + part.rot.z * local
      );
    }
  }

  function currentTime(elapsed) {
    if (o.time) {
      return { h: o.time.h, m: o.time.m, s: o.time.s + (o.time.sweep ? elapsed : 0) };
    }
    const now = new Date();
    return { h: now.getHours(), m: now.getMinutes(), s: now.getSeconds() + now.getMilliseconds() / 1000 };
  }

  function update(elapsed = 0) {
    const { h, m, s } = currentTime(elapsed);
    const hands = parts.reduce((acc, part) => ((acc[part.name] = part), acc), {});
    const handTwist = (name) => hands[name].rot.z * easeInOut(clamp01((explodeAmount - hands[name].delay) / (1 - hands[name].delay)));
    hourHand.rotation.z = hourAngle((h % 12) + m / 60 + s / 3600) + handTwist("hourHand");
    minuteHand.rotation.z = -((m + s / 60) / 60) * TAU + handTwist("minuteHand");
    secondHand.rotation.z = -(s / 60) * TAU + handTwist("secondHand");
    for (const { hand, rate } of subHands) hand.rotation.z = -((s * rate) % 60) / 60 * TAU;
    const spinBoost = 0.3 + explodeAmount * 1.4;
    for (const spinner of spinners) spinner.object.rotation.z = elapsed * spinner.speed * spinBoost;
    if (balance) balance.rotation.z = Math.sin(elapsed * TAU * 1.6) * 1.9;
  }

  function setGlint(position, strength = 1) {
    glintUniforms.uSweep.value = position;
    glintUniforms.uStrength.value = strength;
  }

  function dispose() {
    root.traverse((node) => {
      if (node.geometry) node.geometry.dispose();
      if (node.material) {
        const materials = Array.isArray(node.material) ? node.material : [node.material];
        materials.forEach((material) => {
          Object.values(material).forEach((value) => value && value.isTexture && value.dispose());
          material.dispose();
        });
      }
    });
  }

  setExplode(0);
  update(0);
  return { group: root, parts, setExplode, update, setGlint, dispose, options: o, dayInfo: dialTexture.userData };
}

function buildBand(o, { polished, brushed }) {
  const group = new THREE.Group();
  const curve = braceletCurve();
  const length = curve.getLength();
  const widthAt = (u) => 1.96 - 0.3 * Math.sin(Math.PI * u);
  const matrix = new THREE.Matrix4();
  const scale = new THREE.Matrix4();
  const offset = new THREE.Matrix4();

  if (o.strap === "president" || o.strap === "oyster") {
    const president = o.strap === "president";
    const rows = president ? Math.round(length / 0.34) : Math.round(length / 0.5);
    const pitch = length / rows;
    const thickness = president ? 0.25 : 0.2;
    const radius = president ? 0.11 : 0.05;
    const linkGeometry = new RoundedBoxGeometry(1, pitch * (president ? 0.93 : 0.96), thickness, 3, radius);
    const center = new THREE.InstancedMesh(linkGeometry, polished, rows);
    const left = new THREE.InstancedMesh(linkGeometry, brushed, rows);
    const right = new THREE.InstancedMesh(linkGeometry, brushed, rows);
    const claspHalf = president ? 0 : 0.045;
    let count = 0;
    for (let i = 0; i < rows; i++) {
      const u = (i + 0.5) / rows;
      if (claspHalf && Math.abs(u - 0.5) < claspHalf) continue;
      const w = widthAt(u);
      const cw = w * (president ? 0.33 : 0.28);
      const sw = w * (president ? 0.315 : 0.345);
      const gap = w * 0.012;
      frameOnCurve(curve, u, matrix);
      center.setMatrixAt(count, matrix.clone().multiply(scale.makeScale(cw, 1, 1)));
      left.setMatrixAt(
        count,
        matrix.clone().multiply(offset.makeTranslation(-(cw / 2 + gap + sw / 2), 0, -0.015)).multiply(scale.makeScale(sw, 1, 0.92))
      );
      right.setMatrixAt(
        count,
        matrix.clone().multiply(offset.makeTranslation(cw / 2 + gap + sw / 2, 0, -0.015)).multiply(scale.makeScale(sw, 1, 0.92))
      );
      count++;
    }
    for (const mesh of [center, left, right]) {
      mesh.count = count;
      mesh.instanceMatrix.needsUpdate = true;
      group.add(mesh);
    }
    if (!president) {
      const clasp = new THREE.Mesh(new RoundedBoxGeometry(1.62, 1.05, 0.28, 3, 0.08), brushed);
      clasp.applyMatrix4(frameOnCurve(curve, 0.5, new THREE.Matrix4()));
      group.add(clasp);
    }
    // End links hugging the case between the lugs
    const endLink = new RoundedBoxGeometry(2.02, 0.26, 0.3, 3, 0.1);
    for (const u of [0.004, 0.996]) {
      const piece = new THREE.Mesh(endLink, polished);
      piece.applyMatrix4(frameOnCurve(curve, u, new THREE.Matrix4()));
      group.add(piece);
    }
    return group;
  }

  // Straps
  const kind = o.strap;
  const texture = createStrapTexture({ kind, color: o.strapColor });
  texture.repeat.set(1, 1);
  let material;
  if (kind === "leather") {
    material = leatherMaterial("#ffffff");
    material.map = texture;
  } else if (kind === "mesh") {
    material = metalMaterial(o.metal, "satin");
    material.bumpMap = texture;
    material.bumpScale = 1.4;
    material.roughness = 0.28;
  } else {
    material = rubberMaterial(o.strapColor);
    material.map = texture;
    material.color.set("#ffffff");
  }
  const frames = [];
  const thicknessAt = (u) => (kind === "mesh" ? 0.1 : 0.15 + 0.07 * (1 - Math.sin(Math.PI * u)));
  const strap = new THREE.Mesh(
    strapGeometry(curve, { samples: 260, widthAt: (u) => widthAt(u) - 0.05, thicknessAt, corner: kind === "mesh" ? 0.15 : 0.4, frames }),
    material
  );
  group.add(strap);

  if (kind === "leather") {
    const stitchGeometry = new THREE.BoxGeometry(0.02, 0.075, 0.014);
    const stitchMaterial = new THREE.MeshStandardMaterial({ color: "#efe3cf", roughness: 0.8 });
    const step = 0.13;
    const total = Math.floor(length / step);
    const stitches = new THREE.InstancedMesh(stitchGeometry, stitchMaterial, total * 2);
    let n = 0;
    for (let i = 1; i < total - 1; i++) {
      const u = i / total;
      if (Math.abs(u - 0.5) < 0.05) continue;
      const w = widthAt(u) - 0.05;
      const t = thicknessAt(u);
      frameOnCurve(curve, u, matrix);
      for (const side of [-1, 1]) {
        stitches.setMatrixAt(n++, matrix.clone().multiply(offset.makeTranslation(side * (w / 2 - 0.09), 0, t / 2)));
      }
    }
    stitches.count = n;
    group.add(stitches);
  }

  // Buckle / clasp at the back of the wrist
  const buckleFrame = frameOnCurve(curve, 0.5, new THREE.Matrix4());
  const buckle = new THREE.Group();
  if (kind === "mesh") {
    buckle.add(new THREE.Mesh(new RoundedBoxGeometry(1.7, 0.7, 0.18, 3, 0.06), polished));
  } else {
    const barGeometry = new RoundedBoxGeometry(1.95, 0.09, 0.09, 2, 0.04);
    const sideGeometry = new RoundedBoxGeometry(0.09, 0.62, 0.09, 2, 0.04);
    const top = new THREE.Mesh(barGeometry, polished);
    top.position.y = 0.28;
    const bottom = new THREE.Mesh(barGeometry, polished);
    bottom.position.y = -0.28;
    const leftSide = new THREE.Mesh(sideGeometry, polished);
    leftSide.position.x = -0.93;
    const rightSide = new THREE.Mesh(sideGeometry, polished);
    rightSide.position.x = 0.93;
    const prong = new THREE.Mesh(new RoundedBoxGeometry(0.06, 0.5, 0.05, 2, 0.02), polished);
    prong.position.set(0, 0.02, 0.05);
    buckle.add(top, bottom, leftSide, rightSide, prong);
    buckle.position.z = thicknessAt(0.5) / 2 + 0.03;
  }
  buckle.applyMatrix4(buckleFrame);
  group.add(buckle);
  return group;
}

function createSmartwatch(o) {
  const root = new THREE.Group();
  const head = new THREE.Group();
  root.add(head);
  const parts = [];
  const add = (name, object, explode, delay = 0) => {
    head.add(object);
    parts.push({ name, object, basePos: object.position.clone(), baseRot: object.rotation.clone(), explode: new THREE.Vector3(...explode), rot: new THREE.Vector3(), delay, phase: parts.length });
  };
  const caseMaterial = metalMaterial(o.metal, "satin");
  const body = new THREE.Mesh(new RoundedBoxGeometry(1.95, 2.35, 0.52, 8, 0.44), caseMaterial);
  add("case", body, [0, 0, 0]);
  const glassBody = new THREE.Mesh(
    new RoundedBoxGeometry(1.8, 2.2, 0.08, 8, 0.38),
    new THREE.MeshPhysicalMaterial({ color: "#050506", roughness: 0.04, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 1.6 })
  );
  glassBody.position.z = 0.25;
  add("glass", glassBody, [0, 0, 1.6], 0.1);

  const screenShape = roundedRectShape(1.52, 1.9, 0.3);
  const screenGeometry = new THREE.ShapeGeometry(screenShape, 24);
  const uv = screenGeometry.attributes.uv;
  const pos = screenGeometry.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) / 1.52 + 0.5, pos.getY(i) / 1.9 + 0.5);
  const screen = new THREE.Mesh(
    screenGeometry,
    new THREE.MeshBasicMaterial({ map: createSmartScreenTexture({ date: o.date, accent: o.metal === "rose" ? "#ff9b7a" : "#ffb347" }), toneMapped: false })
  );
  screen.position.z = 0.295;
  add("screen", screen, [0, 0, 1.1], 0.2);
  const reflection = new THREE.Mesh(new THREE.ShapeGeometry(roundedRectShape(1.78, 2.18, 0.37), 24), glassMaterial(1.4, 0.12));
  reflection.position.z = 0.3;
  add("reflection", reflection, [0, 0, 1.62], 0.1);

  const crownGeometry = sweepZ(
    [
      { r: 0, z: 0 },
      { r: 0.2, z: 0 },
      { r: 0.22, z: 0.03 },
      { r: 0.22, z: 0.2, w: 1 },
      { r: 0.2, z: 0.23 },
      { r: 0, z: 0.23 },
    ],
    { segments: 96, modulate: flutes(30, 0.02) }
  );
  crownGeometry.rotateY(Math.PI / 2);
  const crown = new THREE.Mesh(crownGeometry, metalMaterial(o.metal, "polished"));
  crown.position.set(0.95, 0.4, 0);
  add("crown", crown, [1.0, 0, 0], 0.3);
  const button = new THREE.Mesh(new RoundedBoxGeometry(0.12, 0.62, 0.2, 3, 0.05), caseMaterial);
  button.position.set(0.97, -0.35, 0);
  add("button", button, [0.9, 0, 0], 0.3);

  const bandColor = o.strapColor !== DEFAULTS.strapColor ? o.strapColor : { rose: "#e2b3a6", gold: "#efe6d4", black: "#18191c" }[o.metal] || "#23252a";
  const band = buildBand({ ...o, strap: "rubber", strapColor: bandColor }, { polished: caseMaterial, brushed: caseMaterial });
  band.scale.set(0.9, 0.62, 1);
  band.position.z = -0.1;
  root.add(band);
  root.scale.setScalar(o.size);

  let explodeAmount = 0;
  return {
    group: root,
    parts,
    setExplode(amount) {
      explodeAmount = amount;
      for (const part of parts) {
        const local = easeInOut(clamp01((amount - part.delay) / (1 - part.delay)));
        part.object.position.copy(part.basePos).addScaledVector(part.explode, local);
      }
    },
    update() {
      return explodeAmount;
    },
    setGlint() {},
    dispose() {},
    options: o,
    dayInfo: {},
  };
}
