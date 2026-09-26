from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .images import thumbnail_url
from .models import Banner, ContactMessage, Page, SiteSettings, StoreLocation


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    autocomplete_fields = ("hero_product",)
    fieldsets = (
        ("هویت فروشگاه", {"fields": ("site_name", "site_name_en", "tagline", "logo")}),
        (
            "بخش اسکرول سه‌بعدی صفحه اصلی",
            {
                "fields": (
                    "hero_eyebrow",
                    "hero_title",
                    "hero_subtitle",
                    ("hero_cta_text", "hero_cta_url"),
                    "hero_product",
                    ("hero_metal", "hero_dial"),
                ),
                "description": "متن‌ها و رنگ ساعت سه‌بعدی که با اسکرول، قطعه به قطعه سرهم می‌شود.",
            },
        ),
        (
            "تماس و شبکه‌های اجتماعی (فوتر)",
            {
                "fields": (
                    ("phone", "mobile"),
                    "email",
                    "address",
                    "working_hours",
                    ("instagram", "telegram"),
                    ("whatsapp", "twitter"),
                ),
            },
        ),
        ("پیام‌رسان‌های داخلی (اختیاری)", {"fields": (("eitaa", "bale", "rubika"),), "classes": ("collapse",)}),
        (
            "نماد اعتماد الکترونیکی (اینماد) و ساماندهی",
            {
                "fields": ("enamad_code", "samandehi_code"),
                "description": "کد دریافتی از enamad.ir را بدون تغییر در کادر زیر قرار دهید تا در جایگاه مخصوص فوتر نمایش داده شود.",
            },
        ),
        ("ارسال", {"fields": (("shipping_cost", "free_shipping_threshold"),)}),
        ("فوتر و سئو", {"fields": ("footer_about", "copyright_text", "meta_description")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "placement", "style", "is_active", "order", "starts_at", "ends_at")
    list_display_links = ("preview", "title")
    list_editable = ("is_active", "order")
    list_filter = ("placement", "is_active")
    search_fields = ("title", "subtitle")
    readonly_fields = ("preview_large",)
    fieldsets = (
        (None, {"fields": ("placement", "title", "subtitle", ("link", "button_text"))}),
        ("تصویر", {"fields": ("image", "image_mobile", "preview_large", "show_text", "style")}),
        ("نمایش", {"fields": ("is_active", "is_dismissible", "order", ("starts_at", "ends_at"))}),
    )

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:140px;height:44px;object-fit:cover;border-radius:8px" alt="">',
                thumbnail_url(obj.image, 400),
            )
        return format_html(
            '<span style="display:inline-block;padding:6px 10px;border-radius:8px;'
            'background:linear-gradient(90deg,#f3d2bd,#c98468);color:#1a1210;font-size:11px">بنر متنی</span>'
        )

    @admin.display(description="پیش‌نمایش تصویر")
    def preview_large(self, obj):
        if not obj.image:
            return "—"
        return format_html('<img src="{}" style="max-width:100%;border-radius:12px" alt="">', obj.image.url)


@admin.register(StoreLocation)
class StoreLocationAdmin(admin.ModelAdmin):
    change_form_template = "admin/core/storelocation/change_form.html"
    list_display = ("name", "phone", "working_hours", "is_active", "order")
    list_editable = ("is_active", "order")
    fieldsets = (
        (None, {"fields": ("name", "address", "phone", "working_hours", "image")}),
        (
            "موقعیت روی نقشه",
            {
                "fields": (("latitude", "longitude"), "zoom"),
                "description": "روی نقشه کلیک کنید یا نشانگر را بکشید تا مختصات مغازه ثبت شود.",
            },
        ),
        ("لینک‌های مسیریابی (اختیاری)", {"fields": ("neshan_url", "balad_url"), "classes": ("collapse",)}),
        ("نمایش", {"fields": ("is_active", "order")}),
    )

    def render_change_form(self, request, context, *args, **kwargs):
        context["map_tile_url"] = settings.MAP_TILE_URL
        context["map_tile_attribution"] = settings.MAP_TILE_ATTRIBUTION
        return super().render_change_form(request, context, *args, **kwargs)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "show_in_footer", "is_active", "order")
    list_editable = ("show_in_footer", "is_active", "order")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "short_message", "created_at", "is_read")
    list_filter = ("is_read",)
    list_editable = ("is_read",)
    search_fields = ("name", "phone", "message")
    readonly_fields = ("name", "phone", "message", "created_at")

    @admin.display(description="پیام")
    def short_message(self, obj):
        return (obj.message[:60] + "…") if len(obj.message) > 60 else obj.message

    def has_add_permission(self, request):
        return False
