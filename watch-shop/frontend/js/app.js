import Lenis from "lenis";
import { initCart } from "./lib/cart.js";
import { initCardGlow, initCopy, initFilters, initLoadMore, initOtp, initQuantity } from "./lib/forms.js";
import { initHeader, initHeaderBanner } from "./lib/header.js";
import { initMaps } from "./lib/map.js";
import { initMarquees } from "./lib/marquee.js";
import { initScroll } from "./lib/scroll.js";
import { initLightbox, initTracks } from "./lib/tracks.js";
import { dismissLater, prefersReducedMotion } from "./lib/utils.js";

function initSmoothScroll() {
  if (prefersReducedMotion()) return null;
  const lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 0.95, smoothWheel: true });
  const raf = (time) => {
    lenis.raf(time);
    requestAnimationFrame(raf);
  };
  requestAnimationFrame(raf);
  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href^="#"]');
    if (!link || link.getAttribute("href").length < 2) return;
    const target = document.querySelector(link.getAttribute("href"));
    if (!target) return;
    event.preventDefault();
    lenis.scrollTo(target, { offset: -90, duration: 1.4 });
  });
  window.lenis = lenis;
  return lenis;
}

function boot() {
  const lenis = initSmoothScroll();
  initHeaderBanner();
  initHeader({ lenis });
  const scroll = initScroll({ lenis });
  initTracks();
  initLightbox();
  initCardGlow();
  initCart({
    lenis,
    onUpdate: (root) => {
      initTracks(root);
    },
  });
  initOtp();
  initQuantity();
  initFilters();
  initLoadMore((grid) => {
    initTracks(grid);
    initCardGlow(grid);
    scroll.observeReveals(grid);
  });
  initMaps();
  initMarquees({ lenis });
  initCopy();
  document.querySelectorAll("[data-toast]").forEach((toast) => dismissLater(toast, parseInt(toast.dataset.duration, 10) || 5200));
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
