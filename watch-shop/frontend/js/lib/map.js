// Store location map (Leaflet + OpenStreetMap tiles by default), loaded only
// when the map scrolls near the viewport.
let leafletPromise = null;

function loadLeaflet(base) {
  if (window.L) return Promise.resolve(window.L);
  if (leafletPromise) return leafletPromise;
  leafletPromise = new Promise((resolve, reject) => {
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = `${base}leaflet.css`;
    document.head.append(css);
    const script = document.createElement("script");
    script.src = `${base}leaflet.js`;
    script.onload = () => resolve(window.L);
    script.onerror = reject;
    document.head.append(script);
  });
  return leafletPromise;
}

function drawMap(element, L) {
  const stores = JSON.parse(element.dataset.stores || "[]");
  if (!stores.length) return;
  const map = L.map(element, { scrollWheelZoom: false, zoomControl: true, attributionControl: true });
  L.tileLayer(element.dataset.tiles, { attribution: element.dataset.attribution, maxZoom: 19 }).addTo(map);
  const icon = L.divIcon({ className: "", html: '<div class="map-pin"></div>', iconSize: [22, 22], iconAnchor: [11, 11] });
  const markers = stores.map((store) => {
    const marker = L.marker([store.lat, store.lng], { icon, title: store.name }).addTo(map);
    const popup = document.createElement("div");
    popup.dir = "rtl";
    popup.style.fontFamily = "Vazirmatn, sans-serif";
    const title = document.createElement("strong");
    title.textContent = store.name;
    const address = document.createElement("p");
    address.style.margin = "4px 0 0";
    address.textContent = store.address;
    popup.append(title, address);
    marker.bindPopup(popup);
    return marker;
  });
  if (markers.length === 1) {
    map.setView([stores[0].lat, stores[0].lng], stores[0].zoom || 16);
  } else {
    map.fitBounds(L.featureGroup(markers).getBounds().pad(0.3));
  }
  element.addEventListener("click", () => map.scrollWheelZoom.enable(), { once: true });
  document.querySelectorAll("[data-map-focus]").forEach((button) =>
    button.addEventListener("click", () => {
      const store = stores[parseInt(button.dataset.mapFocus, 10)];
      if (store) map.flyTo([store.lat, store.lng], store.zoom || 16, { duration: 1.2 });
    })
  );
}

export function initMaps() {
  const maps = document.querySelectorAll("[data-map]");
  if (!maps.length) return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(async (entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        try {
          const L = await loadLeaflet(entry.target.dataset.leaflet);
          drawMap(entry.target, L);
        } catch {
          entry.target.classList.add("map-failed");
        }
      });
    },
    { rootMargin: "400px 0px" }
  );
  maps.forEach((map) => observer.observe(map));
}
