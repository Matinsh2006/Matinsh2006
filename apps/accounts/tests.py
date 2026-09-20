from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import OTPCode, OTPPurpose, Profile, User
from apps.accounts.validators import normalize_phone


class PhoneNormalizationTests(TestCase):
    def test_various_formats_normalize(self):
        for raw in ["09121234567", "+989121234567", "00989121234567", "9121234567", "۰۹۱۲۱۲۳۴۵۶۷"]:
            self.assertEqual(normalize_phone(raw), "09121234567")


class UserModelTests(TestCase):
    def test_profile_created_with_user(self):
        user = User.objects.create_user(phone="09121234567")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_superuser_requires_password(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(phone="09121234567")


class OTPTests(TestCase):
    def test_generate_invalidates_previous_code(self):
        first = OTPCode.generate("09121234567")
        OTPCode.generate("09121234567")
        first.refresh_from_db()
        self.assertTrue(first.is_used)

    def test_wrong_code_counts_attempt(self):
        otp = OTPCode.generate("09121234567")
        self.assertFalse(otp.verify("00000" if otp.code != "00000" else "11111"))
        self.assertEqual(otp.attempts, 1)
        self.assertFalse(otp.is_used)

    def test_correct_code_consumes_otp(self):
        otp = OTPCode.generate("09121234567")
        self.assertTrue(otp.verify(otp.code))
        self.assertTrue(otp.is_used)
        self.assertFalse(otp.verify(otp.code))


class LoginFlowTests(TestCase):
    def test_login_with_otp_creates_user(self):
        self.client.post(reverse("accounts:login"), {"phone": "0912 123 4567"})
        otp = OTPCode.objects.get(phone="09121234567", purpose=OTPPurpose.LOGIN)
        response = self.client.post(reverse("accounts:verify"), {"code": otp.code}, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(phone="09121234567")
        self.assertTrue(user.phone_verified)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_verify_without_session_redirects(self):
        response = self.client.get(reverse("accounts:verify"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)


class ChangePhoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09121234567")
        self.client.force_login(self.user)

    def test_phone_changes_only_after_otp(self):
        self.client.post(reverse("accounts:change_phone"), {"phone": "09359876543"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09121234567")  # هنوز تغییر نکرده

        otp = OTPCode.objects.get(phone="09359876543", purpose=OTPPurpose.CHANGE_PHONE)
        self.client.post(reverse("accounts:phone_verify"), {"code": otp.code})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09359876543")

    def test_wrong_code_keeps_old_phone(self):
        self.client.post(reverse("accounts:change_phone"), {"phone": "09359876543"})
        self.client.post(reverse("accounts:phone_verify"), {"code": "00000"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09121234567")

    def test_duplicate_phone_rejected(self):
        User.objects.create_user(phone="09359876543")
        response = self.client.post(reverse("accounts:change_phone"), {"phone": "09359876543"})
        self.assertContains(response, "قبلاً در سایت ثبت شده")

    def test_profile_update_saves_user_fields(self):
        self.client.post(
            reverse("accounts:profile"),
            {"full_name": "مریم احمدی", "email": "m@example.com", "city": "تهران", "address": "خیابان آزادی", "province": "تهران", "postal_code": "1234567890"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "مریم احمدی")
        self.assertEqual(self.user.profile.city, "تهران")
