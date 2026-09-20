from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Gender(models.TextChoices):
    WOMEN = "women", _("زنانه")
    MEN = "men", _("مردانه")
    UNISEX = "unisex", _("مشترک")


class ProductKind(models.TextChoices):
    CLOTHING = "clothing", _("لباس")
    SHOES = "shoes", _("کفش")
    BAG = "bag", _("کیف")
    ACCESSORY = "accessory", _("اکسسوری")


def unicode_slug(value):
    return slugify(value, allow_unicode=True)


class Brand(models.Model):
    """برندهایی که مدیر اضافه می‌کند و هنگام ثبت محصول انتخاب می‌شوند."""

    name = models.CharField(_("نام برند"), max_length=120, unique=True)
    slug = models.SlugField(_("اسلاگ"), max_length=140, unique=True, allow_unicode=True, blank=True)
    logo = models.ImageField(_("لوگو"), upload_to="brands/", blank=True, null=True)
    country = models.CharField(_("کشور"), max_length=80, blank=True)
    description = models.TextField(_("توضیحات"), blank=True)
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("برند")
        verbose_name_plural = _("برندها")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unicode_slug(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('catalog:product_list')}?brand={self.slug}"


class Category(models.Model):
    """دسته‌بندی محصولات؛ زنانه و مردانه از هم جدا هستند."""

    name = models.CharField(_("نام دسته"), max_length=120)
    slug = models.SlugField(_("اسلاگ"), max_length=160, unique=True, allow_unicode=True, blank=True)
    gender = models.CharField(
        _("جنسیت"), max_length=10, choices=Gender.choices, default=Gender.WOMEN
    )
    parent = models.ForeignKey(
        "self",
        verbose_name=_("دسته والد"),
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
    )
    image = models.ImageField(_("تصویر"), upload_to="categories/", blank=True, null=True)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("دسته‌بندی")
        verbose_name_plural = _("دسته‌بندی‌ها")
        ordering = ["gender", "order", "name"]
        unique_together = [("name", "gender", "parent")]

    def __str__(self):
        return f"{self.get_gender_display()} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = unicode_slug(f"{self.name}-{self.gender}")
            slug, counter = base, 2
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category_detail", args=[self.slug])


class Color(models.Model):
    name = models.CharField(_("نام رنگ"), max_length=60, unique=True)
    hex_code = models.CharField(
        _("کد رنگ"), max_length=7, default="#000000", help_text=_("مثال: #1f2937")
    )

    class Meta:
        verbose_name = _("رنگ")
        verbose_name_plural = _("رنگ‌ها")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Size(models.Model):
    """سایزبندی؛ هر نوع کالا جدول سایز خودش را دارد."""

    label = models.CharField(_("سایز"), max_length=30)
    size_type = models.CharField(
        _("نوع سایزبندی"), max_length=20, choices=ProductKind.choices, default=ProductKind.CLOTHING
    )
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("سایز")
        verbose_name_plural = _("سایزها")
        ordering = ["size_type", "order", "label"]
        unique_together = [("label", "size_type")]

    def __str__(self):
        return f"{self.label} ({self.get_size_type_display()})"


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_relations(self):
        return self.select_related("brand", "category").prefetch_related("images", "variants")


class Product(models.Model):
    title = models.CharField(_("نام محصول"), max_length=200)
    slug = models.SlugField(_("اسلاگ"), max_length=220, unique=True, allow_unicode=True, blank=True)
    category = models.ForeignKey(
        Category, verbose_name=_("دسته‌بندی"), on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(
        Brand,
        verbose_name=_("برند"),
        on_delete=models.SET_NULL,
        related_name="products",
        blank=True,
        null=True,
    )
    kind = models.CharField(
        _("نوع کالا"), max_length=20, choices=ProductKind.choices, default=ProductKind.CLOTHING
    )
    gender = models.CharField(
        _("جنسیت"), max_length=10, choices=Gender.choices, default=Gender.WOMEN
    )
    short_description = models.CharField(_("توضیح کوتاه"), max_length=300, blank=True)
    description = models.TextField(_("توضیحات"), blank=True)
    price = models.PositiveIntegerField(_("قیمت (تومان)"))
    discount_price = models.PositiveIntegerField(
        _("قیمت با تخفیف (تومان)"), blank=True, null=True
    )
    is_active = models.BooleanField(_("فعال"), default=True)
    is_featured = models.BooleanField(_("محصول ویژه"), default=False)
    created_at = models.DateTimeField(_("تاریخ ثبت"), auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = _("محصول")
        verbose_name_plural = _("محصولات")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = unicode_slug(self.title)
            slug, counter = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        if self.category_id and self.category.gender:
            self.gender = self.category.gender
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_detail", args=[self.slug])

    @property
    def final_price(self):
        return self.discount_price or self.price

    @property
    def has_discount(self):
        return bool(self.discount_price and self.discount_price < self.price)

    @property
    def discount_percent(self):
        if not self.has_discount:
            return 0
        return round((self.price - self.discount_price) * 100 / self.price)

    @property
    def main_image(self):
        images = list(self.images.all())
        if not images:
            return None
        for image in images:
            if image.is_main:
                return image
        return images[0]

    @property
    def in_stock(self):
        return any(variant.stock > 0 for variant in self.variants.all())

    @property
    def available_colors(self):
        seen, colors = set(), []
        for variant in self.variants.all():
            if variant.color and variant.color_id not in seen and variant.stock > 0:
                seen.add(variant.color_id)
                colors.append(variant.color)
        return colors

    @property
    def available_sizes(self):
        seen, sizes = set(), []
        for variant in self.variants.all():
            if variant.size and variant.size_id not in seen and variant.stock > 0:
                seen.add(variant.size_id)
                sizes.append(variant.size)
        return sizes


class ProductImage(models.Model):
    """هر محصول می‌تواند چند عکس داشته باشد (اسلایدر خودکار در صفحه محصول)."""

    product = models.ForeignKey(
        Product, verbose_name=_("محصول"), on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(_("تصویر"), upload_to="products/")
    alt_text = models.CharField(_("متن جایگزین"), max_length=150, blank=True)
    is_main = models.BooleanField(_("تصویر اصلی"), default=False)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("تصویر محصول")
        verbose_name_plural = _("تصاویر محصول")
        ordering = ["-is_main", "order", "id"]

    def __str__(self):
        return f"{self.product.title} - {self.pk}"


class ProductVariant(models.Model):
    """ترکیب سایز و رنگ با موجودی مستقل."""

    product = models.ForeignKey(
        Product, verbose_name=_("محصول"), on_delete=models.CASCADE, related_name="variants"
    )
    size = models.ForeignKey(
        Size,
        verbose_name=_("سایز"),
        on_delete=models.PROTECT,
        related_name="variants",
        blank=True,
        null=True,
    )
    color = models.ForeignKey(
        Color,
        verbose_name=_("رنگ"),
        on_delete=models.PROTECT,
        related_name="variants",
        blank=True,
        null=True,
    )
    sku = models.CharField(_("کد انبار"), max_length=60, blank=True)
    stock = models.PositiveIntegerField(_("موجودی"), default=0)
    extra_price = models.IntegerField(_("اختلاف قیمت (تومان)"), default=0)

    class Meta:
        verbose_name = _("تنوع محصول")
        verbose_name_plural = _("تنوع‌های محصول")
        unique_together = [("product", "size", "color")]
        ordering = ["size__order", "color__name"]

    def __str__(self):
        parts = [self.product.title]
        if self.size:
            parts.append(self.size.label)
        if self.color:
            parts.append(self.color.name)
        return " - ".join(parts)

    @property
    def price(self):
        return max(self.product.final_price + self.extra_price, 0)

    @property
    def label(self):
        parts = []
        if self.size:
            parts.append(f"سایز {self.size.label}")
        if self.color:
            parts.append(f"رنگ {self.color.name}")
        return " / ".join(parts) or "تک‌سایز"
