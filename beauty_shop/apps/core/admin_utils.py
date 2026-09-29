from django.utils.html import format_html

from .utils.jalali import format_jalali
from .utils.text import to_persian_digits


def image_thumb(image, css_class="admin-thumb"):
    """Small <img> preview for admin lists/forms."""
    if not image:
        return "—"
    try:
        url = image.url
    except ValueError:
        return "—"
    return format_html('<img src="{}" class="{}" alt="" loading="lazy">', url, css_class)


def jalali_display(value, fmt="%Y/%m/%d %H:%M"):
    return to_persian_digits(format_jalali(value, fmt)) if value else "—"
