// Copies self-hosted fonts and vendor assets from node_modules into /static.
// Everything is served locally so the site works without foreign CDNs.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const nm = (p) => resolve(root, "node_modules", p);
const out = (p) => resolve(root, "static", p);

const files = [
  ["@fontsource-variable/vazirmatn/files/vazirmatn-arabic-wght-normal.woff2", "fonts/vazirmatn-arabic.woff2"],
  ["@fontsource-variable/vazirmatn/files/vazirmatn-latin-wght-normal.woff2", "fonts/vazirmatn-latin.woff2"],
  ["@fontsource-variable/markazi-text/files/markazi-text-arabic-wght-normal.woff2", "fonts/markazi-arabic.woff2"],
  ["@fontsource/cormorant-garamond/files/cormorant-garamond-latin-400-normal.woff2", "fonts/cormorant-400.woff2"],
  ["@fontsource/cormorant-garamond/files/cormorant-garamond-latin-500-normal.woff2", "fonts/cormorant-500.woff2"],
  ["@fontsource/cormorant-garamond/files/cormorant-garamond-latin-600-normal.woff2", "fonts/cormorant-600.woff2"],
  ["@fontsource/cormorant-garamond/files/cormorant-garamond-latin-500-italic.woff2", "fonts/cormorant-500-italic.woff2"],
  ["leaflet/dist/leaflet.css", "vendor/leaflet/leaflet.css"],
  ["leaflet/dist/images/layers.png", "vendor/leaflet/images/layers.png"],
  ["leaflet/dist/images/layers-2x.png", "vendor/leaflet/images/layers-2x.png"],
  ["leaflet/dist/images/marker-icon.png", "vendor/leaflet/images/marker-icon.png"],
  ["leaflet/dist/images/marker-icon-2x.png", "vendor/leaflet/images/marker-icon-2x.png"],
  ["leaflet/dist/images/marker-shadow.png", "vendor/leaflet/images/marker-shadow.png"],
  ["leaflet/dist/leaflet.js", "vendor/leaflet/leaflet.js"],
];

for (const [from, to] of files) {
  mkdirSync(dirname(out(to)), { recursive: true });
  if (/\.(js|css)$/.test(to)) {
    // Drop source map references: the maps are not shipped and Django's
    // manifest storage would fail on the missing files.
    const text = readFileSync(nm(from), "utf8").replace(/\n?\/[/*]# sourceMappingURL=[^\n]*/g, "");
    writeFileSync(out(to), text);
  } else {
    copyFileSync(nm(from), out(to));
  }
  console.log(`copied ${to}`);
}
