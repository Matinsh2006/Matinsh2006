from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Service(models.Model):
    name = models.CharField("نام خدمت", max_length=150)
    slug = models.SlugField(
        "اسلاگ", max_length=170, unique=True, blank=True, allow_unicode=True
    )
    short_description = models.CharField("توضیح کوتاه", max_length=250, blank=True)
    description = models.TextField("توضیحات کامل", blank=True)
    image = models.ImageField("تصویر خدمت", upload_to="services/", blank=True, null=True)
    price = models.PositiveIntegerField("قیمت (تومان)", default=0)
    duration_minutes = models.PositiveSmallIntegerField("مدت زمان (دقیقه)", default=30)
    deposit_amount = models.PositiveIntegerField(
        "مبلغ بیعانه (تومان)",
        default=0,
        help_text="اگر صفر باشد، برای رزرو این خدمت بیعانه دریافت نمی‌شود.",
    )
    is_active = models.BooleanField("فعال / نمایش در سایت", default=True)
    order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "خدمت"
        verbose_name_plural = "خدمات"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True) or "service"
            slug = base_slug
            counter = 1
            while Service.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:detail", args=[self.slug])

    @property
    def requires_deposit(self):
        return self.deposit_amount > 0
