// Scroll-driven 3D hero: the watch starts exploded into its parts and
// assembles itself as the visitor scrolls (like the reference video).
import * as THREE from "three";
import { createStage, fontsReady, webglAvailable } from "./watch/stage.js";
import { createWatch } from "./watch/model.js";

const clamp01 = (v) => Math.min(1, Math.max(0, v));
const smoothstep = (a, b, v) => {
  const t = clamp01((v - a) / (b - a));
  return t * t * (3 - 2 * t);
};
const lerp = (a, b, t) => a + (b - a) * t;

// Poses along the pinned section's scroll progress (p).
// e = explode amount, r* = rotation, x/y = position, dist = camera distance.
const KEYS_WIDE = [
  { p: 0.0, e: 1, rx: -1.0, ry: 0.3, rz: 0.5, x: -2.1, y: -0.4, dist: 30.5 },
  { p: 0.1, e: 1, rx: -0.96, ry: 0.38, rz: 0.44, x: -2.1, y: -0.4, dist: 30 },
  { p: 0.46, e: 0, rx: -0.16, ry: -0.5, rz: 0.06, x: -2.5, y: -0.05, dist: 22 },
  { p: 0.63, e: 0, rx: -0.1, ry: 0.62, rz: -0.06, x: -2.5, y: -0.05, dist: 22 },
  { p: 0.73, e: 0, rx: -0.05, ry: 0.12, rz: 0.0, x: -1.55, y: 0.3, dist: 8.4 },
  { p: 0.82, e: 0, rx: -0.05, ry: 0.04, rz: 0.0, x: -1.55, y: 0.25, dist: 8.8 },
  { p: 0.91, e: 0, rx: -0.14, ry: -0.42, rz: 0.05, x: -2.7, y: -0.15, dist: 23 },
  { p: 1.0, e: 0, rx: -0.12, ry: -0.34, rz: 0.04, x: -2.7, y: -0.15, dist: 22.5 },
];

const KEYS_NARROW = [
  { p: 0.0, e: 1, rx: -1.0, ry: 0.3, rz: 0.5, x: -0.5, y: 1.3, dist: 34 },
  { p: 0.1, e: 1, rx: -0.96, ry: 0.38, rz: 0.44, x: -0.5, y: 1.3, dist: 33 },
  { p: 0.46, e: 0, rx: -0.16, ry: -0.5, rz: 0.06, x: 0, y: 1.45, dist: 27 },
  { p: 0.63, e: 0, rx: -0.1, ry: 0.62, rz: -0.06, x: 0, y: 1.45, dist: 27 },
  { p: 0.73, e: 0, rx: -0.05, ry: 0.1, rz: 0.0, x: 0, y: 1.55, dist: 14 },
  { p: 0.82, e: 0, rx: -0.05, ry: 0.02, rz: 0.0, x: 0, y: 1.55, dist: 14.5 },
  { p: 0.91, e: 0, rx: -0.14, ry: -0.42, rz: 0.05, x: 0, y: 2.55, dist: 31 },
  { p: 1.0, e: 0, rx: -0.12, ry: -0.34, rz: 0.04, x: 0, y: 2.55, dist: 30.5 },
];

function samplePose(keys, p) {
  if (p <= keys[0].p) return { ...keys[0] };
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i];
    const b = keys[i + 1];
    if (p <= b.p) {
      const t = smoothstep(a.p, b.p, p);
      const pose = {};
      for (const key of Object.keys(a)) pose[key] = lerp(a[key], b[key], t);
      return pose;
    }
  }
  return { ...keys[keys.length - 1] };
}

// Where each floating label points to, in the part's local coordinates.
const LABEL_ANCHORS = {
  crystal: [-1.55, 0.2, 0],
  bezel: [-1.95, 0.25, 0.45],
  dial: [-1.5, 0.25, 0],
  movement: [-1.35, -0.85, -0.1],
};

function sectionProgress(section) {
  if (typeof section._progress === "number") return section._progress;
  const rect = section.getBoundingClientRect();
  const total = rect.height - window.innerHeight;
  return total > 0 ? clamp01(-rect.top / total) : 0;
}

async function initHero(root) {
  const section = root.closest("[data-scene]") || root;
  const canvas = root.querySelector("[data-hero-canvas]");
  const config = JSON.parse(root.dataset.config || "{}");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!canvas || !webglAvailable()) {
    root.classList.add("is-fallback");
    return;
  }

  await fontsReady();
  const narrowQuery = window.matchMedia("(max-width: 767px)");
  const lowPower = narrowQuery.matches || (navigator.hardwareConcurrency || 8) <= 4;
  const stage = createStage(canvas, { pixelRatio: Math.min(window.devicePixelRatio || 1, lowPower ? 1.5 : 2) });
  const pivot = new THREE.Group();
  stage.scene.add(pivot);

  let watch = null;
  function build(metal = config.metal || "rose") {
    const next = createWatch({
      style: "presidential",
      metal,
      dial: config.dial || "chocolate",
      numerals: "persian",
      bezel: "fluted",
      strap: "president",
      brand: config.brand || "SANIYEH",
      brandFa: config.brandFa || "ثانیه",
      quality: lowPower ? "low" : "high",
    });
    stage.applyEnvironment(next.group);
    if (watch) {
      pivot.remove(watch.group);
      watch.dispose();
    }
    watch = next;
    pivot.add(watch.group);
  }
  build();

  const labels = [...root.querySelectorAll("[data-part-label]")].map((el) => ({
    el,
    name: el.dataset.partLabel,
    anchor: new THREE.Vector3(...(LABEL_ANCHORS[el.dataset.partLabel] || [0, 0, 0])),
  }));

  const size = { width: 1, height: 1 };
  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    size.width = Math.max(1, rect.width);
    size.height = Math.max(1, rect.height);
    stage.resize(size.width, size.height);
    requestRender();
  };
  new ResizeObserver(resize).observe(canvas);

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  window.addEventListener(
    "pointermove",
    (event) => {
      if (event.pointerType !== "mouse") return;
      pointer.tx = (event.clientX / window.innerWidth) * 2 - 1;
      pointer.ty = (event.clientY / window.innerHeight) * 2 - 1;
    },
    { passive: true }
  );

  root.querySelectorAll("[data-hero-metal]").forEach((button) => {
    button.addEventListener("click", () => {
      root.querySelectorAll("[data-hero-metal]").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
      build(button.dataset.heroMetal);
      requestRender();
    });
  });

  const clock = new THREE.Clock();
  const worldPoint = new THREE.Vector3();
  let progress = sectionProgress(section);
  let running = false;
  let visible = true;
  let frameId = 0;

  function applyFrame(dt) {
    const target = reduceMotion ? 0.5 : sectionProgress(section);
    progress += (target - progress) * (1 - Math.exp(-dt * 7.5));
    const time = clock.elapsedTime;
    const keys = narrowQuery.matches ? KEYS_NARROW : KEYS_WIDE;
    const pose = samplePose(keys, progress);

    pointer.x += (pointer.tx - pointer.x) * Math.min(1, dt * 3);
    pointer.y += (pointer.ty - pointer.y) * Math.min(1, dt * 3);

    watch.setExplode(pose.e, time);
    watch.update(time);
    const group = watch.group;
    group.rotation.set(
      pose.rx + pointer.y * 0.07,
      pose.ry + pointer.x * 0.12 + Math.sin(time * 0.35) * 0.035 * (1 - pose.e * 0.5),
      pose.rz
    );
    group.position.set(pose.x, pose.y + Math.sin(time * 0.8) * 0.04, 0);

    // Keep the composition inside narrow viewports.
    const aspect = size.width / size.height;
    const fit = aspect < 0.8 ? 0.8 / aspect : 1;
    stage.camera.position.set(0, 0, pose.dist * Math.min(fit, 1.6));
    stage.camera.lookAt(0, 0, 0);

    // Light sweeps across the crystal while it lands and during the close-up.
    const sweepA = smoothstep(0.38, 0.56, progress);
    const sweepB = smoothstep(0.72, 0.84, progress);
    const sweeping = (sweepA > 0 && sweepA < 1) || (sweepB > 0 && sweepB < 1);
    const sweepPos = sweepB > 0 ? lerp(-1.5, 1.5, sweepB) : lerp(-1.5, 1.5, sweepA);
    watch.setGlint(sweepPos, sweeping ? 1 : pose.e * 0.55);

    stage.render();

    // Labels follow the floating parts while the watch is exploded.
    const labelOpacity = narrowQuery.matches ? 0 : smoothstep(0.55, 0.9, pose.e);
    for (const label of labels) {
      const part = watch.parts.find((item) => item.name === label.name);
      if (!part || labelOpacity < 0.01) {
        label.el.style.opacity = "0";
        continue;
      }
      worldPoint.copy(label.anchor);
      part.object.localToWorld(worldPoint);
      worldPoint.project(stage.camera);
      const x = (worldPoint.x * 0.5 + 0.5) * size.width;
      const y = (-worldPoint.y * 0.5 + 0.5) * size.height;
      label.el.style.opacity = String(labelOpacity);
      label.el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    }
    return Math.abs(target - progress) > 0.0005;
  }

  function loop() {
    const dt = Math.min(0.05, clock.getDelta());
    applyFrame(dt);
    frameId = running ? requestAnimationFrame(loop) : 0;
  }

  function start() {
    if (running || !visible || document.hidden) return;
    running = true;
    clock.getDelta();
    frameId = requestAnimationFrame(loop);
  }

  function stop() {
    running = false;
    cancelAnimationFrame(frameId);
    frameId = 0;
  }

  function requestRender() {
    if (!running && watch) applyFrame(0.016);
  }

  if (reduceMotion) {
    progress = 0.5;
    applyFrame(1);
    setInterval(() => !document.hidden && applyFrame(1), 1000);
  } else {
    new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        visible ? start() : stop();
      },
      { rootMargin: "120px 0px" }
    ).observe(section);
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    start();
  }

  resize();
  root.classList.add("is-ready");
}

document.querySelectorAll("[data-hero]").forEach((root) => {
  initHero(root).catch((error) => {
    console.error("3D hero failed, showing the fallback image instead.", error);
    root.classList.add("is-fallback");
  });
});
