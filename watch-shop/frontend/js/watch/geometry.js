import * as THREE from "three";

/**
 * Revolves one or more (r, z) polylines around the Z axis.
 * Points may carry a weight ``w`` that scales an angular radial modulation
 * (used for fluted bezels and knurled crowns). Separate polylines give
 * crisp creases between faces. Profiles should run counter-clockwise in the
 * (r, z) plane for outward facing normals.
 */
export function sweepZ(polylines, { segments = 192, modulate = null } = {}) {
  const lines = Array.isArray(polylines[0]) ? polylines : [polylines];
  const positions = [];
  const uvs = [];
  const indices = [];
  let offset = 0;
  for (const profile of lines) {
    const n = profile.length;
    const lengths = [0];
    for (let j = 1; j < n; j++) {
      lengths.push(lengths[j - 1] + Math.hypot(profile[j].r - profile[j - 1].r, profile[j].z - profile[j - 1].z));
    }
    const total = lengths[n - 1] || 1;
    for (let i = 0; i <= segments; i++) {
      const u = i / segments;
      const theta = u * Math.PI * 2;
      const cos = Math.cos(theta);
      const sin = Math.sin(theta);
      const m = modulate ? modulate(theta) : 0;
      for (let j = 0; j < n; j++) {
        const p = profile[j];
        const r = p.r + (p.w ? p.w * m : 0);
        positions.push(r * cos, r * sin, p.z);
        uvs.push(u, lengths[j] / total);
      }
    }
    for (let i = 0; i < segments; i++) {
      for (let j = 0; j < n - 1; j++) {
        const a = offset + i * n + j;
        const b = offset + (i + 1) * n + j;
        const c = offset + (i + 1) * n + j + 1;
        const d = offset + i * n + j + 1;
        indices.push(a, b, d, b, c, d);
      }
    }
    offset += (segments + 1) * n;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

/** Triangle-wave flutes (0 at the ridge, -depth in the groove). */
export function flutes(count, depth, sharpness = 1) {
  return (theta) => {
    const x = (theta * count) / (Math.PI * 2);
    const tri = Math.abs((x - Math.floor(x)) * 2 - 1); // 1 at ridge, 0 at groove
    return -depth * (1 - Math.pow(tri, sharpness));
  };
}

/** Maps a shape drawn in (u = radial Y, v = Z) and extruded along X. */
export function extrudeSide(shape, depth, bevel = 0.04) {
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 5,
    curveSegments: 24,
  });
  // (u, v, w) -> (x = w, y = u, z = v)
  geometry.applyMatrix4(new THREE.Matrix4().set(0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1));
  geometry.computeVertexNormals();
  return geometry;
}

export function roundedRectShape(width, height, radius) {
  const x = -width / 2;
  const y = -height / 2;
  const r = Math.min(radius, width / 2, height / 2);
  const shape = new THREE.Shape();
  shape.moveTo(x + r, y);
  shape.lineTo(x + width - r, y);
  shape.quadraticCurveTo(x + width, y, x + width, y + r);
  shape.lineTo(x + width, y + height - r);
  shape.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  shape.lineTo(x + r, y + height);
  shape.quadraticCurveTo(x, y + height, x, y + height - r);
  shape.lineTo(x, y + r);
  shape.quadraticCurveTo(x, y, x + r, y);
  return shape;
}

export function gearShape({ teeth = 40, radius = 0.5, toothDepth = 0.04, hole = 0.05, spokes = 5, rim = 0.08 }) {
  const shape = new THREE.Shape();
  const root = radius - toothDepth;
  const steps = teeth * 4;
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * Math.PI * 2;
    const phase = i % 4;
    const r = phase === 1 || phase === 2 ? radius : root;
    const x = Math.cos(a) * r;
    const y = Math.sin(a) * r;
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  const axle = new THREE.Path();
  axle.absarc(0, 0, hole, 0, Math.PI * 2, true);
  shape.holes.push(axle);
  if (spokes > 0 && radius > 0.2) {
    const inner = root - rim;
    const hub = hole + rim * 0.9;
    const gap = 0.35 / spokes;
    for (let s = 0; s < spokes; s++) {
      const a0 = (s / spokes) * Math.PI * 2 + gap;
      const a1 = ((s + 1) / spokes) * Math.PI * 2 - gap;
      const window = new THREE.Path();
      window.absarc(0, 0, inner, a0, a1, false);
      window.absarc(0, 0, hub + (inner - hub) * 0.15, a1, a0, true);
      window.closePath();
      shape.holes.push(window);
    }
  }
  return shape;
}

/**
 * Sweeps a rounded rectangle cross-section along ``curve`` (a strap).
 * ``widthAt(u)`` / ``thicknessAt(u)`` allow tapering.
 */
export function strapGeometry(curve, { samples = 220, widthAt, thicknessAt, corner = 0.35, around = 24, frames }) {
  const positions = [];
  const uvs = [];
  const indices = [];
  const point = new THREE.Vector3();
  const side = new THREE.Vector3(1, 0, 0);
  const cross = [];
  // Unit rounded-rectangle cross-section (x across width, y across thickness)
  for (let k = 0; k < around; k++) {
    const a = (k / around) * Math.PI * 2;
    const cx = Math.cos(a);
    const sy = Math.sin(a);
    // superellipse gives flat faces with rounded edges
    const e = 2 / (1 + corner * 8);
    cross.push([Math.sign(cx) * Math.pow(Math.abs(cx), e), Math.sign(sy) * Math.pow(Math.abs(sy), e)]);
  }
  for (let i = 0; i <= samples; i++) {
    const u = i / samples;
    curve.getPointAt(u, point);
    const tangent = curve.getTangentAt(u).normalize();
    const normal = new THREE.Vector3().crossVectors(side, tangent).normalize();
    const w = widthAt(u) / 2;
    const t = thicknessAt(u) / 2;
    for (let k = 0; k <= around; k++) {
      const [cx, cy] = cross[k % around];
      positions.push(point.x + side.x * cx * w + normal.x * cy * t, point.y + side.y * cx * w + normal.y * cy * t, point.z + side.z * cx * w + normal.z * cy * t);
      uvs.push((cx * 0.5 + 0.5) * 1, u * 12);
    }
    if (frames) frames.push({ u, point: point.clone(), tangent, normal, width: w * 2, thickness: t * 2 });
  }
  const ring = around + 1;
  for (let i = 0; i < samples; i++) {
    for (let k = 0; k < around; k++) {
      const a = i * ring + k;
      const b = (i + 1) * ring + k;
      const c = (i + 1) * ring + k + 1;
      const d = i * ring + k + 1;
      indices.push(a, b, d, b, c, d);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

/** Oval bracelet path in the YZ plane from the 12 o'clock lugs around the back to 6 o'clock. */
export function braceletCurve({ lugY = 2.38, lugZ = -0.22, depth = 4.9, bulge = 2.9 } = {}) {
  const pts = [
    [lugY, lugZ],
    [lugY + 0.42, lugZ - 0.62],
    [bulge, -1.95],
    [bulge - 0.3, -3.2],
    [bulge - 1.25, -4.3],
    [0, -depth],
    [-(bulge - 1.25), -4.3],
    [-(bulge - 0.3), -3.2],
    [-bulge, -1.95],
    [-(lugY + 0.42), lugZ - 0.62],
    [-lugY, lugZ],
  ].map(([y, z]) => new THREE.Vector3(0, y, z));
  return new THREE.CatmullRomCurve3(pts, false, "centripetal", 0.5);
}

/** Matrix placing a unit object on ``curve`` at ``u`` (X = width, Y = tangent, Z = outward). */
export function frameOnCurve(curve, u, matrix = new THREE.Matrix4()) {
  const point = curve.getPointAt(u);
  const tangent = curve.getTangentAt(u).normalize();
  const side = new THREE.Vector3(1, 0, 0);
  const normal = new THREE.Vector3().crossVectors(side, tangent).normalize();
  matrix.makeBasis(side, tangent, normal);
  matrix.setPosition(point);
  return matrix;
}
