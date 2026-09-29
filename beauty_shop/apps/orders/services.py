from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.models import SiteSettings
from apps.core.utils.text import to_persian_digits

from .models import Order, OrderItem


class CheckoutError(Exception):
    """Message is shown to the customer."""


def create_order(user, cart, address, note=""):
    """Turn the cart into a pending order (prices are frozen at this moment)."""
    items = cart.items()
    if not items:
        raise CheckoutError("سبد خرید شما خالی است.")

    with transaction.atomic():
        products = Product.objects.select_for_update().in_bulk([item.product.pk for item in items])
        for item in items:
            product = products.get(item.product.pk)
            if product is None or not product.is_active:
                raise CheckoutError(f"محصول «{item.product.name}» دیگر در دسترس نیست.")
            if product.stock < item.quantity:
                raise CheckoutError(
                    f"موجودی «{product.name}» کافی نیست (موجودی فعلی: {to_persian_digits(product.stock)} عدد)."
                )

        items_total = sum(products[item.product.pk].final_price * item.quantity for item in items)
        shipping_cost = SiteSettings.load().shipping_cost_for(items_total)
        order = Order.objects.create(
            user=user,
            receiver_name=address.receiver_name,
            receiver_phone=address.receiver_phone,
            province=address.province,
            city=address.city,
            postal_code=address.postal_code,
            address=address.full_address,
            note=note,
            items_total=items_total,
            shipping_cost=shipping_cost,
            total=items_total + shipping_cost,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=products[item.product.pk],
                    product_name=products[item.product.pk].name,
                    unit_price=products[item.product.pk].final_price,
                    original_price=products[item.product.pk].price,
                    quantity=item.quantity,
                )
                for item in items
            ]
        )
    cart.clear()
    return order


def order_stock_problems(order):
    """Messages describing items that can no longer be supplied."""
    problems = []
    for item in order.items.select_related("product"):
        product = item.product
        if product is None or not product.is_active:
            problems.append(f"محصول «{item.product_name}» دیگر در دسترس نیست.")
        elif product.stock < item.quantity:
            problems.append(f"موجودی «{item.product_name}» کافی نیست.")
    return problems


def mark_order_paid(order):
    """Mark a pending order as paid and reduce stock. Must run inside a transaction."""
    if order.status != Order.Status.PENDING:
        return False
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at", "updated_at"])
    for item in order.items.all():
        if item.product_id:
            Product.objects.filter(pk=item.product_id).update(
                stock=Greatest(F("stock") - item.quantity, Value(0)),
                sold_count=F("sold_count") + item.quantity,
            )
    return True
