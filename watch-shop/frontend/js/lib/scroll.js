import { clamp01, formatNumber, smoothstep } from "./utils.js";

/** Wraps every word of an element in spans so it can rise in word by word.
 * Persian words are never split into letters, keeping the letter joining intact. */
export function splitWords(element) {
  if (element.dataset.splitReady) return;
  element.dataset.splitReady = "1";
  let index = 0;
  const walk = (node) => {
    [...node.childNodes].forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        const parts = child.textContent.split(/(\s+)/);
        const fragment = document.createDocumentFragment();
        parts.forEach((part) => {
          if (!part) return;
          if (/^\s+$/.test(part)) {
            fragment.append(document.createTextNode(" "));
            return;
          }
          const outer = document.createElement("span");
          outer.className = "split-word";
          const inner = document.createElement("span");
          inner.textContent = part;
          inner.style.setProperty("--i", index++);
          outer.append(inner);
          fragment.append(outer);
        });
        child.replaceWith(fragment);
      } else if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== "BR") {
        walk(child);
      }
    });
  };
  walk(element);
}

function prepareHighlight(element) {
  const words = [];
  const walk = (node) => {
    [...node.childNodes].forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        const fragment = document.createDocumentFragment();
        child.textContent.split(/(\s+)/).forEach((part) => {
          if (!part) return;
          if (/^\s+$/.test(part)) return fragment.append(document.createTextNode(" "));
          const span = document.createElement("span");
          span.className = "hl-word";
          span.textContent = part;
          words.push(span);
          fragment.append(span);
        });
        child.replaceWith(fragment);
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        walk(child);
      }
    });
  };
  walk(element);
  return { element, words };
}

function parseBeat(element) {
  return {
    element,
    from: parseFloat(element.dataset.from || "0"),
    to: parseFloat(element.dataset.to || "1"),
    fade: parseFloat(element.dataset.fade || "0.05"),
    last: -1,
  };
}

function applyBeat(beat, p) {
  const fadeIn = beat.from <= 0 ? 1 : smoothstep(beat.from, beat.from + beat.fade, p);
  const fadeOut = beat.to >= 1 ? 1 : 1 - smoothstep(beat.to - beat.fade, beat.to, p);
  const opacity = Math.min(fadeIn, fadeOut);
  if (Math.abs(opacity - beat.last) < 0.001) return;
  beat.last = opacity;
  const shift = (1 - fadeIn) * 36 - (1 - fadeOut) * 36;
  beat.element.style.opacity = opacity.toFixed(3);
  beat.element.style.visibility = opacity > 0.01 ? "visible" : "hidden";
  beat.element.style.transform = `translate3d(0, ${shift.toFixed(1)}px, 0)`;
  beat.element.classList.toggle("is-visible", opacity > 0.4);
}

function animateCounter(element) {
  const target = parseFloat(element.dataset.countTo);
  const duration = 1800;
  const start = performance.now();
  const step = (now) => {
    const t = clamp01((now - start) / duration);
    const eased = 1 - Math.pow(2, -10 * t);
    element.textContent = formatNumber(target * (t >= 1 ? 1 : eased));
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

export function initScroll({ lenis } = {}) {
  const reveal = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-visible");
        if (entry.target.dataset.countTo) animateCounter(entry.target);
        reveal.unobserve(entry.target);
      }
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.1 }
  );

  const observeReveals = (root = document) => {
    root.querySelectorAll("[data-split]").forEach(splitWords);
    root.querySelectorAll("[data-reveal], [data-split], [data-count-to]").forEach((el) => {
      if (!el.closest("[data-beat]")) reveal.observe(el);
    });
  };
  observeReveals();

  const scenes = [...document.querySelectorAll("[data-scene]")].map((element) => ({
    element,
    beats: [...element.querySelectorAll("[data-beat]")].map(parseBeat),
    bars: [...element.querySelectorAll("[data-scene-bar]")],
    active: true,
    p: -1,
  }));
  const hscrolls = [...document.querySelectorAll("[data-hscroll]")].map((element) => ({
    element,
    track: element.querySelector("[data-hscroll-track]"),
    active: true,
  }));
  const parallax = [...document.querySelectorAll("[data-parallax]")].map((element) => ({
    element,
    speed: parseFloat(element.dataset.parallax) || 0.12,
  }));
  const highlights = [...document.querySelectorAll("[data-highlight]")].map(prepareHighlight);

  const visibility = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const item = scenes.find((s) => s.element === entry.target) || hscrolls.find((h) => h.element === entry.target);
        if (item) item.active = entry.isIntersecting;
      }
    },
    { rootMargin: "25% 0px" }
  );
  scenes.forEach((scene) => visibility.observe(scene.element));
  hscrolls.forEach((item) => visibility.observe(item.element));

  function update() {
    const vh = window.innerHeight;
    for (const scene of scenes) {
      if (!scene.active) continue;
      const rect = scene.element.getBoundingClientRect();
      const total = rect.height - vh;
      const p = total > 0 ? clamp01(-rect.top / total) : 0;
      if (Math.abs(p - scene.p) < 0.00005) continue;
      scene.p = p;
      scene.element._progress = p;
      scene.element.style.setProperty("--p", p.toFixed(4));
      for (const beat of scene.beats) applyBeat(beat, p);
      for (const bar of scene.bars) bar.style.transform = `scaleY(${p.toFixed(4)})`;
    }
    for (const item of hscrolls) {
      if (!item.active || !item.track) continue;
      const rect = item.element.getBoundingClientRect();
      const total = rect.height - vh;
      const p = total > 0 ? clamp01(-rect.top / total) : 0;
      const overflow = Math.max(0, item.track.scrollWidth - item.track.parentElement.clientWidth);
      const direction = document.documentElement.dir === "rtl" ? 1 : -1;
      item.track.style.transform = `translate3d(${(direction * overflow * p).toFixed(1)}px, 0, 0)`;
      item.element.style.setProperty("--p", p.toFixed(4));
    }
    for (const item of parallax) {
      const host = item.element.parentElement;
      const rect = host.getBoundingClientRect();
      if (rect.bottom < -300 || rect.top > vh + 300) continue;
      const offset = (rect.top + rect.height / 2 - vh / 2) * -item.speed;
      item.element.style.transform = `translate3d(0, ${offset.toFixed(1)}px, 0)`;
    }
    for (const { element, words } of highlights) {
      const rect = element.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > vh) continue;
      const progress = clamp01((vh * 0.82 - rect.top) / (rect.height + vh * 0.3));
      const lit = progress * (words.length + 3);
      words.forEach((word, i) => {
        const opacity = (0.16 + clamp01(lit - i) * 0.84).toFixed(2);
        if (word._o !== opacity) {
          word._o = opacity;
          word.style.opacity = opacity;
        }
      });
    }
  }

  if (lenis) {
    lenis.on("scroll", update);
  } else {
    let ticking = false;
    window.addEventListener(
      "scroll",
      () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
          update();
          ticking = false;
        });
      },
      { passive: true }
    );
  }
  window.addEventListener("resize", update);
  window.addEventListener("load", update);
  update();
  return { update, observeReveals };
}
