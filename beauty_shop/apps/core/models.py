import re

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, validate_email
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .fields import RichTextField
from .utils.images import optimize_image_field
from .utils.slugs import unique_slugify
from .utils.text import phone_for_tel_link, phone_to_international, to_latin_digits


def validate_site_link(value):
    """Only relative paths and http(s) links (blocks ``javascript:`` URLs)."""
    if value and not value.startswith(("/", "http://", "https://")):
        raise ValidationError("لینک باید با / (آدرس داخلی سایت) یا https:// شروع شود.")


class SiteSettings(models.Model):
    """Singleton holding the store's general information (edited in the admin)."""

    site_name = models.CharField("نام فروشگاه", max_length=100, default="فروشگاه لوازم آرایشی")
    slogan = models.CharField("شعار", max_length=200, blank=True)
    logo = models.ImageField("لوگو", upload_to="site/", blank=True)
    favicon = models.ImageField(
        "آیکون سایت (favicon)", upload_to="site/", blank=True, help_text="تصویر مربعی، حداقل ۱۹۲×۱۹۲ پیکسل"
    )
    about_short = models.TextField("معرفی کوتاه (نمایش در فوتر)", blank=True)
    phone = models.CharField("تلفن پشتیبانی", max_length=50, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    working_hours = models.CharField("ساعات پاسخگویی", max_length=150, blank=True)
    shipping_cost = models.PositiveIntegerField("هزینه ارسال (تومان)", default=50000)
    free_shipping_threshold = models.PositiveIntegerField(
        "حداقل خرید برای ارسال رایگان (تومان)", default=0, help_text="عدد صفر یعنی ارسال رایگان غیرفعال است."
    )
    enamad_code = models.TextField(
        "کد نماد اعتماد الکترونیکی (اینماد)",
        blank=True,
        help_text="کد HTML دریافتی از سایت enamad.ir را اینجا قرار دهید تا در فوتر نمایش داده شود.",
    )
    meta_description = models.CharField("توضیحات متا (سئو)", max_length=300, blank=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        verbose_name = "تنظیمات کلی سایت"
        verbose_name_plural = "تنظیمات کلی سایت"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        optimize_image_field(self.logo, max_dimension=600)
        optimize_image_field(self.favicon, max_dimension=512)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # The singleton row is never removed.
        return 0, {}

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def shipping_cost_for(self, items_total):
        if self.free_shipping_threshold and items_total >= self.free_shipping_threshold:
            return 0
        return self.shipping_cost

    @property
    def phone_link(self):
        return f"tel:{phone_for_tel_link(self.phone)}" if self.phone else ""


class SocialLink(models.Model):
    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "اینستاگرام"
        TELEGRAM = "telegram", "تلگرام"
        WHATSAPP = "whatsapp", "واتساپ"
        TWITTER = "twitter", "توییتر (ایکس)"
        PHONE = "phone", "تلفن تماس"
        EMAIL = "email", "ایمیل"
        EITAA = "eitaa", "ایتا"
        BALE = "bale", "بله"
        RUBIKA = "rubika", "روبیکا"
        APARAT = "aparat", "آپارات"
        YOUTUBE = "youtube", "یوتیوب"

    PROFILE_URLS = {
        Platform.INSTAGRAM: "https://instagram.com/{}",
        Platform.TELEGRAM: "https://t.me/{}",
        Platform.TWITTER: "https://x.com/{}",
        Platform.EITAA: "https://eitaa.com/{}",
        Platform.BALE: "https://ble.ir/{}",
        Platform.RUBIKA: "https://rubika.ir/{}",
        Platform.APARAT: "https://www.aparat.com/{}",
        Platform.YOUTUBE: "https://www.youtube.com/@{}",
    }
    ICONS = {
        Platform.INSTAGRAM: "instagram",
        Platform.TELEGRAM: "telegram",
        Platform.WHATSAPP: "whatsapp",
        Platform.TWITTER: "x-logo",
        Platform.PHONE: "phone",
        Platform.EMAIL: "mail",
        Platform.APARAT: "play",
        Platform.YOUTUBE: "youtube",
    }

    platform = models.CharField("شبکه اجتماعی", max_length=20, choices=Platform.choices)
    value = models.CharField(
        "نام کاربری / شماره / لینک",
        max_length=200,
        help_text=(
            "اینستاگرام، تلگرام، توییتر و …: نام کاربری (مثل rozbeauty) یا لینک کامل. "
            "واتساپ و تلفن: شماره (مثل 09121234567 یا 02188776655). ایمیل: آدرس ایمیل."
        ),
    )
    title = models.CharField("عنوان نمایشی", max_length=60, blank=True, help_text="اختیاری؛ مثلاً «پشتیبانی واتساپ»")
    show_in_floating = models.BooleanField("نمایش در دکمه تماس شناور", default=True)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "لینک شبکه اجتماعی / تماس"
        verbose_name_plural = "شبکه‌های اجتماعی و راه‌های تماس"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.get_platform_display()}: {self.value}"

    def clean(self):
        value = (self.value or "").strip()
        self.value = value
        if self.platform in (self.Platform.PHONE, self.Platform.WHATSAPP):
            if not value.startswith(("http://", "https://")):
                digits = re.sub(r"\D", "", to_latin_digits(value))
                if len(digits) < 8:
                    raise ValidationError({"value": "شماره تلفن معتبر وارد کنید."})
        elif self.platform == self.Platform.EMAIL:
            try:
                validate_email(value)
            except ValidationError:
                raise ValidationError({"value": "آدرس ایمیل معتبر نیست."}) from None
        elif not value.startswith(("http://", "https://")) and not re.match(r"^@?[\w.\-]+$", value):
            raise ValidationError({"value": "نام کاربری فقط می‌تواند شامل حروف انگلیسی، عدد، نقطه و _ باشد."})

    @property
    def url(self):
        value = (self.value or "").strip()
        if self.platform == self.Platform.PHONE:
            return f"tel:{phone_for_tel_link(value)}"
        if self.platform == self.Platform.EMAIL:
            return f"mailto:{value}"
        if value.startswith(("http://", "https://")):
            return value
        if self.platform == self.Platform.WHATSAPP:
            return f"https://wa.me/{phone_to_international(value)}"
        return self.PROFILE_URLS[self.platform].format(value.lstrip("@"))

    @property
    def is_external(self):
        return self.platform not in (self.Platform.PHONE, self.Platform.EMAIL)

    @property
    def icon(self):
        return self.ICONS.get(self.platform, "message")

    @property
    def label(self):
        return self.title or self.get_platform_display()

    @property
    def display_value(self):
        value = (self.value or "").strip()
        if self.platform in (self.Platform.PHONE, self.Platform.WHATSAPP, self.Platform.EMAIL):
            return value
        if value.startswith(("http://", "https://")):
            return value.split("://", 1)[1].rstrip("/")
        return "@" + value.lstrip("@")


class Branch(models.Model):
    """A physical store location shown on the contact page map."""

    name = models.CharField("نام شعبه", max_length=120, default="فروشگاه مرکزی")
    address = models.TextField("آدرس")
    phone = models.CharField("تلفن", max_length=50, blank=True)
    working_hours = models.CharField("ساعات کاری", max_length=150, blank=True, help_text="مثال: شنبه تا پنجشنبه ۱۰ تا ۲۱")
    latitude = models.DecimalField(
        "عرض جغرافیایی (Latitude)",
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="با کلیک روی نقشه بالا به‌صورت خودکار پر می‌شود.",
    )
    longitude = models.DecimalField(
        "طول جغرافیایی (Longitude)",
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    zoom = models.PositiveSmallIntegerField(
        "بزرگنمایی نقشه", default=16, validators=[MinValueValidator(3), MaxValueValidator(19)]
    )
    neshan_url = models.URLField("لینک مکان در نشان", blank=True, help_text="اختیاری؛ لینک اشتراک‌گذاری از اپلیکیشن نشان")
    balad_url = models.URLField("لینک مکان در بلد", blank=True, help_text="اختیاری؛ لینک اشتراک‌گذاری از اپلیکیشن بلد")
    is_active = models.BooleanField("فعال", default=True)
    order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "موقعیت فروشگاه"
        verbose_name_plural = "موقعیت فروشگاه و شعب"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def coordinates(self):
        return f"{self.latitude},{self.longitude}"

    @property
    def google_maps_url(self):
        return f"https://www.google.com/maps/search/?api=1&query={self.coordinates}"

    @property
    def directions_url(self):
        return f"https://www.google.com/maps/dir/?api=1&destination={self.coordinates}"

    @property
    def phone_link(self):
        return f"tel:{phone_for_tel_link(self.phone)}" if self.phone else ""

    def as_map_data(self):
        return {
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "lat": float(self.latitude),
            "lng": float(self.longitude),
            "zoom": self.zoom,
            "directions": self.directions_url,
        }


class BannerQuerySet(models.QuerySet):
    def live(self):
        now = timezone.now()
        return (
            self.filter(is_active=True)
            .filter(Q(start_at__isnull=True) | Q(start_at__lte=now))
            .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
        )


class Banner(models.Model):
    class Position(models.TextChoices):
        HERO = "hero", "اسلایدر اصلی صفحه نخست"
        PROMO = "promo", "بنر تبلیغاتی میانه صفحه نخست"

    title = models.CharField("عنوان", max_length=150, help_text="به عنوان متن جایگزین تصویر هم استفاده می‌شود.")
    subtitle = models.CharField("زیرعنوان", max_length=250, blank=True)
    image = models.ImageField(
        "تصویر دسکتاپ",
        upload_to="banners/%Y/%m/",
        help_text="اسلایدر: ۱۹۲۰×۶۴۰ پیکسل (نسبت ۳ به ۱) — بنر میانی: ۹۰۰×۴۰۰ پیکسل",
    )
    mobile_image = models.ImageField(
        "تصویر موبایل",
        upload_to="banners/%Y/%m/",
        blank=True,
        help_text="اختیاری؛ برای نمایش بهتر در موبایل — ۸۰۰×۶۰۰ پیکسل (نسبت ۴ به ۳)",
    )
    link = models.CharField(
        "لینک",
        max_length=300,
        blank=True,
        validators=[validate_site_link],
        help_text="مثال: /products/?discount=1 یا /brands/نام-برند/ یا https://…",
    )
    button_text = models.CharField("متن دکمه", max_length=40, blank=True, help_text="مثال: مشاهده و خرید")
    show_text = models.BooleanField("نمایش عنوان روی تصویر", default=True)
    position = models.CharField("محل نمایش", max_length=10, choices=Position.choices, default=Position.HERO)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    start_at = models.DateTimeField("شروع نمایش", null=True, blank=True)
    end_at = models.DateTimeField("پایان نمایش", null=True, blank=True)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)

    objects = BannerQuerySet.as_manager()

    class Meta:
        verbose_name = "بنر"
        verbose_name_plural = "بنرها و اسلایدر"
        ordering = ["position", "order", "-id"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValidationError({"end_at": "زمان پایان باید بعد از زمان شروع باشد."})

    def save(self, *args, **kwargs):
        optimize_image_field(self.image, max_dimension=1920)
        optimize_image_field(self.mobile_image, max_dimension=1000)
        super().save(*args, **kwargs)


class Page(models.Model):
    """Simple content pages such as "About us", "Terms" and "Privacy"."""

    title = models.CharField("عنوان", max_length=150)
    slug = models.SlugField("نامک (آدرس)", max_length=160, unique=True, allow_unicode=True, blank=True)
    body = RichTextField("متن صفحه", blank=True)
    show_in_footer = models.BooleanField("نمایش در فوتر", default=True)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        verbose_name = "صفحه"
        verbose_name_plural = "صفحات ثابت (درباره ما، قوانین و …)"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:page", kwargs={"slug": self.slug})
