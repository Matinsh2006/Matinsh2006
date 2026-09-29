from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .admin_utils import image_thumb, jalali_display
from .models import Banner, Branch, Page, SiteSettings, SocialLink


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("اطلاعات فروشگاه", {"fields": ("site_name", "slogan", "logo", "favicon", "about_short")}),
        (
            "اطلاعات تماس",
            {
                "fields": ("phone", "email", "working_hours"),
                "description": (
                    "لینک‌های اینستاگرام، تلگرام، واتساپ، توییتر و شماره‌های تماس از بخش "
                    "«شبکه‌های اجتماعی و راه‌های تماس» و لوکیشن مغازه از بخش «موقعیت فروشگاه و شعب» اضافه می‌شوند."
                ),
            },
        ),
        ("هزینه ارسال", {"fields": ("shipping_cost", "free_shipping_threshold")}),
        ("سئو و نماد اعتماد", {"fields": ("meta_description", "enamad_code")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform_label", "value", "title", "open_link", "show_in_floating", "order", "is_active")
    list_editable = ("show_in_floating", "order", "is_active")
    list_filter = ("platform", "is_active")
    search_fields = ("value", "title")

    @admin.display(description="شبکه", ordering="platform")
    def platform_label(self, obj):
        return obj.get_platform_display()

    @admin.display(description="لینک ساخته‌شده")
    def open_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', obj.url, obj.url)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "phone", "order", "is_active")
    list_editable = ("order", "is_active")
    readonly_fields = ("map_picker",)
    fieldsets = (
        (None, {"fields": ("name", "address", "phone", "working_hours", "is_active", "order")}),
        ("موقعیت روی نقشه", {"fields": ("map_picker", ("latitude", "longitude"), "zoom")}),
        ("لینک مسیریاب‌ها (اختیاری)", {"fields": ("neshan_url", "balad_url")}),
    )

    class Media:
        css = {"all": ("vendor/leaflet/leaflet.css",)}
        js = ("vendor/leaflet/leaflet.js", "shop_admin/location_picker.js")

    @admin.display(description="انتخاب روی نقشه")
    def map_picker(self, obj):
        return format_html(
            '<div class="location-picker" data-location-picker data-tile-url="{}" data-tile-attribution="{}">'
            '<div class="location-picker__map" dir="ltr"></div>'
            '<p class="help">روی نقشه کلیک کنید یا نشانگر را جابه‌جا کنید تا مختصات به‌طور خودکار ثبت شود.</p>'
            "</div>",
            settings.MAP_TILE_URL,
            settings.MAP_TILE_ATTRIBUTION,
        )


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "title", "position", "order", "is_active", "schedule")
    list_display_links = ("thumbnail", "title")
    list_editable = ("order", "is_active")
    list_filter = ("position", "is_active")
    search_fields = ("title", "subtitle")
    readonly_fields = ("preview",)
    fieldsets = (
        (None, {"fields": ("title", "subtitle", "position", "is_active", "order")}),
        ("تصاویر", {"fields": ("image", "mobile_image", "preview")}),
        ("لینک و دکمه", {"fields": ("link", "button_text", "show_text")}),
        ("زمان‌بندی نمایش (اختیاری)", {"fields": ("start_at", "end_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="تصویر")
    def thumbnail(self, obj):
        return image_thumb(obj.image, "admin-thumb admin-thumb--wide")

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        return image_thumb(obj.image, "admin-preview") if obj and obj.image else "—"

    @admin.display(description="زمان‌بندی")
    def schedule(self, obj):
        if not obj.start_at and not obj.end_at:
            return "همیشه"
        return f"{jalali_display(obj.start_at)} تا {jalali_display(obj.end_at)}"


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "show_in_footer", "order", "is_active")
    list_editable = ("show_in_footer", "order", "is_active")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)
