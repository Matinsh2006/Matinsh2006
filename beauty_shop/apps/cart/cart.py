"""Session based shopping cart: ``{product_id: quantity}`` stored in the session."""
from dataclasses import dataclass

from django.conf import settings

from apps.catalog.models import Product


@dataclass
class CartItem:
    product: Product
    quantity: int

    @property
    def unit_price(self):
        return self.product.final_price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    @property
    def original_total(self):
        return self.product.price * self.quantity

    @property
    def is_available(self):
        return self.product.stock >= self.quantity

    @property
    def max_quantity(self):
        return max(1, self.product.max_order_quantity)


class Cart:
    def __init__(self, request):
        self.session = request.session
        data = self.session.get(settings.CART_SESSION_KEY)
        self.data = data if isinstance(data, dict) else {}
        self._items = None

    def _save(self):
        self.session[settings.CART_SESSION_KEY] = self.data
        self.session.modified = True
        self._items = None

    def add(self, product, quantity=1, replace=False):
        """Add (or set, with ``replace``) a quantity; returns the resulting quantity."""
        key = str(product.pk)
        quantity = quantity if replace else self.data.get(key, 0) + quantity
        quantity = max(0, min(quantity, product.max_order_quantity))
        if quantity:
            self.data[key] = quantity
        else:
            self.data.pop(key, None)
        self._save()
        return quantity

    def remove(self, product_id):
        if self.data.pop(str(product_id), None) is not None:
            self._save()

    def clear(self):
        self.data = {}
        self._save()

    def get_quantity(self, product_id):
        return self.data.get(str(product_id), 0)

    def __len__(self):
        return sum(qty for qty in self.data.values() if isinstance(qty, int))

    def __bool__(self):
        return bool(self.data)

    def items(self):
        if self._items is None:
            ids = [int(key) for key in self.data if str(key).isdigit()]
            products = {p.pk: p for p in Product.objects.active().for_listing().filter(pk__in=ids)}
            # Drop products that were deleted or deactivated since they were added.
            stale = [key for key in self.data if not str(key).isdigit() or int(key) not in products]
            if stale:
                for key in stale:
                    self.data.pop(key, None)
                self._save()
            self._items = [CartItem(products[int(key)], qty) for key, qty in self.data.items()]
        return self._items

    def subtotal(self):
        return sum(item.total_price for item in self.items())

    def original_total(self):
        return sum(item.original_total for item in self.items())

    def savings(self):
        return self.original_total() - self.subtotal()

    def has_unavailable_items(self):
        return any(not item.is_available for item in self.items())
