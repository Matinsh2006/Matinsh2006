/* Beauty shop – front-end behaviour (vanilla JS, no dependencies). */
(function () {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const FA = "۰۱۲۳۴۵۶۷۸۹";
  const AR = "٠١٢٣٤٥٦٧٨٩";
  const toFa = (value) => String(value).replace(/\d/g, (d) => FA[d]);
  const toLatin = (value) =>
    String(value)
      .replace(/[۰-۹]/g, (d) => FA.indexOf(d))
      .replace(/[٠-٩]/g, (d) => AR.indexOf(d));
  const isRTL = (el) => getComputedStyle(el).direction === "rtl";
  const behavior = () => (reduceMotion ? "auto" : "smooth");

  /* ---------- Toast notifications ---------- */
  function toast(message, type = "success", link = null) {
    const stack = $("#toast-stack");
    if (!stack || !message) return;
    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.setAttribute("role", type === "error" ? "alert" : "status");
    const text = document.createElement("span");
    text.className = "toast__text";
    text.textContent = message;
    el.appendChild(text);
    if (link) {
      const a = document.createElement("a");
      a.href = link.href;
      a.textContent = link.label;
      el.appendChild(a);
    }
    stack.appendChild(el);
    setTimeout(() => {
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 300);
    }, 4000);
  }

  /* ---------- Sticky header (shadow + hide on scroll down on mobile) ---------- */
  function initHeader() {
    const header = $(".site-header");
    if (!header) return;
    const mobile = window.matchMedia("(max-width: 991px)");
    let lastY = window.scrollY;
    let ticking = false;
    const update = () => {
      const y = window.scrollY;
      header.classList.toggle("is-scrolled", y > 8);
      const drawerOpen = document.body.classList.contains("no-scroll");
      if (mobile.matches && !drawerOpen && y > 160 && y > lastY + 4) header.classList.add("is-hidden");
      else if (y < lastY - 4 || y <= 160) header.classList.remove("is-hidden");
      lastY = y;
      ticking = false;
    };
    window.addEventListener("scroll", () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    }, { passive: true });
    // Never keep the header hidden while an element inside it has focus.
    header.addEventListener("focusin", () => header.classList.remove("is-hidden"));
    update();
  }

  /* ---------- Drawers: mobile menu and filter sheet ---------- */
  let lastFocus = null;
  function openDrawer(drawer) {
    if (!drawer) return;
    lastFocus = document.activeElement;
    drawer.classList.add("is-open");
    document.body.classList.add("no-scroll");
    $$(`[data-drawer-open="${drawer.id}"]`).forEach((btn) => btn.setAttribute("aria-expanded", "true"));
    const target = $(".drawer__panel [data-drawer-close], .drawer__panel a, .drawer__panel button", drawer);
    if (target) setTimeout(() => target.focus({ preventScroll: true }), 50);
  }
  function closeDrawer(drawer) {
    if (!drawer || !drawer.classList.contains("is-open")) return;
    drawer.classList.remove("is-open");
    if (!$(".drawer.is-open")) document.body.classList.remove("no-scroll");
    $$(`[data-drawer-open="${drawer.id}"]`).forEach((btn) => btn.setAttribute("aria-expanded", "false"));
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
  }
  function initDrawers() {
    document.addEventListener("click", (event) => {
      const opener = event.target.closest("[data-drawer-open]");
      if (opener) {
        event.preventDefault();
        openDrawer(document.getElementById(opener.dataset.drawerOpen));
        return;
      }
      const closer = event.target.closest("[data-drawer-close]");
      if (closer) {
        event.preventDefault();
        closeDrawer(closer.closest(".drawer"));
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") $$(".drawer.is-open").forEach(closeDrawer);
    });
  }

  /* ---------- Scroll helpers (work in both RTL and LTR) ---------- */
  function scrollToChild(track, child, smooth = true) {
    const delta = child.getBoundingClientRect().left - track.getBoundingClientRect().left;
    track.scrollBy({ left: delta, behavior: smooth ? behavior() : "auto" });
  }
  function nearestChildIndex(track, children) {
    const box = track.getBoundingClientRect();
    const center = box.left + box.width / 2;
    let best = 0;
    let bestDistance = Infinity;
    children.forEach((child, index) => {
      const rect = child.getBoundingClientRect();
      const distance = Math.abs(rect.left + rect.width / 2 - center);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = index;
      }
    });
    return best;
  }

  /* ---------- Banner slider (CSS scroll-snap + autoplay) ---------- */
  function initSlider(root) {
    const track = $("[data-slider-track]", root);
    if (!track) return;
    const slides = Array.from(track.children);
    const prev = $("[data-slider-prev]", root);
    const next = $("[data-slider-next]", root);
    const dotsWrap = $("[data-slider-dots]", root);
    if (slides.length < 2) {
      [prev, next, dotsWrap].forEach((el) => el && (el.hidden = true));
      return;
    }

    let current = 0;
    let timer = null;
    let visible = true;
    const delay = parseInt(root.dataset.autoplay || "0", 10);

    const dots = slides.map((_, index) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "slider__dot";
      dot.setAttribute("aria-label", `نمایش بنر ${toFa(index + 1)}`);
      dot.addEventListener("click", () => {
        goTo(index);
        restart();
      });
      dotsWrap.appendChild(dot);
      return dot;
    });

    function goTo(index) {
      current = (index + slides.length) % slides.length;
      scrollToChild(track, slides[current]);
    }
    function sync() {
      current = nearestChildIndex(track, slides);
      dots.forEach((dot, index) => dot.setAttribute("aria-current", index === current ? "true" : "false"));
    }
    function start() {
      if (!delay || reduceMotion || timer || !visible || document.hidden) return;
      timer = setInterval(() => goTo(current + 1), delay);
    }
    function stop() {
      clearInterval(timer);
      timer = null;
    }
    function restart() {
      stop();
      start();
    }

    let raf = 0;
    track.addEventListener("scroll", () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(sync);
    }, { passive: true });
    if (prev) prev.addEventListener("click", () => { goTo(current - 1); restart(); });
    if (next) next.addEventListener("click", () => { goTo(current + 1); restart(); });
    root.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const forward = (event.key === "ArrowLeft") === isRTL(root);
      goTo(current + (forward ? 1 : -1));
      restart();
    });
    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", start);
    root.addEventListener("focusin", stop);
    root.addEventListener("focusout", start);
    track.addEventListener("touchstart", stop, { passive: true });
    track.addEventListener("touchend", () => setTimeout(start, 2500), { passive: true });
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        visible ? start() : stop();
      }, { threshold: 0.3 }).observe(root);
    }
    sync();
    start();
  }

  /* ---------- Horizontal product / brand scrollers ---------- */
  function initHScroll(root) {
    const track = $("[data-hscroll-track]", root);
    if (!track) return;
    const prev = $("[data-hscroll-prev]", root);
    const next = $("[data-hscroll-next]", root);
    const direction = () => (isRTL(track) ? -1 : 1);
    const step = () => track.clientWidth * 0.85;
    if (prev) prev.addEventListener("click", () => track.scrollBy({ left: -direction() * step(), behavior: behavior() }));
    if (next) next.addEventListener("click", () => track.scrollBy({ left: direction() * step(), behavior: behavior() }));
    const update = () => {
      const max = track.scrollWidth - track.clientWidth;
      const position = Math.abs(track.scrollLeft);
      if (prev) prev.disabled = position <= 2;
      if (next) next.disabled = position >= max - 2;
    };
    track.addEventListener("scroll", () => requestAnimationFrame(update), { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  /* ---------- Product gallery + lightbox ---------- */
  function initGallery(root) {
    const track = $("[data-gallery-track]", root);
    if (!track) return;
    const slides = Array.from(track.children);
    const thumbs = $$("[data-gallery-thumb]", root);
    const thumbsWrap = $("[data-gallery-thumbs]", root);
    const counter = $("[data-gallery-counter]", root);
    let current = 0;

    const show = (index, smooth = true) => {
      current = Math.max(0, Math.min(index, slides.length - 1));
      scrollToChild(track, slides[current], smooth);
    };
    const sync = () => {
      current = nearestChildIndex(track, slides);
      thumbs.forEach((thumb, index) => {
        const active = index === current;
        thumb.classList.toggle("is-active", active);
        thumb.setAttribute("aria-current", active ? "true" : "false");
      });
      if (counter) counter.textContent = `${toFa(current + 1)} / ${toFa(slides.length)}`;
      const activeThumb = thumbs[current];
      if (thumbsWrap && activeThumb) {
        const wrapBox = thumbsWrap.getBoundingClientRect();
        const thumbBox = activeThumb.getBoundingClientRect();
        if (thumbBox.left < wrapBox.left || thumbBox.right > wrapBox.right) {
          thumbsWrap.scrollBy({ left: thumbBox.left - wrapBox.left - wrapBox.width / 2 + thumbBox.width / 2, behavior: behavior() });
        }
      }
    };
    let raf = 0;
    track.addEventListener("scroll", () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(sync);
    }, { passive: true });
    thumbs.forEach((thumb, index) => thumb.addEventListener("click", () => show(index)));

    const lightbox = $("[data-lightbox]", root);
    if (lightbox && typeof lightbox.showModal === "function") {
      const image = $("[data-lightbox-img]", lightbox);
      const count = $("[data-lightbox-counter]", lightbox);
      const sources = slides.map((slide) => {
        const img = $("img", slide);
        return { src: img.currentSrc || img.src, alt: img.alt };
      });
      let index = 0;
      const render = () => {
        image.src = sources[index].src;
        image.alt = sources[index].alt;
        if (count) count.textContent = sources.length > 1 ? `${toFa(index + 1)} / ${toFa(sources.length)}` : "";
      };
      const open = (i) => {
        index = i;
        render();
        lightbox.showModal();
        document.body.classList.add("no-scroll");
      };
      const move = (delta) => {
        index = (index + delta + sources.length) % sources.length;
        render();
      };
      slides.forEach((slide, i) => slide.addEventListener("click", () => open(i)));
      const zoom = $("[data-gallery-open]", root);
      if (zoom) zoom.addEventListener("click", () => open(current));
      $("[data-lightbox-close]", lightbox).addEventListener("click", () => lightbox.close());
      const prevBtn = $("[data-lightbox-prev]", lightbox);
      const nextBtn = $("[data-lightbox-next]", lightbox);
      if (prevBtn) prevBtn.addEventListener("click", () => move(-1));
      if (nextBtn) nextBtn.addEventListener("click", () => move(1));
      lightbox.addEventListener("close", () => {
        document.body.classList.remove("no-scroll");
        show(index, false);
      });
      lightbox.addEventListener("click", (event) => {
        if (event.target === lightbox || event.target.classList.contains("lightbox__stage")) lightbox.close();
      });
      lightbox.addEventListener("keydown", (event) => {
        const rtl = isRTL(document.documentElement);
        if (event.key === "ArrowLeft") move(rtl ? 1 : -1);
        if (event.key === "ArrowRight") move(rtl ? -1 : 1);
      });
      let touchX = null;
      lightbox.addEventListener("touchstart", (event) => { touchX = event.touches[0].clientX; }, { passive: true });
      lightbox.addEventListener("touchend", (event) => {
        if (touchX === null || sources.length < 2) return;
        const dx = event.changedTouches[0].clientX - touchX;
        touchX = null;
        if (Math.abs(dx) < 50) return;
        const forward = isRTL(document.documentElement) ? dx > 0 : dx < 0;
        move(forward ? 1 : -1);
      }, { passive: true });
    }
    sync();
  }

  /* ---------- Quantity steppers ---------- */
  function initQuantity() {
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-qty-step]");
      if (!button) return;
      const input = $("input[type=number]", button.closest("[data-qty]"));
      if (!input) return;
      const min = parseInt(input.min || "1", 10);
      const max = parseInt(input.max || "99", 10);
      const value = (parseInt(toLatin(input.value), 10) || 0) + parseInt(button.dataset.qtyStep, 10);
      if (value > max) {
        toast(`حداکثر ${toFa(max)} عدد از این کالا قابل سفارش است.`, "error");
        return;
      }
      if (value < min) return;
      input.value = value;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    // Cart page: submit the quantity form automatically after a short pause.
    document.addEventListener("change", (event) => {
      const form = event.target.closest("form[data-autosubmit]");
      if (!form || !event.target.matches("input[type=number]")) return;
      clearTimeout(form._submitTimer);
      form._submitTimer = setTimeout(() => (form.requestSubmit ? form.requestSubmit() : form.submit()), 600);
    });
  }

  /* ---------- Add to cart without reloading the page ---------- */
  function updateCartCount(count) {
    $$("[data-cart-count]").forEach((badge) => {
      badge.textContent = toFa(count);
      badge.hidden = count === 0;
    });
  }
  function initCartForms() {
    document.addEventListener("submit", async (event) => {
      const form = event.target.closest("form[data-cart-form]");
      if (!form || !window.fetch) return;
      event.preventDefault();
      const buttons = $$("button[type=submit]", form).concat(form.id ? $$(`button[form="${form.id}"]`) : []);
      buttons.forEach((btn) => { btn.disabled = true; btn.classList.add("is-loading"); });
      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
          credentials: "same-origin",
        });
        const data = await response.json();
        if (typeof data.cart_count === "number") updateCartCount(data.cart_count);
        const cartLink = $(".header-action--cart");
        const link = { href: cartLink ? cartLink.getAttribute("href") : "/cart/", label: "مشاهده سبد" };
        toast(data.message, data.ok ? "success" : "error", data.ok ? link : null);
      } catch (error) {
        form.submit();
      } finally {
        buttons.forEach((btn) => { btn.disabled = false; btn.classList.remove("is-loading"); });
      }
    });
  }

  /* ---------- SMS code: resend countdown & auto submit ---------- */
  function initCountdowns() {
    $$("[data-countdown]").forEach((el) => {
      let seconds = parseInt(el.dataset.countdown, 10) || 0;
      const form = el.closest("form");
      const wrap = form && $("[data-countdown-wrap]", form);
      const button = form && $("[data-countdown-button]", form);
      const render = () => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        el.textContent = toFa(`${m}:${String(s).padStart(2, "0")}`);
      };
      if (seconds <= 0) return;
      render();
      const timer = setInterval(() => {
        seconds -= 1;
        if (seconds <= 0) {
          clearInterval(timer);
          if (wrap) wrap.hidden = true;
          if (button) button.hidden = false;
          return;
        }
        render();
      }, 1000);
    });
    $$("[data-autosubmit-length]").forEach((input) => {
      const length = parseInt(input.dataset.autosubmitLength, 10);
      input.addEventListener("input", () => {
        const digits = toLatin(input.value).replace(/\D/g, "");
        const form = input.form;
        if (digits.length === length && form && !form.dataset.submitted) {
          form.requestSubmit ? form.requestSubmit() : form.submit();
        }
      });
    });
  }

  /* ---------- Floating contact button ---------- */
  function initFab() {
    const fab = $("[data-fab]");
    if (!fab) return;
    const toggle = $("[data-fab-toggle]", fab);
    const set = (open) => {
      fab.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
    };
    toggle.addEventListener("click", () => set(!fab.classList.contains("is-open")));
    document.addEventListener("click", (event) => { if (!fab.contains(event.target)) set(false); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") set(false); });
  }

  /* ---------- Sticky "add to cart" bar on mobile product pages ---------- */
  function initStickyBuy() {
    const bar = $("[data-sticky-buy]");
    const anchor = $("[data-buy-anchor]");
    if (!bar || !anchor || !("IntersectionObserver" in window)) return;
    new IntersectionObserver(([entry]) => bar.classList.toggle("is-visible", !entry.isIntersecting)).observe(anchor);
  }

  /* ---------- Checkout: show the new-address form only when selected ---------- */
  function initAddressChoice() {
    const block = $("[data-new-address]");
    const radios = $$("[data-address-choice]");
    if (!block || !radios.length) return;
    const update = () => { block.hidden = !radios.some((radio) => radio.checked && radio.value === "new"); };
    radios.forEach((radio) => radio.addEventListener("change", update));
    update();
  }

  /* ---------- Store location map (Leaflet) ---------- */
  const PIN_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>';
  function initMaps() {
    $$("[data-map]").forEach((el) => {
      const source = document.getElementById(el.dataset.mapSource);
      if (!window.L || !source) return;
      const points = JSON.parse(source.textContent || "[]");
      if (!points.length) return;
      const L = window.L;
      const map = L.map(el, { scrollWheelZoom: false, dragging: !L.Browser.mobile });
      L.tileLayer(el.dataset.tileUrl, { maxZoom: 19, attribution: el.dataset.tileAttribution }).addTo(map);
      const icon = L.divIcon({ className: "map-pin", html: PIN_SVG, iconSize: [40, 40], iconAnchor: [20, 38], popupAnchor: [0, -34] });
      const latLngs = points.map((point) => {
        const popup = document.createElement("div");
        popup.className = "map-popup";
        const title = document.createElement("strong");
        title.textContent = point.name;
        const address = document.createElement("p");
        address.textContent = point.address;
        const link = document.createElement("a");
        link.href = point.directions;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "مسیریابی تا فروشگاه";
        popup.append(title, address, link);
        L.marker([point.lat, point.lng], { icon, title: point.name, alt: point.name }).addTo(map).bindPopup(popup);
        return [point.lat, point.lng];
      });
      if (latLngs.length === 1) map.setView(latLngs[0], points[0].zoom || 16);
      else map.fitBounds(latLngs, { padding: [40, 40] });
      $$("[data-map-focus]").forEach((button) => {
        button.addEventListener("click", () => {
          const i = parseInt(button.dataset.mapFocus, 10);
          map.setView(latLngs[i], points[i].zoom || 16);
          el.scrollIntoView({ behavior: behavior(), block: "center" });
        });
      });
    });
  }

  /* ---------- Small helpers ---------- */
  function initMisc() {
    // Persian/Arabic digits typed in number-like fields become latin digits.
    document.addEventListener("input", (event) => {
      const el = event.target;
      if (!el.matches || !el.matches("[data-latin-digits]")) return;
      const value = toLatin(el.value);
      if (value !== el.value) {
        const position = el.selectionStart;
        el.value = value;
        try { el.setSelectionRange(position, position); } catch (error) { /* not supported for this input type */ }
      }
    });

    document.addEventListener("change", (event) => {
      const select = event.target.closest("select[data-autosubmit]");
      if (select && select.form) select.form.submit();
    });

    document.addEventListener("click", async (event) => {
      const dismiss = event.target.closest("[data-dismiss]");
      if (dismiss) {
        const alert = dismiss.closest(".alert");
        if (alert) alert.remove();
      }
      const copy = event.target.closest("[data-copy]");
      if (copy) {
        try {
          await navigator.clipboard.writeText(copy.dataset.copy);
          toast("لینک کپی شد.");
        } catch (error) {
          toast("کپی لینک ممکن نشد.", "error");
        }
      }
    });

    // Confirmation dialogs and double-submit protection.
    document.addEventListener("submit", (event) => {
      const form = event.target;
      if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
        event.preventDefault();
        return;
      }
      if (form.hasAttribute("data-once")) {
        if (form.dataset.submitted) {
          event.preventDefault();
          return;
        }
        form.dataset.submitted = "1";
        $$("button[type=submit]", form).forEach((btn) => btn.classList.add("is-loading"));
      }
    });
    window.addEventListener("pageshow", () => {
      $$("form[data-once]").forEach((form) => {
        delete form.dataset.submitted;
        $$(".is-loading", form).forEach((btn) => btn.classList.remove("is-loading"));
      });
    });
  }

  function init() {
    initHeader();
    initDrawers();
    $$("[data-slider]").forEach(initSlider);
    $$("[data-hscroll]").forEach(initHScroll);
    $$("[data-gallery]").forEach(initGallery);
    initQuantity();
    initCartForms();
    initCountdowns();
    initFab();
    initStickyBuy();
    initAddressChoice();
    initMaps();
    initMisc();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
