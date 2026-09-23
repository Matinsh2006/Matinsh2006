"""تست‌های پنل کارفرما: دسترسی، ساخت محتوا و مدیریت نوبت."""
from __future__ import annotations

import datetime as dt
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment, Holiday, WorkingHour
from appointments.scheduling import available_slots, working_hour_for
from blog.models import Article
from core.jalali import jalali_str
from core.models import ShopLocation, SiteSettings, SocialLink
from gallery.models import Banner, PortfolioImage, PortfolioItem
from services.models import Service

User = get_user_model()


def image_upload(name: str = "photo.jpg") -> SimpleUploadedFile:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (30, 20), (20, 120, 200)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user("09121112233")
        self.owner = User.objects.create_user("09129998877", is_staff=True)

    def test_anonymous_is_sent_to_staff_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:staff_login"), response.url)

    def test_customer_cannot_open_dashboard(self):
        self.client.force_login(self.customer, backend="accounts.backends.PhoneBackend")
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(response, reverse("core:home"))

    def test_customer_cannot_create_service(self):
        self.client.force_login(self.customer, backend="accounts.backends.PhoneBackend")
        response = self.client.post(
            reverse("dashboard:service_create"), {"title": "نفوذ", "duration_minutes": 30, "order": 0, "base_price": 0}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Service.objects.filter(title="نفوذ").exists())

    def test_owner_can_open_dashboard(self):
        self.client.force_login(self.owner, backend="accounts.backends.PhoneBackend")
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)

    def test_staff_login_with_password(self):
        self.owner.set_password("StrongPass!2026")
        self.owner.save()
        response = self.client.post(
            reverse("accounts:staff_login"), {"phone": "۰۹۱۲۹۹۹۸۸۷۷", "password": "StrongPass!2026"}
        )
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_customer_password_login_is_refused_for_panel(self):
        self.customer.set_password("StrongPass!2026")
        self.customer.save()
        response = self.client.post(
            reverse("accounts:staff_login"), {"phone": "09121112233", "password": "StrongPass!2026"}, follow=True
        )
        self.assertContains(response, "دسترسی پنل مدیریت ندارد")


@override_settings(SMS_BACKEND="accounts.sms.MemorySMSBackend")
class DashboardContentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("09129998877", is_staff=True, full_name="کارفرما")
        self.client.force_login(self.owner, backend="accounts.backends.PhoneBackend")
        WorkingHour.ensure_defaults()

    def test_all_panel_pages_render(self):
        pages = [
            "dashboard:home", "dashboard:appointments", "dashboard:services", "dashboard:service_categories",
            "dashboard:banners", "dashboard:portfolio", "dashboard:articles", "dashboard:article_categories",
            "dashboard:socials", "dashboard:locations", "dashboard:settings", "dashboard:working_hours",
            "dashboard:payments", "dashboard:customers", "dashboard:messages",
            "dashboard:service_create", "dashboard:banner_create", "dashboard:portfolio_create",
            "dashboard:article_create", "dashboard:social_create", "dashboard:location_create",
        ]
        for name in pages:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_owner_adds_new_service(self):
        response = self.client.post(reverse("dashboard:service_create"), {
            "title": "سرامیک بدنه", "short_description": "محافظت از رنگ", "description": "توضیح کامل",
            "base_price": 3500000, "price_note": "", "duration_minutes": 180, "deposit_amount": 500000,
            "is_active": "on", "is_featured": "on", "order": 1,
        })
        self.assertRedirects(response, reverse("dashboard:services"))
        service = Service.objects.get(title="سرامیک بدنه")
        self.assertEqual(service.deposit_for_booking(), 500000)
        self.assertTrue(service.slug)
        # خدمت تازه باید بلافاصله در سایت دیده شود
        self.assertContains(self.client.get(reverse("services:list")), "سرامیک بدنه")

    def test_owner_adds_portfolio_with_before_and_after_images(self):
        response = self.client.post(reverse("dashboard:portfolio_create"), {
            "title": "بازسازی درب عقب", "car_name": "پژو پارس", "description": "شرح کار",
            "duration_label": "۲ روز", "completed_at": jalali_str(timezone.localdate()),
            "order": 0, "is_active": "on", "is_featured": "on",
            "images-TOTAL_FORMS": "4", "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0", "images-MAX_NUM_FORMS": "1000",
            "images-0-image": image_upload("before1.jpg"), "images-0-kind": "before", "images-0-caption": "قبل ۱", "images-0-order": 0,
            "images-1-image": image_upload("before2.jpg"), "images-1-kind": "before", "images-1-caption": "قبل ۲", "images-1-order": 1,
            "images-2-image": image_upload("after1.jpg"), "images-2-kind": "after", "images-2-caption": "بعد ۱", "images-2-order": 0,
            "images-3-image": image_upload("after2.jpg"), "images-3-kind": "after", "images-3-caption": "بعد ۲", "images-3-order": 1,
        })
        self.assertRedirects(response, reverse("dashboard:portfolio"))
        item = PortfolioItem.objects.get(title="بازسازی درب عقب")
        self.assertEqual(item.images.count(), 4)
        self.assertEqual(item.before_images.count(), 2)
        self.assertEqual(item.after_images.count(), 2)
        self.assertEqual(item.completed_at, timezone.localdate())

    def test_owner_adds_banner(self):
        response = self.client.post(reverse("dashboard:banner_create"), {
            "title": "تخفیف پاییزی", "subtitle": "۲۰ درصد تخفیف پولیش", "image": image_upload("banner.jpg"),
            "link_url": "", "button_text": "رزرو", "position": "hero", "order": 0, "is_active": "on",
        })
        self.assertRedirects(response, reverse("dashboard:banners"))
        self.assertTrue(Banner.objects.filter(title="تخفیف پاییزی").exists())
        self.assertContains(self.client.get(reverse("core:home")), "تخفیف پاییزی")

    def test_owner_writes_article(self):
        response = self.client.post(reverse("dashboard:article_create"), {
            "title": "نکات نگهداری رنگ خودرو", "summary": "خلاصه", "content": "پاراگراف اول.\n\nپاراگراف دوم.",
            "tags": "رنگ, نگهداری", "is_published": "on",
            "published_at": timezone.now().strftime("%Y-%m-%dT%H:%M"),
        })
        self.assertRedirects(response, reverse("dashboard:articles"))
        article = Article.objects.get(title="نکات نگهداری رنگ خودرو")
        self.assertEqual(article.author, self.owner)
        self.assertEqual(len(article.paragraphs), 2)
        self.assertContains(self.client.get(reverse("blog:list")), "نکات نگهداری رنگ خودرو")

    def test_owner_adds_social_link(self):
        self.client.post(reverse("dashboard:social_create"), {
            "platform": "instagram", "value": "my_shop", "label": "اینستاگرام ما", "order": 0, "is_active": "on",
        })
        link = SocialLink.objects.get(platform="instagram")
        self.assertEqual(link.url, "https://instagram.com/my_shop")
        self.assertContains(self.client.get(reverse("core:home")), "https://instagram.com/my_shop")

    def test_owner_adds_shop_location(self):
        self.client.post(reverse("dashboard:location_create"), {
            "title": "شعبه دو", "address": "تهران، میدان ولیعصر", "city": "تهران", "province": "تهران",
            "postal_code": "", "phone": "", "latitude": "35.7009", "longitude": "51.3707",
            "map_zoom": 16, "map_link": "", "is_main": "on", "is_active": "on",
        })
        location = ShopLocation.objects.get(title="شعبه دو")
        self.assertEqual(location.settings, SiteSettings.load())
        self.assertContains(self.client.get(reverse("core:contact")), "openstreetmap.org")

    def test_owner_updates_site_settings(self):
        self.client.post(reverse("dashboard:settings"), {
            "brand_name": "صافکاری نمونه", "tagline": "شعار تازه", "about": "درباره ما",
            "phone": "۰۹۱۲۱۱۱۲۲۳۳", "second_phone": "", "email": "", "working_hours": "۹ تا ۲۰",
            "deposit_amount": 300000, "online_payment_enabled": "on", "meta_description": "", "enamad_code": "",
        })
        site = SiteSettings.load()
        self.assertEqual(site.brand_name, "صافکاری نمونه")
        self.assertEqual(site.phone, "09121112233")  # شماره نرمال‌سازی می‌شود
        self.assertEqual(site.deposit_amount, 300000)

    def test_owner_adds_holiday_and_it_blocks_booking(self):
        day = timezone.localdate() + dt.timedelta(days=2)
        while working_hour_for(day) is None:
            day += dt.timedelta(days=1)
        service = Service.objects.create(title="صافکاری", duration_minutes=60)
        self.assertTrue(available_slots(day, service))

        self.client.post(reverse("dashboard:holiday_create"), {"date": jalali_str(day), "title": "تعطیل رسمی"})
        self.assertTrue(Holiday.objects.filter(date=day).exists())
        self.assertEqual(available_slots(day, service), [])

    def test_owner_changes_working_hours(self):
        hours = list(WorkingHour.objects.order_by("weekday"))
        payload = {
            "form-TOTAL_FORMS": str(len(hours)), "form-INITIAL_FORMS": str(len(hours)),
            "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000",
        }
        for index, hour in enumerate(hours):
            payload.update({
                f"form-{index}-id": hour.pk,
                f"form-{index}-weekday": hour.weekday,
                f"form-{index}-open_time": "08:00",
                f"form-{index}-close_time": "22:00",
                f"form-{index}-slot_minutes": 30,
                f"form-{index}-capacity": 2,
            })
            if hour.is_open:
                payload[f"form-{index}-is_open"] = "on"
        response = self.client.post(reverse("dashboard:working_hours"), payload)
        self.assertRedirects(response, reverse("dashboard:working_hours"))
        updated = WorkingHour.objects.first()
        self.assertEqual(updated.slot_minutes, 30)
        self.assertEqual(updated.capacity, 2)


@override_settings(SMS_BACKEND="accounts.sms.MemorySMSBackend")
class AppointmentManagementTests(TestCase):
    def setUp(self):
        WorkingHour.ensure_defaults()
        self.owner = User.objects.create_user("09129998877", is_staff=True)
        self.customer = User.objects.create_user("09121112233")
        self.service = Service.objects.create(title="صافکاری", duration_minutes=60)
        day = timezone.localdate() + dt.timedelta(days=1)
        while working_hour_for(day) is None:
            day += dt.timedelta(days=1)
        self.appointment = Appointment.objects.create(
            user=self.customer, service=self.service, date=day,
            start_time=available_slots(day, self.service)[0], description="تست",
        )
        self.client.force_login(self.owner, backend="accounts.backends.PhoneBackend")

    def test_owner_confirms_appointment_and_customer_is_notified(self):
        from accounts.sms import MemorySMSBackend

        MemorySMSBackend.clear()
        response = self.client.post(
            reverse("dashboard:appointment_manage", args=[self.appointment.tracking_code]),
            {"status": "confirmed", "estimated_price": 900000, "staff_note": "لطفاً ساعت ۹ حاضر باشید.",
             "deposit_amount": 200000},
        )
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(self.appointment.estimated_price, 900000)
        self.assertEqual(len(MemorySMSBackend.outbox), 1)
        self.assertIn(self.appointment.tracking_code, MemorySMSBackend.outbox[0]["message"])

    def test_appointment_list_filters_by_status(self):
        response = self.client.get(reverse("dashboard:appointments"), {"status": "pending"})
        self.assertContains(response, self.appointment.tracking_code)
        response = self.client.get(reverse("dashboard:appointments"), {"status": "done"})
        self.assertNotContains(response, self.appointment.tracking_code)

    def test_appointment_search_by_tracking_code(self):
        response = self.client.get(reverse("dashboard:appointments"), {"q": self.appointment.tracking_code})
        self.assertContains(response, self.service.title)

    def test_staff_can_open_any_appointment(self):
        response = self.client.get(self.appointment.get_absolute_url())
        self.assertEqual(response.status_code, 200)
