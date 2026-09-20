/* اسکریپت‌های عمومی فروشگاه: اسلایدر خودکار، منوی موبایل، سبد خرید و شمارنده کد تایید */
(function () {
  'use strict';

  /* ---------------------------------------------------------------
   * اسلایدر خودکار (هم برای بنرهای زیر هدر و هم گالری عکس محصولات)
   * ساختار: [data-carousel] > [data-carousel-track] > [data-carousel-slide]
   * ------------------------------------------------------------- */
  function initCarousel(root) {
    var track = root.querySelector('[data-carousel-track]');
    var slides = Array.prototype.slice.call(root.querySelectorAll('[data-carousel-slide]'));
    if (!track || slides.length === 0) return;

    var dots = Array.prototype.slice.call(root.querySelectorAll('[data-carousel-dot]'));
    var thumbs = Array.prototype.slice.call(root.querySelectorAll('[data-carousel-thumb]'));
    var interval = parseInt(root.dataset.interval || '5000', 10);
    var index = 0;
    var timer = null;

    function render() {
      track.style.transform = 'translateX(' + (-index * 100) + '%)';
      dots.forEach(function (dot, i) {
        dot.classList.toggle('is-active', i === index);
        dot.setAttribute('aria-current', i === index ? 'true' : 'false');
      });
      thumbs.forEach(function (thumb, i) {
        thumb.classList.toggle('is-active', i === index);
      });
      slides.forEach(function (slide, i) {
        slide.setAttribute('aria-hidden', i === index ? 'false' : 'true');
      });
    }

    function goTo(next) {
      index = (next + slides.length) % slides.length;
      render();
    }

    function play() {
      if (slides.length < 2 || interval <= 0) return;
      stop();
      timer = setInterval(function () { goTo(index + 1); }, interval);
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
    }

    root.querySelectorAll('[data-carousel-prev]').forEach(function (btn) {
      btn.addEventListener('click', function () { goTo(index - 1); play(); });
    });
    root.querySelectorAll('[data-carousel-next]').forEach(function (btn) {
      btn.addEventListener('click', function () { goTo(index + 1); play(); });
    });
    dots.concat(thumbs).forEach(function (el, i) {
      el.addEventListener('click', function () {
        goTo(parseInt(el.dataset.index || i, 10));
        play();
      });
    });

    root.addEventListener('mouseenter', stop);
    root.addEventListener('mouseleave', play);
    document.addEventListener('visibilitychange', function () {
      document.hidden ? stop() : play();
    });

    /* پشتیبانی از کشیدن انگشت روی موبایل */
    var startX = 0;
    root.addEventListener('touchstart', function (e) {
      startX = e.touches[0].clientX;
      stop();
    }, { passive: true });
    root.addEventListener('touchend', function (e) {
      var delta = e.changedTouches[0].clientX - startX;
      if (Math.abs(delta) > 45) { goTo(delta > 0 ? index - 1 : index + 1); }
      play();
    });

    render();
    play();
  }

  /* ------------------------- منوی موبایل ------------------------- */
  function initMobileMenu() {
    var toggle = document.querySelector('[data-mobile-menu-toggle]');
    var menu = document.querySelector('[data-mobile-menu]');
    if (!toggle || !menu) return;
    toggle.addEventListener('click', function () { menu.classList.toggle('hidden'); });
  }

  /* ------------------ افزودن به سبد خرید با ایجکس ---------------- */
  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  function showToast(text, ok) {
    var toast = document.createElement('div');
    toast.className = 'fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl px-5 py-3 text-sm font-bold text-white shadow-lg transition ' +
      (ok ? 'bg-emerald-600' : 'bg-rose-600');
    toast.textContent = text;
    document.body.appendChild(toast);
    setTimeout(function () { toast.style.opacity = '0'; }, 2200);
    setTimeout(function () { toast.remove(); }, 2700);
  }

  function initAjaxCart() {
    document.querySelectorAll('form[data-cart-form]').forEach(function (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        var button = form.querySelector('[type="submit"]');
        if (button) { button.disabled = true; button.classList.add('opacity-60'); }

        fetch(form.action, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') },
          body: new FormData(form)
        })
          .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
          .then(function (result) {
            showToast(result.data.message || (result.ok ? 'انجام شد' : 'خطا'), result.ok);
            var badge = document.querySelector('[data-cart-count]');
            if (badge && typeof result.data.items_count !== 'undefined') {
              badge.textContent = toPersianDigits(result.data.items_count);
              badge.classList.toggle('hidden', result.data.items_count === 0);
            }
          })
          .catch(function () { showToast('ارتباط با سرور برقرار نشد.', false); })
          .finally(function () {
            if (button) { button.disabled = false; button.classList.remove('opacity-60'); }
          });
      });
    });
  }

  function toPersianDigits(value) {
    return String(value).replace(/\d/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[d]; });
  }

  /* ------------- شمارنده معکوس ارسال دوباره کد پیامکی ------------- */
  function initOtpCountdown() {
    var el = document.querySelector('[data-otp-countdown]');
    if (!el) return;
    var seconds = parseInt(el.dataset.otpCountdown || '0', 10);
    var resend = document.querySelector('[data-otp-resend]');

    function tick() {
      if (seconds <= 0) {
        el.classList.add('hidden');
        if (resend) resend.classList.remove('hidden');
        return;
      }
      var m = Math.floor(seconds / 60);
      var s = seconds % 60;
      el.textContent = 'اعتبار کد: ' + toPersianDigits(m + ':' + (s < 10 ? '0' + s : s));
      seconds -= 1;
      setTimeout(tick, 1000);
    }
    if (resend && seconds > 0) resend.classList.add('hidden');
    tick();
  }

  /* --------- ورود خودکار ارقام کد تایید و تبدیل عدد فارسی -------- */
  function initNumericInputs() {
    document.querySelectorAll('input[inputmode="numeric"]').forEach(function (input) {
      input.addEventListener('input', function () {
        input.value = input.value.replace(/[۰-۹]/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'.indexOf(d); })
                                 .replace(/[٠-٩]/g, function (d) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(d); });
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-carousel]').forEach(initCarousel);
    initMobileMenu();
    initAjaxCart();
    initOtpCountdown();
    initNumericInputs();
  });

  window.ShopUI = { initCarousel: initCarousel, showToast: showToast };
})();
