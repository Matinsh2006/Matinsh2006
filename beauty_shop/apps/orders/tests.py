from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.core.testing import make_address, make_product, make_user
from apps.orders.models import Order

NEW_ADDRESS = {
    "address": "new",
    "new-receiver_name": "سارا محمدی",
    "new-receiver_phone": "09121112233",
    "new-province": "تهران",
    "new-city": "تهران",
    "new-postal_code": "1234567890",
    "new-full_address": "خیابان آزادی",
}


@override_settings(PAYMENT_GATEWAY="fake", PAYMENT_ALLOW_FAKE_IN_PRODUCTION=True)
class CheckoutTests(TestCase):
    def setUp(self):
        site = SiteSettings.load()
        site.shipping_cost, site.free_shipping_threshold = 40000, 500000
        site.save()
        self.user = make_user()
        self.product = make_product(price=150000, discount_price=120000, stock=5)

    def add_to_cart(self, quantity=1):
        self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": quantity})

    def test_checkout_requires_login_and_items(self):
        response = self.client.get(reverse("orders:checkout"))
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("orders:checkout")), reverse("cart:detail"))

    def test_checkout_with_new_address_creates_order_and_redirects_to_gateway(self):
        self.client.force_login(self.user)
        self.add_to_cart(2)
        self.assertEqual(self.client.get(reverse("orders:checkout")).status_code, 200)
        response = self.client.post(reverse("orders:checkout"), {**NEW_ADDRESS, "note": "زنگ نزنید"})
        order = Order.objects.get()
        self.assertEqual(order.items_total, 240000)
        self.assertEqual(order.shipping_cost, 40000)
        self.assertEqual(order.total, 280000)
        self.assertEqual(order.items.get().unit_price, 120000)
        self.assertEqual(order.note, "زنگ نزنید")
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(self.user.addresses.count(), 1)
        self.assertIn("/payment/test-gateway/", response["Location"])
        self.assertEqual(self.client.session["cart"], {})

    def test_free_shipping_and_saved_address(self):
        address = make_address(self.user)
        self.client.force_login(self.user)
        self.add_to_cart(5)
        self.client.post(reverse("orders:checkout"), {"address": address.pk})
        order = Order.objects.get()
        self.assertEqual(order.shipping_cost, 0)
        self.assertEqual(order.postal_code, address.postal_code)

    def test_invalid_new_address_shows_errors(self):
        self.client.force_login(self.user)
        self.add_to_cart()
        response = self.client.post(reverse("orders:checkout"), {"address": "new", "new-city": "تهران"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["address_form"].errors)
        self.assertFalse(Order.objects.exists())

    def test_insufficient_stock_blocks_checkout(self):
        self.client.force_login(self.user)
        self.add_to_cart(3)
        self.product.stock = 1
        self.product.save()
        response = self.client.post(reverse("orders:checkout"), NEW_ADDRESS)
        self.assertRedirects(response, reverse("cart:detail"))
        self.assertFalse(Order.objects.exists())

    def test_orders_are_private(self):
        self.client.force_login(self.user)
        self.add_to_cart()
        self.client.post(reverse("orders:checkout"), NEW_ADDRESS)
        order = Order.objects.get()
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 200)
        self.assertContains(self.client.get(reverse("orders:order_list")), order.number)
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 404)
