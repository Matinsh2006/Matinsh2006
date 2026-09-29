from django.conf import settings
from django.db.models import Prefetch
from django.utils.functional import SimpleLazyObject

from .models import Branch, Page, SiteSettings, SocialLink
from .utils.jalali import current_jalali_year


def site(request):
    """Data shared by every page (header, footer, contact buttons)."""
    from apps.catalog.models import Category

    active_children = Category.objects.filter(is_active=True)
    social_links = SocialLink.objects.filter(is_active=True)
    return {
        "site": SimpleLazyObject(SiteSettings.load),
        "social_links": social_links,
        # Shares the queryset above, so both are loaded with a single query.
        "floating_links": SimpleLazyObject(lambda: [link for link in social_links if link.show_in_floating]),
        "footer_pages": Page.objects.filter(is_active=True, show_in_footer=True),
        "nav_categories": Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related(
            Prefetch("children", queryset=active_children)
        ),
        "main_branch": SimpleLazyObject(lambda: Branch.objects.filter(is_active=True).first()),
        "current_jalali_year": SimpleLazyObject(current_jalali_year),
        "CURRENCY": settings.SHOP_CURRENCY_LABEL,
    }
