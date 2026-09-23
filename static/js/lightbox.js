(function () {
  "use strict";

  var lightbox = document.getElementById("lightbox");
  if (!lightbox) return;

  var image = document.getElementById("lightboxImage");
  var closeBtn = document.getElementById("lightboxClose");

  document.querySelectorAll("[data-lightbox-item]").forEach(function (el) {
    el.addEventListener("click", function () {
      image.src = el.getAttribute("data-full");
      lightbox.classList.add("is-open");
    });
  });

  function close() {
    lightbox.classList.remove("is-open");
    image.src = "";
  }

  closeBtn.addEventListener("click", close);
  lightbox.addEventListener("click", function (event) {
    if (event.target === lightbox) close();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") close();
  });
})();
