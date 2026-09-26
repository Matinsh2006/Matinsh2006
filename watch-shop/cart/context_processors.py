from django.utils.functional import SimpleLazyObject

from .cart import Cart


def cart(request):
    return {"cart": SimpleLazyObject(lambda: Cart(request))}
