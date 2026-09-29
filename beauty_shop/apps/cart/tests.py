from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.testing import make_product

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


@override_settings(CART_MAX_QUANTITY_PER_ITEM=5)
class CartTests(TestCase):
    def setUp(self):
        self.product = make_product(price=100000, discount_price=80000, stock=3)

    def add(self, product=None, quantity=1, **extra):
        product = product or self.product
        return self.client.post(reverse("cart:add", args=[product.pk]), {"quantity": quantity}, **extra)

    def test_add_with_ajax_returns_count(self):
        response = self.add(quantity=2, **AJAX)
        self.assertEqual(response.json(), {"ok": True, "message": response.json()["message"], "cart_count": 2})
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 2})

    def test_quantity_is_limited_by_stock(self):
        self.add(quantity=10)
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 3)
        response = self.add(**AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_out_of_stock_and_inactive_products(self):
        soldout = make_product(stock=0)
        self.assertEqual(self.add(soldout, **AJAX).status_code, 400)
        hidden = make_product(is_active=False)
        self.assertEqual(self.add(hidden).status_code, 404)

    def test_cart_page_totals(self):
        self.add(quantity=2)
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.context["subtotal"], 160000)
        self.assertEqual(response.context["savings"], 40000)
        self.assertContains(response, self.product.name)

    def test_update_and_remove(self):
        self.add()
        self.client.post(reverse("cart:update", args=[self.product.pk]), {"quantity": "۲"})
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 2)
        self.client.post(reverse("cart:update", args=[self.product.pk]), {"quantity": 0})
        self.assertEqual(self.client.session["cart"], {})
        self.add()
        self.client.post(reverse("cart:remove", args=[self.product.pk]))
        self.assertEqual(self.client.session["cart"], {})

    def test_deactivated_product_disappears_from_cart(self):
        self.add()
        self.product.is_active = False
        self.product.save()
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.context["items"], [])
        self.assertEqual(self.client.session["cart"], {})

    def test_cart_count_in_header(self):
        self.add(quantity=2)
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.context["cart_count"], 2)
