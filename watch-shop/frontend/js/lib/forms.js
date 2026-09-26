import { faDigits } from "./utils.js";

const toEnglish = (value) =>
  value.replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d));

/** Segmented one-time-code input that keeps a single real <input> for SMS autofill. */
export function initOtp() {
  document.querySelectorAll("[data-otp]").forEach((root) => {
    const input = root.querySelector("input");
    const boxes = [...root.querySelectorAll("[data-otp-box]")];
    const length = boxes.length;
    const form = root.closest("form");
    const paint = () => {
      const digits = toEnglish(input.value).replace(/\D/g, "").slice(0, length);
      if (input.value !== digits) input.value = digits;
      boxes.forEach((box, i) => {
        box.textContent = digits[i] ? faDigits(digits[i]) : "";
        box.classList.toggle("is-filled", !!digits[i]);
        box.classList.toggle("is-active", document.activeElement === input && i === Math.min(digits.length, length - 1));
      });
      if (digits.length === length && form && !form.dataset.submitted) {
        form.dataset.submitted = "1";
        setTimeout(() => form.requestSubmit(), 180);
      }
    };
    input.addEventListener("input", () => {
      delete form?.dataset.submitted;
      paint();
    });
    input.addEventListener("focus", paint);
    input.addEventListener("blur", paint);
    root.addEventListener("click", () => input.focus());
    paint();
  });

  document.querySelectorAll("[data-countdown]").forEach((element) => {
    let remaining = parseInt(element.dataset.countdown, 10) || 0;
    const button = document.querySelector(element.dataset.target);
    const label = element.querySelector("[data-countdown-label]");
    const tick = () => {
      if (remaining <= 0) {
        element.hidden = true;
        if (button) button.disabled = false;
        return;
      }
      if (label) label.textContent = faDigits(`${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}`);
      if (button) button.disabled = true;
      remaining -= 1;
      setTimeout(tick, 1000);
    };
    tick();
  });

  // Normalise Persian digits typed in numeric/phone fields before submit.
  document.querySelectorAll("form").forEach((form) =>
    form.addEventListener("submit", () => {
      form.querySelectorAll("input[inputmode=tel], input[inputmode=numeric]").forEach((field) => {
        field.value = toEnglish(field.value);
      });
    })
  );
}

export function initQuantity() {
  document.querySelectorAll("[data-qty]").forEach((root) => {
    const input = root.querySelector("input");
    const max = parseInt(input.max || "99", 10);
    const min = parseInt(input.min || "1", 10);
    const out = root.querySelector("[data-qty-value]");
    const set = (value) => {
      input.value = String(Math.max(min, Math.min(max, value)));
      if (out) out.textContent = faDigits(input.value);
    };
    root.querySelector("[data-qty-inc]")?.addEventListener("click", () => set(parseInt(input.value, 10) + 1));
    root.querySelector("[data-qty-dec]")?.addEventListener("click", () => set(parseInt(input.value, 10) - 1));
    set(parseInt(input.value, 10) || min);
  });
}

export function initFilters() {
  document.querySelectorAll("[data-autosubmit]").forEach((field) =>
    field.addEventListener("change", () => field.form?.requestSubmit())
  );
  const panel = document.querySelector("[data-filter-panel]");
  document.querySelectorAll("[data-filter-toggle]").forEach((button) =>
    button.addEventListener("click", () => {
      const open = !panel.classList.contains("is-open");
      panel.classList.toggle("is-open", open);
      document.querySelector("[data-filter-overlay]")?.classList.toggle("is-open", open);
      document.documentElement.classList.toggle("overflow-hidden", open);
    })
  );
  document.querySelector("[data-filter-overlay]")?.addEventListener("click", () => {
    panel.classList.remove("is-open");
    document.querySelector("[data-filter-overlay]").classList.remove("is-open");
    document.documentElement.classList.remove("overflow-hidden");
  });
}

export function initLoadMore(onAppend) {
  document.querySelectorAll("[data-load-more]").forEach((button) => {
    button.addEventListener("click", async () => {
      const grid = document.querySelector(button.dataset.target);
      const url = new URL(button.dataset.nextUrl, window.location.href);
      url.searchParams.set("partial", "1");
      button.disabled = true;
      button.classList.add("is-loading");
      try {
        const response = await fetch(url, { headers: { Accept: "text/html" } });
        const html = await response.text();
        const template = document.createElement("template");
        template.innerHTML = html;
        const meta = template.content.querySelector("[data-page-meta]");
        const items = [...template.content.querySelectorAll("[data-grid-item]")];
        items.forEach((item) => grid.append(item));
        onAppend?.(grid);
        if (meta?.dataset.nextUrl) {
          button.dataset.nextUrl = meta.dataset.nextUrl;
          button.disabled = false;
        } else {
          button.closest("[data-load-more-wrap]")?.remove();
        }
        const pageUrl = new URL(url);
        pageUrl.searchParams.delete("partial");
        window.history.replaceState({}, "", pageUrl);
      } catch {
        window.location.href = button.dataset.nextUrl;
      } finally {
        button.classList.remove("is-loading");
      }
    });
  });
}

export function initCardGlow(root = document) {
  root.querySelectorAll(".product-card:not([data-glow-ready])").forEach((card) => {
    card.dataset.glowReady = "1";
    card.addEventListener("pointermove", (event) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
      card.style.setProperty("--my", `${event.clientY - rect.top}px`);
    });
  });
}

export function initCopy() {
  document.querySelectorAll("[data-copy]").forEach((button) =>
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        const label = button.querySelector("[data-copy-label]");
        if (label) {
          const previous = label.textContent;
          label.textContent = "کپی شد";
          setTimeout(() => (label.textContent = previous), 1600);
        }
      } catch {
        /* clipboard unavailable */
      }
    })
  );
}
