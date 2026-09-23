from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Article(models.Model):
    title = models.CharField("عنوان", max_length=200)
    slug = models.SlugField(
        "اسلاگ", max_length=220, unique=True, blank=True, allow_unicode=True
    )
    cover_image = models.ImageField(
        "تصویر شاخص", upload_to="articles/", blank=True, null=True
    )
    summary = models.CharField("خلاصه", max_length=300, blank=True)
    content = models.TextField(
        "متن مقاله",
        help_text="می‌توانید از تگ‌های ساده HTML (مثل b, br, p) برای قالب‌بندی متن استفاده کنید.",
    )
    is_published = models.BooleanField("منتشر شده", default=True)
    published_at = models.DateTimeField("تاریخ انتشار", default=timezone.now)

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True) or "article"
            slug = base_slug
            counter = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("articles:detail", args=[self.slug])
