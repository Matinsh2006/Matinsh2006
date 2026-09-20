from django.test import TestCase
from django.urls import reverse

from apps.core.models import Banner, SiteSetting


class SiteSettingTests(TestCase):
    def test_singleton_always_one_row(self):
        first = SiteSetting.load()
        first.site_name = "بوتیک تست"
        first.save()
        self.assertEqual(SiteSetting.objects.count(), 1)
        self.assertEqual(SiteSetting.load().site_name, "بوتیک تست")

    def test_map_url_built_from_coordinates(self):
        site = SiteSetting.load()
        site.latitude, site.longitude = 35.7446, 51.4158
        site.save()
        self.assertIn("marker=35.7446", site.map_url)

    def test_whatsapp_link_normalized(self):
        site = SiteSetting.load()
        site.whatsapp = "989121234567"
        self.assertEqual(site.whatsapp_link, "https://wa.me/989121234567")


class PublicPageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_contact_page_renders(self):
        self.assertEqual(self.client.get(reverse("core:contact")).status_code, 200)

    def test_home_lists_active_banners_only(self):
        Banner.objects.create(title="بنر فعال", image="banners/a.jpg", is_active=True)
        Banner.objects.create(title="بنر غیرفعال", image="banners/b.jpg", is_active=False)
        response = self.client.get(reverse("core:home"))
        titles = [banner.title for banner in response.context["banners"]]
        self.assertIn("بنر فعال", titles)
        self.assertNotIn("بنر غیرفعال", titles)
