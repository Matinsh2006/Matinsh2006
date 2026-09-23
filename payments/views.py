from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from bookings.models import Appointment

from .models import Payment
from .zarinpal import ZarinPalError, request_payment, verify_payment


@login_required
def request_payment_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id, user=request.user)

    if not appointment.requires_deposit:
        messages.info(request, "برای این خدمت نیازی به پرداخت بیعانه نیست.")
        return redirect("bookings:success", pk=appointment.pk)

    payment, _ = Payment.objects.get_or_create(
        appointment=appointment,
        defaults={"amount": appointment.service.deposit_amount},
    )
    if payment.status == Payment.STATUS_SUCCESS:
        return redirect("payments:result", pk=payment.pk)

    callback_url = request.build_absolute_uri(reverse("payments:callback", args=[payment.pk]))

    try:
        authority, pay_url = request_payment(
            amount=payment.amount,
            description=f"بیعانه نوبت {appointment.service.name} - {appointment.full_name}",
            callback_url=callback_url,
            mobile=appointment.phone_number,
        )
    except ZarinPalError as exc:
        return render(
            request,
            "payments/error.html",
            {"appointment": appointment, "error": str(exc)},
        )

    payment.authority = authority
    payment.save(update_fields=["authority"])
    return redirect(pay_url)


def payment_callback(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    appointment = payment.appointment

    status = request.GET.get("Status")
    authority = request.GET.get("Authority")

    if status != "OK" or not authority:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=["status"])
        return render(request, "payments/result.html", {"payment": payment, "success": False})

    try:
        ref_id, card_pan = verify_payment(amount=payment.amount, authority=authority)
    except ZarinPalError as exc:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=["status"])
        return render(
            request,
            "payments/result.html",
            {"payment": payment, "success": False, "error": str(exc)},
        )

    payment.status = Payment.STATUS_SUCCESS
    payment.ref_id = ref_id or ""
    payment.card_pan = card_pan or ""
    payment.paid_at = timezone.now()
    payment.save(update_fields=["status", "ref_id", "card_pan", "paid_at"])

    if appointment.status == Appointment.STATUS_AWAITING_DEPOSIT:
        appointment.status = Appointment.STATUS_PENDING
        appointment.save(update_fields=["status"])

    return render(request, "payments/result.html", {"payment": payment, "success": True})


@login_required
def payment_result(request, pk):
    payment = get_object_or_404(Payment, pk=pk, appointment__user=request.user)
    return render(
        request,
        "payments/result.html",
        {"payment": payment, "success": payment.status == Payment.STATUS_SUCCESS},
    )
