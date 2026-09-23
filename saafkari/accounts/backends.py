"""بک‌اند احراز هویت مبتنی بر شماره موبایل."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from core.validators import normalize_phone

UserModel = get_user_model()


class PhoneBackend(ModelBackend):
    """
    ورود با شماره موبایل و رمز عبور (برای کارفرما و پنل مدیریت).

    شماره پیش از جست‌وجو نرمال می‌شود تا ‎+98912…‎ و ‎0912…‎ یکسان دیده شوند.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        phone = normalize_phone(username or kwargs.get("phone") or "")
        if not phone or password is None:
            return None
        try:
            user = UserModel.objects.get(phone=phone)
        except UserModel.DoesNotExist:
            # اجرای هش ساختگی برای جلوگیری از حمله‌ی زمان‌سنجی
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
