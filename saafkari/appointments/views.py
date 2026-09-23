"""ثبت، پیگیری و لغو نوبت توسط مشتری."""
from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.sms import send_sms
from core.jalali import format_jalali, jalali_str, parse_jalali
from core.models import SiteSettings
from services.models import Service

from .forms import AppointmentForm, AppointmentPhotoForm
from .models import Appointment, AppointmentPhoto
from .scheduling import BOOKING_WINDOW_DAYS, available_slots, booking_window, open_weekdays, upcoming_holidays


@login_required
@require_http_methods(["GET", "POST"])
def booking_view(request):
    """فرم رزرو نوبت: انتخاب خدمت، تاریخ شمسی، ساعت و ارسال عکس‌های خودرو."""
    site = SiteSettings.load()
    initial = {}
    service_slug = request.GET.get("service")
    if service_slug:
        service = Service.objects.active().filter(slug=service_slug).first()
        if service:
            initial["service"] = service

    form = AppointmentForm(request.POST or None, user=request.user, initial=initial)
    photo_form = AppointmentPhotoForm(request.FILES if request.method == "POST" else None)

    if request.method == "POST":
        if form.is_valid() and photo_form.is_valid():
            with transaction.atomic():
                appointment = form.save(commit=False)
                appointment.user = request.user
                appointment.status = Appointment.Status.PENDING
                appointment.deposit_amount = appointment.service.deposit_for_booking()
                appointment.save()
                photo_form.save(appointment)
                # تکمیل خودکار مشخصات خودرو در پروفایل کاربر
                updates = []
                if appointment.car_model and not request.user.car_model:
                    request.user.car_model = appointment.car_model
                    updates.append("car_model")
                if appointment.plate_number and not request.user.plate_number:
                    request.user.plate_number = appointment.plate_number
                    updates.append("plate_number")
                if updates:
                    request.user.save(update_fields=updates)

            _notify_new_appointment(appointment)
            messages.success(
                request,
                f"نوبت شما با کد پیگیری {appointment.tracking_code} ثبت شد و در انتظار تایید مغازه است.",
            )
            if appointment.needs_deposit:
                return redirect("payments:start", code=appointment.tracking_code)
            return redirect(appointment.get_absolute_url())

        for error in photo_form.errors_list:
            messages.error(request, error)
        if form.errors:
            messages.error(request, "لطفاً خطاهای فرم را برطرف کنید.")

    start, end = booking_window()
    return render(
        request,
        "appointments/booking.html",
        {
            "form": form,
            "site": site,
            "angles": AppointmentPhoto.Angle.choices,
            "max_photos": settings.APPOINTMENT_MAX_PHOTOS,
            "max_photo_mb": settings.APPOINTMENT_MAX_PHOTO_SIZE_MB,
            "min_date": jalali_str(start),
            "max_date": jalali_str(end),
            "booking_days": BOOKING_WINDOW_DAYS,
            "open_weekdays": open_weekdays(),
            "holidays": upcoming_holidays(),
            "services": Service.objects.active(),
        },
    )


def slots_api(request):
    """
    برگرداندن ساعت‌های خالی یک روز به صورت JSON.

    پارامترها: ‎date‎ (شمسی مانند ۱۴۰۵/۰۶/۳۱) و ‎service‎ (شناسه‌ی خدمت)
    """
    date_param = request.GET.get("date", "")
    service_id = request.GET.get("service")
    try:
        date = parse_jalali(date_param)
    except ValueError:
        try:
            date = dt.date.fromisoformat(date_param)
        except ValueError:
            return JsonResponse({"ok": False, "error": "تاریخ نامعتبر است.", "slots": []}, status=400)

    service = Service.objects.active().filter(pk=service_id).first() if service_id else None
    slots = available_slots(date, service=service)
    return JsonResponse(
        {
            "ok": True,
            "date": date.isoformat(),
            "jalali": format_jalali(date, "%A %d %B %Y"),
            "duration": service.duration_minutes if service else None,
            "slots": [slot.strftime("%H:%M") for slot in slots],
        }
    )


@login_required
def my_appointments(request):
    """فهرست نوبت‌های کاربر."""
    appointments = (
        request.user.appointments.select_related("service")
        .prefetch_related("photos", "payments")
        .order_by("-date", "-start_time")
    )
    return render(
        request,
        "appointments/my_list.html",
        {
            "appointments": appointments,
            "upcoming": [item for item in appointments if not item.is_past and item.can_cancel],
        },
    )


@login_required
def appointment_detail(request, code):
    """جزئیات یک نوبت (فقط برای صاحب نوبت یا کارکنان مغازه)."""
    appointment = get_object_or_404(
        Appointment.objects.select_related("service", "user").prefetch_related("photos", "payments"),
        tracking_code=code.upper(),
    )
    if appointment.user_id != request.user.id and not request.user.is_staff:
        messages.error(request, "این نوبت متعلق به حساب شما نیست.")
        return redirect("appointments:mine")
    return render(request, "appointments/detail.html", {"appointment": appointment})


@login_required
@require_POST
def cancel_appointment(request, code):
    """لغو نوبت توسط مشتری."""
    appointment = get_object_or_404(Appointment, tracking_code=code.upper(), user=request.user)
    if not appointment.can_cancel:
        messages.error(request, "این نوبت قابل لغو نیست. برای هماهنگی با مغازه تماس بگیرید.")
    else:
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        messages.success(request, "نوبت شما لغو شد.")
    return redirect("appointments:mine")


def track_view(request):
    """پیگیری نوبت با کد پیگیری، بدون نیاز به ورود."""
    appointment = None
    code = (request.GET.get("code") or "").strip().upper()
    if code:
        appointment = Appointment.objects.filter(tracking_code=code).select_related("service").first()
        if appointment is None:
            messages.error(request, "نوبتی با این کد پیگیری پیدا نشد.")
    return render(request, "appointments/track.html", {"appointment": appointment, "code": code})


def _notify_new_appointment(appointment: Appointment) -> None:
    """پیامک اطلاع‌رسانی ثبت نوبت (خطای پنل نباید ثبت نوبت را خراب کند)."""
    try:
        send_sms(
            appointment.contact_phone or appointment.user.phone,
            f"نوبت شما برای {format_jalali(appointment.date, '%d %B')} ساعت {appointment.start_time:%H:%M} "
            f"ثبت شد. کد پیگیری: {appointment.tracking_code}",
        )
    except Exception:  # pragma: no cover - وابسته به پنل پیامکی
        pass
