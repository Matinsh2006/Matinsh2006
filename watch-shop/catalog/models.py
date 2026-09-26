import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from core.images import optimize_upload


class Gender(models.TextChoices):
    MEN = "men", "مردانه"
    WOMEN = "women", "زنانه"
    UNISEX = "unisex", "یونیسکس (مشترک)"
    KIDS = "kids", "بچگانه"


def _random_name(folder, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"{folder}/{timezone.now():%Y/%m}/{uuid.uuid4().hex[:16]}{ext}"


def brand_logo_path(instance, filename):
    return _random_name("brands", filename)


def category_image_path(instance, filename):
    return _random_name("categories", filename)


def product_image_path(instance, filename):
    return _random_name("products", filename)


class Brand(models.Model):
    name = models.CharField("نام برند", max_length=80, unique=True)
    name_en = models.CharField("نام لاتین", max_length=80, blank=True)
    slug = models.SlugField("نامک (آدرس)", max_length=90, unique=True, allow_unicode=True)
    logo = models.ImageField("لوگو", upload_to=brand_logo_path, blank=True)
    country = models.CharField("کشور", max_length=60, blank=True)
    description = models.TextField("درباره برند", blank=True)
    is_active = models.BooleanField("فعال", default=True)
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.name_en})" if self.name_en else self.name

    def get_absolute_url(self):
        return reverse("catalog:brand", args=[self.slug])


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def roots(self):
        return self.filter(parent__isnull=True)

    def leaves(self):
        return self.filter(children__isnull=True)

    def with_children(self):
        return self.prefetch_related(
            Prefetch("children", queryset=Category.objects.active().order_by("order", "name"))
        )


class Category(models.Model):
    """Two-level tree: watch type (e.g. Sport) › gender (e.g. Women).

    Products are attached to the leaf, so "اسپرت › زنانه" is shown to
    visitors as "ساعت زنانه اسپرت".
    """

    parent = models.ForeignKey(
        "self",
        verbose_name="دسته والد (نوع ساعت)",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.PROTECT,
        limit_choices_to={"parent__isnull": True},
        help_text="برای ساخت نوع ساعت (مثل اسپرت) خالی بگذارید؛ برای زنانه/مردانه، نوع ساعت را انتخاب کنید.",
    )
    name = models.CharField("نام", max_length=80)
    slug = models.SlugField("نامک (آدرس)", max_length=90, allow_unicode=True)
    gender = models.CharField(
        "جنسیت",
        max_length=10,
        choices=Gender.choices,
        blank=True,
        help_text="برای زیردسته‌ها مشخص کنید تا فیلتر «مردانه / زنانه» در کل فروشگاه کار کند.",
    )
    tagline = models.CharField("شعار کوتاه", max_length=140, blank=True)
    description = models.TextField("توضیحات", blank=True)
    image = models.ImageField("تصویر", upload_to=category_image_path, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"], condition=Q(parent__isnull=True), name="catalog_category_unique_root_slug"
            ),
            models.UniqueConstraint(fields=["parent", "slug"], name="catalog_category_unique_child_slug"),
        ]

    def __str__(self):
        if self.parent_id:
            return f"{self.parent.name} › {self.name}"
        return self.name

    @staticmethod
    def _bare(name):
        return name.removeprefix("ساعت ").strip()

    @property
    def title(self):
        """Human title, e.g. "ساعت زنانه اسپرت"."""
        if self.parent_id:
            return f"ساعت {self._bare(self.name)} {self._bare(self.parent.name)}"
        return f"ساعت {self._bare(self.name)}"

    @property
    def is_root(self):
        return self.parent_id is None

    def clean(self):
        if self.parent_id:
            if self.parent_id == self.pk:
                raise ValidationError({"parent": "یک دسته نمی‌تواند والد خودش باشد."})
            if self.parent.parent_id:
                raise ValidationError(
                    {"parent": "فقط دو سطح مجاز است: «نوع ساعت › جنسیت». یک نوع ساعت (دسته اصلی) انتخاب کنید."}
                )
            if self.pk and self.children.exists():
                raise ValidationError({"parent": "این دسته زیرمجموعه دارد و نمی‌تواند زیرمجموعه دسته دیگری شود."})
        qs = Category.objects.filter(parent_id=self.parent_id, slug=self.slug).exclude(pk=self.pk)
        if self.slug and qs.exists():
            raise ValidationError({"slug": "این نامک در همین سطح تکراری است."})

    def get_absolute_url(self):
        if self.parent_id:
            return reverse("catalog:subcategory", args=[self.parent.slug, self.slug])
        return reverse("catalog:category", args=[self.slug])

    def descendant_ids(self):
        return [self.pk, *self.children.values_list("pk", flat=True)]


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def in_category(self, category):
        return self.filter(category_id__in=category.descendant_ids())

    def for_gender(self, gender):
        return self.filter(Q(category__gender=gender) | Q(category__gender=Gender.UNISEX))

    def with_related(self):
        return self.select_related("brand", "category", "category__parent").prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.order_by("order", "id"))
        )


class Product(models.Model):
    class Movement(models.TextChoices):
        QUARTZ = "quartz", "کوارتز (باتری)"
        AUTOMATIC = "automatic", "اتوماتیک"
        MECHANICAL = "mechanical", "مکانیکی (کوکی)"
        SOLAR = "solar", "خورشیدی"
        SMART = "smart", "هوشمند"

    class Strap(models.TextChoices):
        STEEL = "steel", "استیل"
        GOLD = "gold", "فلزی طلایی / رزگلد"
        LEATHER = "leather", "چرم طبیعی"
        RUBBER = "rubber", "رابر (سیلیکونی)"
        CERAMIC = "ceramic", "سرامیک"
        MESH = "mesh", "حصیری (میلانیز)"
        FABRIC = "fabric", "پارچه‌ای"

    class Glass(models.TextChoices):
        SAPPHIRE = "sapphire", "سافایر (یاقوت کبود)"
        MINERAL = "mineral", "مینرال"
        HARDLEX = "hardlex", "هاردلکس"
        ACRYLIC = "acrylic", "اکریلیک"

    name = models.CharField("نام محصول", max_length=160)
    name_en = models.CharField("نام یا مدل لاتین", max_length=160, blank=True)
    slug = models.SlugField("نامک (آدرس)", max_length=180, unique=True, allow_unicode=True)
    sku = models.CharField("کد محصول", max_length=40, unique=True, null=True, blank=True)
    brand = models.ForeignKey(Brand, verbose_name="برند", related_name="products", on_delete=models.PROTECT)
    category = models.ForeignKey(
        Category,
        verbose_name="دسته‌بندی",
        related_name="products",
        on_delete=models.PROTECT,
        help_text="زیرشاخه نهایی را انتخاب کنید؛ مثلاً «اسپرت › زنانه».",
    )
    short_description = models.CharField("توضیح کوتاه", max_length=260, blank=True)
    description = models.TextField("توضیحات کامل", blank=True)

    price = models.PositiveBigIntegerField("قیمت (تومان)")
    compare_at_price = models.PositiveBigIntegerField(
        "قیمت قبل از تخفیف (تومان)", null=True, blank=True, help_text="برای نمایش تخفیف پر کنید."
    )
    stock = models.PositiveIntegerField("موجودی انبار", default=1)

    movement = models.CharField("نوع موتور", max_length=20, choices=Movement.choices, blank=True)
    strap_material = models.CharField("جنس بند", max_length=20, choices=Strap.choices, blank=True)
    case_material = models.CharField("جنس بدنه", max_length=60, blank=True)
    case_diameter = models.DecimalField("قطر بدنه (میلی‌متر)", max_digits=4, decimal_places=1, null=True, blank=True)
    water_resistance = models.PositiveIntegerField("مقاومت در برابر آب (متر)", null=True, blank=True)
    glass = models.CharField("جنس شیشه", max_length=20, choices=Glass.choices, blank=True)
    warranty = models.CharField("گارانتی", max_length=120, blank=True)

    is_active = models.BooleanField("نمایش در فروشگاه", default=True)
    is_featured = models.BooleanField("محصول ویژه صفحه اصلی", default=False)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "-created_at"])]

    def __str__(self):
        return self.name

    def clean(self):
        if self.category_id and self.category.children.exists():
            raise ValidationError(
                {"category": "این دسته زیرشاخه دارد؛ لطفاً زیرشاخه نهایی را انتخاب کنید (مثلاً اسپرت › زنانه)."}
            )
        if self.compare_at_price and self.compare_at_price <= self.price:
            raise ValidationError({"compare_at_price": "قیمت قبل از تخفیف باید بیشتر از قیمت فعلی باشد."})

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = None  # keep the unique constraint happy for empty codes
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product", args=[self.slug])

    @property
    def ordered_images(self):
        return list(self.images.all())

    @property
    def main_image(self):
        images = self.ordered_images
        return images[0] if images else None

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((self.compare_at_price - self.price) * 100 / self.compare_at_price)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def gender(self):
        return self.category.gender if self.category_id else ""

    @property
    def spec_rows(self):
        rows = [
            ("برند", self.brand.name),
            ("دسته‌بندی", self.category.title),
            ("نوع موتور", self.get_movement_display()),
            ("جنس بند", self.get_strap_material_display()),
            ("جنس بدنه", self.case_material),
            ("قطر بدنه", f"{self.case_diameter.normalize():f} میلی‌متر" if self.case_diameter else ""),
            ("مقاومت در برابر آب", f"{self.water_resistance} متر" if self.water_resistance else ""),
            ("جنس شیشه", self.get_glass_display()),
            ("گارانتی", self.warranty),
        ]
        rows += [(spec.label, spec.value) for spec in self.specs.all()]
        return [(label, value) for label, value in rows if value]


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField("تصویر", upload_to=product_image_path)
    alt = models.CharField("متن جایگزین (alt)", max_length=160, blank=True)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.product} #{self.order}"

    def save(self, *args, **kwargs):
        optimize_upload(self.image)
        super().save(*args, **kwargs)

    @property
    def alt_text(self):
        return self.alt or self.product.name


class ProductSpec(models.Model):
    product = models.ForeignKey(Product, related_name="specs", on_delete=models.CASCADE)
    label = models.CharField("عنوان ویژگی", max_length=80)
    value = models.CharField("مقدار", max_length=200)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "ویژگی"
        verbose_name_plural = "سایر ویژگی‌ها"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.label}: {self.value}"
