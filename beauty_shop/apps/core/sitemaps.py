from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Page


class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return ["core:home", "catalog:product_list", "catalog:brand_list", "blog:list", "core:contact"]

    def location(self, item):
        return reverse(item)


class PageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.3

    def items(self):
        return Page.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at
