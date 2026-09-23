import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from config.jalali import format_jalali_date, parse_jalali_date, today_jalali_parts
from salon.models import SalonProfile
from services.models import Service

from .forms import BookingForm
from .models import Appointment
from .slots import get_available_slots


@require_GET
def available_slots_api(request):
    service = get_object_or_404(Service, pk=request.GET.get("service"), is_active=True)
    date_value = parse_jalali_date(request.GET.get("date"))
    if not date_value:
        return JsonResponse({"ok": False, "error": "تاریخ نامعتبر است."}, status=400)

    slots = get_available_slots(service, date_value)
    return JsonResponse(
        {
            "ok": True,
            "date_display": format_jalali_date(date_value),
            "slots": [slot.strftime("%H:%M") for slot in slots],
        }
    )


@login_required
def book_service(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    salon = SalonProfile.get_solo()

    if request.method == "POST":
        form = BookingForm(request.POST, service=service)
        if form.is_valid():
            date_value = form.cleaned_data["date_value"]
            start_time = form.cleaned_data["start_time_value"]
            end_time = (
                datetime.datetime.combine(date_value, start_time)
                + datetime.timedelta(minutes=service.duration_minutes)
            ).time()

            appointment = Appointment.objects.create(
                user=request.user,
                service=service,
                full_name=form.cleaned_data["full_name"],
                phone_number=form.cleaned_data["phone_number"],
                notes=form.cleaned_data["notes"],
                date=date_value,
                start_time=start_time,
                end_time=end_time,
                status=(
                    Appointment.STATUS_AWAITING_DEPOSIT
                    if service.requires_deposit
                    else Appointment.STATUS_PENDING
                ),
            )
            if service.requires_deposit:
                return redirect("payments:request_payment", appointment_id=appointment.pk)
            messages.success(request, "نوبت شما با موفقیت ثبت شد و در انتظار تایید است.")
            return redirect("bookings:success", pk=appointment.pk)
    else:
        form = BookingForm(
            service=service,
            initial={
                "full_name": request.user.full_name,
                "phone_number": request.user.phone_number,
            },
        )

    today_year, today_month, today_day, today_weekday = today_jalali_parts()

    return render(
        request,
        "bookings/book.html",
        {
            "service": service,
            "form": form,
            "salon": salon,
            "today_year": today_year,
            "today_month": today_month,
            "today_day": today_day,
            "today_weekday": today_weekday,
            "max_advance_days": settings.BOOKING_MAX_ADVANCE_DAYS,
        },
    )


@login_required
def booking_success(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, user=request.user)
    return render(request, "bookings/success.html", {"appointment": appointment})
