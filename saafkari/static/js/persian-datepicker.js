/*
 * تقویم شمسی سبک و بدون وابستگی.
 * روی هر ورودی با ویژگی data-jalali-date یک تقویم فارسی باز می‌کند و
 * مقدار را به صورت «۱۴۰۵/۰۶/۳۱» (ارقام لاتین) در همان ورودی می‌گذارد.
 */
(function (global) {
  "use strict";

  var MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
  var WEEKDAYS = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
  var GREGORIAN_MONTH_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

  // ---------------------------------------------------------------- تبدیل‌ها
  function gregorianToJalali(gy, gm, gd) {
    var jy;
    if (gy > 1600) { jy = 979; gy -= 1600; } else { jy = 0; gy -= 621; }
    var gy2 = gm > 2 ? gy + 1 : gy;
    var days = 365 * gy + Math.floor((gy2 + 3) / 4) - Math.floor((gy2 + 99) / 100)
             + Math.floor((gy2 + 399) / 400) - 80 + gd + GREGORIAN_MONTH_DAYS[gm - 1];
    jy += 33 * Math.floor(days / 12053);
    days %= 12053;
    jy += 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days > 365) { jy += Math.floor((days - 1) / 365); days = (days - 1) % 365; }
    var jm, jd;
    if (days < 186) { jm = 1 + Math.floor(days / 31); jd = 1 + (days % 31); }
    else { jm = 7 + Math.floor((days - 186) / 30); jd = 1 + ((days - 186) % 30); }
    return [jy, jm, jd];
  }

  function jalaliToGregorian(jy, jm, jd) {
    var gy;
    if (jy > 979) { gy = 1600; jy -= 979; } else { gy = 621; }
    var days = 365 * jy + Math.floor(jy / 33) * 8 + Math.floor(((jy % 33) + 3) / 4)
             + 78 + jd + (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186);
    gy += 400 * Math.floor(days / 146097);
    days %= 146097;
    if (days > 36524) {
      days -= 1;
      gy += 100 * Math.floor(days / 36524);
      days %= 36524;
      if (days >= 365) { days += 1; }
    }
    gy += 4 * Math.floor(days / 1461);
    days %= 1461;
    if (days > 365) { gy += Math.floor((days - 1) / 365); days = (days - 1) % 365; }
    var gd = days + 1;
    var isLeap = (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0;
    var monthDays = [0, 31, isLeap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    var gm = 0;
    while (gm < 13 && gd > monthDays[gm]) { gd -= monthDays[gm]; gm += 1; }
    return [gy, gm, gd];
  }

  function isJalaliLeap(jy) { return ((((jy + 12) % 33) % 4) === 1); }

  function jalaliMonthLength(jy, jm) {
    if (jm <= 6) { return 31; }
    if (jm <= 11) { return 30; }
    return isJalaliLeap(jy) ? 30 : 29;
  }

  function toPersianDigits(value) {
    return String(value).replace(/\d/g, function (d) { return "۰۱۲۳۴۵۶۷۸۹"[d]; });
  }

  function toLatinDigits(value) {
    return String(value)
      .replace(/[۰-۹]/g, function (d) { return String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)); })
      .replace(/[٠-٩]/g, function (d) { return String("٠١٢٣٤٥٦٧٨٩".indexOf(d)); });
  }

  function pad(value) { return value < 10 ? "0" + value : String(value); }

  function formatJalali(jy, jm, jd) { return jy + "/" + pad(jm) + "/" + pad(jd); }

  function parseJalali(text) {
    var parts = toLatinDigits(text || "").trim().split(/\D+/).filter(Boolean);
    if (parts.length !== 3) { return null; }
    var jy = parseInt(parts[0], 10), jm = parseInt(parts[1], 10), jd = parseInt(parts[2], 10);
    if (!jy || jm < 1 || jm > 12 || jd < 1 || jd > jalaliMonthLength(jy, jm)) { return null; }
    return [jy, jm, jd];
  }

  /** شماره‌ی روز هفته به سبک ایرانی: شنبه=۰ */
  function jalaliWeekday(dateObj) { return (dateObj.getDay() + 1) % 7; }

  function toDate(jy, jm, jd) {
    var g = jalaliToGregorian(jy, jm, jd);
    return new Date(g[0], g[1] - 1, g[2]);
  }

  function isoOf(jy, jm, jd) {
    var g = jalaliToGregorian(jy, jm, jd);
    return g[0] + "-" + pad(g[1]) + "-" + pad(g[2]);
  }

  // ------------------------------------------------------------------ تقویم
  function PersianDatePicker(input, options) {
    this.input = input;
    this.options = options || {};
    this.minDate = parseJalali(this.options.minDate) || null;
    this.maxDate = parseJalali(this.options.maxDate) || null;
    this.openWeekdays = this.options.openWeekdays || null;
    this.holidays = this.options.holidays || [];
    this.onSelect = this.options.onSelect || function () {};

    var today = new Date();
    var current = parseJalali(input.value) || gregorianToJalali(today.getFullYear(), today.getMonth() + 1, today.getDate());
    this.viewYear = current[0];
    this.viewMonth = current[1];
    this.selected = parseJalali(input.value);

    this.build();
  }

  PersianDatePicker.prototype.build = function () {
    var self = this;
    var wrapper = document.createElement("div");
    wrapper.className = "relative";
    this.input.parentNode.insertBefore(wrapper, this.input);
    wrapper.appendChild(this.input);

    var panel = document.createElement("div");
    panel.className = "absolute z-40 mt-2 hidden w-[19rem] rounded-2xl border border-slate-200 bg-white p-4 shadow-xl";
    panel.setAttribute("dir", "rtl");
    wrapper.appendChild(panel);
    this.panel = panel;

    this.input.addEventListener("click", function () { self.toggle(); });
    this.input.addEventListener("focus", function () { self.open(); });
    document.addEventListener("click", function (event) {
      if (!wrapper.contains(event.target)) { self.close(); }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { self.close(); }
    });

    this.render();
  };

  PersianDatePicker.prototype.open = function () { this.panel.classList.remove("hidden"); this.render(); };
  PersianDatePicker.prototype.close = function () { this.panel.classList.add("hidden"); };
  PersianDatePicker.prototype.toggle = function () {
    if (this.panel.classList.contains("hidden")) { this.open(); } else { this.close(); }
  };

  PersianDatePicker.prototype.isDisabled = function (jy, jm, jd) {
    var value = jy * 10000 + jm * 100 + jd;
    if (this.minDate && value < this.minDate[0] * 10000 + this.minDate[1] * 100 + this.minDate[2]) { return true; }
    if (this.maxDate && value > this.maxDate[0] * 10000 + this.maxDate[1] * 100 + this.maxDate[2]) { return true; }
    if (this.holidays.indexOf(isoOf(jy, jm, jd)) !== -1) { return true; }
    if (this.openWeekdays && this.openWeekdays.length) {
      if (this.openWeekdays.indexOf(jalaliWeekday(toDate(jy, jm, jd))) === -1) { return true; }
    }
    return false;
  };

  PersianDatePicker.prototype.render = function () {
    var self = this;
    this.panel.innerHTML = "";

    // سربرگ: ماه و سال با دکمه‌های جابه‌جایی
    var header = document.createElement("div");
    header.className = "mb-3 flex items-center justify-between";
    var prev = document.createElement("button");
    prev.type = "button";
    prev.className = "rounded-lg px-3 py-1.5 text-lg text-slate-600 transition hover:bg-slate-100";
    prev.textContent = "›";
    prev.addEventListener("click", function (e) { e.preventDefault(); self.shift(-1); });
    var next = document.createElement("button");
    next.type = "button";
    next.className = "rounded-lg px-3 py-1.5 text-lg text-slate-600 transition hover:bg-slate-100";
    next.textContent = "‹";
    next.addEventListener("click", function (e) { e.preventDefault(); self.shift(1); });
    var title = document.createElement("span");
    title.className = "font-extrabold text-slate-900";
    title.textContent = MONTHS[this.viewMonth - 1] + " " + toPersianDigits(this.viewYear);
    header.appendChild(next);
    header.appendChild(title);
    header.appendChild(prev);
    this.panel.appendChild(header);

    // نام روزهای هفته
    var weekRow = document.createElement("div");
    weekRow.className = "mb-1 grid grid-cols-7 gap-1 text-center text-xs font-bold text-slate-400";
    WEEKDAYS.forEach(function (name) {
      var cell = document.createElement("span");
      cell.textContent = name;
      weekRow.appendChild(cell);
    });
    this.panel.appendChild(weekRow);

    // روزهای ماه
    var grid = document.createElement("div");
    grid.className = "grid grid-cols-7 gap-1";
    var firstWeekday = jalaliWeekday(toDate(this.viewYear, this.viewMonth, 1));
    for (var blank = 0; blank < firstWeekday; blank += 1) {
      grid.appendChild(document.createElement("span"));
    }

    var total = jalaliMonthLength(this.viewYear, this.viewMonth);
    var todayJ = (function () {
      var t = new Date();
      return gregorianToJalali(t.getFullYear(), t.getMonth() + 1, t.getDate());
    })();

    for (var day = 1; day <= total; day += 1) {
      (function (dayNumber) {
        var disabled = self.isDisabled(self.viewYear, self.viewMonth, dayNumber);
        var isSelected = self.selected && self.selected[0] === self.viewYear
                      && self.selected[1] === self.viewMonth && self.selected[2] === dayNumber;
        var isToday = todayJ[0] === self.viewYear && todayJ[1] === self.viewMonth && todayJ[2] === dayNumber;

        var cell = document.createElement("button");
        cell.type = "button";
        cell.textContent = toPersianDigits(dayNumber);
        cell.className = "rounded-lg py-2 text-sm transition "
          + (disabled ? "cursor-not-allowed text-slate-300 line-through"
                      : "text-slate-700 hover:bg-amber-100 ")
          + (isSelected ? " bg-amber-500 font-black text-slate-900 hover:bg-amber-500" : "")
          + (!isSelected && isToday ? " ring-1 ring-amber-400" : "");
        if (disabled) {
          cell.disabled = true;
        } else {
          cell.addEventListener("click", function (event) {
            event.preventDefault();
            self.select(self.viewYear, self.viewMonth, dayNumber);
          });
        }
        grid.appendChild(cell);
      })(day);
    }
    this.panel.appendChild(grid);

    var hint = document.createElement("p");
    hint.className = "mt-3 border-t border-slate-100 pt-2 text-center text-xs text-slate-400";
    hint.textContent = "روزهای تعطیل مغازه غیرفعال هستند.";
    this.panel.appendChild(hint);
  };

  PersianDatePicker.prototype.shift = function (delta) {
    this.viewMonth += delta;
    if (this.viewMonth > 12) { this.viewMonth = 1; this.viewYear += 1; }
    if (this.viewMonth < 1) { this.viewMonth = 12; this.viewYear -= 1; }
    this.render();
  };

  PersianDatePicker.prototype.select = function (jy, jm, jd) {
    this.selected = [jy, jm, jd];
    this.input.value = formatJalali(jy, jm, jd);
    this.close();
    this.input.dispatchEvent(new Event("change", { bubbles: true }));
    this.onSelect(formatJalali(jy, jm, jd), isoOf(jy, jm, jd));
  };

  global.PersianDate = {
    gregorianToJalali: gregorianToJalali,
    jalaliToGregorian: jalaliToGregorian,
    jalaliMonthLength: jalaliMonthLength,
    toPersianDigits: toPersianDigits,
    toLatinDigits: toLatinDigits,
    parseJalali: parseJalali,
    formatJalali: formatJalali,
    attach: function (input, options) { return new PersianDatePicker(input, options); }
  };

  // اتصال خودکار به ورودی‌هایی که تنظیمات ویژه ندارند
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("input[data-jalali-date]:not([data-jalali-manual])").forEach(function (input) {
      if (input.dataset.jalaliReady === "1") { return; }
      input.dataset.jalaliReady = "1";
      new PersianDatePicker(input, {
        minDate: input.dataset.minDate,
        maxDate: input.dataset.maxDate
      });
    });
  });
})(window);
