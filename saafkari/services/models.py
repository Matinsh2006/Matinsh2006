"""خدمات مغازه (صافکاری، نقاشی، پولیش و ...)."""
from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class ServiceCategory(models.Model):
    """دسته‌بندی خدمات."""

    name = models.CharField(_("نام دسته"), max_length=100, unique=True)
    slug = models.SlugField(_("نشانی یکتا"), max_length=120, unique=True, allow_unicode=True, blank=True)
    description = models.TextField(_("توضیح"), blank=True, default="")
    icon = models.CharField(
        _("آیکون"), max_length=40, blank=True, default="",
        help_text=_("نام آیکون دلخواه برای نمایش کنار دسته."),
    )
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)
    is_active = models.BooleanField(_("فعال"), default=True)

    class Meta:
        verbose_name = _("دسته خدمت")
        verbose_name_plural = _("دسته‌بندی خدمات")
        ordering = ("order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class ServiceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def featured(self):
        return self.active().filter(is_featured=True)


class Service(TimeStampedModel):
    """یک خدمت قابل رزرو؛ کارفرما می‌تواند هر زمان خدمت تازه اضافه کند."""

    category = models.ForeignKey(
        ServiceCategory, verbose_name=_("دسته"), related_name="services",
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    title = models.CharField(_("عنوان خدمت"), max_length=150)
    slug = models.SlugField(_("نشانی یکتا"), max_length=170, unique=True, allow_unicode=True, blank=True)
    short_description = models.CharField(_("توضیح کوتاه"), max_length=250, blank=True, default="")
    description = models.TextField(_("توضیح کامل"), blank=True, default="")
    image = models.ImageField(_("تصویر خدمت"), upload_to="services/%Y/%m/", blank=True, null=True)

    base_price = models.PositiveIntegerField(
        _("قیمت پایه (تومان)"), default=0,
        help_text=_("عدد ۰ یعنی «قیمت پس از کارشناسی»."),
    )
    price_note = models.CharField(
        _("توضیح قیمت"), max_length=120, blank=True, default="",
        help_text=_("مثال: از ۵۰۰ هزار تومان، بسته به میزان آسیب"),
    )
    duration_minutes = models.PositiveSmallIntegerField(
        _("مدت زمان تقریبی (دقیقه)"), default=60,
        help_text=_("برای محاسبه‌ی نوبت‌های خالی استفاده می‌شود."),
    )
    deposit_amount = models.PositiveIntegerField(
        _("بیعانه‌ی این خدمت (تومان)"), default=0,
        help_text=_("اگر ۰ باشد، مبلغ پیش‌فرض تنظیمات سایت استفاده می‌شود."),
    )

    is_active = models.BooleanField(_("فعال (نمایش در سایت)"), default=True)
    is_featured = models.BooleanField(_("نمایش در صفحه نخست"), default=False)
    order = models.PositiveSmallIntegerField(_("ترتیب نمایش"), default=0)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        verbose_name = _("خدمت")
        verbose_name_plural = _("خدمات")
        ordering = ("order", "title")
        indexes = [models.Index(fields=["is_active", "order"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True) or "خدمت"
            slug, counter = base_slug, 2
            while Service.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:detail", kwargs={"slug": self.slug})

    @property
    def price_label(self) -> str:
        """متن نمایشی قیمت با ارقام و جداکننده‌ی فارسی."""
        if self.price_note:
            return self.price_note
        if self.base_price:
            from core.jalali import to_persian_digits

            amount = to_persian_digits(f"{self.base_price:,}").replace(",", "\u066c")
            return f"{amount} تومان"
        return "قیمت پس از کارشناسی"

    def deposit_for_booking(self) -> int:
        """مبلغ بیعانه‌ی این خدمت با در نظر گرفتن تنظیمات سایت."""
        if self.deposit_amount:
            return self.deposit_amount
        from core.models import SiteSettings

        return SiteSettings.load().deposit_amount
