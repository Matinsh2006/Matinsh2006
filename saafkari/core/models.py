"""مدل‌های پایه‌ی سایت: تنظیمات، شعبه/لوکیشن، شبکه‌های اجتماعی و پیام تماس."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import normalize_phone


class TimeStampedModel(models.Model):
    """مدل انتزاعی با زمان ساخت و ویرایش."""

    created_at = models.DateTimeField(_("زمان ثبت"), auto_now_add=True)
    updated_at = models.DateTimeField(_("آخرین ویرایش"), auto_now=True)

    class Meta:
        abstract = True


class SingletonModel(models.Model):
    """مدلی که فقط یک ردیف دارد (تنظیمات سایت)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - از حذف جلوگیری می‌کند
        pass

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(SingletonModel):
    """تنظیمات کلی سایت که کارفرما از پنل ویرایش می‌کند."""

    brand_name = models.CharField(_("نام مغازه"), max_length=120, default="صافکاری و نقاشی")
    tagline = models.CharField(_("شعار کوتاه"), max_length=200, blank=True, default="صافکاری بدون رنگ، نقاشی و پولیش تخصصی")
    about = models.TextField(_("درباره‌ی ما"), blank=True)
    logo = models.ImageField(_("لوگو"), upload_to="site/", blank=True, null=True)
    hero_image = models.ImageField(_("تصویر اصلی صفحه نخست"), upload_to="site/", blank=True, null=True)

    phone = models.CharField(_("شماره تماس اصلی"), max_length=20, blank=True, default="")
    second_phone = models.CharField(_("شماره تماس دوم"), max_length=20, blank=True, default="")
    email = models.EmailField(_("ایمیل"), blank=True, default="")

    working_hours = models.CharField(
        _("ساعت کاری (متن نمایشی)"), max_length=200, blank=True,
        default="شنبه تا پنجشنبه، ۹ صبح تا ۸ شب",
    )

    deposit_amount = models.PositiveIntegerField(
        _("مبلغ پیش‌فرض بیعانه (تومان)"), default=200000,
        help_text=_("مبلغی که هنگام رزرو نوبت به عنوان بیعانه از مشتری گرفته می‌شود."),
    )
    online_payment_enabled = models.BooleanField(_("پرداخت آنلاین بیعانه فعال باشد"), default=True)
    require_deposit = models.BooleanField(
        _("پرداخت بیعانه برای قطعی‌شدن نوبت الزامی است"), default=False,
    )

    meta_description = models.CharField(_("توضیح متا (سئو)"), max_length=300, blank=True, default="")
    enamad_code = models.TextField(_("کد نماد اعتماد الکترونیکی"), blank=True, default="")

    class Meta:
        verbose_name = _("تنظیمات سایت")
        verbose_name_plural = _("تنظیمات سایت")

    def __str__(self):
        return self.brand_name

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone) or self.phone
        self.second_phone = normalize_phone(self.second_phone) or self.second_phone
        super().save(*args, **kwargs)

    @property
    def main_location(self):
        return self.locations.filter(is_active=True).order_by("-is_main", "id").first()


class ShopLocation(TimeStampedModel):
    """لوکیشن مغازه روی نقشه (امکان ثبت چند شعبه)."""

    settings = models.ForeignKey(
        SiteSettings, verbose_name=_("تنظیمات سایت"), related_name="locations",
        on_delete=models.CASCADE, default=1,
    )
    title = models.CharField(_("عنوان شعبه"), max_length=120, default="شعبه اصلی")
    address = models.TextField(_("آدرس"))
    city = models.CharField(_("شهر"), max_length=80, blank=True, default="")
    province = models.CharField(_("استان"), max_length=80, blank=True, default="")
    postal_code = models.CharField(_("کد پستی"), max_length=15, blank=True, default="")
    phone = models.CharField(_("تلفن شعبه"), max_length=20, blank=True, default="")

    latitude = models.DecimalField(
        _("عرض جغرافیایی"), max_digits=10, decimal_places=7, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text=_("مثال: ۳۵.۶۸۹۲ — از گوگل‌مپ یا نشان کپی کنید."),
    )
    longitude = models.DecimalField(
        _("طول جغرافیایی"), max_digits=10, decimal_places=7, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text=_("مثال: ۵۱.۳۸۹۰"),
    )
    map_zoom = models.PositiveSmallIntegerField(_("بزرگ‌نمایی نقشه"), default=16)
    map_link = models.URLField(
        _("لینک مسیریابی"), blank=True, default="",
        help_text=_("در صورت خالی بودن، لینک گوگل‌مپ از مختصات ساخته می‌شود."),
    )
    is_main = models.BooleanField(_("شعبه اصلی"), default=True)
    is_active = models.BooleanField(_("نمایش در سایت"), default=True)

    class Meta:
        verbose_name = _("لوکیشن مغازه")
        verbose_name_plural = _("لوکیشن مغازه")
        ordering = ("-is_main", "title")

    def __str__(self):
        return self.title

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def osm_embed_url(self) -> str:
        """نشانی نقشه‌ی جاسازی‌شده‌ی OpenStreetMap (بدون نیاز به کلید API)."""
        if not self.has_coordinates:
            return ""
        lat, lng = float(self.latitude), float(self.longitude)
        # اندازه‌ی کادر نقشه بر اساس میزان بزرگ‌نمایی انتخابی کارفرما
        span = max(0.0008, 0.02 / max(1, self.map_zoom - 12))
        bbox = f"{lng - span:.6f},{lat - span / 2:.6f},{lng + span:.6f},{lat + span / 2:.6f}"
        return (
            "https://www.openstreetmap.org/export/embed.html"
            f"?bbox={bbox}&layer=mapnik&marker={lat:.6f},{lng:.6f}"
        )

    @property
    def directions_url(self) -> str:
        """لینک مسیریابی؛ اگر کارفرما لینک نداده باشد از مختصات ساخته می‌شود."""
        if self.map_link:
            return self.map_link
        if self.has_coordinates:
            return f"https://www.google.com/maps/dir/?api=1&destination={self.latitude},{self.longitude}"
        return ""


class SocialLink(models.Model):
    """لینک شبکه‌های اجتماعی و راه‌های ارتباطی."""

    class Platform(models.TextChoices):
        TELEGRAM = "telegram", _("تلگرام")
        INSTAGRAM = "instagram", _("اینستاگرام")
        WHATSAPP = "whatsapp", _("واتساپ")
        TWITTER = "twitter", _("توییتر (X)")
        PHONE = "phone", _("تماس تلفنی")
        EITAA = "eitaa", _("ایتا")
        RUBIKA = "rubika", _("روبیکا")
        APARAT = "aparat", _("آپارات")
        YOUTUBE = "youtube", _("یوتیوب")
        LINKEDIN = "linkedin", _("لینکدین")
        EMAIL = "email", _("ایمیل")
        WEBSITE = "website", _("وب‌سایت")

    #: الگوی ساخت نشانی نهایی از روی شناسه‌ی واردشده
    URL_TEMPLATES = {
        Platform.TELEGRAM: "https://t.me/{}",
        Platform.INSTAGRAM: "https://instagram.com/{}",
        Platform.TWITTER: "https://twitter.com/{}",
        Platform.EITAA: "https://eitaa.com/{}",
        Platform.RUBIKA: "https://rubika.ir/{}",
        Platform.APARAT: "https://www.aparat.com/{}",
        Platform.YOUTUBE: "https://youtube.com/{}",
        Platform.LINKEDIN: "https://linkedin.com/in/{}",
    }

    platform = models.CharField(_("شبکه اجتماعی"), max_length=20, choices=Platform.choices)
    value = models.CharField(
        _("شناسه یا نشانی"), max_length=255,
        help_text=_("برای تلگرام/اینستاگرام آیدی بدون @، برای واتساپ و تماس شماره موبایل، برای بقیه نشانی کامل."),
    )
    label = models.CharField(_("برچسب نمایشی"), max_length=80, blank=True, default="")
    order = models.PositiveSmallIntegerField(_("ترتیب نمایش"), default=0)
    is_active = models.BooleanField(_("فعال"), default=True)
    show_in_header = models.BooleanField(_("نمایش در بالای سایت"), default=False)

    class Meta:
        verbose_name = _("لینک شبکه اجتماعی")
        verbose_name_plural = _("لینک‌های شبکه اجتماعی")
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.get_platform_display()} — {self.value}"

    def clean(self):
        if self.platform in {self.Platform.WHATSAPP, self.Platform.PHONE}:
            if not normalize_phone(self.value):
                raise ValidationError({"value": _("برای واتساپ و تماس باید شماره موبایل وارد شود.")})

    @property
    def url(self) -> str:
        """نشانی نهایی بر اساس نوع شبکه‌ی اجتماعی."""
        value = (self.value or "").strip()
        if value.startswith(("http://", "https://", "tel:", "mailto:")):
            return value
        platform = self.platform
        if platform == self.Platform.WHATSAPP:
            phone = normalize_phone(value)
            return f"https://wa.me/98{phone[1:]}" if phone.startswith("0") else f"https://wa.me/{phone}"
        if platform == self.Platform.PHONE:
            return f"tel:{normalize_phone(value) or value}"
        if platform == self.Platform.EMAIL:
            return f"mailto:{value}"
        template = self.URL_TEMPLATES.get(platform)
        if template:
            return template.format(value.lstrip("@"))
        return value

    @property
    def display_label(self) -> str:
        return self.label or self.get_platform_display()


class ContactMessage(TimeStampedModel):
    """پیام‌های فرم تماس با ما."""

    name = models.CharField(_("نام"), max_length=120)
    phone = models.CharField(_("شماره تماس"), max_length=20)
    subject = models.CharField(_("موضوع"), max_length=200, blank=True, default="")
    message = models.TextField(_("متن پیام"))
    is_read = models.BooleanField(_("خوانده شده"), default=False)

    class Meta:
        verbose_name = _("پیام تماس")
        verbose_name_plural = _("پیام‌های تماس")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} — {self.phone}"

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone) or self.phone
        super().save(*args, **kwargs)
