import logging

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .gateways import GatewayError, VerifyResult, get_gateway
from .models import Payment

logger = logging.getLogger(__name__)


def build_callback_url(request, gateway_code):
    path = reverse("payments:callback", args=[gateway_code])
    if settings.SITE_URL:
        return settings.SITE_URL + path
    return request.build_absolute_uri(path)


def start_payment(request, order, gateway_code):
    """Register a payment for ``order`` and redirect the customer to the bank."""
    try:
        gateway = get_gateway(gateway_code)
    except GatewayError as exc:
        messages.error(request, str(exc))
        return redirect(order)

    if not order.is_payable:
        messages.info(request, "این سفارش قبلاً پرداخت یا لغو شده است.")
        return redirect(order)

    unavailable = order.unavailable_items()
    if unavailable:
        names = "، ".join(item.product_name for item in unavailable)
        messages.error(request, f"موجودی این کالاها کافی نیست: {names}. لطفاً سفارش جدید ثبت کنید.")
        return redirect(order)

    payment = Payment.objects.create(order=order, gateway=gateway.code, amount=order.total * 10)
    try:
        result = gateway.request(
            payment,
            build_callback_url(request, gateway.code),
            description=f"پرداخت سفارش {order.number}",
            mobile=order.user.phone,
        )
    except GatewayError as exc:
        payment.status = Payment.Status.FAILED
        payment.message = str(exc)[:255]
        payment.save(update_fields=["status", "message", "updated_at"])
        messages.error(request, str(exc))
        return redirect(order)

    payment.authority = result.authority
    payment.request_data = result.raw
    payment.status = Payment.Status.REDIRECTED
    payment.save(update_fields=["authority", "request_data", "status", "updated_at"])
    logger.info("Payment %s for order %s redirected to %s", payment.pk, order.number, gateway.code)
    return redirect(result.redirect_url)


def complete_payment(gateway, payment, request):
    """Handle the gateway callback: verify and settle ``payment`` exactly once."""
    if payment.status == Payment.Status.PAID:
        return payment

    if not gateway.callback_is_ok(request):
        Payment.objects.filter(
            pk=payment.pk, status__in=[Payment.Status.INITIATED, Payment.Status.REDIRECTED]
        ).update(status=Payment.Status.CANCELED, message="پرداخت توسط کاربر لغو شد یا ناموفق بود.")
        payment.refresh_from_db()
        return payment

    try:
        verification = gateway.verify(payment, request)
    except GatewayError as exc:
        verification = VerifyResult(False, message=str(exc))

    with transaction.atomic():
        locked = Payment.objects.select_for_update().select_related("order").get(pk=payment.pk)
        if locked.status == Payment.Status.PAID:
            return locked
        locked.verify_data = verification.raw
        if verification.success:
            locked.status = Payment.Status.PAID
            locked.ref_id = verification.ref_id
            locked.card_pan = verification.card_pan
            locked.message = ""
            locked.verified_at = timezone.now()
            locked.save()
            if not locked.order.mark_paid():
                logger.warning(
                    "Payment %s succeeded but order %s was not pending (status=%s); refund may be needed.",
                    locked.pk,
                    locked.order.number,
                    locked.order.status,
                )
        else:
            locked.status = Payment.Status.FAILED
            locked.message = (verification.message or "تایید پرداخت ناموفق بود.")[:255]
            locked.save()
    return locked
