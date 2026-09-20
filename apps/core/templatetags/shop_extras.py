from django import template
from django.utils.safestring import mark_safe

register = template.Library()

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


@register.filter
def toman(value):
    """قیمت را با جداکننده هزارگان و ارقام فارسی نمایش می‌دهد."""
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return value
    formatted = f"{number:,}"
    return mark_safe(formatted.translate({ord(str(i)): PERSIAN_DIGITS[i] for i in range(10)}))


@register.filter
def fa_number(value):
    """تبدیل ارقام انگلیسی یک رشته به فارسی."""
    text = str(value)
    return text.translate({ord(str(i)): PERSIAN_DIGITS[i] for i in range(10)})


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """کوئری‌استرینگ فعلی را با مقادیر تازه بازنویسی می‌کند (برای فیلترها و صفحه‌بندی)."""
    request = context["request"]
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    params.pop("page", None) if "page" not in kwargs else None
    return params.urlencode()


@register.filter
def get_item(mapping, key):
    if hasattr(mapping, "get"):
        return mapping.get(key)
    return None
