import { debounce } from "./utils.js";

function lockScroll(lenis, locked) {
  document.documentElement.classList.toggle("overflow-hidden", locked);
  if (lenis) (locked ? lenis.stop() : lenis.start());
}

export function initHeader({ lenis } = {}) {
  const header = document.querySelector("[data-header]");
  if (header) {
    let lastY = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      header.classList.toggle("is-scrolled", y > 24);
      if (y > lastY + 6 && y > 320 && !document.documentElement.classList.contains("overflow-hidden")) {
        header.classList.add("is-hidden");
      } else if (y < lastY - 6 || y < 120) {
        header.classList.remove("is-hidden");
      }
      lastY = y;
    };
    if (lenis) lenis.on("scroll", onScroll);
    else window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // Mobile menu
  const menu = document.querySelector("[data-mobile-menu]");
  const menuButtons = document.querySelectorAll("[data-menu-toggle]");
  const setMenu = (open) => {
    if (!menu) return;
    menu.classList.toggle("is-open", open);
    menu.setAttribute("aria-hidden", String(!open));
    menuButtons.forEach((button) => button.setAttribute("aria-expanded", String(open)));
    lockScroll(lenis, open);
  };
  menuButtons.forEach((button) => button.addEventListener("click", () => setMenu(!menu.classList.contains("is-open"))));
  menu?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => setMenu(false)));
  menu?.querySelectorAll("[data-accordion]").forEach((button) => {
    button.addEventListener("click", () => {
      const panel = document.getElementById(button.getAttribute("aria-controls"));
      const open = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(open));
      panel.style.gridTemplateRows = open ? "1fr" : "0fr";
    });
  });

  // Search overlay with live suggestions
  const overlay = document.querySelector("[data-search]");
  if (overlay) {
    const input = overlay.querySelector("input[name=q]");
    const results = overlay.querySelector("[data-search-results]");
    const setOpen = (open) => {
      overlay.classList.toggle("is-open", open);
      overlay.setAttribute("aria-hidden", String(!open));
      lockScroll(lenis, open);
      if (open) setTimeout(() => input?.focus(), 80);
    };
    document.querySelectorAll("[data-search-open]").forEach((b) => b.addEventListener("click", () => setOpen(true)));
    overlay.querySelectorAll("[data-search-close]").forEach((b) => b.addEventListener("click", () => setOpen(false)));

    let controller = null;
    const render = (data) => {
      results.replaceChildren();
      const section = (title, items, build) => {
        if (!items.length) return;
        const wrap = document.createElement("div");
        wrap.className = "grid gap-2";
        const heading = document.createElement("p");
        heading.className = "text-xs text-sand-500";
        heading.textContent = title;
        wrap.append(heading, ...items.map(build));
        results.append(wrap);
      };
      section("محصولات", data.products, (item) => {
        const a = document.createElement("a");
        a.href = item.url;
        a.className = "group flex items-center gap-4 rounded-2xl p-2 transition hover:bg-white/[0.05]";
        const img = document.createElement("img");
        img.src = item.image || "";
        img.alt = "";
        img.className = "size-14 rounded-xl bg-ink-800 object-cover";
        const text = document.createElement("div");
        text.className = "min-w-0 flex-1";
        const name = document.createElement("p");
        name.className = "truncate text-sand-50";
        name.textContent = item.name;
        const meta = document.createElement("p");
        meta.className = "text-xs text-sand-400";
        meta.textContent = `${item.brand} · ${item.price} تومان`;
        text.append(name, meta);
        a.append(img, text);
        return a;
      });
      const pill = (item) => {
        const a = document.createElement("a");
        a.href = item.url;
        a.className = "chip h-9 w-fit";
        a.textContent = item.name;
        return a;
      };
      section("دسته‌بندی‌ها", data.categories, pill);
      section("برندها", data.brands, pill);
      if (!data.products.length && !data.categories.length && !data.brands.length) {
        const empty = document.createElement("p");
        empty.className = "py-6 text-center text-sand-400";
        empty.textContent = "نتیجه‌ای پیدا نشد؛ عبارت دیگری را امتحان کنید.";
        results.append(empty);
      }
    };
    const search = debounce(async () => {
      const q = input.value.trim();
      if (q.length < 2) {
        results.replaceChildren();
        return;
      }
      controller?.abort();
      controller = new AbortController();
      try {
        const response = await fetch(`${overlay.dataset.suggestUrl}?q=${encodeURIComponent(q)}`, { signal: controller.signal });
        render(await response.json());
      } catch (error) {
        if (error.name !== "AbortError") results.replaceChildren();
      }
    }, 220);
    input?.addEventListener("input", search);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (menu?.classList.contains("is-open")) setMenu(false);
    if (overlay?.classList.contains("is-open")) {
      overlay.classList.remove("is-open");
      lockScroll(lenis, false);
    }
  });
}

/** Rotating, dismissible banner(s) at the very top of every page. */
export function initHeaderBanner() {
  const root = document.querySelector("[data-header-banner]");
  if (!root) return;
  const slides = [...root.querySelectorAll(".hb-slide")];
  const bar = root.querySelector(".hb-progress");
  const duration = 6500;
  let index = 0;
  let timer = 0;

  const show = (next) => {
    slides[index].classList.remove("is-active");
    index = (next + slides.length) % slides.length;
    slides[index].classList.add("is-active");
    if (bar) {
      bar.classList.remove("is-running");
      void bar.offsetWidth;
      bar.classList.add("is-running");
    }
  };
  const play = () => {
    clearInterval(timer);
    if (slides.length > 1) timer = setInterval(() => show(index + 1), duration);
  };
  if (slides.length > 1) {
    root.style.setProperty("--hb-duration", `${duration}ms`);
    bar?.classList.add("is-running");
    root.addEventListener("mouseenter", () => clearInterval(timer));
    root.addEventListener("mouseleave", play);
    root.querySelector("[data-hb-next]")?.addEventListener("click", () => {
      show(index + 1);
      play();
    });
    play();
  }

  root.querySelector("[data-hb-close]")?.addEventListener("click", () => {
    try {
      localStorage.setItem("hb-dismissed", root.dataset.version || "1");
    } catch {
      /* storage unavailable: dismiss for this page view only */
    }
    root.style.height = `${root.offsetHeight}px`;
    requestAnimationFrame(() => {
      root.style.transition = "height .6s cubic-bezier(.16,1,.3,1), opacity .4s";
      root.style.height = "0px";
      root.style.opacity = "0";
    });
    root.addEventListener("transitionend", () => root.remove(), { once: true });
    clearInterval(timer);
  });
}
