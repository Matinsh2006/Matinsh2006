from django.db import models


class PortfolioItem(models.Model):
    title = models.CharField("عنوان نمونه‌کار", max_length=150)
    description = models.TextField("توضیحات", blank=True)
    is_published = models.BooleanField("نمایش در سایت", default=True)
    order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نمونه‌کار"
        verbose_name_plural = "نمونه‌کارها"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def cover_image(self):
        first = self.images.first()
        return first.image if first else None


class PortfolioImage(models.Model):
    TYPE_BEFORE = "before"
    TYPE_AFTER = "after"
    TYPE_GENERAL = "general"
    TYPE_CHOICES = [
        (TYPE_BEFORE, "قبل از انجام کار"),
        (TYPE_AFTER, "بعد از انجام کار"),
        (TYPE_GENERAL, "عمومی"),
    ]

    portfolio_item = models.ForeignKey(
        PortfolioItem, on_delete=models.CASCADE, related_name="images", verbose_name="نمونه‌کار"
    )
    image = models.ImageField("تصویر", upload_to="portfolio/")
    image_type = models.CharField(
        "نوع تصویر", max_length=10, choices=TYPE_CHOICES, default=TYPE_GENERAL
    )
    order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "تصویر نمونه‌کار"
        verbose_name_plural = "تصاویر نمونه‌کار"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.portfolio_item.title} ({self.get_image_type_display()})"
