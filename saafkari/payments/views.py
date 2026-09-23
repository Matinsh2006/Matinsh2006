"""آغاز پرداخت بیعانه، بازگشت از درگاه و رسید."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from appointments.models import Appointment
from core.models import SiteSettings

from .gateways import get_gateway
from .models import Payment


@login_required
def start_payment(request, code):
    """ساخت تراکنش بیعانه و انتقال کاربر به درگاه."""
    appointment = get_object_or_404(Appointment, tracking_code=code.upper(), user=request.user)
    site = SiteSettings.load()

    if not site.online_payment_enabled:
        messages.info(request, "پرداخت آنلاین در حال حاضر غیرفعال است. هنگام مراجعه، بیعانه را حضوری پرداخت کنید.")
        return redirect(appointment.get_absolute_url())
    if appointment.is_deposit_paid:
        messages.info(request, "بیعانه‌ی این نوبت قبلاً پرداخت شده است.")
        return redirect(appointment.get_absolute_url())

    amount = appointment.deposit_amount or site.deposit_amount
    if amount <= 0:
        messages.info(request, "برای این نوبت بیعانه‌ای تعیین نشده است.")
        return redirect(appointment.get_absolute_url())

    gateway = get_gateway()
    # اگر تراکنش پرداخت‌نشده‌ای برای همین نوبت هست، همان استفاده می‌شود
    # تا فهرست پرداخت‌ها پر از تراکنش‌های نیمه‌کاره نشود.
    payment = Payment.objects.filter(
        appointment=appointment, user=request.user, kind=Payment.Kind.DEPOSIT,
        status=Payment.Status.PENDING,
    ).first()
    if payment is None:
        payment = Payment.objects.create(
            appointment=appointment,
            user=request.user,
            amount=amount,
            kind=Payment.Kind.DEPOSIT,
            gateway=gateway.name,
            description=f"بیعانه‌ی {appointment.service.title} — کد {appointment.tracking_code}",
        )
    elif payment.amount != amount or payment.gateway != gateway.name:
        payment.amount = amount
        payment.gateway = gateway.name
        payment.save(update_fields=["amount", "gateway", "updated_at"])
    callback_url = request.build_absolute_uri(
        f"/payments/callback/{payment.invoice_number}/"
    )
    result = gateway.request_payment(payment, callback_url)
    if not result.ok:
        payment.mark_failed(response=result.raw)
        messages.error(request, f"اتصال به درگاه ممکن نشد: {result.error}")
        return redirect(appointment.get_absolute_url())

    payment.authority = result.authority
    payment.gateway_response = result.raw
    payment.save(update_fields=["authority", "gateway_response", "updated_at"])
    return redirect(result.redirect_url)


@require_http_methods(["GET", "POST"])
def payment_callback(request, invoice):
    """بازگشت از درگاه: تایید تراکنش و به‌روزرسانی وضعیت نوبت."""
    payment = get_object_or_404(Payment.objects.select_related("appointment"), invoice_number=invoice)

    if payment.is_paid:
        messages.info(request, "این پرداخت قبلاً تایید شده است.")
        return redirect(payment.get_absolute_url())

    params = {**request.GET.dict(), **request.POST.dict()}
    gateway = get_gateway()
    result = gateway.verify(payment, params)

    if result.ok:
        payment.mark_paid(ref_id=result.ref_id, card_pan=result.card_pan, response=result.raw)
        messages.success(request, f"پرداخت با موفقیت انجام شد. شماره پیگیری: {payment.ref_id}")
    elif result.cancelled:
        payment.mark_failed(status=Payment.Status.CANCELLED, response=result.raw)
        messages.warning(request, "پرداخت لغو شد. نوبت شما همچنان در وضعیت «در انتظار تایید» است.")
    else:
        payment.mark_failed(response=result.raw)
        messages.error(request, f"پرداخت ناموفق بود: {result.error}")

    return redirect(payment.get_absolute_url())


@login_required
def receipt_view(request, invoice):
    """رسید پرداخت."""
    payment = get_object_or_404(
        Payment.objects.select_related("appointment", "user"), invoice_number=invoice
    )
    if payment.user_id != request.user.id and not request.user.is_staff:
        messages.error(request, "این رسید متعلق به حساب شما نیست.")
        return redirect("accounts:profile")
    return render(request, "payments/receipt.html", {"payment": payment})


@login_required
@require_http_methods(["GET", "POST"])
def sandbox_view(request, invoice):
    """
    صفحه‌ی درگاه آزمایشی.

    فقط زمانی کار می‌کند که درگاه فعال، ‎SandboxGateway‎ باشد؛ برای آزمایش
    کامل چرخه‌ی پرداخت پیش از گرفتن مرچنت‌کد واقعی.
    """
    payment = get_object_or_404(Payment.objects.select_related("appointment"), invoice_number=invoice)
    if payment.user_id != request.user.id:
        messages.error(request, "دسترسی به این تراکنش ندارید.")
        return redirect("accounts:profile")
    if payment.gateway != "sandbox":
        return redirect(payment.get_absolute_url())

    if request.method == "POST":
        action = request.POST.get("action")
        return redirect(
            f"/payments/callback/{payment.invoice_number}/?result={'ok' if action == 'pay' else 'cancel'}"
        )
    return render(request, "payments/sandbox.html", {"payment": payment})


@login_required
def my_payments(request):
    """فهرست پرداخت‌های کاربر."""
    payments = Payment.objects.filter(user=request.user).select_related("appointment")
    return render(request, "payments/my_list.html", {"payments": payments})
