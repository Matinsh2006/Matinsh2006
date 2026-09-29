from datetime import timedelta
from unittest import mock

from django.contrib.auth import authenticate
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts import otp
from apps.accounts.models import Address, OTPCode, User
from apps.accounts.sms import SMSError
from apps.accounts.sms import backends as sms_backends
from apps.core.testing import make_address, make_user

LOCMEM = "apps.accounts.sms.backends.LocmemSMSBackend"


def last_code():
    return sms_backends.outbox[-1]["code"]


@override_settings(SMS_BACKEND=LOCMEM, OTP_LENGTH=5, OTP_RESEND_SECONDS=120, OTP_MAX_ATTEMPTS=3)
class LoginFlowTests(TestCase):
    def setUp(self):
        sms_backends.outbox.clear()

    def request_code(self, phone="09123456789", **extra):
        return self.client.post(reverse("accounts:login"), {"phone": phone, **extra})

    def test_login_sends_code_and_creates_user_on_verify(self):
        response = self.request_code("۰۹۱۲ ۳۴۵ ۶۷۸۹")
        self.assertRedirects(response, reverse("accounts:verify"))
        self.assertEqual(sms_backends.outbox[-1]["phone"], "09123456789")
        self.assertEqual(len(last_code()), 5)

        response = self.client.post(reverse("accounts:verify"), {"code": last_code()})
        self.assertRedirects(response, reverse("accounts:profile_edit"), fetch_redirect_response=False)
        user = User.objects.get(phone="09123456789")
        self.assertFalse(user.has_usable_password())
        self.assertIsNotNone(user.phone_verified_at)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_existing_complete_user_goes_to_next_url(self):
        make_user(phone="09123456789", first_name="سارا", last_name="محمدی")
        self.request_code(next="/cart/")
        response = self.client.post(reverse("accounts:verify"), {"code": last_code()})
        self.assertRedirects(response, "/cart/", fetch_redirect_response=False)

    def test_open_redirect_is_ignored(self):
        make_user(phone="09123456789", first_name="سارا", last_name="محمدی")
        self.request_code(next="https://evil.example.com/")
        response = self.client.post(reverse("accounts:verify"), {"code": last_code()})
        self.assertRedirects(response, reverse("accounts:profile"), fetch_redirect_response=False)

    def test_invalid_phone_is_rejected(self):
        response = self.request_code("12345")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "شماره موبایل معتبر نیست")
        self.assertEqual(sms_backends.outbox, [])

    def test_wrong_code_counts_attempts_and_locks(self):
        self.request_code()
        code = last_code()
        wrong = "00000" if code != "00000" else "11111"
        for _ in range(3):
            response = self.client.post(reverse("accounts:verify"), {"code": wrong})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(OTPCode.objects.get().attempts, 3)
        response = self.client.post(reverse("accounts:verify"), {"code": code})
        self.assertContains(response, "تعداد تلاش‌های ناموفق بیش از حد مجاز است")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_code_cannot_be_reused(self):
        self.request_code()
        code = last_code()
        otp.verify_code("09123456789", OTPCode.Purpose.LOGIN, code)
        with self.assertRaises(otp.OTPError):
            otp.verify_code("09123456789", OTPCode.Purpose.LOGIN, code)

    def test_expired_code_is_rejected(self):
        self.request_code()
        OTPCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaisesMessage(otp.OTPError, "منقضی"):
            otp.verify_code("09123456789", OTPCode.Purpose.LOGIN, last_code())

    def test_resend_is_throttled(self):
        self.request_code()
        with self.assertRaises(otp.OTPThrottled):
            otp.send_code("09123456789", OTPCode.Purpose.LOGIN)
        # Asking again from the login page reuses the code that is still valid.
        response = self.request_code()
        self.assertRedirects(response, reverse("accounts:verify"))
        self.assertEqual(len(sms_backends.outbox), 1)
        # After the cool-down a new code is sent and the old one stops working.
        old_code = last_code()
        OTPCode.objects.update(created_at=timezone.now() - timedelta(seconds=200))
        self.client.post(reverse("accounts:verify"), {"action": "resend"})
        self.assertEqual(len(sms_backends.outbox), 2)
        self.assertEqual(OTPCode.objects.filter(is_used=False).count(), 1)
        if old_code != last_code():
            with self.assertRaises(otp.OTPError):
                otp.verify_code("09123456789", OTPCode.Purpose.LOGIN, old_code)

    @override_settings(OTP_MAX_PER_HOUR=2, OTP_RESEND_SECONDS=0)
    def test_hourly_limit(self):
        otp.send_code("09123456789", OTPCode.Purpose.LOGIN)
        otp.send_code("09123456789", OTPCode.Purpose.LOGIN)
        with self.assertRaisesMessage(otp.OTPError, "بیش از حد مجاز"):
            otp.send_code("09123456789", OTPCode.Purpose.LOGIN)

    def test_sms_failure_is_reported_and_not_throttled(self):
        with mock.patch("apps.accounts.otp.send_otp_sms", side_effect=SMSError("down")), self.assertLogs("apps.accounts.otp", "ERROR"):
            response = self.request_code()
        self.assertContains(response, "ارسال پیامک با خطا مواجه شد")
        self.assertFalse(OTPCode.objects.exists())

    def test_inactive_user_cannot_log_in(self):
        make_user(phone="09123456789", is_active=False)
        self.request_code()
        response = self.client.post(reverse("accounts:verify"), {"code": last_code()})
        self.assertContains(response, "غیرفعال")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(SMS_BACKEND=LOCMEM, OTP_LENGTH=5)
class ChangePhoneTests(TestCase):
    def setUp(self):
        sms_backends.outbox.clear()
        self.user = make_user(phone="09120000001", first_name="سارا", last_name="محمدی")
        self.client.force_login(self.user)

    def test_change_phone_after_sms_verification(self):
        response = self.client.post(reverse("accounts:change_phone"), {"phone": "+98 935 111 2233"})
        self.assertRedirects(response, reverse("accounts:change_phone_verify"))
        self.assertEqual(sms_backends.outbox[-1]["phone"], "09351112233")
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09120000001")  # not changed before verification

        response = self.client.post(reverse("accounts:change_phone_verify"), {"code": last_code()})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09351112233")
        # Still logged in and the new number is now the username.
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)
        self.assertEqual(User.objects.get_by_natural_key("09351112233"), self.user)

    def test_wrong_code_does_not_change_phone(self):
        self.client.post(reverse("accounts:change_phone"), {"phone": "09351112233"})
        wrong = "00000" if last_code() != "00000" else "11111"
        self.client.post(reverse("accounts:change_phone_verify"), {"code": wrong})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09120000001")

    def test_cannot_use_taken_or_same_number(self):
        make_user(phone="09351112233")
        response = self.client.post(reverse("accounts:change_phone"), {"phone": "09351112233"})
        self.assertContains(response, "قبلاً در سایت ثبت شده است")
        response = self.client.post(reverse("accounts:change_phone"), {"phone": "09120000001"})
        self.assertContains(response, "یکسان است")
        self.assertEqual(sms_backends.outbox, [])

    def test_code_of_another_user_is_not_accepted(self):
        other = make_user(phone="09120000002")
        otp.send_code("09351112233", OTPCode.Purpose.CHANGE_PHONE, user=other)
        with self.assertRaises(otp.OTPError):
            otp.verify_code("09351112233", OTPCode.Purpose.CHANGE_PHONE, last_code(), user=self.user)


class ProfileAndAddressTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_profile_pages_require_login(self):
        self.client.logout()
        for name in ["accounts:profile", "accounts:profile_edit", "accounts:address_list", "accounts:change_phone"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response["Location"])

    def test_edit_profile(self):
        response = self.client.post(reverse("accounts:profile_edit"), {"first_name": "مریم", "last_name": "کریمی", "email": ""})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_profile_complete)

    def test_first_address_becomes_default_and_default_switches(self):
        data = {
            "receiver_name": "مریم کریمی",
            "receiver_phone": "۰۹۱۲۱۱۱۲۲۳۳",
            "province": "اصفهان",
            "city": "اصفهان",
            "postal_code": "۱۲۳۴۵-۶۷۸۹۰",
            "full_address": "خیابان چهارباغ",
        }
        self.client.post(reverse("accounts:address_create"), data)
        first = Address.objects.get()
        self.assertTrue(first.is_default)
        self.assertEqual(first.postal_code, "1234567890")
        self.assertEqual(first.receiver_phone, "09121112233")

        second = make_address(self.user)
        self.client.post(reverse("accounts:address_set_default", args=[second.pk]))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertTrue(second.is_default)
        self.assertFalse(first.is_default)

        self.client.post(reverse("accounts:address_delete", args=[second.pk]))
        first.refresh_from_db()
        self.assertTrue(first.is_default)

    def test_cannot_touch_other_users_address(self):
        other_address = make_address(make_user())
        self.assertEqual(self.client.get(reverse("accounts:address_update", args=[other_address.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("accounts:address_delete", args=[other_address.pk])).status_code, 404)


class UserManagerTests(TestCase):
    def test_superuser_needs_password_and_can_authenticate_with_any_format(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(phone="09120000000")
        admin = User.objects.create_superuser(phone="+989120000000", password="Str0ng-pass-123")
        self.assertEqual(admin.phone, "09120000000")
        self.assertEqual(authenticate(username="۰۹۱۲۰۰۰۰۰۰۰", password="Str0ng-pass-123"), admin)


class SMSBackendTests(TestCase):
    def response(self, payload):
        return mock.Mock(status_code=200, json=mock.Mock(return_value=payload))

    @override_settings(KAVENEGAR_API_KEY="KEY", KAVENEGAR_OTP_TEMPLATE="verify")
    def test_kavenegar(self):
        with mock.patch("requests.post", return_value=self.response({"return": {"status": 200}})) as post:
            sms_backends.KavenegarSMSBackend().send_otp("09121234567", "12345")
        self.assertIn("/KEY/verify/lookup.json", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["data"], {"receptor": "09121234567", "token": "12345", "template": "verify"})
        with mock.patch("requests.post", return_value=self.response({"return": {"status": 418, "message": "x"}})):
            with self.assertRaises(SMSError):
                sms_backends.KavenegarSMSBackend().send_otp("09121234567", "12345")

    @override_settings(SMSIR_API_KEY="KEY", SMSIR_OTP_TEMPLATE_ID="100200", SMSIR_OTP_PARAMETER="CODE")
    def test_smsir(self):
        with mock.patch("requests.post", return_value=self.response({"status": 1})) as post:
            sms_backends.SmsIrSMSBackend().send_otp("09121234567", "12345")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["templateId"], 100200)
        self.assertEqual(payload["parameters"], [{"name": "CODE", "value": "12345"}])
        self.assertEqual(post.call_args.kwargs["headers"]["X-API-KEY"], "KEY")

    @override_settings(MELIPAYAMAK_USERNAME="u", MELIPAYAMAK_PASSWORD="p", MELIPAYAMAK_OTP_BODY_ID="123")
    def test_melipayamak(self):
        with mock.patch("requests.post", return_value=self.response({"RetStatus": 1})) as post:
            sms_backends.MelipayamakSMSBackend().send_otp("09121234567", "12345")
        self.assertEqual(post.call_args.kwargs["data"]["bodyId"], "123")

    def test_missing_configuration_raises(self):
        with self.assertRaises(SMSError):
            sms_backends.KavenegarSMSBackend().send_otp("09121234567", "12345")
