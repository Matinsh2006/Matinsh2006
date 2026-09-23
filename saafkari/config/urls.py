"""نقشه‌ی نشانی‌های سایت مغازه صافکاری."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("services/", include("services.urls")),
    path("portfolio/", include("gallery.urls")),
    path("blog/", include("blog.urls")),
    path("appointments/", include("appointments.urls")),
    path("payments/", include("payments.urls")),
    path("account/", include("accounts.urls")),
    path("panel/", include("dashboard.urls")),
]

handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
