/* رفتارهای عمومی سایت: منوی موبایل، اسلایدر، شمارش معکوس کد تایید و نمایش بزرگ عکس */
(function () {
  "use strict";

  function toPersian(value) {
    return String(value).replace(/\d/g, function (d) { return "۰۱۲۳۴۵۶۷۸۹"[d]; });
  }

  // ------------------------------------------------------------ منوی موبایل
  var menuButton = document.querySelector("[data-menu-toggle]");
  var mobileMenu = document.querySelector("[data-mobile-menu]");
  if (menuButton && mobileMenu) {
    menuButton.addEventListener("click", function () { mobileMenu.classList.toggle("hidden"); });
  }

  // ----------------------------------------------------- اسلایدر صفحه نخست
  var slider = document.querySelector("[data-hero-slider]");
  if (slider) {
    var slides = slider.querySelectorAll("[data-hero-slide]");
    var dots = slider.querySelectorAll("[data-hero-dot]");
    var index = 0;

    function show(target) {
      index = (target + slides.length) % slides.length;
      slides.forEach(function (slide, position) { slide.classList.toggle("hidden", position !== index); });
      dots.forEach(function (dot, position) {
        if (position === index) { dot.dataset.active = "true"; } else { delete dot.dataset.active; }
      });
    }

    dots.forEach(function (dot) {
      dot.addEventListener("click", function () { show(parseInt(dot.dataset.heroDot, 10)); });
    });
    if (slides.length > 1) { setInterval(function () { show(index + 1); }, 6000); }
  }

  // ------------------------------------------- شمارش معکوس کد تایید پیامکی
  var countdown = document.querySelector("[data-otp-countdown]");
  if (countdown) {
    var remaining = parseInt(countdown.dataset.otpCountdown, 10) || 0;
    var timer = setInterval(function () {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(timer);
        countdown.textContent = "پایان یافته";
        return;
      }
      countdown.textContent = toPersian(remaining);
    }, 1000);
  }

  var resendButton = document.querySelector("[data-resend]");
  if (resendButton) {
    var wait = parseInt(resendButton.dataset.resend, 10) || 0;
    var label = resendButton.textContent.trim();
    if (wait > 0) {
      resendButton.disabled = true;
      var resendTimer = setInterval(function () {
        wait -= 1;
        if (wait <= 0) {
          clearInterval(resendTimer);
          resendButton.disabled = false;
          resendButton.textContent = label;
          return;
        }
        resendButton.textContent = "ارسال دوباره تا " + toPersian(wait) + " ثانیه دیگر";
      }, 1000);
    }
  }

  // ------------------------------------------------- نمایش بزرگ عکس (لایت‌باکس)
  var lightbox = null;
  document.querySelectorAll("[data-lightbox]").forEach(function (image) {
    image.addEventListener("click", function () {
      if (!lightbox) {
        lightbox = document.createElement("div");
        lightbox.className = "fixed inset-0 z-[60] hidden items-center justify-center bg-black/85 p-6";
        lightbox.innerHTML = '<img alt="" class="max-h-full max-w-full rounded-xl object-contain">';
        lightbox.addEventListener("click", function () { lightbox.classList.add("hidden"); lightbox.classList.remove("flex"); });
        document.body.appendChild(lightbox);
      }
      lightbox.querySelector("img").src = image.src;
      lightbox.classList.remove("hidden");
      lightbox.classList.add("flex");
    });
  });

  // --------------------------------- تبدیل خودکار ارقام فارسی در ورودی‌های عددی
  document.querySelectorAll('input[inputmode="numeric"]').forEach(function (input) {
    input.addEventListener("blur", function () {
      input.value = input.value
        .replace(/[۰-۹]/g, function (d) { return String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)); })
        .replace(/[٠-٩]/g, function (d) { return String("٠١٢٣٤٥٦٧٨٩".indexOf(d)); });
    });
  });
})();
