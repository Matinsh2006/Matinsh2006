from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cart.cart import Cart
from payments.gateways import enabled_gateways
from payments.services import start_payment

from .forms import CheckoutForm
from .models import Order, OrderItem


@login_required
def checkout(request):
    cart = Cart(request)
    if not cart:
        messages.info(request, "سبد خرید شما خالی است.")
        return redirect("cart:detail")

    gateways = enabled_gateways()
    form = CheckoutForm(request.user, request.POST or None, gateways=gateways)
    if request.method == "POST" and form.is_valid():
        problems = cart.stock_problems()
        if problems:
            for line in problems:
                cart.add(line.product, line.product.stock, replace=True)
            messages.error(request, "موجودی برخی کالاها تغییر کرده و سبد خرید به‌روزرسانی شد. لطفاً دوباره بررسی کنید.")
            return redirect("cart:detail")

        address = form.cleaned_data["address"]
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                recipient_name=address.recipient_name,
                recipient_phone=address.recipient_phone,
                province=address.province,
                city=address.city,
                postal_code=address.postal_code,
                address=address.full_address,
                note=form.cleaned_data["note"],
                subtotal=cart.subtotal,
                shipping_cost=cart.shipping_cost,
                total=cart.total,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=line.product,
                        product_name=line.product.name,
                        product_sku=line.product.sku or "",
                        unit_price=line.product.price,
                        quantity=line.quantity,
                    )
                    for line in cart
                ]
            )
        return start_payment(request, order, form.cleaned_data["gateway"])

    return render(
        request,
        "orders/checkout.html",
        {"cart": cart, "form": form, "addresses": request.user.addresses.all(), "gateways": gateways},
    )


@login_required
def order_list(request):
    orders = request.user.orders.prefetch_related("items__product__images")
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product__images", "payments"), number=number, user=request.user
    )
    return render(request, "orders/order_detail.html", {"order": order, "gateways": enabled_gateways()})
