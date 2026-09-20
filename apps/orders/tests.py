from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Category, Color, Gender, Product, ProductKind, ProductVariant, Size
from apps.core.models import SiteSetting
from apps.orders.models import Cart, Order, OrderStatus


class CartTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="مانتو", gender=Gender.WOMEN)
        size = Size.objects.create(label="M", size_type=ProductKind.CLOTHING)
        color = Color.objects.create(name="مشکی", hex_code="#000000")
        cls.product = Product.objects.create(title="مانتو کتان", category=category, price=1_000_000)
        cls.variant = ProductVariant.objects.create(
            product=cls.product, size=size, color=color, stock=5
        )
        cls.empty_variant = ProductVariant.objects.create(
            product=cls.product, size=Size.objects.create(label="L", size_type=ProductKind.CLOTHING),
            color=color, stock=0,
        )


class CartViewTests(CartTestData):
    def test_add_to_cart_as_guest(self):
        self.client.post(reverse("orders:cart_add", args=[self.variant.pk]), {"quantity": 2})
        cart = Cart.objects.get()
        self.assertEqual(cart.items_count, 2)
        self.assertEqual(cart.total_price, 2_000_000)

    def test_quantity_capped_at_stock(self):
        self.client.post(reverse("orders:cart_add", args=[self.variant.pk]), {"quantity": 99})
        self.assertEqual(Cart.objects.get().items_count, 5)

    def test_out_of_stock_rejected(self):
        self.client.post(reverse("orders:cart_add", args=[self.empty_variant.pk]), {"quantity": 1})
        self.assertFalse(Cart.objects.filter(items__isnull=False).exists())

    def test_ajax_add_returns_json(self):
        response = self.client.post(
            reverse("orders:cart_add", args=[self.variant.pk]),
            {"quantity": 1},
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["items_count"], 1)

    def test_remove_item(self):
        self.client.post(reverse("orders:cart_add", args=[self.variant.pk]), {"quantity": 1})
        item = Cart.objects.get().items.first()
        self.client.post(reverse("orders:cart_remove", args=[item.pk]))
        self.assertEqual(Cart.objects.get().items_count, 0)

    def test_guest_cart_merges_after_login(self):
        self.client.post(reverse("orders:cart_add", args=[self.variant.pk]), {"quantity": 2})
        user = User.objects.create_user(phone="09121234567")
        self.client.force_login(user)
        self.client.get(reverse("orders:cart_detail"))
        self.assertEqual(Cart.objects.filter(user=user).get().items_count, 2)


class CheckoutTests(CartTestData):
    def setUp(self):
        site = SiteSetting.load()
        site.shipping_cost = 50_000
        site.free_shipping_threshold = 0
        site.save()
        self.client.post(reverse("orders:cart_add", args=[self.variant.pk]), {"quantity": 2})

    def test_checkout_creates_pending_order(self):
        response = self.client.post(
            reverse("orders:checkout"),
            {
                "full_name": "مریم احمدی",
                "phone": "09121234567",
                "province": "تهران",
                "city": "تهران",
                "address": "خیابان آزادی",
                "postal_code": "1234567890",
                "note": "",
            },
        )
        order = Order.objects.get()
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.items_price, 2_000_000)
        self.assertEqual(order.shipping_cost, 50_000)
        self.assertEqual(order.total_price, 2_050_000)
        self.assertEqual(order.items.count(), 1)
        self.assertRedirects(
            response, reverse("payments:start", args=[order.ref_code]), target_status_code=302
        )

    def test_free_shipping_threshold(self):
        site = SiteSetting.load()
        site.free_shipping_threshold = 1_000_000
        site.save()
        self.client.post(
            reverse("orders:checkout"),
            {"full_name": "مریم", "phone": "09121234567", "city": "تهران", "address": "خیابان آزادی"},
        )
        self.assertEqual(Order.objects.get().shipping_cost, 0)

    def test_empty_cart_redirects(self):
        Cart.objects.all().delete()
        response = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(response, reverse("catalog:product_list"))

    def test_invalid_phone_rejected(self):
        response = self.client.post(
            reverse("orders:checkout"),
            {"full_name": "مریم", "phone": "12345", "city": "تهران", "address": "خیابان آزادی"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
