from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog.models import Product
from core.utils import format_number

from .cart import Cart


def _wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def _cart_payload(request, cart, **extra):
    return {
        "ok": True,
        "count": cart.count,
        "subtotal": format_number(cart.subtotal),
        "total": format_number(cart.total),
        "drawer": render_to_string("cart/_drawer_body.html", {"cart": cart}, request=request),
        **extra,
    }


def _back(request, fallback="cart:detail"):
    target = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(fallback)


def _quantity(request, default=1):
    try:
        return int(request.POST.get("quantity", default))
    except (TypeError, ValueError):
        return default


def cart_detail(request):
    return render(request, "cart/cart.html", {"cart": Cart(request)})


def cart_drawer(request):
    return render(request, "cart/_drawer_body.html", {"cart": Cart(request)})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product.objects.active(), pk=product_id)
    cart = Cart(request)
    if not product.in_stock:
        message = "این محصول در حال حاضر موجود نیست."
        if _wants_json(request):
            return JsonResponse({"ok": False, "message": message}, status=400)
        messages.error(request, message)
        return _back(request)

    before = cart.quantity_of(product.pk)
    after = cart.add(product, max(1, _quantity(request)))
    if after == before:
        message = "بیشتر از این تعداد از این محصول موجود نیست."
        ok = False
    else:
        message = f"«{product.name}» به سبد خرید اضافه شد."
        ok = True

    if _wants_json(request):
        return JsonResponse(_cart_payload(request, cart, ok=ok, message=message))
    (messages.success if ok else messages.warning)(request, message)
    return _back(request)


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product.objects.active(), pk=product_id)
    cart = Cart(request)
    quantity = cart.add(product, _quantity(request), replace=True)
    if _wants_json(request):
        return JsonResponse(_cart_payload(request, cart, quantity=quantity))
    return _back(request)


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    if _wants_json(request):
        return JsonResponse(_cart_payload(request, cart))
    messages.info(request, "محصول از سبد خرید حذف شد.")
    return _back(request)
