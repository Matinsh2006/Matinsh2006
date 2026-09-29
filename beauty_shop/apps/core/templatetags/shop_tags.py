from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.core.sanitizer import sanitize_html
from apps.core.utils.jalali import format_jalali
from apps.core.utils.text import mask_phone as _mask_phone
from apps.core.utils.text import to_persian_digits

register = template.Library()


@register.filter
def fa_digits(value):
    """Convert latin digits to Persian digits."""
    return to_persian_digits(value)


@register.filter
def price(value):
    """``1250000`` → ``۱٬۲۵۰٬۰۰۰``"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value
    return to_persian_digits(f"{number:,}".replace(",", "٬"))


@register.filter
def jdate(value, fmt="%e %B %Y"):
    """Jalali date, e.g. ``۷ مهر ۱۴۰۵``. See ``format_jalali`` for tokens."""
    return to_persian_digits(format_jalali(value, fmt))


@register.filter
def jdatetime(value):
    return to_persian_digits(format_jalali(value, "%e %B %Y، ساعت %H:%M"))


@register.filter
def duration(seconds):
    """``125`` → ``۲:۰۵`` (minutes:seconds)."""
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return ""
    return to_persian_digits(f"{seconds // 60}:{seconds % 60:02d}")


@register.filter
def mask_phone(value):
    return to_persian_digits(_mask_phone(value))


@register.filter
def richtext(value):
    """Render editor HTML (sanitized again at output time, defence in depth)."""
    return mark_safe(sanitize_html(value))


@register.simple_tag
def elided_page_range(page_obj, on_each_side=1, on_ends=1):
    return list(
        page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=on_each_side, on_ends=on_ends)
    )


@register.simple_tag
def icon(name, extra_class="", label=""):
    """Inline SVG icon from the sprite in ``partials/icons.html``."""
    if label:
        return format_html(
            '<svg class="icon {}" role="img" aria-label="{}" focusable="false"><use href="#i-{}"></use></svg>',
            extra_class,
            label,
            name,
        )
    return format_html(
        '<svg class="icon {}" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>',
        extra_class,
        name,
    )
