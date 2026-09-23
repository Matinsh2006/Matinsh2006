"""Small helpers for converting between the Gregorian dates Django/SQLite
store and the Jalali (Persian/Shamsi) calendar customers expect to see and
pick from. Kept dependency-free from any single app so every app can import
it (services, bookings, articles, accounts, ...).
"""

import datetime

import jdatetime

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

PERSIAN_MONTH_NAMES = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]

# Python's date.weekday(): Monday=0 ... Sunday=6. The Iranian week starts on
# Saturday, so this maps each Python weekday index to its Persian name.
PERSIAN_WEEKDAY_BY_PY_WEEKDAY = {
    5: "شنبه",
    6: "یکشنبه",
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنجشنبه",
    4: "جمعه",
}


def to_persian_digits(value):
    return str(value).translate(PERSIAN_DIGITS)


def _as_date(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


def gregorian_to_jalali(date_value):
    date_value = _as_date(date_value)
    return jdatetime.date.fromgregorian(date=date_value)


def jalali_to_gregorian(year, month, day):
    return jdatetime.date(year, month, day).togregorian()


def parse_jalali_date(value):
    """Parse a 'YYYY-MM-DD' (or 'YYYY/MM/DD') Jalali date string, accepting
    Persian digits, into a Gregorian ``datetime.date``. Returns ``None`` if
    the value can't be parsed."""
    if not value:
        return None
    normalized = str(value).strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    normalized = normalized.replace("/", "-")
    try:
        year_str, month_str, day_str = normalized.split("-")
        return jalali_to_gregorian(int(year_str), int(month_str), int(day_str))
    except (ValueError, TypeError):
        return None


def format_jalali_date(date_value, with_weekday=True):
    """Human readable Jalali date, e.g. 'دوشنبه ۱ مهر ۱۴۰۵'."""
    date_value = _as_date(date_value)
    if date_value is None:
        return ""
    jalali = gregorian_to_jalali(date_value)
    text = f"{to_persian_digits(jalali.day)} {PERSIAN_MONTH_NAMES[jalali.month - 1]} {to_persian_digits(jalali.year)}"
    if with_weekday:
        weekday_name = PERSIAN_WEEKDAY_BY_PY_WEEKDAY[date_value.weekday()]
        text = f"{weekday_name} {text}"
    return text


def format_jalali_numeric(date_value):
    """Compact numeric Jalali date, e.g. '۱۴۰۵/۰۷/۰۱'."""
    date_value = _as_date(date_value)
    if date_value is None:
        return ""
    jalali = gregorian_to_jalali(date_value)
    return to_persian_digits(f"{jalali.year:04d}/{jalali.month:02d}/{jalali.day:02d}")


def today_jalali_iso():
    """Today's Jalali date as 'YYYY-MM-DD', for wiring into the JS datepicker."""
    today = jdatetime.date.today()
    return f"{today.year:04d}-{today.month:02d}-{today.day:02d}"


def format_jalali_iso(date_value):
    """Ascii 'YYYY-MM-DD' Jalali string, used as a hidden-input value that the
    JS datepicker and the server both agree on (no locale/digit surprises)."""
    date_value = _as_date(date_value)
    if date_value is None:
        return ""
    jalali = gregorian_to_jalali(date_value)
    return f"{jalali.year:04d}-{jalali.month:02d}-{jalali.day:02d}"


def today_jalali_parts():
    """(year, month, day, weekday_index) for today, weekday_index being
    0=Saturday..6=Friday - the same anchor format the JS datepicker uses."""
    today = datetime.date.today()
    jalali = gregorian_to_jalali(today)
    weekday_index = [5, 6, 0, 1, 2, 3, 4].index(today.weekday())
    return jalali.year, jalali.month, jalali.day, weekday_index
