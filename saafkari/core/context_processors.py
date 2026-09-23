"""تزریق تنظیمات سایت، لینک‌های اجتماعی و لوکیشن به همه‌ی قالب‌ها."""
from __future__ import annotations

from django.db import OperationalError, ProgrammingError

from .models import ShopLocation, SiteSettings, SocialLink


def site_settings(request):
    """
    داده‌های سراسری قالب‌ها.

    در نبود جدول‌ها (قبل از اجرای migrate) مقادیر خالی برگردانده می‌شود تا
    اولین اجرای پروژه با خطا مواجه نشود.
    """
    try:
        settings_obj = SiteSettings.load()
        links = list(SocialLink.objects.filter(is_active=True))
        location = (
            ShopLocation.objects.filter(is_active=True).order_by("-is_main", "id").first()
        )
    except (OperationalError, ProgrammingError):  # pragma: no cover - قبل از migrate
        return {"site": None, "social_links": [], "header_social_links": [], "shop_location": None}
    return {
        "site": settings_obj,
        "social_links": links,
        "header_social_links": [link for link in links if link.show_in_header],
        "shop_location": location,
    }
