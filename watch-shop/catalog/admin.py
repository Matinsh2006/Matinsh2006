from django.contrib import admin
from django.db.models import Count, F
from django.db.models.functions import Coalesce
from django.utils.html import format_html

from core.images import thumbnail_url
from core.utils import format_number

from .forms import CategoryAdminForm, GroupedCategoryChoiceField, ProductAdminForm
from .models import Brand, Category, Gender, Product, ProductImage, ProductSpec


def _preview(image, size=64):
    if not image:
        return "—"
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:10px;'
        'background:#111" alt="">',
        thumbnail_url(image, 200),
        size,
        size,
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("logo_preview", "name", "name_en", "country", "product_count", "is_active", "order")
    list_display_links = ("logo_preview", "name")
    list_editable = ("is_active", "order")
    search_fields = ("name", "name_en")
    prepopulated_fields = {"slug": ("name_en",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(num_products=Count("products"))

    @admin.display(description="لوگو")
    def logo_preview(self, obj):
        return _preview(obj.logo, 40)

    @admin.display(description="تعداد محصول", ordering="num_products")
    def product_count(self, obj):
        return obj.num_products


class ChildCategoryInline(admin.TabularInline):
    model = Category
    fk_name = "parent"
    extra = 0
    fields = ("name", "slug", "gender", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    verbose_name = "زیرشاخه"
    verbose_name_plural = "زیرشاخه‌ها (مثلاً مردانه / زنانه)"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ("tree_name", "title_display", "gender", "product_count", "is_active", "order")
    list_editable = ("is_active", "order")
    list_filter = ("gender", "is_active", ("parent", admin.RelatedOnlyFieldListFilter))
    search_fields = ("name", "parent__name")
    prepopulated_fields = {"slug": ("name",)}
    fields = (
        "parent",
        "name",
        "slug",
        "gender",
        "tagline",
        "description",
        "image",
        "is_active",
        "order",
        "create_gender_children",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent").annotate(num_products=Count("products"))

    def get_ordering(self, request):
        # Every watch type is directly followed by its sub-categories.
        return [
            Coalesce("parent__order", "order").asc(),
            Coalesce("parent__name", "name").asc(),
            F("parent_id").asc(nulls_first=True),
            "order",
            "name",
        ]

    def get_inlines(self, request, obj):
        return [ChildCategoryInline] if obj is None or obj.parent_id is None else []

    @admin.display(description="نام", ordering="name")
    def tree_name(self, obj):
        if obj.parent_id:
            return format_html('<span style="opacity:.55">{} ›</span> {}', obj.parent.name, obj.name)
        return format_html("<strong>{}</strong>", obj.name)

    @admin.display(description="عنوان نمایشی")
    def title_display(self, obj):
        return obj.title

    @admin.display(description="تعداد محصول", ordering="num_products")
    def product_count(self, obj):
        return obj.num_products

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        wants_children = form.cleaned_data.get("create_gender_children")
        if obj.parent_id is None and wants_children and not obj.children.exists():
            for index, (slug, name, gender) in enumerate(
                [("men", "مردانه", Gender.MEN), ("women", "زنانه", Gender.WOMEN)]
            ):
                Category.objects.create(parent=obj, slug=slug, name=name, gender=gender, order=index)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("preview", "image", "alt", "order")
    readonly_fields = ("preview",)
    ordering = ("order", "id")

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        return _preview(obj.image, 72)


class ProductSpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = (
        "image_preview",
        "name",
        "brand",
        "category_title",
        "price_display",
        "stock",
        "is_active",
        "is_featured",
    )
    list_display_links = ("image_preview", "name")
    list_editable = ("stock", "is_active", "is_featured")
    list_filter = (
        "is_active",
        "is_featured",
        ("category__parent", admin.RelatedOnlyFieldListFilter),
        "category__gender",
        ("brand", admin.RelatedOnlyFieldListFilter),
        "movement",
        "strap_material",
    )
    search_fields = ("name", "name_en", "sku", "brand__name", "brand__name_en")
    list_select_related = ("brand", "category", "category__parent")
    autocomplete_fields = ("brand",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ProductSpecInline]
    save_on_top = True
    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("name", "name_en", "slug", "sku", "brand", "category")}),
        ("قیمت و موجودی", {"fields": (("price", "compare_at_price"), "stock")}),
        (
            "تصاویر",
            {
                "fields": ("bulk_images",),
                "description": "تصویر اول گالری، تصویر اصلی محصول است. ترتیب را در جدول پایین صفحه تنظیم کنید.",
            },
        ),
        ("توضیحات", {"fields": ("short_description", "description")}),
        (
            "مشخصات فنی",
            {
                "fields": (
                    ("movement", "strap_material"),
                    ("case_material", "case_diameter"),
                    ("water_resistance", "glass"),
                    "warranty",
                )
            },
        ),
        ("نمایش", {"fields": ("is_active", "is_featured")}),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            kwargs["queryset"] = (
                Category.objects.leaves()
                .select_related("parent")
                .order_by(
                    Coalesce("parent__order", "order"),
                    Coalesce("parent__name", "name"),
                    F("parent_id").asc(nulls_first=True),
                    "order",
                    "name",
                )
            )
            kwargs["form_class"] = GroupedCategoryChoiceField
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        files = form.cleaned_data.get("bulk_images") or []
        if files:
            product = form.instance
            start = (product.images.order_by("-order").values_list("order", flat=True).first() or 0) + 1
            for offset, uploaded in enumerate(files):
                ProductImage.objects.create(product=product, image=uploaded, order=start + offset)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("images")

    @admin.display(description="تصویر")
    def image_preview(self, obj):
        images = obj.images.all()
        return _preview(images[0].image if images else None, 52)

    @admin.display(description="دسته‌بندی", ordering="category__parent__name")
    def category_title(self, obj):
        return obj.category.title

    @admin.display(description="قیمت (تومان)", ordering="price")
    def price_display(self, obj):
        return format_number(obj.price)
