from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Page


class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return ["core:home", "catalog:shop", "catalog:men", "catalog:women", "core:contact"]

    def location(self, item):
        return reverse(item)


class PageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    def items(self):
        return Page.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at
