from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, F, Prefetch, When
from django.urls import reverse

from apps.core.fields import RichTextField
from apps.core.utils.images import optimize_image_field
from apps.core.utils.slugs import unique_slugify
from apps.core.utils.text import normalize_persian


class Category(models.Model):
    name = models.CharField("نام", max_length=100)
    slug = models.SlugField("نامک (آدرس)", max_length=120, unique=True, allow_unicode=True, blank=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="دسته والد",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="برای زیردسته، دسته اصلی را انتخاب کنید.",
    )
    image = models.ImageField("تصویر / آیکون", upload_to="categories/", blank=True)
    description = models.TextField("توضیحات", blank=True)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.parent.name} › {self.name}" if self.parent_id else self.name

    def clean(self):
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError({"parent": "یک دسته نمی‌تواند والد خودش باشد."})
        if self.parent and self.parent.parent_id:
            raise ValidationError({"parent": "دسته‌بندی حداکثر دو سطح (دسته و زیردسته) دارد."})

    def save(self, *args, **kwargs):
        self.name = normalize_persian(self.name)
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        optimize_image_field(self.image, max_dimension=400)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category", kwargs={"category_slug": self.slug})

    def get_descendant_ids(self):
        return [self.pk, *self.children.values_list("pk", flat=True)]


class Brand(models.Model):
    name = models.CharField("نام برند", max_length=100, unique=True)
    name_en = models.CharField("نام انگلیسی", max_length=100, blank=True)
    slug = models.SlugField(
        "نامک (آدرس)",
        max_length=120,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="در صورت خالی بودن از نام انگلیسی (یا فارسی) ساخته می‌شود.",
    )
    logo = models.ImageField(
        "لوگو", upload_to="brands/", blank=True, help_text="تصویر مربعی با پس‌زمینه سفید یا شفاف، حداقل ۳۰۰×۳۰۰ پیکسل"
    )
    country = models.CharField("کشور سازنده", max_length=60, blank=True)
    description = RichTextField("معرفی برند", blank=True)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = normalize_persian(self.name)
        if not self.slug:
            self.slug = unique_slugify(self, self.name_en or self.name)
        optimize_image_field(self.logo, max_dimension=500)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:brand_detail", kwargs={"brand_slug": self.slug})


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_listing(self):
        return self.select_related("brand", "category").prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.order_by("order", "id"))
        )

    def discounted(self):
        return self.filter(discount_price__isnull=False, discount_price__lt=F("price"))

    def in_stock(self):
        return self.filter(stock__gt=0)

    def with_effective_price(self):
        return self.annotate(
            effective_price=Case(
                When(discount_price__isnull=False, discount_price__lt=F("price"), then=F("discount_price")),
                default=F("price"),
                output_field=models.PositiveIntegerField(),
            )
        )


class Product(models.Model):
    name = models.CharField("نام محصول", max_length=200)
    slug = models.SlugField("نامک (آدرس)", max_length=220, unique=True, allow_unicode=True, blank=True)
    sku = models.CharField("کد محصول (SKU)", max_length=50, blank=True)
    brand = models.ForeignKey(
        Brand, verbose_name="برند", on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    category = models.ForeignKey(
        Category,
        verbose_name="دسته‌بندی",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    short_description = models.CharField("توضیح کوتاه", max_length=300, blank=True)
    description = RichTextField("توضیحات کامل", blank=True)
    price = models.PositiveIntegerField("قیمت (تومان)")
    discount_price = models.PositiveIntegerField(
        "قیمت پس از تخفیف (تومان)", null=True, blank=True, help_text="برای محصول بدون تخفیف خالی بگذارید."
    )
    stock = models.PositiveIntegerField("موجودی انبار", default=0)
    is_active = models.BooleanField("نمایش در سایت", default=True)
    is_featured = models.BooleanField("پیشنهاد ویژه", default=False)
    sold_count = models.PositiveIntegerField("تعداد فروش", default=0)
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
        if self.discount_price is not None and self.price is not None and self.discount_price >= self.price:
            raise ValidationError({"discount_price": "قیمت پس از تخفیف باید کمتر از قیمت اصلی باشد."})

    def save(self, *args, **kwargs):
        self.name = normalize_persian(self.name)
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def has_discount(self):
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def final_price(self):
        return self.discount_price if self.has_discount else self.price

    @property
    def discount_percent(self):
        if not self.has_discount or not self.price:
            return 0
        return max(1, round((self.price - self.discount_price) * 100 / self.price))

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def max_order_quantity(self):
        return min(self.stock, settings.CART_MAX_QUANTITY_PER_ITEM)

    @property
    def main_image(self):
        images = list(self.images.all())
        return images[0] if images else None


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        "تصویر", upload_to="products/%Y/%m/", help_text="تصویر مربعی پیشنهاد می‌شود (مثلاً ۱۰۰۰×۱۰۰۰ پیکسل)."
    )
    alt_text = models.CharField("متن جایگزین (سئو)", max_length=200, blank=True)
    order = models.PositiveIntegerField("ترتیب", default=0, help_text="تصویر با کمترین عدد، تصویر اصلی است.")

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ["order", "id"]

    def __str__(self):
        return self.alt

    def save(self, *args, **kwargs):
        optimize_image_field(self.image)
        super().save(*args, **kwargs)

    @property
    def alt(self):
        return self.alt_text or self.product.name


class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="specifications"
    )
    title = models.CharField("ویژگی", max_length=100, help_text="مثال: حجم، نوع پوست، کشور سازنده")
    value = models.CharField("مقدار", max_length=200, help_text="مثال: ۵۰ میلی‌لیتر")
    order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "مشخصه"
        verbose_name_plural = "مشخصات فنی"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title}: {self.value}"
