from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cart.cart import Cart
from orders.models import Order

from .gateways import GATEWAY_CLASSES, FakeGateway, enabled_gateways
from .models import Payment
from .services import complete_payment, start_payment


@login_required
@require_POST
def pay_order(request, number):
    order = get_object_or_404(Order, number=number, user=request.user)
    gateways = enabled_gateways()
    default_code = gateways[0].code if gateways else ""
    return start_payment(request, order, request.POST.get("gateway") or default_code)


@csrf_exempt
def callback(request, gateway_code):
    gateway_class = GATEWAY_CLASSES.get(gateway_code)
    if gateway_class is None or (gateway_class is FakeGateway and not settings.PAYMENT_ALLOW_FAKE):
        raise Http404
    gateway = gateway_class()
    authority = gateway.authority_from_callback(request)
    payment = (
        Payment.objects.select_related("order").filter(gateway=gateway_code, authority=authority).first()
        if authority
        else None
    )
    if payment is None:
        return render(request, "payments/unknown.html", status=404)
    complete_payment(gateway, payment, request)
    return redirect("payments:result", number=payment.order.number)


@login_required
def result(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number, user=request.user)
    payment = order.payments.first()
    if order.is_paid:
        Cart(request).clear()
    return render(
        request,
        "payments/result.html",
        {"order": order, "payment": payment, "success": order.is_paid, "gateways": enabled_gateways()},
    )


def fake_gateway(request, authority):
    if not settings.PAYMENT_ALLOW_FAKE:
        raise Http404
    payment = get_object_or_404(Payment.objects.select_related("order"), gateway=FakeGateway.code, authority=authority)
    callback_url = request.GET.get("callback", "")
    if not url_has_allowed_host_and_scheme(callback_url, allowed_hosts={request.get_host()}):
        callback_url = reverse("payments:callback", args=[FakeGateway.code])
    return render(
        request,
        "payments/fake_gateway.html",
        {
            "payment": payment,
            "ok_url": f"{callback_url}?{urlencode({'authority': authority, 'status': 'ok'})}",
            "cancel_url": f"{callback_url}?{urlencode({'authority': authority, 'status': 'nok'})}",
        },
    )
