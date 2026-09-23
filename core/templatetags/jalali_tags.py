from django import template

from config.jalali import (
    format_jalali_date,
    format_jalali_iso,
    format_jalali_numeric,
    to_persian_digits,
)

register = template.Library()


@register.filter(name="jalali")
def jalali_filter(value):
    """{{ some_date|jalali }} -> 'دوشنبه ۱ مهر ۱۴۰۵'"""
    return format_jalali_date(value)


@register.filter(name="jalali_iso")
def jalali_iso_filter(value):
    """{{ some_date|jalali_iso }} -> '1405-07-01' (ascii, for hidden inputs)"""
    return format_jalali_iso(value)


@register.filter(name="jalali_numeric")
def jalali_numeric_filter(value):
    """{{ some_date|jalali_numeric }} -> '۱۴۰۵/۰۷/۰۱'"""
    return format_jalali_numeric(value)


@register.filter(name="persian_digits")
def persian_digits_filter(value):
    return to_persian_digits(value)


@register.filter(name="toman")
def toman_filter(value):
    """{{ 150000|toman }} -> '۱۵۰,۰۰۰ تومان'"""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return value
    return to_persian_digits(f"{amount:,}") + " تومان"
