from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import ProductVariant
from apps.core.models import SiteSetting

from .cart import get_cart
from .forms import CheckoutForm
from .models import CartItem, Order, OrderItem


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def cart_detail(request):
    cart = get_cart(request)
    site = SiteSetting.load()
    shipping = _shipping_cost(site, cart.total_price if cart else 0)
    return render(
        request,
        "orders/cart.html",
        {"cart": cart, "shipping_cost": shipping, "grand_total": (cart.total_price if cart else 0) + shipping},
    )


def _shipping_cost(site, subtotal):
    if site.free_shipping_threshold and subtotal >= site.free_shipping_threshold:
        return 0
    return site.shipping_cost


@require_POST
def cart_add(request, variant_id):
    """افزودن یک تنوع محصول (سایز/رنگ مشخص) به سبد خرید."""
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
    quantity = max(int(request.POST.get("quantity", 1) or 1), 1)

    if variant.stock <= 0:
        message = "این سایز/رنگ موجود نیست."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": message}, status=400)
        messages.error(request, message)
        return redirect(variant.product.get_absolute_url())

    cart = get_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
    item.quantity = min((0 if created else item.quantity) + quantity, variant.stock)
    item.save()

    message = f"«{variant.product.title}» به سبد خرید اضافه شد."
    if _is_ajax(request):
        return JsonResponse(
            {"ok": True, "message": message, "items_count": cart.items_count, "total": cart.total_price}
        )
    messages.success(request, message)
    return redirect("orders:cart_detail")


@require_POST
def cart_update(request, item_id):
    cart = get_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    quantity = int(request.POST.get("quantity", 1) or 1)
    if quantity <= 0:
        item.delete()
    else:
        item.quantity = min(quantity, item.variant.stock)
        item.save(update_fields=["quantity"])
    if _is_ajax(request):
        return JsonResponse({"ok": True, "items_count": cart.items_count, "total": cart.total_price})
    return redirect("orders:cart_detail")


@require_POST
def cart_remove(request, item_id):
    cart = get_cart(request)
    get_object_or_404(CartItem, pk=item_id, cart=cart).delete()
    messages.info(request, "کالا از سبد خرید حذف شد.")
    return redirect("orders:cart_detail")


def checkout(request):
    """ثبت اطلاعات گیرنده و ساخت سفارش در انتظار پرداخت."""
    cart = get_cart(request)
    if not cart or not cart.items.exists():
        messages.warning(request, "سبد خرید شما خالی است.")
        return redirect("catalog:product_list")

    site = SiteSetting.load()
    form = CheckoutForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = form.save(commit=False)
            order.user = request.user if request.user.is_authenticated else None
            order.save()
            for item in cart.items.select_related("variant__product"):
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    product_title=item.variant.product.title,
                    variant_label=item.variant.label,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                )
            order.recalculate(shipping_cost=_shipping_cost(site, cart.total_price))
            order.save(update_fields=["items_price", "shipping_cost", "total_price"])
        return redirect("payments:start", ref_code=order.ref_code)

    shipping = _shipping_cost(site, cart.total_price)
    return render(
        request,
        "orders/checkout.html",
        {"cart": cart, "form": form, "shipping_cost": shipping, "grand_total": cart.total_price + shipping},
    )


def order_detail(request, ref_code):
    order = get_object_or_404(Order.objects.prefetch_related("items"), ref_code=ref_code)
    if order.user_id and (not request.user.is_authenticated or order.user_id != request.user.id):
        messages.error(request, "دسترسی به این سفارش ندارید.")
        return redirect("core:home")
    return render(request, "orders/order_detail.html", {"order": order})
