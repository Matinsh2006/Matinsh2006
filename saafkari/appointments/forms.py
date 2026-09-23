"""فرم‌های رزرو نوبت و مدیریت آن‌ها."""
from __future__ import annotations

import datetime as dt

from django import forms
from django.conf import settings
from django.utils import timezone

from core.forms import INPUT_CLASS, JalaliDateField
from core.jalali import format_jalali, to_latin_digits
from core.validators import normalize_phone, validate_iran_mobile
from services.models import Service

from .models import Appointment, AppointmentPhoto
from .scheduling import BOOKING_WINDOW_DAYS, available_slots, working_hour_for


class AppointmentForm(forms.ModelForm):
    """فرم ثبت نوبت توسط مشتری (تاریخ شمسی + مشخصات خودرو)."""

    date = JalaliDateField(label="تاریخ نوبت (شمسی)")
    start_time = forms.TimeField(
        label="ساعت نوبت",
        widget=forms.Select(attrs={"class": INPUT_CLASS, "data-slot-select": "true"}),
    )

    class Meta:
        model = Appointment
        fields = ("service", "date", "start_time", "car_model", "plate_number", "contact_phone", "description")
        widgets = {
            "service": forms.Select(attrs={"class": INPUT_CLASS, "data-service-select": "true"}),
            "car_model": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "مثال: پژو ۲۰۶ تیپ ۵، سفید"}),
            "plate_number": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "۱۲ ب ۳۴۵ ایران ۲۲"}),
            "contact_phone": forms.TextInput(attrs={"class": INPUT_CLASS, "dir": "ltr", "inputmode": "numeric"}),
            "description": forms.Textarea(attrs={
                "class": INPUT_CLASS, "rows": 5,
                "placeholder": "مثال: گلگیر جلو سمت راست فرورفتگی دارد و رنگ آن خط افتاده. خودرو قابل حرکت است.",
            }),
        }
        labels = {"contact_phone": "شماره تماس"}

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.active()
        self.fields["service"].empty_label = "خدمت موردنظر را انتخاب کنید"
        self.fields["description"].required = True
        if user is not None:
            self.fields["contact_phone"].initial = user.phone
            if not self.initial.get("car_model"):
                self.fields["car_model"].initial = user.car_model
            if not self.initial.get("plate_number"):
                self.fields["plate_number"].initial = user.plate_number
        # ساعت‌های ممکن به صورت پویا اعتبارسنجی می‌شوند؛ گزینه‌ها را باز می‌گذاریم.
        self.fields["start_time"].widget.choices = []

    def clean_contact_phone(self):
        phone = normalize_phone(self.cleaned_data.get("contact_phone"))
        if phone:
            validate_iran_mobile(phone)
        return phone

    def clean_start_time(self):
        value = self.cleaned_data.get("start_time")
        if isinstance(value, str):
            value = dt.datetime.strptime(to_latin_digits(value), "%H:%M").time()
        return value

    def clean(self):
        cleaned = super().clean()
        date = cleaned.get("date")
        start_time = cleaned.get("start_time")
        service = cleaned.get("service")
        if not (date and start_time and service):
            return cleaned

        today = timezone.localdate()
        if date < today:
            self.add_error("date", "تاریخ نوبت نمی‌تواند در گذشته باشد.")
            return cleaned
        if date > today + dt.timedelta(days=BOOKING_WINDOW_DAYS):
            self.add_error("date", f"فقط تا {BOOKING_WINDOW_DAYS} روز آینده می‌توانید نوبت بگیرید.")
            return cleaned
        if working_hour_for(date) is None:
            self.add_error("date", f"مغازه در {format_jalali(date, '%A %d %B')} تعطیل است.")
            return cleaned

        slots = available_slots(date, service=service)
        if start_time not in slots:
            self.add_error("start_time", "این ساعت دیگر خالی نیست. ساعت دیگری انتخاب کنید.")

        if self.user is not None:
            duplicate = Appointment.objects.filter(
                user=self.user, date=date, start_time=start_time,
                status__in=Appointment.BLOCKING_STATUSES,
            ).exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error(None, "شما برای همین تاریخ و ساعت نوبت ثبت کرده‌اید.")
        return cleaned


class AppointmentPhotoForm(forms.Form):
    """
    اعتبارسنجی عکس‌های ارسالی مشتری.

    برای هر زاویه یک ورودی جدا در قالب وجود دارد؛ این فرم فایل‌ها را
    یک‌جا بررسی می‌کند (نوع فایل و حجم).
    """

    def __init__(self, files=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files_map: dict[str, list] = {}
        self.errors_list: list[str] = []
        self._collect(files)

    def _collect(self, files):
        if not files:
            return
        max_photos = getattr(settings, "APPOINTMENT_MAX_PHOTOS", 8)
        max_mb = getattr(settings, "APPOINTMENT_MAX_PHOTO_SIZE_MB", 5)
        image_field = forms.ImageField()
        total = 0
        for angle, _label in AppointmentPhoto.Angle.choices:
            for uploaded in files.getlist(f"photo_{angle}"):
                if not uploaded:
                    continue
                if total >= max_photos:
                    self.errors_list.append(f"حداکثر {max_photos} عکس می‌توانید ارسال کنید.")
                    return
                if uploaded.size > max_mb * 1024 * 1024:
                    self.errors_list.append(f"حجم «{uploaded.name}» بیشتر از {max_mb} مگابایت است.")
                    continue
                try:
                    image_field.clean(uploaded)
                except forms.ValidationError:
                    self.errors_list.append(f"فایل «{uploaded.name}» عکس معتبری نیست.")
                    continue
                self.files_map.setdefault(angle, []).append(uploaded)
                total += 1

    @property
    def photo_count(self) -> int:
        return sum(len(items) for items in self.files_map.values())

    def is_valid(self) -> bool:
        return not self.errors_list

    def save(self, appointment: Appointment) -> int:
        """ذخیره‌ی عکس‌ها برای نوبت و بازگرداندن تعداد ذخیره‌شده."""
        created = 0
        for angle, uploads in self.files_map.items():
            for uploaded in uploads:
                AppointmentPhoto.objects.create(appointment=appointment, image=uploaded, angle=angle)
                created += 1
        return created


class AppointmentStatusForm(forms.ModelForm):
    """فرم مدیریت نوبت در پنل کارفرما."""

    class Meta:
        model = Appointment
        fields = ("status", "estimated_price", "staff_note", "deposit_amount", "is_deposit_paid")
        widgets = {
            "status": forms.Select(attrs={"class": INPUT_CLASS}),
            "estimated_price": forms.NumberInput(attrs={"class": INPUT_CLASS, "dir": "ltr", "min": 0}),
            "staff_note": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
            "deposit_amount": forms.NumberInput(attrs={"class": INPUT_CLASS, "dir": "ltr", "min": 0}),
        }
