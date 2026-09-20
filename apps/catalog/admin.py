from django.contrib import admin
from django.utils.html import format_html

from .models import Brand, Category, Color, Product, ProductImage, ProductVariant, Size


class ProductImageInline(admin.TabularInline):
    """افزودن چند عکس برای هر محصول."""

    model = ProductImage
    extra = 3
    fields = ("image", "alt_text", "is_main", "order")


class ProductVariantInline(admin.TabularInline):
    """سایزبندی و رنگ‌بندی با موجودی مستقل."""

    model = ProductVariant
    extra = 3
    autocomplete_fields = ("size", "color")
    fields = ("size", "color", "sku", "stock", "extra_price")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "title", "category", "brand", "kind", "price", "stock_total", "is_active")
    list_filter = ("gender", "kind", "category", "brand", "is_active", "is_featured")
    list_editable = ("is_active",)
    list_display_links = ("thumbnail", "title")
    search_fields = ("title", "description", "brand__name")
    autocomplete_fields = ("category", "brand")
    inlines = [ProductImageInline, ProductVariantInline]
    fieldsets = (
        ("مشخصات اصلی", {"fields": ("title", "slug", "short_description", "description")}),
        ("دسته‌بندی و برند", {"fields": ("category", "brand", "kind", "gender")}),
        ("قیمت و وضعیت", {"fields": ("price", "discount_price", "is_active", "is_featured")}),
    )
    prepopulated_fields = {}

    @admin.display(description="تصویر")
    def thumbnail(self, obj):
        image = obj.main_image
        if image:
            return format_html('<img src="{}" style="height:44px;border-radius:6px" />', image.image.url)
        return "—"

    @admin.display(description="موجودی کل")
    def stock_total(self, obj):
        return sum(variant.stock for variant in obj.variants.all())


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "gender", "parent", "order", "is_active")
    list_filter = ("gender", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name", "country")


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("label", "size_type", "order")
    list_filter = ("size_type",)
    list_editable = ("order",)
    search_fields = ("label",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("swatch", "name", "hex_code")
    list_display_links = ("swatch", "name")
    search_fields = ("name",)

    @admin.display(description="رنگ")
    def swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:22px;height:22px;border-radius:50%;'
            'border:1px solid #ddd;background:{}"></span>',
            obj.hex_code,
        )
