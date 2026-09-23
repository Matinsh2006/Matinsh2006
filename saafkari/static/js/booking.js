/*
 * منطق صفحه‌ی رزرو نوبت:
 *  ۱) تقویم شمسی با غیرفعال‌کردن روزهای تعطیل مغازه
 *  ۲) گرفتن ساعت‌های خالی از سرور و نمایش به صورت دکمه
 *  ۳) پیش‌نمایش عکس‌های انتخاب‌شده در هر باکس
 */
(function () {
  "use strict";

  var config = window.BOOKING_CONFIG || {};
  var dateInput = document.querySelector("input[data-jalali-date]");
  var serviceSelect = document.querySelector("[data-service-select]");
  var slotsBox = document.querySelector("[data-slots]");
  var slotInput = document.querySelector("[data-slot-input]");
  var serviceInfo = document.querySelector("[data-service-info]");

  function message(text) {
    slotsBox.innerHTML = "";
    var paragraph = document.createElement("p");
    paragraph.className = "col-span-full py-3 text-center text-sm text-slate-500";
    paragraph.textContent = text;
    slotsBox.appendChild(paragraph);
  }

  function selectSlot(button, value) {
    slotsBox.querySelectorAll("button").forEach(function (item) {
      item.dataset.selected = "false";
      item.className = "rounded-xl border border-slate-300 bg-white px-2 py-2.5 text-sm font-bold text-slate-700 transition hover:border-amber-500";
    });
    button.dataset.selected = "true";
    button.className = "rounded-xl border-2 border-amber-500 bg-amber-500 px-2 py-2.5 text-sm font-black text-slate-900";
    slotInput.value = value;
  }

  function renderSlots(slots) {
    slotsBox.innerHTML = "";
    if (!slots.length) {
      message("برای این روز ساعت خالی وجود ندارد. روز دیگری انتخاب کنید.");
      slotInput.value = "";
      return;
    }
    slots.forEach(function (time) {
      var button = document.createElement("button");
      button.type = "button";
      button.textContent = window.PersianDate ? window.PersianDate.toPersianDigits(time) : time;
      button.className = "rounded-xl border border-slate-300 bg-white px-2 py-2.5 text-sm font-bold text-slate-700 transition hover:border-amber-500";
      button.addEventListener("click", function () { selectSlot(button, time); });
      if (slotInput.value === time) { selectSlot(button, time); }
      slotsBox.appendChild(button);
    });
  }

  function loadSlots() {
    if (!dateInput || !dateInput.value) {
      message("ابتدا تاریخ را از تقویم انتخاب کنید.");
      return;
    }
    if (!serviceSelect || !serviceSelect.value) {
      message("ابتدا خدمت موردنظر را انتخاب کنید.");
      return;
    }
    message("در حال دریافت ساعت‌های خالی...");
    var url = config.slotsUrl + "?date=" + encodeURIComponent(dateInput.value)
            + "&service=" + encodeURIComponent(serviceSelect.value);
    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (!data.ok) { message(data.error || "دریافت ساعت‌ها ممکن نشد."); return; }
        renderSlots(data.slots || []);
        if (serviceInfo && data.duration) {
          serviceInfo.classList.remove("hidden");
          serviceInfo.textContent = "مدت تقریبی این خدمت " +
            (window.PersianDate ? window.PersianDate.toPersianDigits(data.duration) : data.duration) +
            " دقیقه است. ساعت پایان بر همین اساس رزرو می‌شود.";
        }
      })
      .catch(function () { message("خطا در ارتباط با سرور. دوباره تلاش کنید."); });
  }

  // ------------------------------------------------------------ راه‌اندازی
  if (dateInput && window.PersianDate) {
    dateInput.dataset.jalaliManual = "1";
    dateInput.dataset.jalaliReady = "1";
    window.PersianDate.attach(dateInput, {
      minDate: config.minDate,
      maxDate: config.maxDate,
      openWeekdays: config.openWeekdays,
      holidays: config.holidays,
      onSelect: loadSlots
    });
  }
  if (dateInput) { dateInput.addEventListener("change", loadSlots); }
  if (serviceSelect) { serviceSelect.addEventListener("change", loadSlots); }
  if (slotsBox && dateInput && dateInput.value && serviceSelect && serviceSelect.value) { loadSlots(); }

  // ------------------------------------------- پیش‌نمایش عکس‌های انتخاب‌شده
  document.querySelectorAll("[data-photo-box]").forEach(function (box) {
    var input = box.querySelector("[data-photo-input]");
    var preview = box.querySelector("[data-photo-preview]");
    var placeholder = box.querySelector("[data-photo-placeholder]");
    var nameLabel = box.querySelector("[data-photo-name]");
    if (!input) { return; }

    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) {
        preview.classList.add("hidden");
        placeholder.classList.remove("hidden");
        nameLabel.textContent = "برای انتخاب عکس کلیک کنید";
        return;
      }
      preview.src = URL.createObjectURL(file);
      preview.classList.remove("hidden");
      placeholder.classList.add("hidden");
      box.classList.add("border-amber-500", "bg-amber-50");
      var sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      nameLabel.textContent = window.PersianDate
        ? window.PersianDate.toPersianDigits(sizeMb) + " مگابایت — برای تغییر کلیک کنید"
        : sizeMb + " MB";
    });
  });
})();
