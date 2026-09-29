/*
 * Lightweight RTL rich text editor for the Django admin (no dependencies).
 * The HTML is sanitized again on the server before it is stored.
 */
(function () {
  "use strict";

  const TOOLS = [
    { cmd: "formatBlock", arg: "<p>", label: "پاراگراف", text: "¶" },
    { cmd: "formatBlock", arg: "<h2>", label: "تیتر اصلی", text: "H2" },
    { cmd: "formatBlock", arg: "<h3>", label: "تیتر فرعی", text: "H3" },
    { sep: true },
    { cmd: "bold", label: "پررنگ", html: "<b>B</b>" },
    { cmd: "italic", label: "مورب", html: "<i>I</i>" },
    { cmd: "underline", label: "زیرخط", html: "<u>U</u>" },
    { sep: true },
    { cmd: "insertUnorderedList", label: "فهرست نقطه‌ای", text: "•≡" },
    { cmd: "insertOrderedList", label: "فهرست شماره‌دار", text: "۱≡" },
    { cmd: "formatBlock", arg: "<blockquote>", label: "نقل قول / نکته", text: "❝" },
    { cmd: "insertHorizontalRule", label: "خط جداکننده", text: "―" },
    { sep: true },
    { cmd: "link", label: "درج لینک", text: "🔗" },
    { cmd: "unlink", label: "حذف لینک", text: "⛓̸" },
    { cmd: "image", label: "درج تصویر", text: "🖼" },
    { sep: true },
    { cmd: "removeFormat", label: "حذف قالب‌بندی", text: "✕" },
    { cmd: "undo", label: "برگرداندن", text: "↶" },
    { cmd: "redo", label: "انجام مجدد", text: "↷" },
    { cmd: "source", label: "نمایش / ویرایش کد HTML", text: "</>" },
  ];

  const escapeHtml = (value) =>
    String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);

  function csrfToken(root) {
    const form = root.closest("form");
    const input = form && form.querySelector("input[name=csrfmiddlewaretoken]");
    if (input) return input.value;
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function init(root) {
    if (root.dataset.rteReady) return;
    root.dataset.rteReady = "1";
    const textarea = root.querySelector("textarea");
    if (!textarea) return;

    const toolbar = document.createElement("div");
    toolbar.className = "rte__toolbar";
    toolbar.setAttribute("role", "toolbar");
    const editor = document.createElement("div");
    editor.className = "rte__editor";
    editor.contentEditable = "true";
    editor.dir = "rtl";
    editor.setAttribute("role", "textbox");
    editor.setAttribute("aria-multiline", "true");
    editor.innerHTML = textarea.value;
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/jpeg,image/png,image/webp,image/gif";
    fileInput.hidden = true;

    let sourceMode = false;
    let savedRange = null;

    const sync = () => {
      if (sourceMode) return;
      const isEmpty = !editor.textContent.trim() && !editor.querySelector("img, hr");
      textarea.value = isEmpty ? "" : editor.innerHTML;
    };
    const saveSelection = () => {
      const selection = window.getSelection();
      if (selection.rangeCount && editor.contains(selection.anchorNode)) savedRange = selection.getRangeAt(0).cloneRange();
    };
    const restoreSelection = () => {
      editor.focus();
      const selection = window.getSelection();
      selection.removeAllRanges();
      if (savedRange) {
        selection.addRange(savedRange);
      } else {
        const range = document.createRange();
        range.selectNodeContents(editor);
        range.collapse(false);
        selection.addRange(range);
      }
    };

    TOOLS.forEach((tool) => {
      if (tool.sep) {
        const sep = document.createElement("span");
        sep.className = "rte__sep";
        toolbar.appendChild(sep);
        return;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.className = "rte__btn";
      button.title = tool.label;
      button.setAttribute("aria-label", tool.label);
      if (tool.html) button.innerHTML = tool.html;
      else button.textContent = tool.text;
      button.addEventListener("mousedown", (event) => event.preventDefault()); // keep the selection
      button.addEventListener("click", () => run(tool, button));
      toolbar.appendChild(button);
    });

    function run(tool, button) {
      if (tool.cmd === "source") {
        sourceMode = !sourceMode;
        if (sourceMode) {
          textarea.value = editor.innerHTML;
        } else {
          editor.innerHTML = textarea.value;
        }
        root.classList.toggle("is-source", sourceMode);
        button.classList.toggle("is-active", sourceMode);
        toolbar.querySelectorAll(".rte__btn").forEach((b) => { if (b !== button) b.disabled = sourceMode; });
        return;
      }
      if (sourceMode) return;
      restoreSelection();
      if (tool.cmd === "link") {
        const url = window.prompt("آدرس لینک را وارد کنید (مثلاً https://example.com یا /products/):", "https://");
        restoreSelection();
        if (url && /^(https?:\/\/|mailto:|tel:|\/)/i.test(url.trim())) document.execCommand("createLink", false, url.trim());
      } else if (tool.cmd === "image") {
        fileInput.click();
        return;
      } else {
        document.execCommand(tool.cmd, false, tool.arg || null);
      }
      sync();
    }

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      const url = root.dataset.uploadUrl;
      if (!url) {
        window.alert("آپلود تصویر در دسترس نیست.");
        return;
      }
      const body = new FormData();
      body.append("image", file);
      root.classList.add("is-uploading");
      try {
        const response = await fetch(url, {
          method: "POST",
          body,
          headers: { "X-CSRFToken": csrfToken(root) },
          credentials: "same-origin",
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "آپلود تصویر ناموفق بود.");
        const alt = window.prompt("متن جایگزین تصویر (برای سئو و نابینایان):", "") || "";
        restoreSelection();
        document.execCommand("insertHTML", false, `<img src="${escapeHtml(data.url)}" alt="${escapeHtml(alt)}" loading="lazy">`);
        sync();
      } catch (error) {
        window.alert(error.message);
      } finally {
        root.classList.remove("is-uploading");
        fileInput.value = "";
      }
    });

    editor.addEventListener("input", sync);
    editor.addEventListener("blur", sync);
    editor.addEventListener("keyup", saveSelection);
    editor.addEventListener("mouseup", saveSelection);
    document.addEventListener("selectionchange", saveSelection);
    // Paste as clean text (keeps paragraphs) to avoid junk styles from Word/websites.
    editor.addEventListener("paste", (event) => {
      event.preventDefault();
      const text = (event.clipboardData || window.clipboardData).getData("text/plain");
      if (/\n\s*\n/.test(text)) {
        const html = text
          .split(/\n\s*\n/)
          .map((part) => `<p>${escapeHtml(part.trim()).replace(/\n/g, "<br>")}</p>`)
          .join("");
        document.execCommand("insertHTML", false, html);
      } else {
        document.execCommand("insertText", false, text);
      }
      sync();
    });
    const form = root.closest("form");
    if (form) form.addEventListener("submit", () => { if (!sourceMode) sync(); });

    try { document.execCommand("defaultParagraphSeparator", false, "p"); } catch (error) { /* older browsers */ }
    root.insertBefore(toolbar, textarea);
    root.insertBefore(editor, textarea);
    root.appendChild(fileInput);
    root.classList.add("is-ready");
  }

  const initAll = (scope) => (scope || document).querySelectorAll("[data-rte]").forEach(init);
  document.addEventListener("DOMContentLoaded", () => initAll());
  // Support editors inside admin inlines added dynamically.
  document.addEventListener("formset:added", (event) => initAll(event.target));
})();
