"""کمک‌تابع‌های کار با سبد خرید.

شناسه سبد مهمان در داده‌های سشن نگه‌داری می‌شود، نه در کلید سشن؛
چون جنگو هنگام ورود کاربر کلید سشن را از نو می‌سازد و در آن حالت
سبد مهمان گم می‌شد.
"""
from .models import Cart

CART_SESSION_KEY = "cart_id"


def get_cart(request, create=True):
    """سبد خرید کاربر جاری را برمی‌گرداند (کاربر وارد شده یا مهمان)."""
    guest_cart = _session_cart(request)

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if guest_cart is not None:
            if cart is None:
                guest_cart.user = request.user
                guest_cart.save(update_fields=["user"])
                cart = guest_cart
            elif guest_cart.pk != cart.pk:
                cart.merge_from(guest_cart)
            request.session.pop(CART_SESSION_KEY, None)
        if cart is None and create:
            cart = Cart.objects.create(user=request.user)
        return cart

    if guest_cart is None and create:
        guest_cart = Cart.objects.create(session_key=request.session.session_key or "")
        request.session[CART_SESSION_KEY] = guest_cart.pk
    return guest_cart


def _session_cart(request):
    """سبد مهمان ذخیره‌شده در سشن (در صورت وجود)."""
    cart_id = request.session.get(CART_SESSION_KEY)
    if not cart_id:
        return None
    return Cart.objects.filter(pk=cart_id, user__isnull=True).first()
