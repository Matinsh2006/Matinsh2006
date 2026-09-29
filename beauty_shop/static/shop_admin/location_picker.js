/* Admin: pick the store location by clicking on a Leaflet map. */
(function () {
  "use strict";

  const PIN_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>';
  const TEHRAN = [35.6997, 51.338];
  const toLatin = (value) =>
    String(value)
      .replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d))
      .replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d));

  function init() {
    const root = document.querySelector("[data-location-picker]");
    const latInput = document.getElementById("id_latitude");
    const lngInput = document.getElementById("id_longitude");
    const zoomInput = document.getElementById("id_zoom");
    if (!root || !latInput || !lngInput || !window.L) return;

    const L = window.L;
    const readPoint = () => {
      const lat = parseFloat(toLatin(latInput.value));
      const lng = parseFloat(toLatin(lngInput.value));
      return Number.isFinite(lat) && Number.isFinite(lng) ? [lat, lng] : null;
    };
    const initial = readPoint();
    const map = L.map(root.querySelector(".location-picker__map")).setView(
      initial || TEHRAN,
      initial ? parseInt(zoomInput && zoomInput.value, 10) || 16 : 11
    );
    L.tileLayer(root.dataset.tileUrl, { maxZoom: 19, attribution: root.dataset.tileAttribution }).addTo(map);
    const icon = L.divIcon({ className: "map-pin", html: PIN_SVG, iconSize: [40, 40], iconAnchor: [20, 38] });
    const marker = L.marker(initial || TEHRAN, { icon, draggable: true }).addTo(map);

    const setPoint = (latlng, pan) => {
      latInput.value = latlng.lat.toFixed(6);
      lngInput.value = latlng.lng.toFixed(6);
      marker.setLatLng(latlng);
      if (pan) map.panTo(latlng);
    };
    map.on("click", (event) => setPoint(event.latlng, false));
    marker.on("dragend", () => setPoint(marker.getLatLng(), false));
    map.on("zoomend", () => { if (zoomInput) zoomInput.value = map.getZoom(); });
    [latInput, lngInput].forEach((input) =>
      input.addEventListener("change", () => {
        const point = readPoint();
        if (point) {
          marker.setLatLng(point);
          map.setView(point);
        }
      })
    );

    if (navigator.geolocation) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "button location-picker__locate";
      button.textContent = "استفاده از موقعیت فعلی من";
      button.addEventListener("click", () => {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            setPoint(L.latLng(position.coords.latitude, position.coords.longitude), true);
            map.setZoom(17);
          },
          () => window.alert("دسترسی به موقعیت مکانی ممکن نشد.")
        );
      });
      root.appendChild(button);
    }
    setTimeout(() => map.invalidateSize(), 250);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
