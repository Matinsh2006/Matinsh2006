import datetime
import json
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.core.models import Banner, Branch, Page, SiteSettings, SocialLink, validate_site_link
from apps.core.sanitizer import sanitize_html
from apps.core.templatetags.shop_tags import duration, jdate, price
from apps.core.testing import make_product
from apps.core.utils.jalali import format_jalali, gregorian_to_jalali
from apps.core.utils.text import (
    html_to_text,
    is_valid_mobile,
    mask_phone,
    normalize_persian,
    normalize_phone,
    phone_to_international,
    to_latin_digits,
    to_persian_digits,
)

TEMP_MEDIA = tempfile.mkdtemp()


def png_file(name="image.png", size=(20, 20)):
    buffer = BytesIO()
    Image.new("RGB", size, (200, 30, 90)).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class JalaliTests(TestCase):
    def test_known_dates(self):
        self.assertEqual(gregorian_to_jalali(2024, 3, 20), (1403, 1, 1))
        self.assertEqual(gregorian_to_jalali(2025, 3, 21), (1404, 1, 1))
        self.assertEqual(gregorian_to_jalali(2026, 9, 29), (1405, 7, 7))
        self.assertEqual(gregorian_to_jalali(2000, 1, 1), (1378, 10, 11))
        self.assertEqual(gregorian_to_jalali(2023, 3, 20), (1401, 12, 29))

    def test_format(self):
        self.assertEqual(format_jalali(datetime.date(2026, 9, 29)), "7 مهر 1405")
        self.assertEqual(format_jalali(datetime.date(2026, 9, 29), "%Y/%m/%d %A"), "1405/07/07 سه‌شنبه")
        self.assertEqual(format_jalali(None), "")

    def test_aware_datetime_uses_tehran_time(self):
        value = datetime.datetime(2026, 9, 28, 21, 0, tzinfo=datetime.timezone.utc)  # 00:30 in Tehran
        self.assertEqual(format_jalali(value, "%e %B %H:%M"), "7 مهر 00:30")


class TextUtilsTests(TestCase):
    def test_normalize_phone(self):
        for raw in ["09121234567", "+98 912 123 4567", "00989121234567", "989121234567", "9121234567", "۰۹۱۲۱۲۳۴۵۶۷", "0912-123-4567"]:
            self.assertEqual(normalize_phone(raw), "09121234567", raw)
        self.assertTrue(is_valid_mobile("09121234567"))
        self.assertFalse(is_valid_mobile("0212345678"))
        self.assertFalse(is_valid_mobile(normalize_phone("12345")))

    def test_digits_and_letters(self):
        self.assertEqual(to_persian_digits("SPF50"), "SPF۵۰")
        self.assertEqual(to_latin_digits("۱۲۳٤٥"), "12345")
        self.assertEqual(normalize_persian("كيك ۱۰"), "کیک 10")

    def test_phone_helpers(self):
        self.assertEqual(phone_to_international("09121234567"), "989121234567")
        self.assertEqual(phone_to_international("+98 912 123 4567"), "989121234567")
        self.assertEqual(mask_phone("09121234567"), "0912***4567")

    def test_html_to_text_keeps_words_apart(self):
        self.assertEqual(html_to_text("<p>سلام</p><p>دنیا &amp; ما</p>"), "سلام دنیا & ما")


class TemplateFilterTests(TestCase):
    def test_price(self):
        self.assertEqual(price(1250000), "۱٬۲۵۰٬۰۰۰")
        self.assertEqual(price("abc"), "abc")

    def test_jdate_and_duration(self):
        self.assertEqual(jdate(datetime.date(2026, 9, 29)), "۷ مهر ۱۴۰۵")
        self.assertEqual(duration(125), "۲:۰۵")


class SanitizerTests(TestCase):
    def test_dangerous_markup_is_removed(self):
        html = '<p onclick="x()">متن <a href="javascript:alert(1)">لینک</a></p><script>alert(1)</script><img src="/media/a.jpg" onerror="x">'
        cleaned = sanitize_html(html)
        self.assertNotIn("script", cleaned)
        self.assertNotIn("onclick", cleaned)
        self.assertNotIn("onerror", cleaned)
        self.assertNotIn("javascript:", cleaned)
        self.assertIn('<img src="/media/a.jpg">', cleaned)

    def test_rich_text_field_sanitizes_on_save(self):
        page = Page.objects.create(title="درباره ما", body="<h2>عنوان</h2><script>bad()</script><p>متن</p>")
        page.refresh_from_db()
        self.assertEqual(page.body, "<h2>عنوان</h2><p>متن</p>")

    def test_persian_slug_is_generated_and_resolvable(self):
        page = Page.objects.create(title="قوانین و مقررات")
        self.assertEqual(page.slug, "قوانین-و-مقررات")
        response = self.client.get(page.get_absolute_url())
        self.assertContains(response, "قوانین و مقررات")
        second = Page.objects.create(title="قوانین و مقررات")
        self.assertEqual(second.slug, "قوانین-و-مقررات-2")


class SocialLinkTests(TestCase):
    def link(self, platform, value):
        return SocialLink(platform=platform, value=value)

    def test_urls(self):
        P = SocialLink.Platform
        self.assertEqual(self.link(P.INSTAGRAM, "@my.shop").url, "https://instagram.com/my.shop")
        self.assertEqual(self.link(P.TELEGRAM, "my_shop").url, "https://t.me/my_shop")
        self.assertEqual(self.link(P.WHATSAPP, "0912 123 4567").url, "https://wa.me/989121234567")
        self.assertEqual(self.link(P.TWITTER, "myshop").url, "https://x.com/myshop")
        self.assertEqual(self.link(P.PHONE, "۰۲۱-۸۸۷۷۶۶۵۵").url, "tel:02188776655")
        self.assertEqual(self.link(P.EMAIL, "a@b.ir").url, "mailto:a@b.ir")
        self.assertEqual(self.link(P.INSTAGRAM, "https://instagram.com/x").url, "https://instagram.com/x")
        self.assertEqual(self.link(P.TWITTER, "myshop").icon, "x-logo")

    def test_validation(self):
        P = SocialLink.Platform
        with self.assertRaises(ValidationError):
            self.link(P.PHONE, "12").clean()
        with self.assertRaises(ValidationError):
            self.link(P.EMAIL, "not-an-email").clean()
        with self.assertRaises(ValidationError):
            self.link(P.INSTAGRAM, "bad handle!").clean()
        self.link(P.INSTAGRAM, "good.handle_1").clean()


class SiteSettingsAndBannerTests(TestCase):
    def test_singleton_and_shipping(self):
        site = SiteSettings.load()
        site.shipping_cost, site.free_shipping_threshold = 50000, 1000000
        site.save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.load().shipping_cost_for(999999), 50000)
        self.assertEqual(SiteSettings.load().shipping_cost_for(1000000), 0)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA)
    def test_live_banners_respect_schedule(self):
        now = timezone.now()
        Banner.objects.create(title="فعال", image=png_file())
        Banner.objects.create(title="غیرفعال", image=png_file(), is_active=False)
        Banner.objects.create(title="آینده", image=png_file(), start_at=now + datetime.timedelta(days=1))
        Banner.objects.create(title="تمام‌شده", image=png_file(), end_at=now - datetime.timedelta(days=1))
        self.assertEqual(list(Banner.objects.live().values_list("title", flat=True)), ["فعال"])

    def test_banner_link_validation(self):
        validate_site_link("/products/?discount=1")
        validate_site_link("https://example.com")
        with self.assertRaises(ValidationError):
            validate_site_link("javascript:alert(1)")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class CoreViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def test_home_page(self):
        for index in range(3):
            Banner.objects.create(title=f"بنر {index}", image=png_file(), order=index)
        make_product(name="کرم آبرسان", discount_price=80000)
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-slider")
        self.assertEqual(response.content.decode().count('class="slider__slide"'), 3)
        self.assertContains(response, "کرم آبرسان")

    def test_contact_page_contains_map_data(self):
        Branch.objects.create(name="شعبه یک", address="تهران", latitude="35.700000", longitude="51.400000")
        SocialLink.objects.create(platform=SocialLink.Platform.WHATSAPP, value="09121234567")
        response = self.client.get(reverse("core:contact"))
        self.assertContains(response, "https://wa.me/989121234567")
        data = json.loads(response.content.decode().split('id="map-data" type="application/json">')[1].split("</script>")[0])
        self.assertEqual(data[0]["lat"], 35.7)

    def test_robots_sitemap_and_favicon(self):
        make_product()
        self.assertContains(self.client.get("/robots.txt"), "Sitemap:")
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        self.assertEqual(self.client.get("/favicon.ico").status_code, 301)

    def test_editor_upload_requires_staff(self):
        url = reverse("core:editor_upload")
        self.assertEqual(self.client.post(url, {"image": png_file()}).status_code, 403)
        staff = get_user_model().objects.create_user(phone="09120000009", password="x-Strong-pass-1", is_staff=True)
        self.client.force_login(staff)
        response = self.client.post(url, {"image": png_file()})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["url"].startswith("/media/editor/"))
        bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        self.assertEqual(self.client.post(url, {"image": bad}).status_code, 400)
