from django.contrib import admin
from django.utils.html import format_html

from .models import Banner, SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ("اطلاعات فروشگاه", {"fields": ("site_name", "tagline", "logo", "about")}),
        (
            "لوکیشن و تماس",
            {
                "fields": (
                    "phone",
                    "email",
                    "city",
                    "address",
                    "postal_code",
                    ("latitude", "longitude"),
                    "map_embed_url",
                    "working_hours",
                )
            },
        ),
        ("شبکه‌های اجتماعی", {"fields": ("telegram", "instagram", "whatsapp", "twitter")}),
        ("ارسال", {"fields": ("shipping_cost", "free_shipping_threshold")}),
    )

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "is_active", "order")
    list_editable = ("is_active", "order")
    list_display_links = ("preview", "title")
    search_fields = ("title", "subtitle")

    @admin.display(description="تصویر")
    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:6px" />', obj.image.url)
        return "—"
