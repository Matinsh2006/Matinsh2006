// Manual-scroll image tracks: native swipe + scroll-snap on touch, drag with
// the mouse, arrows, dots, thumbnails and keyboard. Works in RTL.
import { isRTL } from "./utils.js";

function edgeDelta(track, slide) {
  const trackRect = track.getBoundingClientRect();
  const rect = slide.getBoundingClientRect();
  return isRTL() ? rect.right - trackRect.right : rect.left - trackRect.left;
}

function nearestIndex(track, slides) {
  let best = 0;
  let bestDistance = Infinity;
  slides.forEach((slide, i) => {
    const distance = Math.abs(edgeDelta(track, slide));
    if (distance < bestDistance) {
      bestDistance = distance;
      best = i;
    }
  });
  return best;
}

function setupTrack(track) {
  if (track.dataset.trackReady) return;
  track.dataset.trackReady = "1";
  const host = track.closest("[data-carousel]") || track.parentElement;
  const slides = [...track.children];
  if (!slides.length) return;

  const prev = host.querySelector("[data-prev]");
  const next = host.querySelector("[data-next]");
  const dotsHost = host.querySelector("[data-dots]");
  const thumbs = [...host.querySelectorAll("[data-thumb]")];
  const counter = host.querySelector("[data-counter]");
  let index = 0;

  const dots = [];
  if (dotsHost && slides.length > 1) {
    slides.forEach((_, i) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.setAttribute("aria-label", `تصویر ${i + 1}`);
      dot.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        go(i);
      });
      dotsHost.append(dot);
      dots.push(dot);
    });
  }

  function sync() {
    dots.forEach((dot, i) => dot.setAttribute("aria-current", String(i === index)));
    thumbs.forEach((thumb, i) => thumb.setAttribute("aria-current", String(i === index)));
    if (prev) prev.disabled = index === 0;
    if (next) next.disabled = index >= slides.length - 1;
    if (counter) counter.textContent = `${(index + 1).toLocaleString("fa-IR")} / ${slides.length.toLocaleString("fa-IR")}`;
  }

  function go(i, behavior = "smooth") {
    index = Math.max(0, Math.min(slides.length - 1, i));
    track.scrollBy({ left: edgeDelta(track, slides[index]), behavior });
    sync();
  }

  let settleTimer = 0;
  track.addEventListener(
    "scroll",
    () => {
      clearTimeout(settleTimer);
      settleTimer = setTimeout(() => {
        index = nearestIndex(track, slides);
        sync();
      }, 90);
    },
    { passive: true }
  );

  prev?.addEventListener("click", (e) => {
    e.preventDefault();
    go(index - 1);
  });
  next?.addEventListener("click", (e) => {
    e.preventDefault();
    go(index + 1);
  });
  thumbs.forEach((thumb, i) =>
    thumb.addEventListener("click", (e) => {
      e.preventDefault();
      go(i);
    })
  );

  track.addEventListener("keydown", (event) => {
    const forward = isRTL() ? "ArrowLeft" : "ArrowRight";
    const backward = isRTL() ? "ArrowRight" : "ArrowLeft";
    if (event.key === forward) {
      event.preventDefault();
      go(index + 1);
    } else if (event.key === backward) {
      event.preventDefault();
      go(index - 1);
    }
  });

  // Mouse drag
  let startX = 0;
  let startScroll = 0;
  let pressed = false;
  let moved = false;
  track.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    // Nested tracks (a card's photos inside a product rail): innermost wins.
    if (event.target.closest("[data-track]") !== track) return;
    pressed = true;
    moved = false;
    startX = event.clientX;
    startScroll = track.scrollLeft;
  });
  window.addEventListener("pointermove", (event) => {
    if (!pressed) return;
    const dx = event.clientX - startX;
    if (!moved && Math.abs(dx) > 6) {
      moved = true;
      track.classList.add("is-dragging");
    }
    if (moved) track.scrollLeft = startScroll - dx;
  });
  window.addEventListener("pointerup", () => {
    if (!pressed) return;
    pressed = false;
    if (moved) {
      track.classList.remove("is-dragging");
      go(nearestIndex(track, slides));
      setTimeout(() => (moved = false), 0);
    }
  });
  track.addEventListener(
    "click",
    (event) => {
      if (moved) {
        event.preventDefault();
        event.stopPropagation();
      }
    },
    true
  );
  track.addEventListener("dragstart", (event) => event.preventDefault());

  sync();
  track._goTo = go;
}

export function initTracks(root = document) {
  root.querySelectorAll("[data-track]").forEach(setupTrack);
}

/** Full-screen viewer for product photos. */
export function initLightbox() {
  const box = document.querySelector("[data-lightbox]");
  if (!box) return;
  const track = box.querySelector("[data-track]");
  const open = (i) => {
    box.classList.add("is-open");
    box.setAttribute("aria-hidden", "false");
    document.documentElement.classList.add("overflow-hidden");
    requestAnimationFrame(() => track?._goTo?.(i, "instant"));
  };
  const close = () => {
    box.classList.remove("is-open");
    box.setAttribute("aria-hidden", "true");
    document.documentElement.classList.remove("overflow-hidden");
  };
  document.querySelectorAll("[data-lightbox-open]").forEach((trigger) => {
    trigger.addEventListener("click", () => open(parseInt(trigger.dataset.lightboxOpen, 10) || 0));
  });
  box.querySelectorAll("[data-lightbox-close]").forEach((b) => b.addEventListener("click", close));
  document.addEventListener("keydown", (e) => e.key === "Escape" && box.classList.contains("is-open") && close());
}
