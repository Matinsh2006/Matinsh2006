"""بنرها و نمونه‌کارها (عکس قبل و بعد از انجام خدمات)."""
from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class BannerQuerySet(models.QuerySet):
    def live(self):
        """بنرهای فعال که در بازه‌ی نمایش خود هستند."""
        now = timezone.now()
        return self.filter(is_active=True).filter(
            models.Q(start_at__isnull=True) | models.Q(start_at__lte=now)
        ).filter(models.Q(end_at__isnull=True) | models.Q(end_at__gte=now))


class Banner(TimeStampedModel):
    """بنر تبلیغاتی/نمونه‌کار که کارفرما در بخش‌های مختلف سایت درج می‌کند."""

    class Position(models.TextChoices):
        HERO = "hero", _("اسلایدر بالای صفحه نخست")
        MIDDLE = "middle", _("میانه‌ی صفحه نخست")
        SIDEBAR = "sidebar", _("ستون کناری")
        FOOTER = "footer", _("پایین صفحه")

    title = models.CharField(_("عنوان"), max_length=150)
    subtitle = models.CharField(_("زیرعنوان"), max_length=250, blank=True, default="")
    image = models.ImageField(_("تصویر بنر"), upload_to="banners/%Y/%m/")
    mobile_image = models.ImageField(
        _("تصویر نسخه موبایل"), upload_to="banners/%Y/%m/", blank=True, null=True,
        help_text=_("اختیاری؛ اگر خالی باشد همان تصویر اصلی نمایش داده می‌شود."),
    )
    link_url = models.CharField(_("لینک مقصد"), max_length=300, blank=True, default="")
    button_text = models.CharField(_("متن دکمه"), max_length=60, blank=True, default="")
    position = models.CharField(_("محل نمایش"), max_length=20, choices=Position.choices, default=Position.HERO)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)
    is_active = models.BooleanField(_("فعال"), default=True)
    start_at = models.DateTimeField(_("شروع نمایش"), null=True, blank=True)
    end_at = models.DateTimeField(_("پایان نمایش"), null=True, blank=True)

    objects = BannerQuerySet.as_manager()

    class Meta:
        verbose_name = _("بنر")
        verbose_name_plural = _("بنرها")
        ordering = ("order", "-created_at")

    def __str__(self):
        return self.title

    @property
    def display_image(self):
        return self.image


class PortfolioItem(TimeStampedModel):
    """
    یک نمونه‌کار انجام‌شده.

    هر نمونه‌کار می‌تواند چند عکس «قبل» و چند عکس «بعد» داشته باشد تا
    کیفیت کار در زاویه‌های مختلف دیده شود.
    """

    title = models.CharField(_("عنوان نمونه‌کار"), max_length=160)
    slug = models.SlugField(_("نشانی یکتا"), max_length=180, unique=True, allow_unicode=True, blank=True)
    service = models.ForeignKey(
        "services.Service", verbose_name=_("خدمت مرتبط"), related_name="portfolio_items",
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    car_name = models.CharField(_("خودرو"), max_length=120, blank=True, default="", help_text=_("مثال: پراید ۱۳۱ سفید"))
    description = models.TextField(_("شرح کار انجام‌شده"), blank=True, default="")
    cover = models.ImageField(
        _("تصویر شاخص"), upload_to="portfolio/%Y/%m/", blank=True, null=True,
        help_text=_("اگر خالی باشد، اولین عکس «بعد» به عنوان کاور استفاده می‌شود."),
    )
    duration_label = models.CharField(_("مدت انجام کار"), max_length=80, blank=True, default="", help_text=_("مثال: ۲ روز کاری"))
    completed_at = models.DateField(_("تاریخ انجام"), null=True, blank=True)
    is_featured = models.BooleanField(_("نمایش در صفحه نخست"), default=False)
    is_active = models.BooleanField(_("فعال"), default=True)
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("نمونه‌کار")
        verbose_name_plural = _("نمونه‌کارها")
        ordering = ("order", "-completed_at", "-created_at")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True) or "نمونه-کار"
            slug, counter = base_slug, 2
            while PortfolioItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("gallery:detail", kwargs={"slug": self.slug})

    # -------------------------------------------------------------- عکس‌ها
    @property
    def before_images(self):
        return self.images.filter(kind=PortfolioImage.Kind.BEFORE)

    @property
    def after_images(self):
        return self.images.filter(kind=PortfolioImage.Kind.AFTER)

    @property
    def cover_image(self):
        """تصویر شاخص یا اولین عکسِ «بعد»."""
        if self.cover:
            return self.cover
        first_after = self.after_images.first() or self.images.first()
        return first_after.image if first_after else None

    @property
    def image_count(self) -> int:
        return self.images.count()


class PortfolioImage(models.Model):
    """عکس نمونه‌کار با برچسب قبل/حین/بعد."""

    class Kind(models.TextChoices):
        BEFORE = "before", _("قبل از انجام کار")
        DURING = "during", _("حین انجام کار")
        AFTER = "after", _("بعد از انجام کار")

    item = models.ForeignKey(
        PortfolioItem, verbose_name=_("نمونه‌کار"), related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(_("عکس"), upload_to="portfolio/%Y/%m/")
    kind = models.CharField(_("نوع عکس"), max_length=10, choices=Kind.choices, default=Kind.AFTER)
    caption = models.CharField(_("توضیح عکس"), max_length=150, blank=True, default="")
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("عکس نمونه‌کار")
        verbose_name_plural = _("عکس‌های نمونه‌کار")
        ordering = ("kind", "order", "id")

    def __str__(self):
        return f"{self.item.title} — {self.get_kind_display()}"
