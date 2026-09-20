from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class SingletonModel(models.Model):
    """مدلی که فقط یک ردیف دارد (تنظیمات سایت)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - از حذف جلوگیری می‌کند
        raise ValidationError(_("تنظیمات سایت قابل حذف نیست."))

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class SiteSetting(SingletonModel):
    """اطلاعات کلی فروشگاه: نام، لوکیشن و شبکه‌های اجتماعی."""

    site_name = models.CharField(_("نام فروشگاه"), max_length=120, default="بوتیک ایرانی")
    tagline = models.CharField(_("شعار فروشگاه"), max_length=200, blank=True)
    logo = models.ImageField(_("لوگو"), upload_to="site/", blank=True, null=True)
    about = models.TextField(_("درباره ما"), blank=True)

    # --- تماس و لوکیشن مغازه ---
    phone = models.CharField(_("شماره تماس"), max_length=20, blank=True)
    email = models.EmailField(_("ایمیل"), blank=True)
    address = models.CharField(_("آدرس مغازه"), max_length=300, blank=True)
    city = models.CharField(_("شهر"), max_length=80, blank=True)
    postal_code = models.CharField(_("کد پستی"), max_length=20, blank=True)
    latitude = models.DecimalField(
        _("عرض جغرافیایی"), max_digits=9, decimal_places=6, blank=True, null=True
    )
    longitude = models.DecimalField(
        _("طول جغرافیایی"), max_digits=9, decimal_places=6, blank=True, null=True
    )
    map_embed_url = models.URLField(
        _("لینک نقشه (iframe)"),
        blank=True,
        help_text=_("در صورت خالی بودن، از مختصات جغرافیایی نقشه ساخته می‌شود."),
    )
    working_hours = models.CharField(_("ساعات کاری"), max_length=200, blank=True)

    # --- شبکه‌های اجتماعی ---
    telegram = models.URLField(_("تلگرام"), blank=True)
    instagram = models.URLField(_("اینستاگرام"), blank=True)
    whatsapp = models.CharField(
        _("واتساپ"),
        max_length=120,
        blank=True,
        help_text=_("شماره با کد کشور، مثال: 989121234567"),
    )
    twitter = models.URLField(_("توییتر (X)"), blank=True)

    shipping_cost = models.PositiveIntegerField(_("هزینه ارسال (تومان)"), default=0)
    free_shipping_threshold = models.PositiveIntegerField(
        _("سقف ارسال رایگان (تومان)"), default=0, help_text=_("صفر یعنی غیرفعال")
    )

    class Meta:
        verbose_name = _("تنظیمات سایت")
        verbose_name_plural = _("تنظیمات سایت")

    def __str__(self):
        return self.site_name

    @property
    def whatsapp_link(self):
        if not self.whatsapp:
            return ""
        if self.whatsapp.startswith("http"):
            return self.whatsapp
        return f"https://wa.me/{self.whatsapp.lstrip('+')}"

    @property
    def map_url(self):
        """آدرس iframe نقشه؛ یا دستی یا ساخته‌شده از مختصات."""
        if self.map_embed_url:
            return self.map_embed_url
        if self.latitude is not None and self.longitude is not None:
            lat, lng = self.latitude, self.longitude
            delta = 0.006
            bbox = f"{float(lng) - delta}%2C{float(lat) - delta}%2C{float(lng) + delta}%2C{float(lat) + delta}"
            return (
                f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}"
                f"&layer=mapnik&marker={lat}%2C{lng}"
            )
        return ""

    @property
    def directions_url(self):
        if self.latitude is not None and self.longitude is not None:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        if self.address:
            return f"https://www.google.com/maps/search/?api=1&query={self.address}"
        return ""

    @property
    def has_social(self):
        return any([self.telegram, self.instagram, self.whatsapp, self.twitter, self.phone])


class Banner(models.Model):
    """بنرهای اسلایدر زیر هدر."""

    title = models.CharField(_("عنوان"), max_length=150, blank=True)
    subtitle = models.CharField(_("زیرعنوان"), max_length=250, blank=True)
    image = models.ImageField(_("تصویر"), upload_to="banners/")
    link = models.CharField(_("لینک"), max_length=300, blank=True)
    button_text = models.CharField(_("متن دکمه"), max_length=60, blank=True)
    is_active = models.BooleanField(_("فعال"), default=True)
    order = models.PositiveSmallIntegerField(_("ترتیب نمایش"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("بنر")
        verbose_name_plural = _("بنرها")
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title or f"بنر #{self.pk}"
