from django.contrib.sitemaps import Sitemap

from .models import Brand, Category, Product


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.active().order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Category.objects.active().select_related("parent").order_by("parent_id", "order")


class BrandSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Brand.objects.filter(is_active=True)
