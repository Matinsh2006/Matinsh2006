from django.contrib import admin, messages
from django.db.models import Count, Prefetch

from apps.core.admin_utils import image_thumb

from .models import Brand, Category, Product, ProductImage, ProductSpecification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "parent", "product_count", "order", "is_active")
    list_display_links = ("thumbnail", "name")
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("parent",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent").annotate(num_products=Count("products"))

    @admin.display(description="تصویر")
    def thumbnail(self, obj):
        return image_thumb(obj.image)

    @admin.display(description="تعداد محصول", ordering="num_products")
    def product_count(self, obj):
        return obj.num_products


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "name_en", "country", "product_count", "order", "is_active")
    list_display_links = ("thumbnail", "name")
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "name_en")
    prepopulated_fields = {"slug": ("name_en",)}
    fields = ("name", "name_en", "slug", "logo", "country", "description", "order", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(num_products=Count("products"))

    @admin.display(description="لوگو")
    def thumbnail(self, obj):
        return image_thumb(obj.logo)

    @admin.display(description="تعداد محصول", ordering="num_products")
    def product_count(self, obj):
        return obj.num_products


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ("preview", "image", "alt_text", "order")
    readonly_fields = ("preview",)
    verbose_name = "تصویر"
    verbose_name_plural = "تصاویر محصول (می‌توانید چند تصویر اضافه کنید؛ تصویر با کمترین «ترتیب» تصویر اصلی است)"

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        return image_thumb(obj.image) if obj and obj.pk else "—"


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 2
    fields = ("title", "value", "order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "name",
        "brand",
        "category",
        "price",
        "discount_price",
        "stock",
        "is_active",
        "is_featured",
        "sold_count",
    )
    list_display_links = ("thumbnail", "name")
    list_editable = ("price", "discount_price", "stock", "is_active", "is_featured")
    list_filter = ("is_active", "is_featured", "brand", "category")
    search_fields = ("name", "sku", "brand__name", "brand__name_en")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("brand", "category")
    readonly_fields = ("sold_count", "created_at", "updated_at")
    inlines = (ProductImageInline, ProductSpecificationInline)
    list_per_page = 30
    save_on_top = True
    actions = ("make_active", "make_inactive", "make_featured")
    fieldsets = (
        (None, {"fields": ("name", "slug", "sku", "brand", "category")}),
        ("قیمت و موجودی", {"fields": (("price", "discount_price"), "stock")}),
        ("توضیحات", {"fields": ("short_description", "description")}),
        ("وضعیت", {"fields": ("is_active", "is_featured", "sold_count", "created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("brand", "category", "category__parent")
            .prefetch_related(Prefetch("images", queryset=ProductImage.objects.order_by("order", "id")))
        )

    @admin.display(description="تصویر")
    def thumbnail(self, obj):
        image = obj.main_image
        return image_thumb(image.image) if image else "—"

    @admin.action(description="نمایش محصولات انتخاب‌شده در سایت")
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} محصول فعال شد.", messages.SUCCESS)

    @admin.action(description="مخفی کردن محصولات انتخاب‌شده")
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} محصول غیرفعال شد.", messages.SUCCESS)

    @admin.action(description="افزودن به پیشنهادهای ویژه")
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} محصول به پیشنهادهای ویژه اضافه شد.", messages.SUCCESS)
