/*
 * Minimal, dependency-free Jalali (Persian/Shamsi) calendar date picker.
 *
 * Design note: instead of re-implementing full Gregorian<->Jalali
 * conversion in JavaScript (an easy place to introduce off-by-one bugs),
 * this widget only ever does arithmetic *within* the Jalali calendar. It
 * anchors itself to "today" as computed by the trusted Python backend
 * (jdatetime, exposed via data-today-* attributes) and, from there, counts
 * days forward/backward using Jalali month/year lengths to know which
 * weekday any given day falls on. The server remains the single source of
 * truth for converting the picked date back to Gregorian on submit.
 *
 * Leap-year rule: the 33-year cycle approximation (a Jalali year is leap
 * when `year % 33` is one of 1,5,9,13,17,22,26,30). It is accurate for
 * centuries around the present day, which is all a booking calendar needs.
 */
(function () {
  "use strict";

  var PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
  var MONTH_NAMES = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
  ];
  var WEEKDAY_LETTERS = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
  var LEAP_REMAINDERS = [1, 5, 9, 13, 17, 22, 26, 30];

  function toPersianDigits(value) {
    return String(value).replace(/[0-9]/g, function (d) {
      return PERSIAN_DIGITS[+d];
    });
  }

  function pad2(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function isLeapJalaliYear(year) {
    var remainder = ((year % 33) + 33) % 33;
    return LEAP_REMAINDERS.indexOf(remainder) !== -1;
  }

  function daysInJalaliMonth(year, month) {
    if (month <= 6) return 31;
    if (month <= 11) return 30;
    return isLeapJalaliYear(year) ? 30 : 29;
  }

  function daysInJalaliYear(year) {
    return isLeapJalaliYear(year) ? 366 : 365;
  }

  function jalaliDayOfYear(year, month, day) {
    var days = day;
    for (var m = 1; m < month; m += 1) {
      days += daysInJalaliMonth(year, m);
    }
    return days;
  }

  // (y2,m2,d2) - (y1,m1,d1) in days, using only Jalali calendar arithmetic.
  function jalaliDaysBetween(y1, m1, d1, y2, m2, d2) {
    if (y1 === y2) {
      return jalaliDayOfYear(y2, m2, d2) - jalaliDayOfYear(y1, m1, d1);
    }
    if (y2 < y1) {
      return -jalaliDaysBetween(y2, m2, d2, y1, m1, d1);
    }
    var total = daysInJalaliYear(y1) - jalaliDayOfYear(y1, m1, d1);
    for (var y = y1 + 1; y < y2; y += 1) {
      total += daysInJalaliYear(y);
    }
    total += jalaliDayOfYear(y2, m2, d2);
    return total;
  }

  function monthOrdinal(year, month) {
    return year * 12 + month;
  }

  function Datepicker(root, options) {
    this.root = root;
    this.textInput = root.querySelector("[data-role=display]");
    this.hiddenInput = root.querySelector("[data-role=value]");
    this.popup = root.querySelector("[data-role=popup]");

    this.todayY = options.todayYear;
    this.todayM = options.todayMonth;
    this.todayD = options.todayDay;
    this.todayWeekday = options.todayWeekday; // 0=Saturday .. 6=Friday
    this.maxAdvanceDays = options.maxAdvanceDays || 90;
    this.maxAheadMonths = options.maxAheadMonths || 6;

    this.viewYear = this.todayY;
    this.viewMonth = this.todayM;

    var initial = options.initialValue;
    if (initial && /^\d{4}-\d{2}-\d{2}$/.test(initial)) {
      var parts = initial.split("-");
      this.viewYear = parseInt(parts[0], 10);
      this.viewMonth = parseInt(parts[1], 10);
      this.selectedDay = parseInt(parts[2], 10);
      this.selectedYear = this.viewYear;
      this.selectedMonth = this.viewMonth;
    }

    this._bind();
    this._render();
  }

  Datepicker.prototype._bind = function () {
    var self = this;

    this.textInput.addEventListener("click", function () {
      self._toggle();
    });
    this.textInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        self._toggle();
      }
    });

    document.addEventListener("click", function (event) {
      if (!root_contains(self.root, event.target)) {
        self._close();
      }
    });

    function root_contains(root, target) {
      return root === target || root.contains(target);
    }
  };

  Datepicker.prototype._toggle = function () {
    if (this.popup.hidden) {
      this._open();
    } else {
      this._close();
    }
  };

  Datepicker.prototype._open = function () {
    this.popup.hidden = false;
    this._renderCalendar();
  };

  Datepicker.prototype._close = function () {
    this.popup.hidden = true;
  };

  Datepicker.prototype._render = function () {
    if (this.selectedDay) {
      this._select(this.selectedYear, this.selectedMonth, this.selectedDay, false);
    }
    this._renderCalendar();
  };

  Datepicker.prototype._changeMonth = function (delta) {
    var ord = monthOrdinal(this.viewYear, this.viewMonth) + delta;
    this.viewYear = Math.floor((ord - 1) / 12);
    this.viewMonth = ord - this.viewYear * 12;
    this._renderCalendar();
  };

  Datepicker.prototype._weekdayOf = function (year, month, day) {
    var delta = jalaliDaysBetween(this.todayY, this.todayM, this.todayD, year, month, day);
    return ((this.todayWeekday + delta) % 7 + 7) % 7;
  };

  Datepicker.prototype._isDisabled = function (year, month, day) {
    var delta = jalaliDaysBetween(this.todayY, this.todayM, this.todayD, year, month, day);
    return delta < 0 || delta > this.maxAdvanceDays;
  };

  Datepicker.prototype._select = function (year, month, day, close) {
    this.selectedYear = year;
    this.selectedMonth = month;
    this.selectedDay = day;

    var iso = year + "-" + pad2(month) + "-" + pad2(day);
    this.hiddenInput.value = iso;

    var weekdayIndex = this._weekdayOf(year, month, day);
    var weekdayName = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"][weekdayIndex];
    this.textInput.value = weekdayName + " " + toPersianDigits(day) + " " + MONTH_NAMES[month - 1] + " " + toPersianDigits(year);

    this.hiddenInput.dispatchEvent(new Event("change", { bubbles: true }));

    if (close) {
      this._close();
    }
  };

  Datepicker.prototype._renderCalendar = function () {
    var self = this;
    var year = this.viewYear;
    var month = this.viewMonth;
    var totalDays = daysInJalaliMonth(year, month);
    var firstWeekday = this._weekdayOf(year, month, 1);

    var html = "";
    html += '<div class="jdp-header">';
    html += '<button type="button" class="jdp-nav" data-nav="prev">قبلی</button>';
    html += '<span class="jdp-title">' + MONTH_NAMES[month - 1] + " " + toPersianDigits(year) + "</span>";
    html += '<button type="button" class="jdp-nav" data-nav="next">بعدی</button>';
    html += "</div>";

    html += '<div class="jdp-weekdays">';
    for (var w = 0; w < 7; w += 1) {
      html += '<span>' + WEEKDAY_LETTERS[w] + "</span>";
    }
    html += "</div>";

    html += '<div class="jdp-days">';
    for (var i = 0; i < firstWeekday; i += 1) {
      html += '<span class="jdp-day jdp-day-empty"></span>';
    }
    for (var day = 1; day <= totalDays; day += 1) {
      var disabled = this._isDisabled(year, month, day);
      var isSelected = this.selectedYear === year && this.selectedMonth === month && this.selectedDay === day;
      var classes = "jdp-day";
      if (disabled) classes += " jdp-day-disabled";
      if (isSelected) classes += " jdp-day-selected";
      html += '<button type="button" class="' + classes + '" data-day="' + day + '"' + (disabled ? " disabled" : "") + ">" + toPersianDigits(day) + "</button>";
    }
    html += "</div>";

    this.popup.innerHTML = html;

    var canGoPrev = monthOrdinal(year, month) > monthOrdinal(this.todayY, this.todayM);
    var canGoNext = monthOrdinal(year, month) < monthOrdinal(this.todayY, this.todayM) + this.maxAheadMonths;
    var prevBtn = this.popup.querySelector('[data-nav=prev]');
    var nextBtn = this.popup.querySelector('[data-nav=next]');
    prevBtn.disabled = !canGoPrev;
    nextBtn.disabled = !canGoNext;

    prevBtn.addEventListener("click", function () {
      self._changeMonth(-1);
    });
    nextBtn.addEventListener("click", function () {
      self._changeMonth(1);
    });

    var dayButtons = this.popup.querySelectorAll(".jdp-day:not(.jdp-day-empty):not([disabled])");
    dayButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        self._select(year, month, parseInt(button.getAttribute("data-day"), 10), true);
      });
    });
  };

  function init(root) {
    if (root.dataset.jdpInitialized) return;
    root.dataset.jdpInitialized = "1";
    new Datepicker(root, {
      todayYear: parseInt(root.dataset.todayYear, 10),
      todayMonth: parseInt(root.dataset.todayMonth, 10),
      todayDay: parseInt(root.dataset.todayDay, 10),
      todayWeekday: parseInt(root.dataset.todayWeekday, 10),
      maxAdvanceDays: parseInt(root.dataset.maxAdvanceDays || "90", 10),
      maxAheadMonths: parseInt(root.dataset.maxAheadMonths || "6", 10),
      initialValue: root.dataset.initialValue || ""
    });
  }

  function initAll() {
    document.querySelectorAll("[data-jalali-datepicker]").forEach(init);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }

  window.JalaliDatepicker = {
    init: init,
    initAll: initAll,
    toPersianDigits: toPersianDigits,
    isLeapJalaliYear: isLeapJalaliYear,
    daysInJalaliMonth: daysInJalaliMonth,
    jalaliDaysBetween: jalaliDaysBetween
  };
})();
