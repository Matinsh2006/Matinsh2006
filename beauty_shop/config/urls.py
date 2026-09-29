from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, register_converter

from apps.blog.sitemaps import ArticleSitemap
from apps.catalog.sitemaps import BrandSitemap, CategorySitemap, ProductSitemap
from apps.core.converters import UnicodeSlugConverter
from apps.core.sitemaps import PageSitemap, StaticViewSitemap
from apps.core.views import favicon, robots_txt

register_converter(UnicodeSlugConverter, "uslug")

admin.site.site_header = "پنل مدیریت فروشگاه"
admin.site.site_title = "مدیریت فروشگاه"
admin.site.index_title = "داشبورد"

sitemaps = {
    "static": StaticViewSitemap,
    "pages": PageSitemap,
    "categories": CategorySitemap,
    "brands": BrandSitemap,
    "products": ProductSitemap,
    "articles": ArticleSitemap,
}

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.core.urls")),
    path("", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("", include("apps.orders.urls")),
    path("account/", include("apps.accounts.urls")),
    path("payment/", include("apps.payments.urls")),
    path("blog/", include("apps.blog.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("favicon.ico", favicon, name="favicon"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
