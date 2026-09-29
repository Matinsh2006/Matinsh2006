from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.fields import RichTextField
from apps.core.utils.images import optimize_image_field
from apps.core.utils.slugs import unique_slugify
from apps.core.utils.text import html_to_text, normalize_persian

WORDS_PER_MINUTE = 200


class ArticleCategory(models.Model):
    name = models.CharField("نام", max_length=100)
    slug = models.SlugField("نامک (آدرس)", max_length=120, unique=True, allow_unicode=True, blank=True)
    order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "دسته‌بندی مقاله"
        verbose_name_plural = "دسته‌بندی مقالات"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = normalize_persian(self.name)
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:category", kwargs={"slug": self.slug})


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Article.Status.PUBLISHED, published_at__lte=timezone.now())


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        PUBLISHED = "published", "منتشرشده"

    title = models.CharField("عنوان", max_length=200)
    slug = models.SlugField("نامک (آدرس)", max_length=220, unique=True, allow_unicode=True, blank=True)
    category = models.ForeignKey(
        ArticleCategory,
        verbose_name="دسته‌بندی",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="نویسنده",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    cover = models.ImageField(
        "تصویر شاخص", upload_to="articles/%Y/%m/", blank=True, help_text="ابعاد پیشنهادی: ۱۲۰۰×۶۷۵ پیکسل (۱۶ به ۹)"
    )
    summary = models.TextField("خلاصه", max_length=500, blank=True, help_text="در فهرست مقالات و نتایج گوگل نمایش داده می‌شود.")
    body = RichTextField("متن مقاله")
    status = models.CharField("وضعیت", max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_featured = models.BooleanField("مقاله ویژه", default=False)
    published_at = models.DateTimeField(
        "زمان انتشار", default=timezone.now, help_text="برای انتشار زمان‌بندی‌شده، زمانی در آینده انتخاب کنید."
    )
    related_products = models.ManyToManyField(
        "catalog.Product", verbose_name="محصولات مرتبط", blank=True, related_name="articles"
    )
    views = models.PositiveIntegerField("تعداد بازدید", default=0)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.title = normalize_persian(self.title)
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        optimize_image_field(self.cover)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED and self.published_at <= timezone.now()

    @property
    def reading_time(self):
        return max(1, round(len(html_to_text(self.body).split()) / WORDS_PER_MINUTE))

    @property
    def excerpt(self):
        if self.summary:
            return self.summary
        text = html_to_text(self.body)
        return text[:220] + ("…" if len(text) > 220 else "")
