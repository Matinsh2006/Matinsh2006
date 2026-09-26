import os
import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .images import optimize_upload
from .utils import normalize_link, tel_link, whatsapp_link


def _random_name(folder, filename):
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"{folder}/{uuid.uuid4().hex[:16]}{ext}"


def site_upload_path(instance, filename):
    return _random_name("site", filename)


def banner_upload_path(instance, filename):
    return _random_name("banners", filename)


def store_upload_path(instance, filename):
    return _random_name("stores", filename)


class SiteSettings(models.Model):
    """Store-wide content editable from the admin (a single row)."""

    class Metal(models.TextChoices):
        ROSE = "rose", "رزگلد"
        GOLD = "gold", "طلایی"
        STEEL = "steel", "استیل نقره‌ای"
        BLACK = "black", "مشکی مات"

    class Dial(models.TextChoices):
        CHOCOLATE = "chocolate", "شکلاتی سان‌برست"
        BLACK = "black", "مشکی"
        BLUE = "blue", "سرمه‌ای"
        GREEN = "green", "سبز زیتونی"
        SILVER = "silver", "نقره‌ای"
        CHAMPAGNE = "champagne", "شامپاینی"

    # Identity
    site_name = models.CharField("نام فروشگاه", max_length=80, default="ثانیه")
    site_name_en = models.CharField("نام لاتین", max_length=80, default="SANIYEH", blank=True)
    tagline = models.CharField("شعار", max_length=160, default="گالری ساعت‌های اصل مردانه و زنانه", blank=True)
    logo = models.ImageField(
        "لوگو", upload_to=site_upload_path, blank=True, help_text="اگر خالی باشد، نام فروشگاه به‌صورت لوگوتایپ نمایش داده می‌شود."
    )

    # Contact & social networks (shown in the footer)
    phone = models.CharField("شماره تماس", max_length=30, blank=True, help_text="مثال: 021-12345678")
    mobile = models.CharField("موبایل پشتیبانی", max_length=30, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    address = models.TextField("نشانی (فوتر)", blank=True)
    working_hours = models.CharField("ساعات پاسخگویی", max_length=160, blank=True)
    telegram = models.CharField("تلگرام", max_length=200, blank=True, help_text="نام کاربری (بدون @) یا لینک کامل")
    instagram = models.CharField("اینستاگرام", max_length=200, blank=True, help_text="نام کاربری یا لینک کامل")
    whatsapp = models.CharField("واتساپ", max_length=200, blank=True, help_text="شماره موبایل (مثلاً 09121234567) یا لینک کامل")
    twitter = models.CharField("توییتر (ایکس)", max_length=200, blank=True, help_text="نام کاربری یا لینک کامل")
    eitaa = models.CharField("ایتا", max_length=200, blank=True)
    bale = models.CharField("بله", max_length=200, blank=True)
    rubika = models.CharField("روبیکا", max_length=200, blank=True)

    # Trust badges
    enamad_code = models.TextField(
        "کد نماد اعتماد الکترونیکی (اینماد)",
        blank=True,
        help_text="کد HTML دریافتی از پنل enamad.ir را کامل و بدون تغییر اینجا قرار دهید.",
    )
    samandehi_code = models.TextField("کد نشان ساماندهی", blank=True, help_text="اختیاری؛ کد HTML نشان ساماندهی.")

    # Footer
    footer_about = models.TextField("متن معرفی کوتاه در فوتر", blank=True)
    copyright_text = models.CharField("متن کپی‌رایت", max_length=200, blank=True)

    # Hero (scroll-driven 3D watch)
    hero_eyebrow = models.CharField("روتیتر", max_length=80, default="گالری ساعت ثانیه", blank=True)
    hero_title = models.CharField("تیتر اصلی", max_length=120, default="هر ثانیه، یک شاهکار")
    hero_subtitle = models.TextField(
        "متن زیر تیتر",
        blank=True,
        default="اصیل‌ترین ساعت‌های مچی مردانه و زنانه؛ با ضمانت اصالت، ارسال بیمه‌شده و مشاوره تخصصی.",
    )
    hero_cta_text = models.CharField("متن دکمه", max_length=40, default="مشاهده مجموعه", blank=True)
    hero_cta_url = models.CharField("لینک دکمه", max_length=300, default="/shop/", blank=True)
    hero_product = models.ForeignKey(
        "catalog.Product",
        verbose_name="محصول معرفی‌شده در انتهای انیمیشن",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    hero_metal = models.CharField("رنگ بدنه ساعت سه‌بعدی", max_length=10, choices=Metal.choices, default=Metal.ROSE)
    hero_dial = models.CharField("رنگ صفحه ساعت سه‌بعدی", max_length=10, choices=Dial.choices, default=Dial.CHOCOLATE)

    # Shipping
    shipping_cost = models.PositiveIntegerField("هزینه ارسال (تومان)", default=150_000)
    free_shipping_threshold = models.PositiveBigIntegerField(
        "ارسال رایگان برای خرید بالای (تومان)", default=10_000_000, help_text="صفر یعنی ارسال رایگان غیرفعال است."
    )

    # SEO
    meta_description = models.CharField("توضیحات متا (سئو)", max_length=300, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self):
        return "تنظیمات سایت"

    def save(self, *args, **kwargs):
        self.pk = 1
        optimize_upload(self.logo, max_side=800)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return (0, {})

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def social_links(self):
        candidates = [
            ("instagram", "اینستاگرام", normalize_link(self.instagram, "https://instagram.com/{}")),
            ("telegram", "تلگرام", normalize_link(self.telegram, "https://t.me/{}")),
            ("whatsapp", "واتساپ", whatsapp_link(self.whatsapp)),
            ("twitter", "توییتر", normalize_link(self.twitter, "https://x.com/{}")),
            ("eitaa", "ایتا", normalize_link(self.eitaa, "https://eitaa.com/{}")),
            ("bale", "بله", normalize_link(self.bale, "https://ble.ir/{}")),
            ("rubika", "روبیکا", normalize_link(self.rubika, "https://rubika.ir/{}")),
        ]
        return [{"key": key, "label": label, "url": url} for key, label, url in candidates if url]

    @property
    def phone_link(self):
        return tel_link(self.phone)

    @property
    def mobile_link(self):
        return tel_link(self.mobile)

    @property
    def has_trust_badges(self):
        return bool(self.enamad_code.strip() or self.samandehi_code.strip())


class BannerQuerySet(models.QuerySet):
    def live(self):
        now = timezone.now()
        return self.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        )


class Banner(models.Model):
    class Placement(models.TextChoices):
        HEADER = "header", "بنر هدر (بالای همه صفحات)"
        HOME = "home", "بنر تبلیغاتی صفحه اصلی"

    class Style(models.TextChoices):
        GOLD = "gold", "طلایی"
        DARK = "dark", "تیره"
        LIGHT = "light", "روشن"

    title = models.CharField("عنوان", max_length=120)
    subtitle = models.CharField("زیرعنوان", max_length=220, blank=True)
    image = models.ImageField(
        "تصویر دسکتاپ",
        upload_to=banner_upload_path,
        blank=True,
        help_text="بنر هدر: حدود ۱۹۲۰×۱۶۰ پیکسل. بنر صفحه اصلی: حدود ۱۶۰۰×۹۰۰ پیکسل. بدون تصویر، بنر متنی با پس‌زمینه طلایی نمایش داده می‌شود.",
    )
    image_mobile = models.ImageField(
        "تصویر موبایل", upload_to=banner_upload_path, blank=True, help_text="اختیاری؛ حدود ۷۵۰×۲۰۰ برای بنر هدر."
    )
    link = models.CharField("لینک", max_length=300, blank=True, help_text="مثلاً /category/sport/ یا یک آدرس کامل")
    button_text = models.CharField("متن دکمه", max_length=40, blank=True)
    placement = models.CharField("محل نمایش", max_length=10, choices=Placement.choices, default=Placement.HEADER)
    style = models.CharField("سبک رنگی", max_length=10, choices=Style.choices, default=Style.GOLD)
    show_text = models.BooleanField("نمایش متن روی تصویر", default=True)
    is_dismissible = models.BooleanField("کاربر بتواند بنر را ببندد", default=True)
    is_active = models.BooleanField("فعال", default=True)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)
    starts_at = models.DateTimeField("شروع نمایش", null=True, blank=True)
    ends_at = models.DateTimeField("پایان نمایش", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BannerQuerySet.as_manager()

    class Meta:
        verbose_name = "بنر"
        verbose_name_plural = "بنرها"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        optimize_upload(self.image)
        optimize_upload(self.image_mobile)
        super().save(*args, **kwargs)

    @property
    def is_external(self):
        return self.link.startswith(("http://", "https://"))

    @property
    def version(self):
        """Changes whenever the banner is edited, so a dismissed banner re-appears after edits."""
        return f"{self.pk}-{int(self.updated_at.timestamp()) if self.updated_at else 0}"


class StoreLocation(models.Model):
    name = models.CharField("نام شعبه", max_length=100, default="شعبه مرکزی")
    address = models.TextField("نشانی")
    phone = models.CharField("تلفن شعبه", max_length=30, blank=True)
    working_hours = models.CharField("ساعات کاری", max_length=200, blank=True, help_text="مثال: شنبه تا پنجشنبه ۱۰ الی ۲۲")
    latitude = models.DecimalField("عرض جغرافیایی (Latitude)", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("طول جغرافیایی (Longitude)", max_digits=9, decimal_places=6)
    zoom = models.PositiveSmallIntegerField("بزرگنمایی نقشه", default=16)
    image = models.ImageField("تصویر مغازه", upload_to=store_upload_path, blank=True)
    neshan_url = models.URLField("لینک نشان", blank=True, help_text="اختیاری؛ در غیر این صورت خودکار ساخته می‌شود.")
    balad_url = models.URLField("لینک بلد", blank=True, help_text="اختیاری؛ در غیر این صورت خودکار ساخته می‌شود.")
    is_active = models.BooleanField("فعال", default=True)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "لوکیشن مغازه"
        verbose_name_plural = "لوکیشن مغازه‌ها"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        optimize_upload(self.image, max_side=1600)
        super().save(*args, **kwargs)

    @property
    def lat(self):
        return f"{Decimal(str(self.latitude)):f}"

    @property
    def lng(self):
        return f"{Decimal(str(self.longitude)):f}"

    @property
    def coords(self):
        return f"{self.lat},{self.lng}"

    @property
    def google_maps_url(self):
        return f"https://www.google.com/maps/search/?api=1&query={self.coords}"

    @property
    def directions_url(self):
        return f"https://www.google.com/maps/dir/?api=1&destination={self.coords}"

    @property
    def waze_url(self):
        return f"https://waze.com/ul?ll={self.coords}&navigate=yes"

    @property
    def neshan_link(self):
        return self.neshan_url or f"https://neshan.org/maps/@{self.coords},{self.zoom}z,0p"

    @property
    def balad_link(self):
        return self.balad_url or (
            f"https://balad.ir/location?latitude={self.lat}&longitude={self.lng}&zoom={self.zoom}"
        )

    @property
    def phone_link(self):
        return tel_link(self.phone)


class Page(models.Model):
    title = models.CharField("عنوان", max_length=120)
    slug = models.SlugField("نامک (آدرس)", max_length=140, unique=True, allow_unicode=True)
    content = models.TextField("محتوا", help_text="می‌توانید از تگ‌های ساده HTML مثل <h2>، <p> و <ul> استفاده کنید.")
    show_in_footer = models.BooleanField("نمایش در فوتر", default=True)
    is_active = models.BooleanField("فعال", default=True)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "صفحه"
        verbose_name_plural = "صفحات ثابت"
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:page", args=[self.slug])


class ContactMessage(models.Model):
    name = models.CharField("نام", max_length=120)
    phone = models.CharField("شماره تماس", max_length=20)
    message = models.TextField("پیام")
    is_read = models.BooleanField("خوانده شده", default=False)
    created_at = models.DateTimeField("زمان ارسال", auto_now_add=True)

    class Meta:
        verbose_name = "پیام تماس"
        verbose_name_plural = "پیام‌های تماس با ما"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.phone}"
