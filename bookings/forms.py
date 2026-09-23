import datetime

from django import forms
from django.conf import settings

from accounts.models import phone_validator
from config.jalali import parse_jalali_date

from .slots import get_available_slots


class BookingForm(forms.Form):
    jalali_date = forms.CharField(widget=forms.HiddenInput)
    start_time = forms.CharField(widget=forms.HiddenInput)
    full_name = forms.CharField(
        label="نام و نام خانوادگی",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        label="شماره تماس",
        max_length=11,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    notes = forms.CharField(
        label="توضیحات (اختیاری)",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, service=None, **kwargs):
        self.service = service
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        jalali_date = cleaned.get("jalali_date")
        start_time_str = cleaned.get("start_time")
        if not jalali_date or not start_time_str:
            raise forms.ValidationError("لطفاً تاریخ و ساعت نوبت را از تقویم انتخاب کنید.")

        date_value = parse_jalali_date(jalali_date)
        if not date_value:
            raise forms.ValidationError("تاریخ انتخاب‌شده نامعتبر است.")

        max_date = datetime.date.today() + datetime.timedelta(
            days=settings.BOOKING_MAX_ADVANCE_DAYS
        )
        if date_value < datetime.date.today() or date_value > max_date:
            raise forms.ValidationError("تاریخ انتخاب‌شده خارج از بازه مجاز رزرو است.")

        try:
            hour_str, minute_str = start_time_str.split(":")
            start_time = datetime.time(int(hour_str), int(minute_str))
        except (ValueError, AttributeError):
            raise forms.ValidationError("ساعت انتخاب‌شده نامعتبر است.")

        available = get_available_slots(self.service, date_value)
        if start_time not in available:
            raise forms.ValidationError(
                "این ساعت دیگر در دسترس نیست؛ لطفاً یک ساعت دیگر انتخاب کنید."
            )

        cleaned["date_value"] = date_value
        cleaned["start_time_value"] = start_time
        return cleaned
