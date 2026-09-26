export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
export const clamp01 = (value) => clamp(value, 0, 1);
export const lerp = (a, b, t) => a + (b - a) * t;

export function smoothstep(edge0, edge1, value) {
  const t = clamp01((value - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
}

const FA = "۰۱۲۳۴۵۶۷۸۹";
export const faDigits = (value) => String(value).replace(/\d/g, (d) => FA[+d]);
export const formatNumber = (value) => faDigits(Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, "٬"));

export function debounce(fn, wait = 200) {
  let timer = 0;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

export const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
export const isRTL = () => document.documentElement.dir === "rtl";

export function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  if (match) return decodeURIComponent(match[1]);
  return document.querySelector("input[name=csrfmiddlewaretoken]")?.value || "";
}

export function toast(message, type = "info") {
  const stack = document.querySelector("[data-toasts]");
  if (!stack || !message) return;
  const item = document.createElement("div");
  item.className = `toast pointer-events-auto flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm shadow-2xl backdrop-blur-xl ${
    type === "error" ? "border-danger/30 bg-ink-800/90 text-sand-50" : "border-gold-300/25 bg-ink-800/90 text-sand-50"
  }`;
  item.setAttribute("role", "status");
  const dot = document.createElement("span");
  dot.className = `mt-1.5 size-2 shrink-0 rounded-full ${type === "error" ? "bg-danger" : "bg-gold-300"}`;
  const text = document.createElement("p");
  text.className = "leading-6";
  text.textContent = message;
  item.append(dot, text);
  stack.append(item);
  dismissLater(item);
}

export function dismissLater(item, delay = 5200) {
  const close = () => {
    item.classList.add("is-leaving");
    item.addEventListener("animationend", () => item.remove(), { once: true });
  };
  const timer = setTimeout(close, delay);
  item.querySelector("[data-toast-close]")?.addEventListener("click", () => {
    clearTimeout(timer);
    close();
  });
}
