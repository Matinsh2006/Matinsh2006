"""
ابزار تبدیل و قالب‌بندی تاریخ شمسی (جلالی) — بدون وابستگی خارجی.

الگوریتم تبدیل، پیاده‌سازی استاندارد و آزموده‌ی تقویم جلالی است و برای
بازه‌ی سال‌های میلادی ۶۲۲ تا ۲۵۰۰ معتبر است.
"""
from __future__ import annotations

import datetime as _dt
import re

MONTH_NAMES = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)
# شنبه = ۰ ... جمعه = ۶
WEEKDAY_NAMES = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")
WEEKDAY_SHORT = ("ش", "ی", "د", "س", "چ", "پ", "ج")

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_TO_LATIN = {ord(c): str(i) for i, c in enumerate(PERSIAN_DIGITS)}
_TO_LATIN.update({ord(c): str(i) for i, c in enumerate(ARABIC_DIGITS)})
_TO_PERSIAN = {ord(str(i)): c for i, c in enumerate(PERSIAN_DIGITS)}

_GREGORIAN_MONTH_DAYS = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def to_latin_digits(value) -> str:
    """ارقام فارسی/عربی را به لاتین تبدیل می‌کند."""
    if value is None:
        return ""
    return str(value).translate(_TO_LATIN)


def to_persian_digits(value) -> str:
    """ارقام لاتین را به فارسی تبدیل می‌کند."""
    if value is None:
        return ""
    return str(value).translate(_TO_PERSIAN)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ میلادی به شمسی."""
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + _GREGORIAN_MONTH_DAYS[gm - 1]
    )
    jy += 33 * (days // 12053)
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


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ شمسی به میلادی."""
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = (
        365 * jy
        + (jy // 33) * 8
        + ((jy % 33) + 3) // 4
        + 78
        + jd
        + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    )
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    month_days = [
        0, 31, 29 if is_gregorian_leap(gy) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31,
    ]
    gm = 0
    while gm < 13 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return gy, gm, gd


def is_gregorian_leap(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def is_jalali_leap(jy: int) -> bool:
    """سال کبیسه‌ی شمسی بر اساس چرخه‌ی ۳۳ ساله."""
    return (((jy + 12) % 33) % 4) == 1


def jalali_month_length(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def jalali_weekday(date: _dt.date) -> int:
    """شماره‌ی روز هفته به سبک ایرانی: شنبه=۰ تا جمعه=۶."""
    return (date.weekday() + 2) % 7


def date_to_jalali(value) -> tuple[int, int, int] | None:
    """یک ‎date/datetime‎ را به سه‌تایی شمسی تبدیل می‌کند."""
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        value = _localize(value).date()
    if not isinstance(value, _dt.date):
        return None
    return gregorian_to_jalali(value.year, value.month, value.day)


def _localize(value: _dt.datetime) -> _dt.datetime:
    """در صورت فعال‌بودن منطقه‌ی زمانی، تاریخ را به وقت محلی می‌برد."""
    try:
        from django.utils import timezone

        if timezone.is_aware(value):
            return timezone.localtime(value)
    except Exception:  # pragma: no cover - خارج از چرخه‌ی جنگو
        pass
    return value


def format_jalali(value, fmt: str = "%d %B %Y", persian_digits: bool = True) -> str:
    """
    قالب‌بندی تاریخ شمسی.

    نگه‌دارنده‌ها: ‎%Y‎ سال، ‎%m‎ ماه دو رقمی، ‎%-m‎ ماه، ‎%d‎ روز دو رقمی،
    ‎%-d‎ روز، ‎%B‎ نام ماه، ‎%A‎ نام روز هفته، ‎%H:%M‎ ساعت و دقیقه.
    """
    if value is None:
        return ""
    jalali = date_to_jalali(value)
    if jalali is None:
        return ""
    jy, jm, jd = jalali
    base = value.date() if isinstance(value, _dt.datetime) else value
    if isinstance(value, _dt.datetime):
        local = _localize(value)
        base = local.date()
        hour, minute, second = local.hour, local.minute, local.second
    else:
        hour = minute = second = 0
    replacements = {
        "%Y": f"{jy:04d}",
        "%y": f"{jy % 100:02d}",
        "%m": f"{jm:02d}",
        "%-m": str(jm),
        "%d": f"{jd:02d}",
        "%-d": str(jd),
        "%B": MONTH_NAMES[jm - 1],
        "%A": WEEKDAY_NAMES[jalali_weekday(base)],
        "%a": WEEKDAY_SHORT[jalali_weekday(base)],
        "%H": f"{hour:02d}",
        "%M": f"{minute:02d}",
        "%S": f"{second:02d}",
    }
    out = fmt
    for key in ("%-m", "%-d", "%Y", "%y", "%m", "%d", "%B", "%A", "%a", "%H", "%M", "%S"):
        out = out.replace(key, replacements[key])
    return to_persian_digits(out) if persian_digits else out


_DATE_RE = re.compile(r"^(\d{4})\D(\d{1,2})\D(\d{1,2})$")


def parse_jalali(value: str) -> _dt.date:
    """
    رشته‌ی تاریخ شمسی («۱۴۰۵/۰۶/۳۱» یا «1405-06-31») را به ‎date‎ میلادی
    تبدیل می‌کند. در صورت نامعتبر بودن، ‎ValueError‎ می‌دهد.
    """
    text = to_latin_digits(value).strip()
    match = _DATE_RE.match(text)
    if not match:
        raise ValueError("قالب تاریخ باید به صورت ۱۴۰۴/۰۱/۰۱ باشد.")
    jy, jm, jd = (int(part) for part in match.groups())
    if not 1 <= jm <= 12:
        raise ValueError("شماره‌ی ماه شمسی باید بین ۱ تا ۱۲ باشد.")
    if not 1 <= jd <= jalali_month_length(jy, jm):
        raise ValueError("روز واردشده در این ماه شمسی وجود ندارد.")
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    return _dt.date(gy, gm, gd)


def jalali_str(value, sep: str = "/", persian_digits: bool = False) -> str:
    """نمایش عددی تاریخ شمسی، مناسب مقداردهی فیلدهای فرم."""
    jalali = date_to_jalali(value)
    if jalali is None:
        return ""
    jy, jm, jd = jalali
    text = f"{jy:04d}{sep}{jm:02d}{sep}{jd:02d}"
    return to_persian_digits(text) if persian_digits else text


def today_jalali() -> tuple[int, int, int]:
    from django.utils import timezone

    return date_to_jalali(timezone.localdate())
