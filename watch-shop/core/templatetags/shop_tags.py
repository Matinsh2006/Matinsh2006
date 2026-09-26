import datetime

import jdatetime
from django import template
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from accounts.utils import mask_phone
from core.icons import SOCIAL_ICONS, UI_ICONS
from core.images import thumbnail_url
from core.utils import fa_digits, format_number

register = template.Library()

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


@register.filter
def fa(value):
    """Persian digits: {{ value|fa }}"""
    return fa_digits(value)


@register.filter
def toman(value):
    """12500000 -> ۱۲٬۵۰۰٬۰۰۰"""
    return format_number(value)


@register.filter
def masked(phone):
    return fa_digits(mask_phone(phone))


def _to_jalali(value):
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return jdatetime.datetime.fromgregorian(datetime=value)
    if isinstance(value, datetime.date):
        return jdatetime.date.fromgregorian(date=value)
    return None


@register.filter
def jdate(value, style="long"):
    """Jalali date. Styles: long (۳ مهر ۱۴۰۵), short (۱۴۰۵/۰۷/۰۳), full (with time)."""
    jalali = _to_jalali(value)
    if jalali is None:
        return ""
    if style == "short":
        text = f"{jalali.year}/{jalali.month:02d}/{jalali.day:02d}"
    else:
        text = f"{jalali.day} {JALALI_MONTHS[jalali.month - 1]} {jalali.year}"
        if style == "full" and isinstance(jalali, jdatetime.datetime):
            text += f"، ساعت {jalali.hour:02d}:{jalali.minute:02d}"
    return fa_digits(text)


@register.simple_tag
def jalali_year():
    return fa_digits(jdatetime.date.today().year)


@register.filter
def thumb(image, width=600):
    """URL of a WebP thumbnail: {{ product.main_image.image|thumb:800 }}"""
    return thumbnail_url(image, width)


@register.simple_tag
def srcset(image, *widths):
    if not image:
        return ""
    return ", ".join(f"{thumbnail_url(image, w)} {w}w" for w in widths)


@register.simple_tag
def icon(name, css_class="size-5", stroke="1.5"):
    body = UI_ICONS.get(name, "")
    return format_html(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="{}" stroke-linecap="round" stroke-linejoin="round" class="{}" aria-hidden="true">{}</svg>',
        stroke,
        css_class,
        mark_safe(body),
    )


@register.simple_tag
def social_icon(name, css_class="size-5"):
    body = SOCIAL_ICONS.get(name, "")
    return format_html(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="{}" aria-hidden="true">{}</svg>',
        css_class,
        mark_safe(body),
    )


@register.filter
def stagger(index, columns=4):
    """Reveal delay (ms) so items in the same row animate one after another."""
    try:
        return (int(index) % int(columns)) * 90
    except (TypeError, ValueError):
        return 0
