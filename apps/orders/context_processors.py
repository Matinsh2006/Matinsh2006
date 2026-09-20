from .cart import get_cart


def cart_summary(request):
    """تعداد و مبلغ سبد خرید برای نمایش در هدر."""
    try:
        cart = get_cart(request, create=False)
    except Exception:  # pragma: no cover - قبل از اجرای مهاجرت‌ها
        cart = None
    return {
        "cart_items_count": cart.items_count if cart else 0,
        "cart_total_price": cart.total_price if cart else 0,
    }
