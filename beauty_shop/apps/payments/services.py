import logging

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from apps.orders.services import mark_order_paid, order_stock_problems

from .gateways import GatewayError, GatewayResult, get_gateway
from .models import Payment

logger = logging.getLogger(__name__)

RIAL_PER_TOMAN = 10


def start_payment_for_order(request, order):
    """Create a Payment, register it with the gateway and redirect the customer there."""
    problems = order_stock_problems(order)
    if problems:
        for problem in problems:
            messages.error(request, problem)
        return redirect(order)

    try:
        gateway = get_gateway()
    except ImproperlyConfigured:
        logger.exception("Payment gateway is misconfigured")
        gateway = None
    if gateway is None or not gateway.is_available():
        messages.error(request, "درگاه پرداخت در حال حاضر در دسترس نیست. لطفاً کمی بعد دوباره تلاش کنید.")
        return redirect(order)

    payment = Payment.objects.create(order=order, gateway=gateway.code, amount=order.total)
    callback_url = request.build_absolute_uri(reverse("payments:callback", kwargs={"uuid": payment.uuid}))
    try:
        result = gateway.request_payment(
            amount_rial=order.total * RIAL_PER_TOMAN,
            callback_url=callback_url,
            description=f"پرداخت سفارش شماره {order.number}",
            mobile=order.user.phone,
            order_number=order.number,
        )
    except GatewayError:
        logger.exception("Payment request failed for order %s", order.number)
        result = GatewayResult(ok=False, message="ارتباط با درگاه پرداخت برقرار نشد.")

    payment.raw_data = {"request": result.raw}
    if not result.ok:
        payment.status = Payment.Status.FAILED
        payment.message = result.message[:255]
        payment.save(update_fields=["status", "message", "raw_data", "updated_at"])
        messages.error(request, f"{result.message} لطفاً دوباره تلاش کنید.")
        return redirect(order)

    payment.authority = result.authority
    payment.status = Payment.Status.REDIRECTED
    payment.save(update_fields=["authority", "status", "raw_data", "updated_at"])
    return redirect(result.redirect_url)


def verify_callback(payment_uuid, params):
    """
    Verify a payment when the customer returns from the gateway.

    Returns ``(payment, message, retryable)``. The row is locked so a payment is
    never verified (and the order never marked paid) twice.
    """
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order", "order__user").get(uuid=payment_uuid)
        if payment.status in (Payment.Status.SUCCESS, Payment.Status.FAILED):
            return payment, payment.message, False

        gateway = get_gateway(payment.gateway)
        if gateway.get_callback_authority(params) != payment.authority:
            result = GatewayResult(ok=False, message="اطلاعات بازگشتی از درگاه با این تراکنش مطابقت ندارد.")
        else:
            try:
                result = gateway.verify_payment(
                    payment=payment, amount_rial=payment.amount * RIAL_PER_TOMAN, params=params
                )
            except GatewayError:
                logger.exception("Verifying payment %s failed", payment.uuid)
                message = (
                    "ارتباط با درگاه برای تایید پرداخت برقرار نشد. چند لحظه بعد صفحه را دوباره بارگذاری کنید؛ "
                    "در صورت کسر وجه و عدم تایید، مبلغ حداکثر تا ۷۲ ساعت به حساب شما بازمی‌گردد."
                )
                return payment, message, True

        payment.raw_data = {**payment.raw_data, "verify": result.raw}
        if result.ok:
            payment.status = Payment.Status.SUCCESS
            payment.ref_id = result.ref_id
            payment.card_pan = result.card_pan
            payment.message = "پرداخت با موفقیت انجام شد."
            payment.verified_at = timezone.now()
            payment.save()
            if not mark_order_paid(payment.order):
                logger.warning(
                    "Payment %s succeeded but order %s was not pending (status=%s) – refund may be required.",
                    payment.uuid,
                    payment.order.number,
                    payment.order.status,
                )
        else:
            payment.status = Payment.Status.FAILED
            payment.message = result.message[:255]
            payment.save()
    return payment, payment.message, False
