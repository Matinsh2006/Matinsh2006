from django.conf import settings
from django.utils.functional import SimpleLazyObject

from catalog.models import Category

from .models import Banner, Page, SiteSettings, StoreLocation


def shop(request):
    """Store-wide data used by the base layout (header, footer, banners).

    Everything is lazy so admin pages that don't use it cost no queries.
    """
    return {
        "shop": SimpleLazyObject(SiteSettings.load),
        "header_banners": SimpleLazyObject(
            lambda: list(Banner.objects.live().filter(placement=Banner.Placement.HEADER))
        ),
        "nav_categories": SimpleLazyObject(
            lambda: list(Category.objects.active().roots().with_children().order_by("order", "name"))
        ),
        "footer_pages": SimpleLazyObject(
            lambda: list(Page.objects.filter(is_active=True, show_in_footer=True))
        ),
        "primary_store": SimpleLazyObject(lambda: StoreLocation.objects.filter(is_active=True).first()),
        "DEBUG": settings.DEBUG,
        "map_tile_url": settings.MAP_TILE_URL,
        "map_tile_attribution": settings.MAP_TILE_ATTRIBUTION,
    }
