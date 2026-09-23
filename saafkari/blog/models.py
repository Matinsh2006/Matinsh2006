"""مقالات و مطالب آموزشی سایت."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class ArticleCategory(models.Model):
    """دسته‌بندی مقالات."""

    name = models.CharField(_("نام دسته"), max_length=100, unique=True)
    slug = models.SlugField(_("نشانی یکتا"), max_length=120, unique=True, allow_unicode=True, blank=True)
    description = models.CharField(_("توضیح کوتاه"), max_length=250, blank=True, default="")
    order = models.PositiveSmallIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("دسته مقاله")
        verbose_name_plural = _("دسته‌بندی مقالات")
        ordering = ("order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True, published_at__lte=timezone.now())


class Article(TimeStampedModel):
    """مقاله‌ی سایت؛ کارفرما از پنل مقاله‌ی تازه اضافه می‌کند."""

    title = models.CharField(_("عنوان مقاله"), max_length=200)
    slug = models.SlugField(_("نشانی یکتا"), max_length=220, unique=True, allow_unicode=True, blank=True)
    category = models.ForeignKey(
        ArticleCategory, verbose_name=_("دسته"), related_name="articles",
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("نویسنده"), related_name="articles",
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    cover = models.ImageField(_("تصویر شاخص"), upload_to="articles/%Y/%m/", blank=True, null=True)
    summary = models.TextField(_("خلاصه"), max_length=500, blank=True, default="")
    content = models.TextField(_("متن مقاله"), help_text=_("می‌توانید از پاراگراف‌های ساده استفاده کنید."))
    tags = models.CharField(
        _("برچسب‌ها"), max_length=250, blank=True, default="",
        help_text=_("برچسب‌ها را با ویرگول جدا کنید. مثال: صافکاری, نقاشی خودرو"),
    )

    is_published = models.BooleanField(_("منتشر شده"), default=True)
    published_at = models.DateTimeField(_("تاریخ انتشار"), default=timezone.now)
    is_featured = models.BooleanField(_("نمایش در صفحه نخست"), default=False)
    views_count = models.PositiveIntegerField(_("تعداد بازدید"), default=0)
    reading_minutes = models.PositiveSmallIntegerField(_("زمان مطالعه (دقیقه)"), default=0)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        verbose_name = _("مقاله")
        verbose_name_plural = _("مقالات")
        ordering = ("-published_at",)
        indexes = [models.Index(fields=["is_published", "-published_at"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True) or "مقاله"
            slug, counter = base_slug, 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.summary:
            self.summary = self.content[:250]
        if not self.reading_minutes:
            words = len(self.content.split())
            self.reading_minutes = max(1, round(words / 200))
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})

    @property
    def tag_list(self) -> list[str]:
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    @property
    def paragraphs(self) -> list[str]:
        """متن مقاله به صورت پاراگراف‌های جدا برای نمایش امن در قالب."""
        return [part.strip() for part in self.content.replace("\r\n", "\n").split("\n\n") if part.strip()]
