from datetime import time as time_of_day

from django.db import models


class SalonProfile(models.Model):
    """Site-wide info about the shop. Deliberately a singleton (pk is always 1)
    since the site represents a single salon."""

    name = models.CharField("نام مغازه", max_length=150, default="آرایشگاه زنانه")
    tagline = models.CharField("شعار کوتاه", max_length=200, blank=True)
    about = models.TextField("درباره ما", blank=True)
    logo = models.ImageField("لوگو", upload_to="salon/", blank=True, null=True)
    hero_image = models.ImageField(
        "تصویر هدر سایت", upload_to="salon/", blank=True, null=True
    )

    address = models.TextField("آدرس مغازه", blank=True)
    map_lat = models.FloatField("عرض جغرافیایی (lat)", blank=True, null=True)
    map_lng = models.FloatField("طول جغرافیایی (lng)", blank=True, null=True)
    map_link = models.URLField(
        "لینک نقشه (اختیاری)",
        blank=True,
        help_text="اگر مختصات دقیق را ندارید، لینک اشتراک‌گذاری گوگل‌مپ را اینجا وارد کنید.",
    )

    contact_phone = models.CharField(
        "شماره تماس نمایشی", max_length=15, blank=True, help_text="برای دکمه تماس در سایت"
    )
    telegram_url = models.URLField("لینک تلگرام", blank=True)
    instagram_url = models.URLField("لینک اینستاگرام", blank=True)
    whatsapp_url = models.URLField(
        "لینک واتساپ", blank=True, help_text="مثلاً https://wa.me/98912xxxxxxx"
    )
    twitter_url = models.URLField("لینک توییتر (X)", blank=True)

    is_open_saturday = models.BooleanField("باز - شنبه", default=True)
    is_open_sunday = models.BooleanField("باز - یکشنبه", default=True)
    is_open_monday = models.BooleanField("باز - دوشنبه", default=True)
    is_open_tuesday = models.BooleanField("باز - سه‌شنبه", default=True)
    is_open_wednesday = models.BooleanField("باز - چهارشنبه", default=True)
    is_open_thursday = models.BooleanField("باز - پنجشنبه", default=True)
    is_open_friday = models.BooleanField("باز - جمعه", default=False)

    opening_time = models.TimeField("ساعت باز شدن", default=time_of_day(10, 0))
    closing_time = models.TimeField("ساعت بسته شدن", default=time_of_day(20, 0))
    slot_duration_minutes = models.PositiveSmallIntegerField(
        "فاصله بین نوبت‌ها (دقیقه)", default=30
    )

    class Meta:
        verbose_name = "اطلاعات مغازه"
        verbose_name_plural = "اطلاعات مغازه"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    _WEEKDAY_FIELD_BY_INDEX = {
        0: "is_open_monday",
        1: "is_open_tuesday",
        2: "is_open_wednesday",
        3: "is_open_thursday",
        4: "is_open_friday",
        5: "is_open_saturday",
        6: "is_open_sunday",
    }

    def is_open_on(self, date_value):
        field_name = self._WEEKDAY_FIELD_BY_INDEX[date_value.weekday()]
        return getattr(self, field_name)

    def map_embed_url(self):
        if self.map_lat is not None and self.map_lng is not None:
            return (
                f"https://www.google.com/maps?q={self.map_lat},{self.map_lng}"
                "&hl=fa&z=16&output=embed"
            )
        return ""

    def map_view_url(self):
        if self.map_lat is not None and self.map_lng is not None:
            return f"https://www.google.com/maps?q={self.map_lat},{self.map_lng}"
        return self.map_link

    def social_links(self):
        links = []
        if self.telegram_url:
            links.append({"key": "telegram", "label": "تلگرام", "url": self.telegram_url})
        if self.instagram_url:
            links.append({"key": "instagram", "label": "اینستاگرام", "url": self.instagram_url})
        if self.whatsapp_url:
            links.append({"key": "whatsapp", "label": "واتساپ", "url": self.whatsapp_url})
        if self.twitter_url:
            links.append({"key": "twitter", "label": "توییتر", "url": self.twitter_url})
        return links
