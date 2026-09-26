from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import otp as otp_service
from .models import Address, OneTimePassword, User
from .sms import KavenegarSMSBackend, SMSError, SmsIrSMSBackend
from .utils import mask_phone, normalize_phone
from .validators import validate_iran_mobile


class PhoneUtilsTests(TestCase):
    def test_normalize_variants(self):
        for raw in ["09121234567", "۰۹۱۲۱۲۳۴۵۶۷", "+989121234567", "00989121234567", "989121234567", "9121234567", "0912 123 4567"]:
            self.assertEqual(normalize_phone(raw), "09121234567", raw)

    def test_validator(self):
        validate_iran_mobile("09121234567")
        with self.assertRaises(ValidationError):
            validate_iran_mobile("0212345678")

    def test_mask(self):
        self.assertEqual(mask_phone("09121234567"), "0912***4567")

    def test_create_user_is_passwordless(self):
        user = User.objects.create_user(phone="۰۹۱۲۱۲۳۴۵۶۷")
        self.assertEqual(user.phone, "09121234567")
        self.assertFalse(user.has_usable_password())


@override_settings(SMS_BACKEND="console", OTP_DEBUG_SHOW_CODE=False)
class OTPServiceTests(TestCase):
    def test_send_and_verify(self):
        otp, code = otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)
        self.assertEqual(len(code), 5)
        self.assertNotIn(code, otp.code_hash)
        verified = otp_service.verify_otp("09121234567", OneTimePassword.Purpose.LOGIN, code)
        self.assertTrue(verified.is_used)
        with self.assertRaises(otp_service.OTPError):
            otp_service.verify_otp("09121234567", OneTimePassword.Purpose.LOGIN, code)

    def test_resend_cooldown(self):
        otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)
        with self.assertRaises(otp_service.OTPError) as ctx:
            otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)
        self.assertGreater(ctx.exception.wait_seconds, 0)

    def test_wrong_code_counts_attempts(self):
        otp, code = otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)
        wrong = "11111" if code != "11111" else "22222"
        with self.assertRaises(otp_service.OTPError):
            otp_service.verify_otp("09121234567", OneTimePassword.Purpose.LOGIN, wrong)
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)

    def test_expired_code(self):
        otp, code = otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)
        OneTimePassword.objects.filter(pk=otp.pk).update(expires_at=timezone.now())
        with self.assertRaises(otp_service.OTPError):
            otp_service.verify_otp("09121234567", OneTimePassword.Purpose.LOGIN, code)

    def test_persian_digits_are_accepted(self):
        _, code = otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)
        persian = code.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        otp_service.verify_otp("09121234567", OneTimePassword.Purpose.LOGIN, persian)

    def test_failed_sms_allows_immediate_retry(self):
        with mock.patch("accounts.sms.ConsoleSMSBackend.send_otp", side_effect=SMSError("down")):
            with self.assertRaises(otp_service.OTPError):
                otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)
        otp_service.send_otp("09121234567", OneTimePassword.Purpose.LOGIN)


class SMSBackendTests(TestCase):
    @override_settings(KAVENEGAR_API_KEY="key", KAVENEGAR_OTP_TEMPLATE="verify")
    def test_kavenegar_request(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"return": {"status": 200, "message": "تایید شد"}, "entries": []}
        with mock.patch("accounts.sms.requests.post", return_value=response) as post:
            KavenegarSMSBackend().send_otp("09121234567", "12345")
        url = post.call_args.args[0]
        self.assertEqual(url, "https://api.kavenegar.com/v1/key/verify/lookup.json")
        self.assertEqual(post.call_args.kwargs["data"], {"receptor": "09121234567", "token": "12345", "template": "verify"})

    @override_settings(SMSIR_API_KEY="key", SMSIR_OTP_TEMPLATE_ID="123456", SMSIR_OTP_PARAM_NAME="CODE")
    def test_smsir_error_raises(self):
        response = mock.Mock(status_code=400)
        response.json.return_value = {"status": 0, "message": "خطا"}
        with mock.patch("accounts.sms.requests.post", return_value=response):
            with self.assertRaises(SMSError):
                SmsIrSMSBackend().send_otp("09121234567", "12345")

    def test_unconfigured_backend_raises(self):
        with self.assertRaises(SMSError):
            KavenegarSMSBackend().send_otp("09121234567", "12345")


@override_settings(SMS_BACKEND="console", OTP_DEBUG_SHOW_CODE=True)
class LoginFlowTests(TestCase):
    def test_signup_creates_profile_with_phone(self):
        captured = {}
        real_send = otp_service.send_otp

        def capture(*args, **kwargs):
            result = real_send(*args, **kwargs)
            captured["code"] = result[1]
            return result

        with mock.patch("accounts.views.otp_service.send_otp", side_effect=capture):
            response = self.client.post(reverse("accounts:login"), {"phone": "۰۹۱۲ ۱۲۳ ۴۵۶۷"})
        self.assertRedirects(response, reverse("accounts:verify"))
        response = self.client.post(reverse("accounts:verify"), {"code": captured["code"]})
        self.assertRedirects(response, reverse("accounts:profile_edit"))
        user = User.objects.get(phone="09121234567")
        self.assertIsNotNone(user.phone_verified_at)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

        response = self.client.post(reverse("accounts:profile_edit"), {"first_name": "سارا", "last_name": "رضایی", "email": ""})
        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.get_full_name(), "سارا رضایی")
        self.assertContains(self.client.get(reverse("accounts:profile")), "سارا")

    def test_invalid_phone_rejected(self):
        response = self.client.post(reverse("accounts:login"), {"phone": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(OneTimePassword.objects.exists())

    def test_wrong_code_shows_error(self):
        self.client.post(reverse("accounts:login"), {"phone": "09121234567"})
        response = self.client.post(reverse("accounts:verify"), {"code": "00000"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])


@override_settings(SMS_BACKEND="console", OTP_DEBUG_SHOW_CODE=False)
class ChangePhoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09121234567", first_name="علی", last_name="محمدی")
        self.client.force_login(self.user)

    def _send(self, phone):
        captured = {}
        real_send = otp_service.send_otp

        def capture(*args, **kwargs):
            result = real_send(*args, **kwargs)
            captured["code"] = result[1]
            captured["phone"] = args[0]
            return result

        with mock.patch("accounts.views.otp_service.send_otp", side_effect=capture):
            response = self.client.post(reverse("accounts:change_phone"), {"phone": phone})
        return response, captured

    def test_change_phone_after_sms_verification(self):
        response, captured = self._send("09351112233")
        self.assertRedirects(response, reverse("accounts:change_phone_verify"))
        self.assertEqual(captured["phone"], "09351112233")
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09121234567")  # not changed before verification

        response = self.client.post(reverse("accounts:change_phone_verify"), {"code": captured["code"]})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09351112233")
        # Still logged in after the username change
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    def test_cannot_take_someone_elses_phone(self):
        User.objects.create_user(phone="09351112233")
        response, captured = self._send("09351112233")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("code", captured)

    def test_wrong_code_keeps_old_phone(self):
        self._send("09351112233")
        self.client.post(reverse("accounts:change_phone_verify"), {"code": "00000"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09121234567")


class AddressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09121234567")
        self.client.force_login(self.user)

    def test_first_address_becomes_default(self):
        response = self.client.post(
            reverse("accounts:address_create"),
            {
                "title": "خانه",
                "recipient_name": "علی محمدی",
                "recipient_phone": "۰۹۱۲۱۲۳۴۵۶۷",
                "province": "تهران",
                "city": "تهران",
                "postal_code": "۱۲۳۴۵۶۷۸۹۰",
                "address": "خیابان ولیعصر",
            },
        )
        self.assertEqual(response.status_code, 302)
        address = Address.objects.get(user=self.user)
        self.assertTrue(address.is_default)
        self.assertEqual(address.postal_code, "1234567890")
        self.assertEqual(address.recipient_phone, "09121234567")
