import re

from django.core.exceptions import ValidationError

from .utils import is_valid_mobile, to_english_digits


def validate_iran_mobile(value):
    if not is_valid_mobile(value):
        raise ValidationError(
            "شماره موبایل معتبر نیست. نمونه صحیح: ۰۹۱۲۱۲۳۴۵۶۷",
            code="invalid_mobile",
        )


def validate_postal_code(value):
    if not re.fullmatch(r"\d{10}", to_english_digits(value)):
        raise ValidationError("کد پستی باید ۱۰ رقم باشد.", code="invalid_postal_code")
