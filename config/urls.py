from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f"پنل مدیریت {settings.SITE_NAME}"
admin.site.site_title = settings.SITE_NAME
admin.site.index_title = "مدیریت سایت"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("account/", include("accounts.urls")),
    path("services/", include("services.urls")),
    path("booking/", include("bookings.urls")),
    path("payment/", include("payments.urls")),
    path("gallery/", include("gallery.urls")),
    path("articles/", include("articles.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
