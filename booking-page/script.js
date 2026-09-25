/* See Villa On West Blvd — favorite button and booking sheet */
(() => {
  'use strict';

  const BOOKING = {
    pricePerNight: 330,
    cleaningFee: 40,
    defaultGuests: 2,
    maxGuests: 4,
    monthsAhead: 12,
    weekStartsOn: 0, // 0 = Sunday, 1 = Monday, 6 = Saturday
    locale: 'en-US',
    currency: 'USD',
  };
  const FAVORITE_KEY = 'see-villa-west-blvd:favorite';
  const DAY_MS = 24 * 60 * 60 * 1000;

  const $ = (selector, root = document) => root.querySelector(selector);

  const money = new Intl.NumberFormat(BOOKING.locale, {
    style: 'currency',
    currency: BOOKING.currency,
    maximumFractionDigits: 0,
  });
  const shortDate = new Intl.DateTimeFormat(BOOKING.locale, { weekday: 'short', month: 'short', day: 'numeric' });
  const longDate = new Intl.DateTimeFormat(BOOKING.locale, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
  const monthName = new Intl.DateTimeFormat(BOOKING.locale, { month: 'long', year: 'numeric' });
  const weekdayName = new Intl.DateTimeFormat(BOOKING.locale, { weekday: 'short' });
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ---------- date helpers (all dates are local midnights) ---------- */

  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const startOfMonth = (d) => new Date(d.getFullYear(), d.getMonth(), 1);
  const addDays = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
  const addMonths = (d, n) => new Date(d.getFullYear(), d.getMonth() + n, 1);
  const nightsBetween = (from, to) => Math.round((to - from) / DAY_MS);
  const isSameDay = (a, b) => Boolean(a && b) && a.getTime() === b.getTime();
  const toKey = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const fromKey = (key) => {
    const [y, m, d] = key.split('-').map(Number);
    return new Date(y, m - 1, d);
  };
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

  /* ---------- favorite (heart) ---------- */

  const storage = {
    get(key) {
      try { return window.localStorage.getItem(key); } catch { return null; }
    },
    set(key, value) {
      try { window.localStorage.setItem(key, value); } catch { /* storage unavailable */ }
    },
  };

  const favButton = $('.fav');

  favButton.setAttribute('aria-pressed', String(storage.get(FAVORITE_KEY) === '1'));

  favButton.addEventListener('click', () => {
    const isFavorite = favButton.getAttribute('aria-pressed') !== 'true';
    favButton.setAttribute('aria-pressed', String(isFavorite));
    storage.set(FAVORITE_KEY, isFavorite ? '1' : '0');

    favButton.classList.remove('is-popping');
    if (isFavorite) {
      void favButton.offsetWidth; // restart the animation
      favButton.classList.add('is-popping');
    }
  });

  favButton.addEventListener('animationend', () => favButton.classList.remove('is-popping'));

  /* ---------- booking sheet ---------- */

  const sheet = $('#booking');
  const panel = $('.sheet__panel', sheet);
  const form = $('#booking-form');
  const doneView = $('.done', sheet);
  const doneTitle = $('.done__title', sheet);
  const confirmButton = $('.confirm', form);
  const grid = $('.cal__grid', sheet);
  const monthLabel = $('#cal-month');
  const prevMonthButton = $('[data-month="-1"]', sheet);
  const nextMonthButton = $('[data-month="1"]', sheet);
  const lessGuestsButton = $('[data-guests="-1"]', sheet);
  const moreGuestsButton = $('[data-guests="1"]', sheet);
  const summary = $('.summary', sheet);
  const dateCells = { in: $('[data-field="in"]', sheet), out: $('[data-field="out"]', sheet) };
  const el = {
    checkIn: $('#checkin-value'),
    checkOut: $('#checkout-value'),
    guests: $('#guests'),
    maxGuests: $('#max-guests'),
    nights: $('#nights-label'),
    subtotal: $('#subtotal'),
    cleaningFee: $('#cleaning-fee'),
    total: $('#total'),
    doneIn: $('#done-in'),
    doneOut: $('#done-out'),
    doneGuests: $('#done-guests'),
    doneTotal: $('#done-total'),
  };

  const state = {
    today: startOfDay(new Date()),
    view: startOfMonth(new Date()),
    checkIn: null,
    checkOut: null,
    hover: null,
    guests: BOOKING.defaultGuests,
    submitting: false,
    booked: false,
  };

  let submitTimer = 0;
  let closeTimer = 0;

  const getNights = () => (state.checkIn && state.checkOut ? nightsBetween(state.checkIn, state.checkOut) : 0);
  const getTotal = () => getNights() * BOOKING.pricePerNight + BOOKING.cleaningFee;

  /* weekday header row */
  const weekdays = $('.cal__weekdays', sheet);
  for (let i = 0; i < 7; i += 1) {
    const label = document.createElement('span');
    // 1 Feb 2026 was a Sunday
    label.textContent = weekdayName.format(new Date(2026, 1, 1 + ((BOOKING.weekStartsOn + i) % 7))).slice(0, 2);
    weekdays.append(label);
  }

  function renderCalendar() {
    const { view, today } = state;
    const firstMonth = startOfMonth(today);
    const lastMonth = addMonths(firstMonth, BOOKING.monthsAhead);

    monthLabel.textContent = monthName.format(view);
    prevMonthButton.disabled = view <= firstMonth;
    nextMonthButton.disabled = view >= lastMonth;

    const offset = (view.getDay() - BOOKING.weekStartsOn + 7) % 7;
    const daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
    const cells = document.createDocumentFragment();

    for (let i = 0; i < offset; i += 1) {
      cells.append(document.createElement('span'));
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const date = new Date(view.getFullYear(), view.getMonth(), day);
      const button = document.createElement('button');
      const number = document.createElement('span');

      button.type = 'button';
      button.className = 'day';
      button.tabIndex = -1;
      button.dataset.date = toKey(date);
      button.dataset.label = longDate.format(date);
      button.disabled = date < today;
      button.classList.toggle('is-today', isSameDay(date, today));
      number.textContent = String(day);
      button.append(number);
      cells.append(button);
    }

    grid.replaceChildren(cells);
    paintRange();

    const tabStop =
      (state.checkIn && grid.querySelector(`[data-date="${toKey(state.checkIn)}"]`)) ||
      grid.querySelector('.day.is-today') ||
      grid.querySelector('.day:not(:disabled)');
    if (tabStop) tabStop.tabIndex = 0;
  }

  function paintRange() {
    const { checkIn, checkOut, hover } = state;
    const previewEnd = checkIn && !checkOut && hover && hover > checkIn ? hover : null;
    const end = checkOut || previewEnd;

    grid.querySelectorAll('.day').forEach((button) => {
      const date = fromKey(button.dataset.date);
      const isStart = isSameDay(date, checkIn);
      const isEnd = isSameDay(date, checkOut);

      button.classList.toggle('is-start', isStart);
      button.classList.toggle('is-end', isEnd);
      button.classList.toggle('is-preview-end', isSameDay(date, previewEnd));
      button.classList.toggle('has-range', isStart && Boolean(end));
      button.classList.toggle('is-in-range', Boolean(checkIn && end && date > checkIn && date < end));
      button.setAttribute('aria-pressed', String(isStart || isEnd));

      let label = button.dataset.label;
      if (isStart) label += ', check-in';
      if (isEnd) label += ', check-out';
      button.setAttribute('aria-label', label);
    });
  }

  function setTabStop(button) {
    grid.querySelectorAll('.day[tabindex="0"]').forEach((b) => { b.tabIndex = -1; });
    button.tabIndex = 0;
  }

  function selectDate(date) {
    if (!state.checkIn || state.checkOut || date <= state.checkIn) {
      state.checkIn = date;
      state.checkOut = null;
    } else {
      state.checkOut = date;
    }
    state.hover = null;
    paintRange();
    updateSummary();
  }

  function setDateValue(node, date) {
    node.textContent = date ? shortDate.format(date) : 'Add date';
    node.classList.toggle('is-empty', !date);
  }

  function updateSummary() {
    const nights = getNights();

    setDateValue(el.checkIn, state.checkIn);
    setDateValue(el.checkOut, state.checkOut);
    dateCells.in.classList.toggle('is-active', !state.checkIn);
    dateCells.out.classList.toggle('is-active', Boolean(state.checkIn && !state.checkOut));

    summary.classList.toggle('is-empty', nights === 0);
    if (nights > 0) {
      el.nights.textContent = `${money.format(BOOKING.pricePerNight)} × ${plural(nights, 'night')}`;
      el.subtotal.textContent = money.format(nights * BOOKING.pricePerNight);
      el.cleaningFee.textContent = money.format(BOOKING.cleaningFee);
      el.total.textContent = money.format(getTotal());
    }

    if (!state.submitting) {
      confirmButton.disabled = nights === 0;
      if (nights > 0) {
        confirmButton.textContent = `Reserve · ${money.format(getTotal())}`;
      } else {
        confirmButton.textContent = state.checkIn ? 'Select check-out date' : 'Select your dates';
      }
    }
  }

  function setGuests(count) {
    state.guests = Math.min(BOOKING.maxGuests, Math.max(1, count));
    el.guests.textContent = String(state.guests);
    lessGuestsButton.disabled = state.guests <= 1;
    moreGuestsButton.disabled = state.guests >= BOOKING.maxGuests;
  }

  function resetBooking() {
    window.clearTimeout(submitTimer);
    Object.assign(state, { checkIn: null, checkOut: null, hover: null, submitting: false, booked: false });
    confirmButton.classList.remove('is-loading');
    confirmButton.removeAttribute('aria-busy');
    form.hidden = false;
    doneView.hidden = true;
    setGuests(BOOKING.defaultGuests);
    updateSummary();
  }

  function showConfirmation() {
    const nights = getNights();
    state.submitting = false;
    state.booked = true;

    el.doneIn.textContent = shortDate.format(state.checkIn);
    el.doneOut.textContent = shortDate.format(state.checkOut);
    el.doneGuests.textContent = plural(state.guests, 'guest');
    el.doneTotal.textContent = `${money.format(getTotal())} · ${plural(nights, 'night')}`;

    form.hidden = true;
    doneView.hidden = false;
    panel.scrollTop = 0;
    doneTitle.focus();
  }

  /* ---------- open / close ---------- */

  function openSheet() {
    if (sheet.open) return;

    state.today = startOfDay(new Date());
    if (state.booked || (state.checkIn && state.checkIn < state.today)) resetBooking();
    state.view = startOfMonth(state.checkIn || state.today);
    renderCalendar();
    updateSummary();

    sheet.showModal();
    document.documentElement.classList.add('is-locked');
    panel.scrollTop = 0;
    // wait a frame so the entry transition runs
    requestAnimationFrame(() => requestAnimationFrame(() => sheet.classList.add('is-open')));
  }

  function closeSheet() {
    if (!sheet.open || sheet.classList.contains('is-closing')) return;

    sheet.classList.remove('is-open');
    sheet.classList.add('is-closing');

    const finish = () => {
      window.clearTimeout(closeTimer);
      panel.removeEventListener('transitionend', onTransitionEnd);
      if (sheet.open) sheet.close();
    };
    const onTransitionEnd = (event) => {
      if (event.target === panel) finish();
    };

    if (reducedMotion.matches) {
      finish();
      return;
    }
    panel.addEventListener('transitionend', onTransitionEnd);
    closeTimer = window.setTimeout(finish, 500);
  }

  // runs however the dialog was closed
  sheet.addEventListener('close', () => {
    sheet.classList.remove('is-open', 'is-closing');
    document.documentElement.classList.remove('is-locked');
    if (state.submitting) resetBooking();
  });

  // Esc
  sheet.addEventListener('cancel', (event) => {
    event.preventDefault();
    closeSheet();
  });

  // backdrop click (only when the press also started on the backdrop)
  let pressedBackdrop = false;
  sheet.addEventListener('pointerdown', (event) => {
    pressedBackdrop = event.target === sheet;
  });

  sheet.addEventListener('click', (event) => {
    if (event.target.closest('[data-close]') || (event.target === sheet && pressedBackdrop)) {
      closeSheet();
    }
    pressedBackdrop = false;
  });

  $('.reserve').addEventListener('click', openSheet);

  /* ---------- calendar interactions ---------- */

  [prevMonthButton, nextMonthButton].forEach((button) => {
    button.addEventListener('click', () => {
      state.view = addMonths(state.view, Number(button.dataset.month));
      renderCalendar();
      if (button.disabled) (button === prevMonthButton ? nextMonthButton : prevMonthButton).focus();
    });
  });

  grid.addEventListener('click', (event) => {
    const button = event.target.closest('.day');
    if (!button || button.disabled) return;
    setTabStop(button);
    selectDate(fromKey(button.dataset.date));
  });

  // preview the stay while choosing the check-out date
  grid.addEventListener('pointerover', (event) => {
    const button = event.target.closest('.day');
    const date = button && !button.disabled ? fromKey(button.dataset.date) : null;
    if (isSameDay(date, state.hover)) return;
    state.hover = date;
    if (state.checkIn && !state.checkOut) paintRange();
  });

  grid.addEventListener('pointerleave', () => {
    state.hover = null;
    if (state.checkIn && !state.checkOut) paintRange();
  });

  // arrow keys move between days, across months if needed
  grid.addEventListener('keydown', (event) => {
    const button = event.target.closest('.day');
    const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
    if (!button || step === undefined) return;
    event.preventDefault();

    const target = addDays(fromKey(button.dataset.date), step);
    if (target < state.today) return;

    if (target.getMonth() !== state.view.getMonth() || target.getFullYear() !== state.view.getFullYear()) {
      if (startOfMonth(target) > addMonths(startOfMonth(state.today), BOOKING.monthsAhead)) return;
      state.view = startOfMonth(target);
      renderCalendar();
    }

    const next = grid.querySelector(`[data-date="${toKey(target)}"]`);
    if (!next) return;
    setTabStop(next);
    next.focus();
    if (state.checkIn && !state.checkOut) {
      state.hover = target;
      paintRange();
    }
  });

  /* ---------- guests + submit ---------- */

  [lessGuestsButton, moreGuestsButton].forEach((button) => {
    button.addEventListener('click', () => {
      setGuests(state.guests + Number(button.dataset.guests));
      if (button.disabled) (button === lessGuestsButton ? moreGuestsButton : lessGuestsButton).focus();
    });
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (state.submitting || getNights() === 0) return;

    state.submitting = true;
    const spinner = document.createElement('span');
    spinner.className = 'spinner';
    spinner.setAttribute('aria-hidden', 'true');
    confirmButton.replaceChildren(spinner, 'Reserving…');
    confirmButton.classList.add('is-loading');
    confirmButton.setAttribute('aria-busy', 'true');

    // stands in for the request to a booking API
    submitTimer = window.setTimeout(showConfirmation, reducedMotion.matches ? 0 : 900);
  });

  /* ---------- init ---------- */

  el.maxGuests.textContent = String(BOOKING.maxGuests);
  setGuests(BOOKING.defaultGuests);
  updateSummary();
})();
