"""اعتبارسنج‌ها و نرمال‌سازهای مشترک (شماره موبایل، تصویر و ...)."""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .jalali import to_latin_digits

IRAN_MOBILE_RE = re.compile(r"^09\d{9}$")


def normalize_phone(value) -> str:
    """
    شماره‌ی موبایل ایران را به قالب یکسان ‎09XXXXXXXXX‎ تبدیل می‌کند.

    ورودی‌های پذیرفته‌شده: ‎+989121234567‎، ‎00989121234567‎،
    ‎989121234567‎، ‎9121234567‎، ‎0912-123-4567‎ و ارقام فارسی.
    """
    if not value:
        return ""
    digits = re.sub(r"\D", "", to_latin_digits(value))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits


def validate_iran_mobile(value):
    """اعتبارسنجی شماره موبایل ایران پس از نرمال‌سازی."""
    if not IRAN_MOBILE_RE.match(normalize_phone(value)):
        raise ValidationError(_("شماره موبایل معتبر نیست. نمونه‌ی درست: ۰۹۱۲۱۲۳۴۵۶۷"))


def mask_phone(value: str) -> str:
    """نمایش نیمه‌پنهان شماره برای پیام‌ها: ‎0912***4567‎."""
    phone = normalize_phone(value)
    if len(phone) != 11:
        return phone or ""
    return f"{phone[:4]}***{phone[-4:]}"


def validate_image_size(image, max_mb: int | None = None):
    """جلوگیری از آپلود عکس‌های بیش از حد بزرگ."""
    from django.conf import settings

    limit = max_mb or getattr(settings, "APPOINTMENT_MAX_PHOTO_SIZE_MB", 5)
    size = getattr(image, "size", None)
    if size and size > limit * 1024 * 1024:
        raise ValidationError(_("حجم هر عکس نباید بیشتر از %(limit)s مگابایت باشد.") % {"limit": limit})
