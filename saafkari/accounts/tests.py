"""تست‌های ورود با کد پیامکی و تغییر شماره موبایل."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import OTPCode, OTPPurpose
from accounts.sms import MemorySMSBackend
from core.validators import mask_phone, normalize_phone

User = get_user_model()


@override_settings(SMS_BACKEND="accounts.sms.MemorySMSBackend")
class PhoneNormalizationTests(TestCase):
    def test_various_formats_normalize_to_same_number(self):
        for raw in ["09121234567", "+989121234567", "00989121234567", "9121234567",
                    "0912-123-4567", "۰۹۱۲۱۲۳۴۵۶۷"]:
            self.assertEqual(normalize_phone(raw), "09121234567", raw)

    def test_mask_hides_middle_digits(self):
        self.assertEqual(mask_phone("09121234567"), "0912***4567")


@override_settings(SMS_BACKEND="accounts.sms.MemorySMSBackend")
class OTPLoginTests(TestCase):
    def setUp(self):
        MemorySMSBackend.clear()

    def _sent_code(self) -> str:
        """آخرین کدی که به صندوق پیامک آزمایشی رفته است."""
        message = MemorySMSBackend.outbox[-1]["message"]
        return "".join(char for char in message if char.isdigit())

    def test_login_creates_user_and_authenticates(self):
        response = self.client.post(reverse("accounts:login"), {"phone": "09121112233"})
        self.assertRedirects(response, reverse("accounts:login_verify"))
        self.assertEqual(len(MemorySMSBackend.outbox), 1)

        response = self.client.post(reverse("accounts:login_verify"), {"code": self._sent_code()})
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(phone="09121112233")
        self.assertTrue(user.is_phone_verified)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_wrong_code_does_not_authenticate(self):
        self.client.post(reverse("accounts:login"), {"phone": "09121112233"})
        response = self.client.post(reverse("accounts:login_verify"), {"code": "00000"}, follow=True)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "درست نیست")

    def test_expired_code_is_rejected(self):
        self.client.post(reverse("accounts:login"), {"phone": "09121112233"})
        otp = OTPCode.objects.latest("created_at")
        code = self._sent_code()
        OTPCode.objects.filter(pk=otp.pk).update(expires_at=otp.created_at)
        self.client.post(reverse("accounts:login_verify"), {"code": code})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_invalid_phone_is_rejected(self):
        response = self.client.post(reverse("accounts:login"), {"phone": "12345"})
        self.assertContains(response, "معتبر نیست")
        self.assertEqual(len(MemorySMSBackend.outbox), 0)

    @override_settings(OTP_HOURLY_LIMIT=2, OTP_RESEND_COOLDOWN=0)
    def test_hourly_limit_blocks_further_codes(self):
        for _ in range(2):
            self.client.post(reverse("accounts:login"), {"phone": "09121112233"})
        response = self.client.post(reverse("accounts:login"), {"phone": "09121112233"}, follow=True)
        self.assertContains(response, "بیش از حد مجاز")
        self.assertEqual(len(MemorySMSBackend.outbox), 2)

    def test_code_is_stored_hashed(self):
        self.client.post(reverse("accounts:login"), {"phone": "09121112233"})
        otp = OTPCode.objects.latest("created_at")
        self.assertNotIn(self._sent_code(), otp.code_hash)


@override_settings(SMS_BACKEND="accounts.sms.MemorySMSBackend")
class PhoneChangeTests(TestCase):
    def setUp(self):
        MemorySMSBackend.clear()
        self.user = User.objects.create_user("09121112233", full_name="مشتری")
        self.client.force_login(self.user, backend="accounts.backends.PhoneBackend")

    def _sent_code(self) -> str:
        message = MemorySMSBackend.outbox[-1]["message"]
        return "".join(char for char in message if char.isdigit())

    def test_phone_changes_after_sms_verification(self):
        response = self.client.post(reverse("accounts:phone_change"), {"new_phone": "09309998877"})
        self.assertRedirects(response, reverse("accounts:phone_change_verify"))
        # کد باید به شماره‌ی جدید ارسال شود، نه شماره‌ی قبلی
        self.assertEqual(MemorySMSBackend.outbox[-1]["phone"], "09309998877")

        self.client.post(reverse("accounts:phone_change_verify"), {"code": self._sent_code()})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09309998877")
        self.assertIsNotNone(self.user.phone_changed_at)

    def test_phone_does_not_change_without_verification(self):
        self.client.post(reverse("accounts:phone_change"), {"new_phone": "09309998877"})
        self.client.post(reverse("accounts:phone_change_verify"), {"code": "11111"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09121112233")

    def test_duplicate_phone_is_rejected(self):
        User.objects.create_user("09309998877")
        response = self.client.post(reverse("accounts:phone_change"), {"new_phone": "09309998877"})
        self.assertContains(response, "قبلاً در سایت ثبت شده")
        self.assertEqual(len(MemorySMSBackend.outbox), 0)

    def test_same_phone_is_rejected(self):
        response = self.client.post(reverse("accounts:phone_change"), {"new_phone": "09121112233"})
        self.assertContains(response, "یکسان است")

    def test_otp_purpose_is_isolated(self):
        """کد «تغییر شماره» نباید برای ورود کار کند."""
        self.client.post(reverse("accounts:phone_change"), {"new_phone": "09309998877"})
        otp = OTPCode.objects.latest("created_at")
        self.assertEqual(otp.purpose, OTPPurpose.PHONE_CHANGE)
