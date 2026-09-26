import * as THREE from "three";

export const DIALS = {
  chocolate: { center: "#a4674a", mid: "#58301f", edge: "#190b06", ink: "#f7e1d2" },
  black: { center: "#393a3f", mid: "#141518", edge: "#020203", ink: "#f4f4f4" },
  blue: { center: "#4a74c9", mid: "#1c3478", edge: "#050b22", ink: "#eef3ff" },
  green: { center: "#62845a", mid: "#2b4326", edge: "#081106", ink: "#f0f5e9" },
  silver: { center: "#fdfdfc", mid: "#dfe0e1", edge: "#a2a6aa", ink: "#1b1c1f", light: true },
  champagne: { center: "#fdf0d5", mid: "#e5cc9d", edge: "#a38457", ink: "#3a2a17", light: true },
  white: { center: "#ffffff", mid: "#f2f2f0", edge: "#d2d3d2", ink: "#141414", light: true },
  mop: { center: "#fff9f7", mid: "#f5e7e9", edge: "#dcc6cb", ink: "#3b2a2d", light: true },
  pink: { center: "#fbe0dc", mid: "#ecb9b3", edge: "#b98079", ink: "#3d1f1d", light: true },
};

const METAL_GRADIENTS = {
  rose: ["#ffe7dc", "#eaa78b", "#a15c43"],
  gold: ["#fff5d0", "#e8c16e", "#9f7429"],
  steel: ["#ffffff", "#cdd2d7", "#767d85"],
  black: ["#9b9ba0", "#4c4c51", "#161618"],
  titanium: ["#f2f1ee", "#b3b2ae", "#6c6b68"],
};

const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
export const faDigits = (value) => String(value).replace(/\d/g, (d) => FA_DIGITS[+d]);

export function persianDateParts(date = new Date()) {
  try {
    const day = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { day: "numeric" }).format(date);
    const weekday = new Intl.DateTimeFormat("fa-IR", { weekday: "long" }).format(date);
    const month = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { month: "long" }).format(date);
    return { day, weekday, month };
  } catch {
    return { day: faDigits(date.getDate()), weekday: "", month: "" };
  }
}

function canvas2d(width, height = width) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return [canvas, canvas.getContext("2d")];
}

function toTexture(canvas, { srgb = true, anisotropy = 8 } = {}) {
  const texture = new THREE.CanvasTexture(canvas);
  if (srgb) texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = anisotropy;
  texture.needsUpdate = true;
  return texture;
}

// Deterministic pseudo random so every render of a model looks identical.
function rng(seed = 7) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function drawSpaced(ctx, text, x, y, spacing) {
  const chars = [...text];
  const widths = chars.map((ch) => ctx.measureText(ch).width);
  const total = widths.reduce((a, b) => a + b, 0) + spacing * (chars.length - 1);
  let cursor = x - total / 2;
  const align = ctx.textAlign;
  ctx.textAlign = "left";
  chars.forEach((ch, i) => {
    ctx.fillText(ch, cursor, y);
    cursor += widths[i] + spacing;
  });
  ctx.textAlign = align;
}

function metalFill(ctx, metal, y0, y1) {
  const stops = METAL_GRADIENTS[metal] || METAL_GRADIENTS.rose;
  const gradient = ctx.createLinearGradient(0, y0, 0, y1);
  gradient.addColorStop(0, stops[0]);
  gradient.addColorStop(0.5, stops[1]);
  gradient.addColorStop(1, stops[2]);
  return gradient;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawSunburst(ctx, c, R, palette, seed) {
  const random = rng(seed);
  const rays = 1100;
  for (let i = 0; i < rays; i++) {
    const a0 = (i / rays) * Math.PI * 2;
    const a1 = ((i + 1.2) / rays) * Math.PI * 2;
    const alpha = 0.012 + random() * 0.05;
    ctx.fillStyle = i % 2 ? `rgba(255,255,255,${alpha})` : `rgba(0,0,0,${alpha * 1.3})`;
    ctx.beginPath();
    ctx.moveTo(c, c);
    ctx.arc(c, c, R, a0, a1);
    ctx.closePath();
    ctx.fill();
  }
  // The characteristic "bow tie" of a sunburst dial under a key light.
  if (ctx.createConicGradient) {
    const lobes = ctx.createConicGradient(-Math.PI / 3.2, c, c);
    const hi = palette.light ? 0.18 : 0.16;
    const lo = palette.light ? 0.1 : 0.22;
    lobes.addColorStop(0, `rgba(255,255,255,${hi})`);
    lobes.addColorStop(0.22, `rgba(0,0,0,${lo})`);
    lobes.addColorStop(0.5, `rgba(255,255,255,${hi})`);
    lobes.addColorStop(0.72, `rgba(0,0,0,${lo})`);
    lobes.addColorStop(1, `rgba(255,255,255,${hi})`);
    ctx.fillStyle = lobes;
    ctx.beginPath();
    ctx.arc(c, c, R, 0, Math.PI * 2);
    ctx.fill();
  }
  // Soft vignette towards the rim.
  const vignette = ctx.createRadialGradient(c, c, R * 0.55, c, c, R);
  vignette.addColorStop(0, "rgba(0,0,0,0)");
  vignette.addColorStop(1, `rgba(0,0,0,${palette.light ? 0.12 : 0.35})`);
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, c * 2, c * 2);
}

function drawMotherOfPearl(ctx, c, R, seed) {
  const random = rng(seed);
  const tints = ["255,214,226", "214,236,255", "219,255,232", "255,240,214", "236,220,255"];
  for (let i = 0; i < 90; i++) {
    const x = c + (random() - 0.5) * R * 2;
    const y = c + (random() - 0.5) * R * 2;
    const r = R * (0.08 + random() * 0.35);
    const blob = ctx.createRadialGradient(x, y, 0, x, y, r);
    blob.addColorStop(0, `rgba(${tints[i % tints.length]},${0.18 + random() * 0.2})`);
    blob.addColorStop(1, `rgba(${tints[i % tints.length]},0)`);
    ctx.fillStyle = blob;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  for (let i = 0; i < 260; i++) {
    ctx.strokeStyle = `rgba(255,255,255,${0.05 + random() * 0.08})`;
    ctx.lineWidth = 1 + random() * 3;
    ctx.beginPath();
    const y = c + (random() - 0.5) * R * 2;
    ctx.moveTo(c - R, y);
    ctx.bezierCurveTo(c - R / 2, y + (random() - 0.5) * 60, c + R / 2, y + (random() - 0.5) * 60, c + R, y);
    ctx.stroke();
  }
}

function drawMinuteTrack(ctx, c, R, ink, { outer = 0.965, major = 0.91, minor = 0.935, scale = 1 } = {}) {
  ctx.save();
  ctx.strokeStyle = ink;
  ctx.lineCap = "round";
  for (let i = 0; i < 60; i++) {
    const a = (i / 60) * Math.PI * 2 - Math.PI / 2;
    const isHour = i % 5 === 0;
    const r0 = R * outer;
    const r1 = R * (isHour ? major : minor);
    ctx.globalAlpha = isHour ? 0.95 : 0.6;
    ctx.lineWidth = (isHour ? R * 0.009 : R * 0.0045) * scale;
    ctx.beginPath();
    ctx.moveTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0);
    ctx.lineTo(c + Math.cos(a) * r1, c + Math.sin(a) * r1);
    ctx.stroke();
  }
  ctx.restore();
}

function drawWindow(ctx, x, y, w, h, text, font, metal) {
  ctx.save();
  // Frame
  ctx.fillStyle = metalFill(ctx, metal, y - h / 2, y + h / 2);
  roundRect(ctx, x - w / 2 - h * 0.09, y - h / 2 - h * 0.09, w + h * 0.18, h * 1.18, h * 0.16);
  ctx.shadowColor = "rgba(0,0,0,0.5)";
  ctx.shadowBlur = h * 0.12;
  ctx.shadowOffsetY = h * 0.05;
  ctx.fill();
  ctx.shadowColor = "transparent";
  // Disc
  const paper = ctx.createLinearGradient(0, y - h / 2, 0, y + h / 2);
  paper.addColorStop(0, "#e9e6df");
  paper.addColorStop(0.35, "#fbfaf6");
  paper.addColorStop(1, "#f0ede6");
  ctx.fillStyle = paper;
  roundRect(ctx, x - w / 2, y - h / 2, w, h, h * 0.1);
  ctx.fill();
  ctx.fillStyle = "#15120f";
  ctx.font = font;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.direction = "rtl";
  ctx.fillText(text, x, y + h * 0.04);
  ctx.restore();
}

function drawAppliedText(ctx, text, x, y, font, metal, size, onLightDial = false) {
  ctx.save();
  ctx.font = font;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.direction = "rtl";
  ctx.shadowColor = onLightDial ? "rgba(0,0,0,0.35)" : "rgba(0,0,0,0.6)";
  ctx.shadowBlur = size * 0.1;
  ctx.shadowOffsetY = size * 0.05;
  if (onLightDial) {
    // Darker, polished-looking numerals stay legible on silver/white dials.
    const stops = METAL_GRADIENTS[metal] || METAL_GRADIENTS.rose;
    const gradient = ctx.createLinearGradient(0, y - size * 0.5, 0, y + size * 0.5);
    gradient.addColorStop(0, stops[2]);
    gradient.addColorStop(0.5, "#2b2118");
    gradient.addColorStop(1, stops[2]);
    ctx.fillStyle = gradient;
  } else {
    ctx.fillStyle = metalFill(ctx, metal, y - size * 0.5, y + size * 0.5);
  }
  ctx.fillText(text, x, y);
  ctx.shadowColor = "transparent";
  ctx.lineWidth = Math.max(1, size * 0.012);
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.strokeText(text, x, y - size * 0.01);
  ctx.restore();
}

const ROMAN = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"];

function drawSubdial(ctx, x, y, r, ink, palette, labels) {
  ctx.save();
  const recess = ctx.createRadialGradient(x, y - r * 0.2, r * 0.1, x, y, r);
  recess.addColorStop(0, palette.light ? "rgba(0,0,0,0.04)" : "rgba(255,255,255,0.06)");
  recess.addColorStop(1, palette.light ? "rgba(0,0,0,0.14)" : "rgba(0,0,0,0.35)");
  ctx.fillStyle = recess;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fill();
  // Snailing (concentric grooves)
  for (let i = 4; i < r; i += 3) {
    ctx.strokeStyle = `rgba(255,255,255,${palette.light ? 0.05 : 0.035})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(x, y, i, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.strokeStyle = ink;
  for (let i = 0; i < 30; i++) {
    const a = (i / 30) * Math.PI * 2 - Math.PI / 2;
    const long = i % 5 === 0;
    ctx.globalAlpha = long ? 0.95 : 0.55;
    ctx.lineWidth = long ? r * 0.035 : r * 0.018;
    ctx.beginPath();
    ctx.moveTo(x + Math.cos(a) * r * 0.93, y + Math.sin(a) * r * 0.93);
    ctx.lineTo(x + Math.cos(a) * r * (long ? 0.76 : 0.84), y + Math.sin(a) * r * (long ? 0.76 : 0.84));
    ctx.stroke();
  }
  ctx.globalAlpha = 0.9;
  ctx.fillStyle = ink;
  ctx.font = `600 ${r * 0.24}px Vazirmatn, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  labels.forEach((label, i) => {
    const a = (i / labels.length) * Math.PI * 2 - Math.PI / 2;
    ctx.fillText(label, x + Math.cos(a) * r * 0.55, y + Math.sin(a) * r * 0.55);
  });
  ctx.restore();
}

/**
 * Draws a complete watch dial. Hands and 3D applied markers are separate
 * meshes; everything else (print, numerals, windows) lives in this texture.
 */
export function createDialTexture(options = {}) {
  const {
    dial = "chocolate",
    metal = "rose",
    style = "presidential",
    numerals = "persian",
    size = 2048,
    brand = "SANIYEH",
    brandFa = "ثانیه",
    origin = "TEHRAN",
    date = new Date(),
    seed = 11,
  } = options;
  const palette = DIALS[dial] || DIALS.chocolate;
  const [canvas, ctx] = canvas2d(size);
  const c = size / 2;
  const R = size / 2;
  const ink = palette.ink;

  const base = ctx.createRadialGradient(c, c * 0.9, 0, c, c, R);
  base.addColorStop(0, palette.center);
  base.addColorStop(0.58, palette.mid);
  base.addColorStop(1, palette.edge);
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, size, size);

  if (dial === "mop") drawMotherOfPearl(ctx, c, R, seed);
  else drawSunburst(ctx, c, R, palette, seed);

  const { day, weekday } = persianDateParts(date);
  const printColor = ink;

  if (style === "diver") {
    drawMinuteTrack(ctx, c, R, printColor, { outer: 0.97, major: 0.93, minor: 0.945, scale: 1.2 });
  } else {
    drawMinuteTrack(ctx, c, R, printColor);
  }

  // Numerals printed/applied in the texture
  if (numerals === "persian" || numerals === "roman") {
    const skip = new Set(style === "presidential" ? [0, 3] : style === "chrono" ? [3, 6, 9] : [3]);
    const radius = R * (numerals === "roman" ? 0.74 : 0.755);
    for (let hour = 0; hour < 12; hour++) {
      if (skip.has(hour)) continue;
      const a = (hour / 12) * Math.PI * 2 - Math.PI / 2;
      const x = c + Math.cos(a) * radius;
      const y = c + Math.sin(a) * radius;
      if (numerals === "roman") {
        const fontSize = R * 0.13;
        drawAppliedText(ctx, ROMAN[hour], x, y, `600 ${fontSize}px "Cormorant Garamond", serif`, metal, fontSize, palette.light);
      } else {
        const fontSize = R * 0.19;
        const label = faDigits(hour === 0 ? 12 : hour);
        drawAppliedText(ctx, label, x, y + fontSize * 0.08, `600 ${fontSize}px "Markazi Text", serif`, metal, fontSize, palette.light);
      }
    }
  }

  if (style === "chrono") {
    const sr = R * 0.2;
    drawSubdial(ctx, c + R * 0.44, c, sr, printColor, palette, ["۳۰", "۱۰", "۲۰"]);
    drawSubdial(ctx, c - R * 0.44, c, sr, printColor, palette, ["۶۰", "۲۰", "۴۰"]);
    drawSubdial(ctx, c, c + R * 0.44, sr, printColor, palette, ["۱۲", "۴", "۸"]);
  }

  // Windows
  const windowFont = (px, weight = 700) => `${weight} ${px}px Vazirmatn, sans-serif`;
  if (style === "presidential") {
    drawWindow(ctx, c, c - R * 0.64, R * 0.46, R * 0.15, weekday, windowFont(R * 0.085, 600), metal);
    drawWindow(ctx, c + R * 0.74, c, R * 0.2, R * 0.15, day, windowFont(R * 0.11), metal);
  } else if (style === "diver" || style === "classic") {
    drawWindow(ctx, c + R * 0.72, c, R * 0.18, R * 0.14, day, windowFont(R * 0.1), metal);
  }

  // Brand print
  ctx.save();
  ctx.fillStyle = printColor;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const brandY = style === "presidential" ? c - R * 0.36 : c - R * 0.42;
  const markSize = R * 0.075;
  ctx.font = `600 ${markSize}px "Cormorant Garamond", serif`;
  drawSpaced(ctx, brand.toUpperCase(), c, brandY, markSize * 0.28);
  ctx.globalAlpha = 0.85;
  ctx.font = `500 ${R * 0.032}px "Cormorant Garamond", serif`;
  const subline = { diver: "DIVER · 300 M", chrono: "CHRONOGRAPH", classic: "AUTOMATIC", presidential: "AUTOMATIC CHRONOMETER" }[style] || "AUTOMATIC";
  drawSpaced(ctx, subline, c, brandY + R * 0.085, R * 0.012);
  if (style !== "chrono") {
    ctx.globalAlpha = 0.9;
    ctx.direction = "rtl";
    ctx.font = `600 ${R * 0.085}px "Markazi Text", serif`;
    ctx.fillText(brandFa, c, c + R * (style === "diver" ? 0.4 : 0.36));
    ctx.globalAlpha = 0.6;
    ctx.font = `500 ${R * 0.03}px "Cormorant Garamond", serif`;
    drawSpaced(ctx, origin.toUpperCase(), c, c + R * (style === "diver" ? 0.49 : 0.45), R * 0.018);
  }
  ctx.restore();

  const texture = toTexture(canvas);
  texture.userData = { day, weekday };
  return texture;
}

export function createRadialAnisotropyTexture(size = 512) {
  // Encodes a radial brushing direction for the sunburst dial.
  const [canvas, ctx] = canvas2d(size);
  const image = ctx.createImageData(size, size);
  const c = size / 2;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = x - c;
      const dy = c - y;
      const len = Math.hypot(dx, dy) || 1;
      // Tangential direction reads as radial streaks.
      const tx = -dy / len;
      const ty = dx / len;
      const i = (y * size + x) * 4;
      image.data[i] = (tx * 0.5 + 0.5) * 255;
      image.data[i + 1] = (ty * 0.5 + 0.5) * 255;
      image.data[i + 2] = 255;
      image.data[i + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
  const texture = toTexture(canvas, { srgb: false });
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

export function createPerlageTexture(size = 1024) {
  const [canvas, ctx] = canvas2d(size);
  ctx.fillStyle = "#b9b2a6";
  ctx.fillRect(0, 0, size, size);
  const step = size / 26;
  const r = step * 0.78;
  for (let row = -1; row < 28; row++) {
    for (let col = -1; col < 28; col++) {
      const x = col * step + (row % 2 ? step / 2 : 0);
      const y = row * step * 0.88;
      const g = ctx.createRadialGradient(x - r * 0.2, y - r * 0.2, r * 0.05, x, y, r);
      g.addColorStop(0, "#f1ece3");
      g.addColorStop(0.55, "#c9c1b4");
      g.addColorStop(1, "#8f887d");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  const texture = toTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

export function createCotesTexture(size = 1024, tint = "#e7c9a0") {
  const [canvas, ctx] = canvas2d(size);
  ctx.fillStyle = tint;
  ctx.fillRect(0, 0, size, size);
  ctx.save();
  ctx.translate(size / 2, size / 2);
  ctx.rotate(-Math.PI / 5);
  const stripe = size / 9;
  for (let x = -size; x < size; x += stripe) {
    const g = ctx.createLinearGradient(x, 0, x + stripe, 0);
    g.addColorStop(0, "rgba(0,0,0,0.22)");
    g.addColorStop(0.45, "rgba(255,255,255,0.28)");
    g.addColorStop(0.55, "rgba(255,255,255,0.32)");
    g.addColorStop(1, "rgba(0,0,0,0.22)");
    ctx.fillStyle = g;
    ctx.fillRect(x, -size, stripe, size * 2);
  }
  ctx.restore();
  return toTexture(canvas);
}

export function createInsertTexture({ kind = "diver", color = "#0c0d10", ink = "#e9e6dd", size = 1024 } = {}) {
  const [canvas, ctx] = canvas2d(size);
  const c = size / 2;
  const R = size / 2;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(c, c, R, 0, Math.PI * 2);
  ctx.fill();
  const sheen = ctx.createLinearGradient(0, 0, size, size);
  sheen.addColorStop(0, "rgba(255,255,255,0.08)");
  sheen.addColorStop(0.5, "rgba(255,255,255,0)");
  sheen.addColorStop(1, "rgba(255,255,255,0.05)");
  ctx.fillStyle = sheen;
  ctx.fill();
  ctx.fillStyle = ink;
  ctx.strokeStyle = ink;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const inner = 0.83;
  const mid = (1 + inner) / 2;
  if (kind === "diver") {
    for (let i = 0; i < 60; i++) {
      const a = (i / 60) * Math.PI * 2 - Math.PI / 2;
      if (i === 0) continue;
      if (i % 10 === 0) {
        ctx.save();
        ctx.translate(c + Math.cos(a) * R * mid, c + Math.sin(a) * R * mid);
        ctx.rotate(a + Math.PI / 2);
        ctx.font = `700 ${R * 0.085}px Vazirmatn, sans-serif`;
        ctx.fillText(String(i), 0, R * 0.005);
        ctx.restore();
      } else if (i < 15 || i % 5 === 0) {
        ctx.lineWidth = i % 5 === 0 ? R * 0.018 : R * 0.008;
        const r0 = R * (i % 5 === 0 ? 0.87 : 0.9);
        ctx.beginPath();
        ctx.moveTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0);
        ctx.lineTo(c + Math.cos(a) * R * 0.97, c + Math.sin(a) * R * 0.97);
        ctx.stroke();
      }
    }
    // Lume triangle at 12
    ctx.save();
    ctx.translate(c, c - R * mid);
    ctx.fillStyle = "#f3f0e2";
    ctx.beginPath();
    ctx.moveTo(-R * 0.05, -R * 0.05);
    ctx.lineTo(R * 0.05, -R * 0.05);
    ctx.lineTo(0, R * 0.055);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  } else {
    // Tachymeter scale
    const speeds = [500, 400, 300, 250, 200, 180, 160, 140, 120, 110, 100, 90, 80, 75, 70, 65, 60];
    ctx.font = `600 ${R * 0.05}px Vazirmatn, sans-serif`;
    speeds.forEach((speed) => {
      const seconds = 3600 / speed;
      const a = (seconds / 60) * Math.PI * 2 - Math.PI / 2;
      ctx.save();
      ctx.translate(c + Math.cos(a) * R * 0.895, c + Math.sin(a) * R * 0.895);
      ctx.rotate(a + Math.PI / 2);
      ctx.fillText(String(speed), 0, 0);
      ctx.restore();
    });
    ctx.save();
    ctx.translate(c, c - R * 0.9);
    ctx.font = `700 ${R * 0.04}px Vazirmatn, sans-serif`;
    ctx.fillText("TACHYMETRE", 0, 0);
    ctx.restore();
  }
  return toTexture(canvas);
}

export function createCasebackTexture({ brand = "SANIYEH", metal = "steel", size = 1024 } = {}) {
  const [canvas, ctx] = canvas2d(size);
  const c = size / 2;
  const stops = METAL_GRADIENTS[metal] || METAL_GRADIENTS.steel;
  ctx.fillStyle = stops[1];
  ctx.fillRect(0, 0, size, size);
  for (let r = 8; r < c; r += 3) {
    ctx.strokeStyle = `rgba(${r % 2 ? "255,255,255" : "0,0,0"},0.06)`;
    ctx.beginPath();
    ctx.arc(c, c, r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(40,30,25,0.55)";
  ctx.font = `600 ${size * 0.032}px "Cormorant Garamond", serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const text = `${brand.toUpperCase()} · SAPPHIRE CRYSTAL · WATER RESISTANT 100 M · `;
  const chars = [...text];
  chars.forEach((ch, i) => {
    const a = (i / chars.length) * Math.PI * 2 - Math.PI / 2;
    ctx.save();
    ctx.translate(c + Math.cos(a) * size * 0.4, c + Math.sin(a) * size * 0.4);
    ctx.rotate(a + Math.PI / 2);
    ctx.fillText(ch, 0, 0);
    ctx.restore();
  });
  return toTexture(canvas);
}

export function createStrapTexture({ kind = "leather", color = "#5a3322", size = 512, seed = 3 } = {}) {
  const [canvas, ctx] = canvas2d(size);
  const random = rng(seed);
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, size, size);
  if (kind === "leather") {
    for (let i = 0; i < 5000; i++) {
      const x = random() * size;
      const y = random() * size;
      const r = 0.5 + random() * 2.2;
      ctx.fillStyle = random() > 0.5 ? "rgba(0,0,0,0.12)" : "rgba(255,255,255,0.05)";
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
  } else if (kind === "mesh") {
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, size, size);
    const step = size / 48;
    for (let y = 0; y < size + step; y += step) {
      for (let x = 0; x < size + step; x += step) {
        const g = ctx.createLinearGradient(x, y, x + step, y + step);
        g.addColorStop(0, "#ffffff");
        g.addColorStop(1, "#555555");
        ctx.fillStyle = g;
        ctx.fillRect(x + 1, y + 1, step * 0.9, step * 0.45);
      }
    }
  } else if (kind === "rubber") {
    for (let y = 0; y < size; y += size / 32) {
      ctx.fillStyle = "rgba(255,255,255,0.05)";
      ctx.fillRect(0, y, size, size / 96);
    }
  }
  const texture = toTexture(canvas, { srgb: kind !== "mesh" });
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

export function createSmartScreenTexture({ date = new Date(), accent = "#ff7a59", width = 800, height = 1000 } = {}) {
  const [canvas, ctx] = canvas2d(width, height);
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, width, height);
  const { day, weekday, month } = persianDateParts(date);
  ctx.direction = "rtl";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = accent;
  ctx.font = `600 ${width * 0.07}px Vazirmatn, sans-serif`;
  ctx.fillText(`${weekday} ${day} ${month}`, width / 2, height * 0.15);
  ctx.fillStyle = "#ffffff";
  ctx.font = `300 ${width * 0.34}px Vazirmatn, sans-serif`;
  ctx.direction = "ltr";
  ctx.fillText(faDigits("10:09"), width / 2, height * 0.38);
  // Activity rings
  const rings = [
    ["#ff375f", 0.78],
    ["#a4f94c", 0.62],
    ["#34d8ef", 0.9],
  ];
  const cx = width * 0.3;
  const cy = height * 0.74;
  rings.forEach(([color, value], i) => {
    const r = width * (0.17 - i * 0.045);
    ctx.lineCap = "round";
    ctx.lineWidth = width * 0.035;
    ctx.strokeStyle = color + "33";
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * value);
    ctx.stroke();
  });
  ctx.direction = "rtl";
  ctx.fillStyle = "#ff375f";
  ctx.font = `700 ${width * 0.1}px Vazirmatn, sans-serif`;
  ctx.fillText(faDigits("72"), width * 0.72, height * 0.68);
  ctx.fillStyle = "#9a9a9a";
  ctx.font = `500 ${width * 0.05}px Vazirmatn, sans-serif`;
  ctx.fillText("ضربان قلب", width * 0.72, height * 0.78);
  ctx.fillStyle = "#34d8ef";
  ctx.font = `600 ${width * 0.06}px Vazirmatn, sans-serif`;
  ctx.fillText(`${faDigits("8")}٬${faDigits("420")} قدم`, width * 0.72, height * 0.88);
  return toTexture(canvas);
}
