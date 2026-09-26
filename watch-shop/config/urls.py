from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve

from catalog.sitemaps import BrandSitemap, CategorySitemap, ProductSitemap
from core.sitemaps import PageSitemap, StaticViewSitemap

admin.site.site_header = "مدیریت فروشگاه"
admin.site.site_title = "پنل مدیریت"
admin.site.index_title = "داشبورد فروشگاه"

sitemaps = {
    "static": StaticViewSitemap,
    "pages": PageSitemap,
    "categories": CategorySitemap,
    "brands": BrandSitemap,
    "products": ProductSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("accounts.urls")),
    path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")),
    path("payment/", include("payments.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("", include("catalog.urls")),
    path("", include("core.urls")),
]

if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]

handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
