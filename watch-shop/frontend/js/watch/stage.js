import * as THREE from "three";

/** A small photo studio: soft boxes and strip lights for crisp metal reflections. */
function createStudioScene() {
  const scene = new THREE.Scene();
  const room = new THREE.Mesh(
    new THREE.BoxGeometry(30, 18, 30),
    new THREE.MeshBasicMaterial({ color: new THREE.Color("#0b0a09"), side: THREE.BackSide })
  );
  scene.add(room);
  const panel = (width, height, intensity, color, position) => {
    const material = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity), side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
    mesh.position.set(...position);
    mesh.lookAt(0, 0, 0);
    scene.add(mesh);
  };
  panel(12, 4, 5.5, "#ffffff", [0, 8, 3]); // top softbox
  panel(3, 11, 4.2, "#fff1e4", [-10, 1.5, 4]); // warm left strip
  panel(3, 11, 3.2, "#e9f1ff", [10, 0.5, 2]); // cool right strip
  panel(10, 2.5, 2.2, "#ffe6d3", [0, -3.5, 10]); // front fill
  panel(7, 7, 1.2, "#ffffff", [2, 3, -11]); // back
  panel(2, 2, 7, "#ffffff", [-5, 6, 8]); // small sparkle source
  panel(18, 9, 0.9, "#fff3e8", [0, 1.5, 15]); // large dim reflector behind the camera
  return scene;
}

export function createStage(canvas, { pixelRatio, alpha = true, exposure = 1.05, preserveDrawingBuffer = false } = {}) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha,
    powerPreference: "high-performance",
    preserveDrawingBuffer,
  });
  renderer.setPixelRatio(pixelRatio ?? Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = exposure;
  if (alpha) renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envMap = pmrem.fromScene(createStudioScene(), 0.035).texture;
  pmrem.dispose();

  // No punctual lights on purpose: a directional light makes flat, glossy
  // parts (crystal, dial) flash completely white at certain angles. All the
  // lighting comes from the studio environment's soft boxes instead.

  const camera = new THREE.PerspectiveCamera(24, 1, 0.1, 200);
  camera.position.set(0, 0, 17);

  function resize(width, height) {
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(1, height);
    camera.updateProjectionMatrix();
  }

  // Assign the environment per material: ``envMapIntensity`` is ignored for
  // materials that only inherit ``scene.environment``.
  function applyEnvironment(object) {
    object.traverse((node) => {
      const materials = node.material ? (Array.isArray(node.material) ? node.material : [node.material]) : [];
      for (const material of materials) {
        if (material.isMeshStandardMaterial && !material.envMap) {
          material.envMap = envMap;
          material.needsUpdate = true;
        }
      }
    });
  }

  return {
    renderer,
    scene,
    camera,
    envMap,
    applyEnvironment,
    resize,
    render: () => renderer.render(scene, camera),
    dispose: () => {
      envMap.dispose();
      renderer.dispose();
    },
  };
}

export function webglAvailable() {
  try {
    const canvas = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (canvas.getContext("webgl2") || canvas.getContext("webgl")));
  } catch {
    return false;
  }
}

export async function fontsReady(families = ['600 64px "Markazi Text"', '600 64px "Cormorant Garamond"', "600 64px Vazirmatn", "300 64px Vazirmatn"]) {
  if (!document.fonts) return;
  try {
    await Promise.race([
      Promise.all(families.map((f) => document.fonts.load(f, "ابپ SANIYEH ۱۲۳"))),
      new Promise((resolve) => setTimeout(resolve, 2500)),
    ]);
  } catch {
    /* fall back to system fonts */
  }
}
