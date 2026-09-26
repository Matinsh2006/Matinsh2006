import { faDigits, toast } from "./utils.js";

export function initCart({ lenis, onUpdate } = {}) {
  const drawer = document.querySelector("[data-cart-drawer]");
  const overlay = document.querySelector("[data-cart-overlay]");
  const body = drawer?.querySelector("[data-drawer-body]");

  const setOpen = (open) => {
    if (!drawer) return;
    drawer.classList.toggle("is-open", open);
    overlay?.classList.toggle("is-open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    document.documentElement.classList.toggle("overflow-hidden", open);
    if (lenis) (open ? lenis.stop() : lenis.start());
  };

  const setCount = (count) => {
    document.querySelectorAll("[data-cart-count]").forEach((badge) => {
      badge.textContent = faDigits(count);
      badge.hidden = !count;
    });
  };

  const renderDrawer = (html) => {
    if (body && typeof html === "string") {
      body.innerHTML = html;
      onUpdate?.(body);
    }
  };

  document.querySelectorAll("[data-cart-open]").forEach((button) =>
    button.addEventListener("click", async (event) => {
      if (!drawer) return;
      event.preventDefault();
      setOpen(true);
      try {
        const response = await fetch(drawer.dataset.drawerUrl, { headers: { Accept: "text/html" } });
        renderDrawer(await response.text());
      } catch {
        /* keep the current content */
      }
    })
  );
  document.querySelectorAll("[data-cart-close]").forEach((button) => button.addEventListener("click", () => setOpen(false)));
  overlay?.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (e) => e.key === "Escape" && drawer?.classList.contains("is-open") && setOpen(false));

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-cart-form]");
    if (!form || !drawer) return;
    event.preventDefault();
    const submitter = event.submitter || form.querySelector("[type=submit]");
    const data = new FormData(form);
    if (submitter?.name) data.set(submitter.name, submitter.value);
    form.classList.add("is-loading");
    if (submitter) submitter.disabled = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: data,
        headers: { Accept: "application/json", "X-Requested-With": "fetch" },
        credentials: "same-origin",
      });
      const payload = await response.json();
      if (payload.drawer) renderDrawer(payload.drawer);
      if (typeof payload.count === "number") setCount(payload.count);
      if (form.dataset.cartForm === "add") {
        if (payload.ok) setOpen(true);
        else toast(payload.message, "error");
      }
    } catch {
      form.submit();
    } finally {
      form.classList.remove("is-loading");
      if (submitter) submitter.disabled = false;
    }
  });
}
