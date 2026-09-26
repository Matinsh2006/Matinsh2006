"""Session based shopping cart."""
from dataclasses import dataclass
from functools import cached_property

from catalog.models import Product
from core.models import SiteSettings

CART_SESSION_KEY = "cart"
MAX_QUANTITY_PER_ITEM = 10


@dataclass
class CartLine:
    product: Product
    quantity: int

    @property
    def unit_price(self):
        return self.product.price

    @property
    def total(self):
        return self.product.price * self.quantity

    @property
    def max_quantity(self):
        return min(self.product.stock, MAX_QUANTITY_PER_ITEM)


class Cart:
    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(CART_SESSION_KEY)
        self.data = {str(k): int(v) for k, v in raw.items()} if isinstance(raw, dict) else {}

    # -- mutations -----------------------------------------------------------
    def add(self, product, quantity=1, replace=False):
        """Add ``quantity`` of ``product`` (or set it with ``replace``).

        Returns the resulting quantity (capped by stock).
        """
        key = str(product.pk)
        current = 0 if replace else self.data.get(key, 0)
        limit = min(product.stock, MAX_QUANTITY_PER_ITEM)
        new_quantity = max(0, min(current + int(quantity), limit))
        if new_quantity:
            self.data[key] = new_quantity
        else:
            self.data.pop(key, None)
        self._save()
        return new_quantity

    def remove(self, product_id):
        self.data.pop(str(product_id), None)
        self._save()

    def clear(self):
        self.data = {}
        self.session.pop(CART_SESSION_KEY, None)
        self.session.modified = True
        self.__dict__.pop("lines", None)

    def _save(self):
        self.session[CART_SESSION_KEY] = self.data
        self.session.modified = True
        self.__dict__.pop("lines", None)

    # -- reading ---------------------------------------------------------------
    @cached_property
    def lines(self):
        if not self.data:
            return []
        products = Product.objects.active().with_related().in_bulk([int(pk) for pk in self.data if pk.isdigit()])
        lines = []
        for key, quantity in self.data.items():
            product = products.get(int(key)) if key.isdigit() else None
            if product and quantity > 0:
                lines.append(CartLine(product=product, quantity=quantity))
        return lines

    def __iter__(self):
        return iter(self.lines)

    def __len__(self):
        return sum(self.data.values())

    def __bool__(self):
        return bool(self.lines)

    def quantity_of(self, product_id):
        return self.data.get(str(product_id), 0)

    @property
    def count(self):
        return sum(line.quantity for line in self.lines)

    @property
    def subtotal(self):
        return sum(line.total for line in self.lines)

    @property
    def savings(self):
        return sum(
            (line.product.compare_at_price - line.product.price) * line.quantity
            for line in self.lines
            if line.product.compare_at_price and line.product.compare_at_price > line.product.price
        )

    @cached_property
    def _settings(self):
        return SiteSettings.load()

    @property
    def shipping_cost(self):
        if not self.lines:
            return 0
        threshold = self._settings.free_shipping_threshold
        if threshold and self.subtotal >= threshold:
            return 0
        return self._settings.shipping_cost

    @property
    def free_shipping_remaining(self):
        threshold = self._settings.free_shipping_threshold
        if not threshold:
            return 0
        return max(0, threshold - self.subtotal)

    @property
    def free_shipping_progress(self):
        threshold = self._settings.free_shipping_threshold
        if not threshold:
            return 100
        return min(100, round(self.subtotal * 100 / threshold))

    @property
    def total(self):
        return self.subtotal + self.shipping_cost

    def stock_problems(self):
        """Lines whose quantity is no longer available."""
        return [line for line in self.lines if line.quantity > line.product.stock]
