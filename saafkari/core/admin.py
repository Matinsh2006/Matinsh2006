from django.contrib import admin
from django.utils.html import format_html

from .models import ContactMessage, ShopLocation, SiteSettings, SocialLink

admin.site.site_header = "پنل مدیریت مغازه صافکاری"
admin.site.site_title = "مدیریت سایت"
admin.site.index_title = "خوش آمدید"


class ShopLocationInline(admin.StackedInline):
    model = ShopLocation
    extra = 0
    fields = (
        "title", "address", ("city", "province"), ("postal_code", "phone"),
        ("latitude", "longitude"), ("map_zoom", "map_link"), ("is_main", "is_active"),
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    inlines = [ShopLocationInline]
    fieldsets = (
        ("معرفی", {"fields": ("brand_name", "tagline", "about", "logo", "hero_image")}),
        ("راه‌های ارتباطی", {"fields": ("phone", "second_phone", "email", "working_hours")}),
        ("پرداخت", {"fields": ("deposit_amount", "online_payment_enabled", "require_deposit")}),
        ("سئو و اعتماد", {"fields": ("meta_description", "enamad_code")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ShopLocation)
class ShopLocationAdmin(admin.ModelAdmin):
    list_display = ("title", "city", "address", "is_main", "is_active")
    list_editable = ("is_main", "is_active")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "value", "link", "order", "show_in_header", "is_active")
    list_editable = ("order", "show_in_header", "is_active")
    list_filter = ("platform", "is_active")

    @admin.display(description="نشانی نهایی")
    def link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', obj.url, obj.url)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "subject", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "phone", "subject", "message")
    readonly_fields = ("name", "phone", "subject", "message", "created_at")

    def has_add_permission(self, request):
        return False
