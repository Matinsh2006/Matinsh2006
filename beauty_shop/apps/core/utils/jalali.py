"""Gregorian → Jalali (Solar Hijri) conversion without external dependencies."""
import datetime

from django.utils import timezone

MONTH_NAMES = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)
# Indexed by ``date.weekday()`` (Monday == 0).
WEEKDAY_NAMES = ("دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه")

_DAYS_BEFORE_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def gregorian_to_jalali(gy, gm, gd):
    """Return ``(year, month, day)`` in the Jalali calendar."""
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + 365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        + gd
        + _DAYS_BEFORE_MONTH[gm - 1]
    )
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def format_jalali(value, fmt="%e %B %Y"):
    """
    Format a date/datetime as a Jalali string.

    Tokens: ``%Y`` year, ``%y`` 2-digit year, ``%m`` month (01), ``%n`` month (1),
    ``%d`` day (01), ``%e`` day (1), ``%B`` month name, ``%A`` weekday name,
    ``%H`` hour, ``%M`` minute.
    """
    if not value:
        return ""
    time_part = None
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        time_part = value
        value = value.date()
    elif not isinstance(value, datetime.date):
        return str(value)

    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    tokens = {
        "%Y": str(jy),
        "%y": f"{jy % 100:02d}",
        "%m": f"{jm:02d}",
        "%n": str(jm),
        "%d": f"{jd:02d}",
        "%e": str(jd),
        "%B": MONTH_NAMES[jm - 1],
        "%A": WEEKDAY_NAMES[value.weekday()],
        "%H": f"{time_part.hour:02d}" if time_part else "",
        "%M": f"{time_part.minute:02d}" if time_part else "",
    }
    result = fmt
    for token, replacement in tokens.items():
        result = result.replace(token, replacement)
    return result


def current_jalali_year():
    today = timezone.localdate()
    return gregorian_to_jalali(today.year, today.month, today.day)[0]
