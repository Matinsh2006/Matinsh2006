from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Color, Gender, Product, ProductKind, ProductVariant, Size
from apps.core.models import SiteSetting
from apps.orders.models import Order, OrderStatus
from apps.payments.models import Payment, PaymentStatus


class PaymentFlowTests(TestCase):
    def setUp(self):
        site = SiteSetting.load()
        site.shipping_cost = 0
        site.save()
        category = Category.objects.create(name="مانتو", gender=Gender.WOMEN)
        size = Size.objects.create(label="M", size_type=ProductKind.CLOTHING)
        color = Color.objects.create(name="مشکی", hex_code="#000000")
        product = Product.objects.create(title="مانتو کتان", category=category, price=1_000_000)
        self.variant = ProductVariant.objects.create(
            product=product, size=size, color=color, stock=5
        )
        self.client.post(reverse("orders:cart_add", args=[self.variant.pk]), {"quantity": 2})
        self.client.post(
            reverse("orders:checkout"),
            {"full_name": "مریم", "phone": "09121234567", "city": "تهران", "address": "خیابان آزادی"},
        )
        self.order = Order.objects.get()

    def test_start_creates_payment_and_redirects_to_gateway(self):
        response = self.client.get(reverse("payments:start", args=[self.order.ref_code]))
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, self.order.total_price)
        self.assertEqual(payment.status, PaymentStatus.REDIRECTED)
        self.assertRedirects(response, reverse("payments:sandbox", args=[payment.pk]))

    def test_successful_callback_marks_order_paid_and_reduces_stock(self):
        self.client.get(reverse("payments:start", args=[self.order.ref_code]))
        payment = Payment.objects.get()
        self.client.get(reverse("payments:callback", args=[payment.pk]), {"status": "OK"})

        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.SUCCESS)
        self.assertTrue(payment.ref_id)
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertIsNotNone(self.order.paid_at)
        self.assertEqual(self.variant.stock, 3)

    def test_canceled_callback_keeps_order_pending(self):
        self.client.get(reverse("payments:start", args=[self.order.ref_code]))
        payment = Payment.objects.get()
        self.client.get(reverse("payments:callback", args=[payment.pk]), {"status": "NOK"})

        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CANCELED)
        self.assertEqual(self.order.status, OrderStatus.PENDING)
        self.assertEqual(self.variant.stock, 5)

    def test_cart_emptied_after_successful_payment(self):
        self.client.get(reverse("payments:start", args=[self.order.ref_code]))
        payment = Payment.objects.get()
        self.client.get(reverse("payments:callback", args=[payment.pk]), {"status": "OK"})
        response = self.client.get(reverse("orders:cart_detail"))
        self.assertEqual(response.context["cart"].items_count, 0)

    def test_double_callback_does_not_double_reduce_stock(self):
        self.client.get(reverse("payments:start", args=[self.order.ref_code]))
        payment = Payment.objects.get()
        self.client.get(reverse("payments:callback", args=[payment.pk]), {"status": "OK"})
        self.client.get(reverse("payments:callback", args=[payment.pk]), {"status": "OK"})
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)

    def test_paid_order_cannot_start_new_payment(self):
        self.order.status = OrderStatus.PAID
        self.order.save()
        response = self.client.get(reverse("payments:start", args=[self.order.ref_code]))
        self.assertRedirects(response, reverse("orders:order_detail", args=[self.order.ref_code]))
        self.assertFalse(Payment.objects.exists())

    def test_result_page_renders(self):
        self.client.get(reverse("payments:start", args=[self.order.ref_code]))
        payment = Payment.objects.get()
        self.client.get(reverse("payments:callback", args=[payment.pk]), {"status": "OK"})
        response = self.client.get(reverse("payments:result", args=[self.order.ref_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پرداخت با موفقیت انجام شد")
