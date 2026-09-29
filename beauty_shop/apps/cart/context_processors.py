from .cart import Cart


def cart(request):
    if not hasattr(request, "session"):
        return {}
    return {"cart_count": len(Cart(request))}
