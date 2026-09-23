"""فیلدها و ویجت‌های مشترک فرم‌ها (تاریخ شمسی)."""
from __future__ import annotations

import datetime as dt

from django import forms

from .jalali import jalali_str, parse_jalali

INPUT_CLASS = (
    "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 shadow-sm "
    "transition focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
)


class JalaliDateWidget(forms.TextInput):
    """ورودی متنی تاریخ شمسی که تقویم جاوااسکریپتی به آن وصل می‌شود."""

    def __init__(self, attrs=None):
        default_attrs = {
            "class": INPUT_CLASS + " cursor-pointer",
            "autocomplete": "off",
            "readonly": "readonly",
            "placeholder": "۱۴۰۵/۰۱/۰۱",
            "data-jalali-date": "true",
            "dir": "ltr",
        }
        default_attrs.update(attrs or {})
        super().__init__(default_attrs)

    def format_value(self, value):
        """مقدار ذخیره‌شده (میلادی) را به رشته‌ی شمسی تبدیل می‌کند."""
        if isinstance(value, (dt.date, dt.datetime)):
            return jalali_str(value)
        return value


class JalaliDateField(forms.Field):
    """فیلد تاریخ شمسی؛ ورودی «۱۴۰۵/۰۶/۳۱» را به ‎date‎ میلادی تبدیل می‌کند."""

    widget = JalaliDateWidget
    default_error_messages = {"invalid": "تاریخ واردشده معتبر نیست. از تقویم استفاده کنید."}

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        try:
            return parse_jalali(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc) or self.error_messages["invalid"], code="invalid") from exc

    def prepare_value(self, value):
        if isinstance(value, (dt.date, dt.datetime)):
            return jalali_str(value)
        return value


class ContactForm(forms.ModelForm):
    """فرم تماس با ما."""

    class Meta:
        from .models import ContactMessage

        model = ContactMessage
        fields = ("name", "phone", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام و نام خانوادگی"}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "dir": "ltr", "inputmode": "numeric", "placeholder": "۰۹۱۲۱۲۳۴۵۶۷"}),
            "subject": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "موضوع پیام"}),
            "message": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 5, "placeholder": "متن پیام شما..."}),
        }

    def clean_phone(self):
        from .validators import normalize_phone, validate_iran_mobile

        phone = normalize_phone(self.cleaned_data["phone"])
        validate_iran_mobile(phone)
        return phone
