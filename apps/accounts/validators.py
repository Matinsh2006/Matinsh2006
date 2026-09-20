import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

PHONE_RE = re.compile(r"^09\d{9}$")
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def to_english_digits(value: str) -> str:
    """تبدیل ارقام فارسی/عربی به انگلیسی."""
    if not value:
        return ""
    table = {ord(p): str(i) for i, p in enumerate(PERSIAN_DIGITS)}
    table.update({ord(a): str(i) for i, a in enumerate(ARABIC_DIGITS)})
    return value.translate(table)


def normalize_phone(value: str) -> str:
    """شماره موبایل را به قالب 09xxxxxxxxx تبدیل می‌کند."""
    value = to_english_digits(str(value or "")).strip()
    value = re.sub(r"[\s\-()]", "", value)
    if value.startswith("+98"):
        value = "0" + value[3:]
    elif value.startswith("0098"):
        value = "0" + value[4:]
    elif value.startswith("98") and len(value) == 12:
        value = "0" + value[2:]
    elif value.startswith("9") and len(value) == 10:
        value = "0" + value
    return value


def validate_iranian_phone(value):
    if not PHONE_RE.match(normalize_phone(value)):
        raise ValidationError(_("شماره موبایل معتبر نیست. نمونه درست: ۰۹۱۲۱۲۳۴۵۶۷"))
