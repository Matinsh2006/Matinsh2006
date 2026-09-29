from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import AddressForm
from apps.cart.cart import Cart
from apps.core.models import SiteSettings
from apps.payments.gateways import get_gateway
from apps.payments.services import start_payment_for_order

from .models import Order, OrderItem
from .services import CheckoutError, create_order


@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    cart = Cart(request)
    items = cart.items()
    if not items:
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:detail")
    if cart.has_unavailable_items():
        messages.error(request, "موجودی برخی از کالاهای سبد خرید کافی نیست. لطفاً تعداد آن‌ها را اصلاح کنید.")
        return redirect("cart:detail")

    user = request.user
    addresses = list(user.addresses.all())
    default_choice = str(addresses[0].pk) if addresses else "new"
    selected = request.POST.get("address") or default_choice
    is_new_address_post = request.method == "POST" and selected == "new"
    # No HTML "required" attributes: the block is hidden when a saved address is chosen.
    address_form = AddressForm(
        request.POST if is_new_address_post else None,
        prefix="new",
        initial={"receiver_name": user.get_full_name(), "receiver_phone": user.phone},
        use_required_attribute=False,
    )
    note = request.POST.get("note", "").strip()[:500]

    if request.method == "POST":
        address = None
        if selected == "new":
            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = user
                address.save()
        else:
            address = next((a for a in addresses if str(a.pk) == selected), None)
            if address is None:
                messages.error(request, "لطفاً یک آدرس برای ارسال سفارش انتخاب کنید.")
        if address is not None:
            try:
                order = create_order(user, cart, address, note)
            except CheckoutError as exc:
                messages.error(request, str(exc))
                return redirect("cart:detail")
            return start_payment_for_order(request, order)

    try:
        gateway = get_gateway()
    except ImproperlyConfigured:
        gateway = None
    subtotal = cart.subtotal()
    shipping = SiteSettings.load().shipping_cost_for(subtotal)
    context = {
        "items": items,
        "addresses": addresses,
        "selected_address": selected,
        "address_form": address_form,
        "note": note,
        "subtotal": subtotal,
        "shipping": shipping,
        "total": subtotal + shipping,
        "savings": cart.savings(),
        "gateway": gateway,
    }
    return render(request, "orders/checkout.html", context)


@login_required
def order_list(request):
    orders = request.user.orders.prefetch_related("items").order_by("-created_at")
    page_obj = Paginator(orders, 10).get_page(request.GET.get("page"))
    return render(request, "orders/order_list.html", {"page_obj": page_obj, "orders": page_obj.object_list})


@login_required
def order_detail(request, number):
    items = OrderItem.objects.select_related("product").prefetch_related("product__images")
    order = get_object_or_404(
        Order.objects.prefetch_related(Prefetch("items", queryset=items)),
        number=number,
        user=request.user,
    )
    context = {"order": order, "payments": order.payments.order_by("-created_at")}
    return render(request, "orders/order_detail.html", context)
