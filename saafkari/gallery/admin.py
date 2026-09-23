from django.contrib import admin
from django.utils.html import format_html

from .models import Banner, PortfolioImage, PortfolioItem


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 4
    fields = ("image", "kind", "caption", "order")


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ("title", "service", "car_name", "image_count", "completed_at", "is_featured", "is_active")
    list_editable = ("is_featured", "is_active")
    list_filter = ("is_active", "is_featured", "service")
    search_fields = ("title", "car_name", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PortfolioImageInline]

    @admin.display(description="تعداد عکس")
    def image_count(self, obj):
        return obj.images.count()


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "position", "order", "is_active", "start_at", "end_at")
    list_editable = ("position", "order", "is_active")
    list_filter = ("position", "is_active")
    search_fields = ("title", "subtitle")

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:42px;border-radius:6px" />', obj.image.url)
        return "—"


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ("item", "kind", "caption", "order")
    list_filter = ("kind",)
