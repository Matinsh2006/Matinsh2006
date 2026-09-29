from django import forms
from django.core.validators import RegexValidator
from django.db import models

from apps.core.utils.text import normalize_phone

iran_mobile_validator = RegexValidator(
    r"^09\d{9}$", "شماره موبایل باید ۱۱ رقم باشد و با ۰۹ شروع شود (مثال: 09123456789)."
)
postal_code_validator = RegexValidator(r"^\d{10}$", "کد پستی باید ۱۰ رقم باشد.")


class PhoneNumberFormField(forms.CharField):
    """Accepts Persian digits, spaces, +98/0098 prefixes and normalizes them."""

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 20
        super().__init__(*args, **kwargs)
        self.widget.attrs.update(
            {"dir": "ltr", "inputmode": "tel", "autocomplete": "tel", "placeholder": "09123456789"}
        )

    def to_python(self, value):
        return normalize_phone(super().to_python(value))


class PhoneNumberField(models.CharField):
    """Iranian mobile number stored as ``09xxxxxxxxx``."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 11)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return normalize_phone(value) if value else value

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", PhoneNumberFormField)
        return super().formfield(**kwargs)
