"""فیلترها و تگ‌های قالب برای نمایش فارسی: تاریخ شمسی، ارقام و مبلغ."""
from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

from core.jalali import format_jalali, jalali_str, to_persian_digits

register = template.Library()


@register.filter(name="jalali")
def jalali(value, fmt: str = "%d %B %Y"):
    """نمایش تاریخ شمسی: ‎{{ obj.date|jalali }}‎ → «۳۱ شهریور ۱۴۰۵»."""
    return format_jalali(value, fmt)


@register.filter(name="jalali_datetime")
def jalali_datetime(value, fmt: str = "%d %B %Y — %H:%M"):
    """نمایش تاریخ و ساعت شمسی."""
    return format_jalali(value, fmt)


@register.filter(name="jalali_short")
def jalali_short(value):
    """نمایش عددی تاریخ شمسی: «۱۴۰۵/۰۶/۳۱»."""
    return jalali_str(value, persian_digits=True)


@register.filter(name="jalali_input")
def jalali_input(value):
    """مقدار مناسب برای ورودی فرم تاریخ شمسی (ارقام لاتین)."""
    return jalali_str(value, persian_digits=False)


@register.filter(name="fa")
def fa(value):
    """تبدیل ارقام لاتین به فارسی."""
    return to_persian_digits(value)


@register.filter(name="toman")
def toman(value):
    """نمایش مبلغ به تومان با جداکننده‌ی هزارگان و ارقام فارسی."""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return ""
    # جداکننده‌ی هزارگان فارسی (٬) به‌جای ویرگول لاتین
    return to_persian_digits(f"{amount:,}").replace(",", "\u066c")


@register.filter(name="toman_label")
def toman_label(value):
    """نمایش مبلغ همراه با واژه‌ی «تومان»."""
    formatted = toman(value)
    return f"{formatted} تومان" if formatted else "—"


@register.filter(name="phone_display")
def phone_display(value):
    """
    نمایش خوانای شماره تماس.

    موبایل: ‎۰۹۱۲ ۱۲۳ ۴۵۶۷‎ — تلفن ثابت: ‎۰۲۱ ۳۳۴۴۵۵۶۶‎
    """
    import re

    from core.jalali import to_latin_digits

    digits = re.sub(r"\D", "", to_latin_digits(value or ""))
    if not digits:
        return to_persian_digits(value)
    if digits.startswith("0098"):
        digits = "0" + digits[4:]
    elif digits.startswith("98") and len(digits) in (12, 13):
        digits = "0" + digits[2:]
    if digits.startswith("09") and len(digits) == 11:
        return to_persian_digits(f"{digits[:4]} {digits[4:7]} {digits[7:]}")
    if digits.startswith("0") and len(digits) == 11:
        # شماره ثابت با پیش‌شماره‌ی سه‌رقمی، مانند ۰۲۱ یا ۰۳۱
        return to_persian_digits(f"{digits[:3]} {digits[3:]}")
    return to_persian_digits(digits)


@register.simple_tag
def star_rating(score, out_of: int = 5):
    """نمایش ستاره‌ای امتیاز (برای نظرات مشتری‌ها)."""
    try:
        filled = max(0, min(int(score), out_of))
    except (TypeError, ValueError):
        filled = 0
    return mark_safe("★" * filled + "☆" * (out_of - filled))


@register.filter(name="attr")
def attr(obj, name):
    """خواندن ویژگی یا متد یک شیء در قالب: ‎{{ item|attr:"title" }}‎."""
    value = getattr(obj, name, "")
    if callable(value):
        try:
            value = value()
        except TypeError:  # pragma: no cover - متدهای نیازمند آرگومان
            return ""
    if isinstance(value, bool):
        return "بله" if value else "خیر"
    return "—" if value in (None, "") else value


@register.filter(name="querystring_without")
def querystring_without(request, key):
    """نشانی فعلی بدون یک پارامتر (برای صفحه‌بندی و فیلترها)."""
    params = request.GET.copy()
    params.pop(key, None)
    encoded = params.urlencode()
    return f"?{encoded}&" if encoded else "?"
