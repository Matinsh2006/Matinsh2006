from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Banner, SiteSettings, StoreLocation
from .templatetags.shop_tags import jdate, toman
from .utils import fa_digits, normalize_link, tel_link, whatsapp_link


class UtilsTests(TestCase):
    def test_digits_and_prices(self):
        self.assertEqual(fa_digits("09121234567"), "۰۹۱۲۱۲۳۴۵۶۷")
        self.assertEqual(toman(12500000), "۱۲٬۵۰۰٬۰۰۰")

    def test_social_links(self):
        self.assertEqual(normalize_link("@myshop", "https://t.me/{}"), "https://t.me/myshop")
        self.assertEqual(normalize_link("my.shop", "https://instagram.com/{}"), "https://instagram.com/my.shop")
        self.assertEqual(normalize_link("t.me/myshop", "https://t.me/{}"), "https://t.me/myshop")
        self.assertEqual(normalize_link("https://x.com/a", "https://x.com/{}"), "https://x.com/a")
        self.assertEqual(whatsapp_link("۰۹۱۲۱۲۳۴۵۶۷"), "https://wa.me/989121234567")
        self.assertEqual(tel_link("021-8877 6655"), "tel:02188776655")

    def test_jalali_date(self):
        import datetime

        self.assertEqual(jdate(datetime.date(2026, 9, 25)), "۳ مهر ۱۴۰۵")
        self.assertEqual(jdate(datetime.date(2026, 3, 21), "short"), "۱۴۰۵/۰۱/۰۱")


class SiteSettingsTests(TestCase):
    def test_singleton(self):
        first = SiteSettings.load()
        first.site_name = "زمان"
        first.save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.load().site_name, "زمان")
        first.delete()
        self.assertEqual(SiteSettings.objects.count(), 1)


class LayoutTests(TestCase):
    def setUp(self):
        settings_obj = SiteSettings.load()
        settings_obj.telegram = "saniyeh"
        settings_obj.instagram = "saniyeh.gallery"
        settings_obj.whatsapp = "09123456789"
        settings_obj.twitter = "saniyeh"
        settings_obj.phone = "021-88776655"
        settings_obj.enamad_code = '<a referrerpolicy="origin" target="_blank" href="https://trustseal.enamad.ir/?id=1"><img src="https://trustseal.enamad.ir/logo.aspx?id=1" alt="" id="enamad-seal"></a>'
        settings_obj.save()

    def test_footer_socials_phone_and_enamad(self):
        response = self.client.get(reverse("core:home"))
        for url in ["https://t.me/saniyeh", "https://instagram.com/saniyeh.gallery", "https://wa.me/989123456789", "https://x.com/saniyeh", "tel:021-88776655".replace("-", "")]:
            self.assertContains(response, url)
        self.assertContains(response, 'id="enamad-seal"', html=False)

    def test_header_banner_and_schedule(self):
        Banner.objects.create(title="تخفیف ویژه یلدا", placement=Banner.Placement.HEADER, link="/shop/")
        Banner.objects.create(title="بنر غیرفعال", placement=Banner.Placement.HEADER, is_active=False)
        response = self.client.get(reverse("catalog:shop"))
        self.assertContains(response, "data-header-banner")
        self.assertContains(response, "تخفیف ویژه یلدا")
        self.assertNotContains(response, "بنر غیرفعال")

    @override_settings(DEBUG=True)
    def test_enamad_placeholder_for_staff(self):
        settings_obj = SiteSettings.load()
        settings_obj.enamad_code = ""
        settings_obj.save()
        admin = get_user_model().objects.create_superuser(phone="09120000000", password="x-pass-12345")
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse("core:home")), "جایگاه نماد اعتماد الکترونیکی")

    def test_store_location_links(self):
        store = StoreLocation.objects.create(name="شعبه مرکزی", address="تهران", latitude="35.757450", longitude="51.409680")
        self.assertIn("35.757450,51.409680", store.directions_url)
        response = self.client.get(reverse("core:contact"))
        self.assertContains(response, "data-map")
        self.assertContains(response, "شعبه مرکزی")
        self.assertContains(response, "balad.ir/location?latitude=35.757450")

    def test_contact_form(self):
        response = self.client.post(reverse("core:contact"), {"name": "مریم", "phone": "09121234567", "message": "سلام"})
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse("core:contact"), {"name": "bot", "phone": "09121234567", "message": "spam", "website": "x"})
        self.assertEqual(response.status_code, 200)

    def test_robots_and_sitemap(self):
        self.assertContains(self.client.get("/robots.txt"), "Sitemap:")
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
