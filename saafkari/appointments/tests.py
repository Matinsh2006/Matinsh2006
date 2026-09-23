"""تست‌های رزرو نوبت با تاریخ شمسی و ارسال عکس."""
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
from core.jalali import jalali_str, jalali_weekday
from services.models import Service

User = get_user_model()


def make_upload(name: str = "car.jpg") -> SimpleUploadedFile:
    """ساخت یک عکس واقعی کوچک برای تست آپلود."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 30, 30)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class SchedulingTests(TestCase):
    def setUp(self):
        WorkingHour.ensure_defaults()
        self.service = Service.objects.create(title="صافکاری", duration_minutes=60)

    def _next_open_day(self, offset: int = 1) -> dt.date:
        day = timezone.localdate() + dt.timedelta(days=offset)
        while working_hour_for(day) is None:
            day += dt.timedelta(days=1)
        return day

    def test_friday_is_closed_by_default(self):
        day = timezone.localdate()
        while jalali_weekday(day) != 6:  # جمعه
            day += dt.timedelta(days=1)
        self.assertIsNone(working_hour_for(day))
        self.assertEqual(available_slots(day, self.service), [])

    def test_holiday_removes_all_slots(self):
        day = self._next_open_day()
        self.assertTrue(available_slots(day, self.service))
        Holiday.objects.create(date=day, title="تعطیل رسمی")
        self.assertEqual(available_slots(day, self.service), [])

    def test_booked_slot_is_removed(self):
        day = self._next_open_day()
        user = User.objects.create_user("09121112233")
        slots = available_slots(day, self.service)
        Appointment.objects.create(
            user=user, service=self.service, date=day, start_time=slots[0], description="تست"
        )
        self.assertNotIn(slots[0], available_slots(day, self.service))

    def test_long_service_blocks_overlapping_slots(self):
        """خدمت ۱۸۰ دقیقه‌ای باید سه بازه‌ی یک‌ساعته را اشغال کند."""
        day = self._next_open_day()
        long_service = Service.objects.create(title="نقاشی", duration_minutes=180)
        user = User.objects.create_user("09121112244")
        before = available_slots(day, self.service)
        Appointment.objects.create(
            user=user, service=long_service, date=day, start_time=before[0], description="تست"
        )
        after = available_slots(day, self.service)
        self.assertEqual(len(before) - len(after), 3)

    def test_capacity_allows_parallel_bookings(self):
        day = self._next_open_day()
        WorkingHour.objects.filter(weekday=jalali_weekday(day)).update(capacity=2)
        user = User.objects.create_user("09121112255")
        slot = available_slots(day, self.service)[0]
        Appointment.objects.create(user=user, service=self.service, date=day, start_time=slot, description="۱")
        self.assertIn(slot, available_slots(day, self.service))
        Appointment.objects.create(user=user, service=self.service, date=day, start_time=slot, description="۲")
        self.assertNotIn(slot, available_slots(day, self.service))

    def test_cancelled_appointment_frees_slot(self):
        day = self._next_open_day()
        user = User.objects.create_user("09121112266")
        slot = available_slots(day, self.service)[0]
        appointment = Appointment.objects.create(
            user=user, service=self.service, date=day, start_time=slot, description="تست"
        )
        self.assertNotIn(slot, available_slots(day, self.service))
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        self.assertIn(slot, available_slots(day, self.service))


@override_settings(SMS_BACKEND="accounts.sms.MemorySMSBackend")
class BookingViewTests(TestCase):
    def setUp(self):
        WorkingHour.ensure_defaults()
        self.service = Service.objects.create(title="صافکاری بدون رنگ", duration_minutes=60, deposit_amount=150000)
        self.user = User.objects.create_user("09121112233", full_name="مشتری تست")
        self.client.force_login(self.user, backend="accounts.backends.PhoneBackend")
        self.day = timezone.localdate() + dt.timedelta(days=1)
        while working_hour_for(self.day) is None:
            self.day += dt.timedelta(days=1)
        self.slot = available_slots(self.day, self.service)[0]

    def _payload(self, **overrides):
        data = {
            "service": self.service.pk,
            "date": jalali_str(self.day),
            "start_time": self.slot.strftime("%H:%M"),
            "car_model": "پژو ۲۰۶",
            "plate_number": "۱۲ ب ۳۴۵ ایران ۲۲",
            "contact_phone": "09121112233",
            "description": "گلگیر جلو سمت راست فرورفتگی دارد.",
        }
        data.update(overrides)
        return data

    def test_booking_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("appointments:booking"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_booking_creates_appointment_with_photos(self):
        payload = self._payload()
        payload["photo_front"] = make_upload("front.jpg")
        payload["photo_closeup"] = make_upload("closeup.jpg")
        response = self.client.post(reverse("appointments:booking"), payload)
        self.assertEqual(response.status_code, 302)

        appointment = Appointment.objects.get(user=self.user)
        self.assertEqual(appointment.date, self.day)
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertEqual(appointment.deposit_amount, 150000)
        self.assertEqual(appointment.photos.count(), 2)
        self.assertEqual(
            sorted(appointment.photos.values_list("angle", flat=True)), ["closeup", "front"]
        )
        self.assertTrue(appointment.tracking_code)
        # ساعت پایان باید از روی مدت خدمت محاسبه شود
        self.assertEqual(appointment.end_time, (dt.datetime.combine(self.day, self.slot) + dt.timedelta(minutes=60)).time())

    def test_booking_rejects_taken_slot(self):
        other = User.objects.create_user("09129998877")
        Appointment.objects.create(
            user=other, service=self.service, date=self.day, start_time=self.slot, description="قبلی"
        )
        response = self.client.post(reverse("appointments:booking"), self._payload())
        self.assertContains(response, "خالی نیست")
        self.assertFalse(Appointment.objects.filter(user=self.user).exists())

    def test_booking_rejects_past_date(self):
        past = jalali_str(timezone.localdate() - dt.timedelta(days=3))
        response = self.client.post(reverse("appointments:booking"), self._payload(date=past))
        self.assertContains(response, "گذشته")
        self.assertFalse(Appointment.objects.filter(user=self.user).exists())

    def test_booking_rejects_closed_day(self):
        Holiday.objects.create(date=self.day, title="تعطیل")
        response = self.client.post(reverse("appointments:booking"), self._payload())
        self.assertContains(response, "تعطیل")
        self.assertFalse(Appointment.objects.filter(user=self.user).exists())

    def test_booking_rejects_non_image_upload(self):
        payload = self._payload()
        payload["photo_front"] = SimpleUploadedFile("bad.txt", b"not an image", content_type="text/plain")
        response = self.client.post(reverse("appointments:booking"), payload, follow=True)
        self.assertContains(response, "عکس معتبری نیست")
        self.assertFalse(Appointment.objects.filter(user=self.user).exists())

    @override_settings(APPOINTMENT_MAX_PHOTO_SIZE_MB=0)
    def test_oversized_photo_is_rejected(self):
        payload = self._payload()
        payload["photo_front"] = make_upload()
        response = self.client.post(reverse("appointments:booking"), payload, follow=True)
        self.assertContains(response, "مگابایت")
        self.assertFalse(Appointment.objects.filter(user=self.user).exists())

    def test_slots_api_returns_available_times(self):
        response = self.client.get(
            reverse("appointments:slots"), {"date": jalali_str(self.day), "service": self.service.pk}
        )
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn(self.slot.strftime("%H:%M"), data["slots"])
        self.assertEqual(data["duration"], 60)

    def test_slots_api_rejects_bad_date(self):
        response = self.client.get(reverse("appointments:slots"), {"date": "نامعتبر"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_customer_can_cancel_own_appointment(self):
        appointment = Appointment.objects.create(
            user=self.user, service=self.service, date=self.day, start_time=self.slot, description="تست"
        )
        self.client.post(reverse("appointments:cancel", args=[appointment.tracking_code]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)

    def test_other_users_cannot_open_appointment(self):
        appointment = Appointment.objects.create(
            user=self.user, service=self.service, date=self.day, start_time=self.slot, description="تست"
        )
        self.client.logout()
        intruder = User.objects.create_user("09355556677")
        self.client.force_login(intruder, backend="accounts.backends.PhoneBackend")
        response = self.client.get(appointment.get_absolute_url())
        self.assertRedirects(response, reverse("appointments:mine"))

    def test_tracking_page_finds_appointment(self):
        appointment = Appointment.objects.create(
            user=self.user, service=self.service, date=self.day, start_time=self.slot, description="تست"
        )
        response = self.client.get(reverse("appointments:track"), {"code": appointment.tracking_code})
        self.assertContains(response, self.service.title)
