from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.orders.cart import get_cart
from apps.orders.models import Order, OrderStatus

from .gateways import get_gateway
from .models import Payment, PaymentStatus


def start(request, ref_code):
    """ساخت تراکنش و هدایت کاربر به درگاه."""
    order = get_object_or_404(Order, ref_code=ref_code)
    if order.is_paid:
        messages.info(request, "این سفارش قبلاً پرداخت شده است.")
        return redirect("orders:order_detail", ref_code=order.ref_code)

    gateway = get_gateway(request)
    payment = Payment.objects.create(
        order=order, gateway=gateway.name, amount=order.total_price
    )
    result = gateway.start(payment)
    if not result.success:
        payment.status = PaymentStatus.FAILED
        payment.error_message = result.message
        payment.save(update_fields=["status", "error_message"])
        messages.error(request, result.message or "اتصال به درگاه پرداخت ناموفق بود.")
        return redirect("orders:checkout")

    payment.authority = result.authority
    payment.status = PaymentStatus.REDIRECTED
    payment.save(update_fields=["authority", "status"])
    return HttpResponseRedirect(result.redirect_url)


@require_http_methods(["GET", "POST"])
def sandbox(request, payment_id):
    """صفحه درگاه آزمایشی؛ در محیط واقعی جای آن را درگاه بانک می‌گیرد."""
    payment = get_object_or_404(Payment, pk=payment_id)
    if request.method == "POST":
        status = "OK" if request.POST.get("action") == "pay" else "NOK"
        return redirect(f"/payment/callback/{payment.pk}/?status={status}")
    return render(request, "payments/sandbox.html", {"payment": payment, "order": payment.order})


def callback(request, payment_id):
    """بازگشت از درگاه: تایید تراکنش، کسر موجودی و خالی کردن سبد."""
    payment = get_object_or_404(Payment.objects.select_related("order"), pk=payment_id)
    order = payment.order

    if payment.status == PaymentStatus.SUCCESS:
        return redirect("payments:result", ref_code=order.ref_code)

    gateway = get_gateway(request, name=payment.gateway)
    data = request.GET.dict()
    result = gateway.verify(payment, data)

    if not result.success:
        payment.status = PaymentStatus.CANCELED if data.get("status") == "NOK" else PaymentStatus.FAILED
        payment.error_message = result.message
        payment.save(update_fields=["status", "error_message"])
        messages.error(request, result.message or "پرداخت ناموفق بود.")
        return redirect("payments:result", ref_code=order.ref_code)

    with transaction.atomic():
        payment.status = PaymentStatus.SUCCESS
        payment.ref_id = result.ref_id
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "ref_id", "verified_at"])

        order.status = OrderStatus.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])

        for item in order.items.select_related("variant"):
            variant = item.variant
            if variant:
                variant.stock = max(variant.stock - item.quantity, 0)
                variant.save(update_fields=["stock"])

    cart = get_cart(request, create=False)
    if cart:
        cart.items.all().delete()

    messages.success(request, "پرداخت با موفقیت انجام شد.")
    return redirect("payments:result", ref_code=order.ref_code)


def result(request, ref_code):
    order = get_object_or_404(Order.objects.prefetch_related("items", "payments"), ref_code=ref_code)
    payment = order.payments.first()
    return render(
        request,
        "payments/result.html",
        {"order": order, "payment": payment, "gateway": settings.PAYMENT_GATEWAY},
    )
