"""تست‌های تاریخ شمسی، فیلترهای قالب و صفحه‌های عمومی سایت."""
from __future__ import annotations

import datetime as dt

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

import io

from blog.models import Article
from core.jalali import (
    format_jalali,
    gregorian_to_jalali,
    is_jalali_leap,
    jalali_month_length,
    jalali_to_gregorian,
    jalali_weekday,
    parse_jalali,
    to_latin_digits,
    to_persian_digits,
)
from core.models import ShopLocation, SiteSettings, SocialLink
from gallery.models import PortfolioImage, PortfolioItem
from services.models import Service

User = get_user_model()


def make_test_image(name: str = "sample.jpg"):
    """عکس کوچک واقعی برای تست‌های نمایش گالری."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), (10, 120, 200)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class JalaliConversionTests(TestCase):
    def test_known_dates(self):
        cases = [
            ((2026, 9, 22), (1405, 6, 31)),
            ((2026, 3, 21), (1405, 1, 1)),
            ((2024, 3, 20), (1403, 1, 1)),
            ((1979, 2, 11), (1357, 11, 22)),
        ]
        for gregorian, jalali in cases:
            self.assertEqual(gregorian_to_jalali(*gregorian), jalali)
            self.assertEqual(jalali_to_gregorian(*jalali), gregorian)

    def test_roundtrip_over_thirty_years(self):
        day = dt.date(2000, 1, 1)
        while day < dt.date(2030, 1, 1):
            jy, jm, jd = gregorian_to_jalali(day.year, day.month, day.day)
            self.assertEqual(jalali_to_gregorian(jy, jm, jd), (day.year, day.month, day.day))
            self.assertLessEqual(jd, jalali_month_length(jy, jm))
            day += dt.timedelta(days=1)

    def test_leap_year_esfand_has_thirty_days(self):
        self.assertTrue(is_jalali_leap(1403))
        self.assertEqual(jalali_month_length(1403, 12), 30)
        self.assertEqual(jalali_month_length(1404, 12), 29)

    def test_weekday_saturday_is_zero(self):
        saturday = dt.date(2026, 9, 26)
        self.assertEqual(jalali_weekday(saturday), 0)

    def test_format_uses_persian_digits_and_month_names(self):
        self.assertEqual(format_jalali(dt.date(2026, 9, 22), "%d %B %Y"), "۳۱ شهریور ۱۴۰۵")
        self.assertEqual(format_jalali(dt.date(2026, 9, 26), "%A"), "شنبه")

    def test_parse_accepts_persian_digits_and_separators(self):
        self.assertEqual(parse_jalali("۱۴۰۵/۰۶/۳۱"), dt.date(2026, 9, 22))
        self.assertEqual(parse_jalali("1405-06-31"), dt.date(2026, 9, 22))

    def test_parse_rejects_invalid_dates(self):
        for invalid in ["1405/13/01", "1405/12/31", "hello", "1405/01"]:
            with self.assertRaises(ValueError):
                parse_jalali(invalid)

    def test_digit_helpers(self):
        self.assertEqual(to_persian_digits("1405"), "۱۴۰۵")
        self.assertEqual(to_latin_digits("۱۴۰۵"), "1405")
        self.assertEqual(to_latin_digits("٠٩١٢"), "0912")


class TemplateFilterTests(TestCase):
    def render(self, template: str, **context) -> str:
        return Template(template).render(Context(context)).strip()

    def test_jalali_filter(self):
        self.assertEqual(self.render("{{ value|jalali }}", value=dt.date(2026, 9, 22)), "۳۱ شهریور ۱۴۰۵")

    def test_toman_filter_adds_separators(self):
        self.assertEqual(self.render("{{ value|toman }}", value=1500000), "۱٬۵۰۰٬۰۰۰")

    def test_toman_label_handles_empty(self):
        self.assertEqual(self.render("{{ value|toman_label }}", value=None), "—")

    def test_phone_display_groups_digits(self):
        self.assertEqual(self.render("{{ value|phone_display }}", value="09121234567"), "۰۹۱۲ ۱۲۳ ۴۵۶۷")

    def test_attr_filter_reads_attributes_and_booleans(self):
        service = Service(title="پولیش", is_active=True)
        self.assertEqual(self.render("{{ item|attr:'title' }}", item=service), "پولیش")
        self.assertEqual(self.render("{{ item|attr:'is_active' }}", item=service), "بله")


class SocialLinkTests(TestCase):
    def test_urls_are_built_per_platform(self):
        cases = [
            ("telegram", "shop", "https://t.me/shop"),
            ("telegram", "@shop", "https://t.me/shop"),
            ("instagram", "shop", "https://instagram.com/shop"),
            ("twitter", "shop", "https://twitter.com/shop"),
            ("whatsapp", "09121234567", "https://wa.me/989121234567"),
            ("phone", "+989121234567", "tel:09121234567"),
            ("email", "a@b.com", "mailto:a@b.com"),
            ("website", "https://example.com", "https://example.com"),
        ]
        for platform, value, expected in cases:
            self.assertEqual(SocialLink(platform=platform, value=value).url, expected, platform)

    def test_whatsapp_requires_valid_phone(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            SocialLink(platform="whatsapp", value="سلام").clean()


class ShopLocationTests(TestCase):
    def test_map_url_is_built_from_coordinates(self):
        location = ShopLocation(
            settings=SiteSettings.load(), title="شعبه", address="تهران",
            latitude=35.7009, longitude=51.3707, map_zoom=16,
        )
        self.assertIn("openstreetmap.org", location.osm_embed_url)
        self.assertIn("marker=35.700900,51.370700", location.osm_embed_url)
        self.assertIn("google.com/maps", location.directions_url)

    def test_custom_map_link_wins(self):
        location = ShopLocation(settings=SiteSettings.load(), address="تهران", map_link="https://neshan.org/x")
        self.assertEqual(location.directions_url, "https://neshan.org/x")

    def test_missing_coordinates_give_empty_urls(self):
        location = ShopLocation(settings=SiteSettings.load(), address="تهران")
        self.assertEqual(location.osm_embed_url, "")
        self.assertEqual(location.directions_url, "")


class PublicPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = SiteSettings.load()
        ShopLocation.objects.create(
            settings=site, title="شعبه اصلی", address="تهران، خیابان آزادی",
            latitude=35.7009, longitude=51.3707,
        )
        SocialLink.objects.create(platform="telegram", value="shop", show_in_header=True)
        cls.service = Service.objects.create(title="صافکاری بدون رنگ", short_description="تست", is_featured=True)
        cls.item = PortfolioItem.objects.create(title="بازسازی گلگیر", car_name="۲۰۶")
        PortfolioImage.objects.create(item=cls.item, kind=PortfolioImage.Kind.BEFORE, image=make_test_image())
        cls.article = Article.objects.create(title="راهنمای صافکاری", content="متن آزمایشی مقاله.")

    def test_all_public_pages_render(self):
        pages = [
            reverse("core:home"),
            reverse("core:about"),
            reverse("core:contact"),
            reverse("services:list"),
            self.service.get_absolute_url(),
            reverse("gallery:list"),
            self.item.get_absolute_url(),
            reverse("blog:list"),
            self.article.get_absolute_url(),
            reverse("appointments:track"),
            reverse("accounts:login"),
            reverse("accounts:staff_login"),
        ]
        for page in pages:
            with self.subTest(page=page):
                self.assertEqual(self.client.get(page).status_code, 200)

    def test_contact_form_saves_message(self):
        from core.models import ContactMessage

        response = self.client.post(
            reverse("core:contact"),
            {"name": "علی", "phone": "۰۹۱۲۱۲۳۴۵۶۷", "subject": "سوال", "message": "سلام"},
        )
        self.assertRedirects(response, reverse("core:contact"))
        message = ContactMessage.objects.get()
        self.assertEqual(message.phone, "09121234567")

    def test_article_view_counter_increases(self):
        self.client.get(self.article.get_absolute_url())
        self.article.refresh_from_db()
        self.assertEqual(self.article.views_count, 1)

    def test_unicode_slugs_are_generated(self):
        self.assertEqual(self.service.slug, "صافکاری-بدون-رنگ")
        self.assertEqual(self.article.slug, "راهنمای-صافکاری")

    def test_404_page_uses_site_template(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
