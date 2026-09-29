from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from apps.orders.models import Order

from .gateways.fake import fake_gateway_allowed
from .models import Payment
from .services import start_payment_for_order, verify_callback


@login_required
@require_POST
def start_payment(request, number):
    """The pay button of a pending order (e.g. retrying after a failed payment)."""
    order = get_object_or_404(Order, number=number, user=request.user)
    if not order.is_payable:
        messages.info(request, "این سفارش در وضعیت قابل پرداخت نیست.")
        return redirect(order)
    return start_payment_for_order(request, order)


@csrf_exempt  # gateways may return with a cross-site POST
@require_http_methods(["GET", "POST"])
def payment_callback(request, uuid):
    params = request.POST if request.method == "POST" else request.GET
    try:
        payment, message, retryable = verify_callback(uuid, params)
    except Payment.DoesNotExist:
        raise Http404("تراکنش یافت نشد.") from None
    context = {
        "payment": payment,
        "order": payment.order,
        "success": payment.is_success,
        "message": message,
        "retryable": retryable,
        "retry_url": request.get_full_path(),
    }
    return render(request, "payments/result.html", context)


def fake_gateway(request, authority):
    """Simulated bank page for the test gateway (development only)."""
    if not fake_gateway_allowed():
        raise Http404
    payment = get_object_or_404(
        Payment.objects.select_related("order"),
        authority=authority,
        gateway="fake",
        status=Payment.Status.REDIRECTED,
    )
    callback = reverse("payments:callback", kwargs={"uuid": payment.uuid})
    context = {
        "payment": payment,
        "success_url": f"{callback}?{urlencode({'authority': authority, 'status': 'OK'})}",
        "cancel_url": f"{callback}?{urlencode({'authority': authority, 'status': 'NOK'})}",
    }
    return render(request, "payments/fake_gateway.html", context)
