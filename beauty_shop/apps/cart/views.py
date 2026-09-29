from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.utils import get_safe_next_url
from apps.catalog.models import Product
from apps.core.models import SiteSettings
from apps.core.utils.text import to_latin_digits, to_persian_digits

from .cart import Cart


def _parse_quantity(value, default=1):
    try:
        return int(to_latin_digits(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def _wants_json(request):
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
    )


def _respond(request, cart, ok, message, level=None):
    if _wants_json(request):
        return JsonResponse({"ok": ok, "message": message, "cart_count": len(cart)}, status=200 if ok else 400)
    (level or (messages.success if ok else messages.error))(request, message)
    return redirect(get_safe_next_url(request, request.POST.get("next")) or "cart:detail")


def cart_detail(request):
    cart = Cart(request)
    items = cart.items()
    site = SiteSettings.load()
    subtotal = cart.subtotal()
    shipping = site.shipping_cost_for(subtotal) if items else 0
    threshold = site.free_shipping_threshold
    context = {
        "items": items,
        "subtotal": subtotal,
        "shipping": shipping,
        "total": subtotal + shipping,
        "savings": cart.savings(),
        "free_shipping_remaining": threshold - subtotal if threshold and 0 < subtotal < threshold else 0,
        "has_unavailable": cart.has_unavailable_items(),
    }
    return render(request, "cart/cart_detail.html", context)


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product.objects.active(), pk=product_id)
    if not product.in_stock:
        return _respond(request, cart, False, "این محصول در حال حاضر موجود نیست.")

    before = cart.get_quantity(product.pk)
    after = cart.add(product, max(1, _parse_quantity(request.POST.get("quantity"))))
    if after == before:
        message = f"حداکثر {to_persian_digits(after)} عدد از این محصول قابل سفارش است و در سبد شما قرار دارد."
        return _respond(request, cart, False, message)
    return _respond(request, cart, True, f"«{product.name}» به سبد خرید اضافه شد.")


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = Product.objects.active().filter(pk=product_id).first()
    quantity = _parse_quantity(request.POST.get("quantity"), default=0)
    if product is None or quantity <= 0:
        cart.remove(product_id)
        return _respond(request, cart, True, "محصول از سبد خرید حذف شد.", level=messages.info)

    result = cart.add(product, quantity, replace=True)
    if result == 0:
        return _respond(request, cart, False, f"«{product.name}» ناموجود شد و از سبد خرید حذف شد.")
    if result < quantity:
        return _respond(
            request, cart, False, f"حداکثر {to_persian_digits(result)} عدد از «{product.name}» قابل سفارش است."
        )
    return _respond(request, cart, True, "سبد خرید به‌روزرسانی شد.")


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return _respond(request, cart, True, "محصول از سبد خرید حذف شد.", level=messages.info)
