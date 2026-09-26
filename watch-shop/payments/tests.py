from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Address, User
from catalog.models import Brand, Category, Gender, Product
from core.models import SiteSettings
from orders.models import Order

from .gateways import GatewayError, ZarinPalGateway, ZibalGateway
from .models import Payment


def json_response(payload, status=200):
    response = mock.Mock(status_code=status)
    response.json.return_value = payload
    return response


class CheckoutTestMixin:
    def setUp(self):
        settings_obj = SiteSettings.load()
        settings_obj.shipping_cost = 100_000
        settings_obj.free_shipping_threshold = 0
        settings_obj.save()
        brand = Brand.objects.create(name="کاوه", slug="kaveh")
        sport = Category.objects.create(name="اسپرت", slug="sport")
        men = Category.objects.create(parent=sport, name="مردانه", slug="men", gender=Gender.MEN)
        self.product = Product.objects.create(name="ساعت", slug="watch", brand=brand, category=men, price=2_000_000, stock=3)
        self.user = User.objects.create_user(phone="09121234567", first_name="علی", last_name="محمدی")
        self.address = Address.objects.create(
            user=self.user,
            recipient_name="علی محمدی",
            recipient_phone="09121234567",
            province="تهران",
            city="تهران",
            postal_code="1234567890",
            address="ولیعصر",
        )
        self.client.force_login(self.user)

    def add_to_cart(self, quantity=2):
        return self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": quantity}, HTTP_ACCEPT="application/json")

    def checkout(self, gateway):
        return self.client.post(
            reverse("orders:checkout"),
            {"address": self.address.pk, "gateway": gateway, "accept_terms": "on", "note": ""},
        )


@override_settings(PAYMENT_GATEWAYS=["fake", "zarinpal", "zibal"], PAYMENT_ALLOW_FAKE=True)
class FakeGatewayFlowTests(CheckoutTestMixin, TestCase):
    def test_cart_json_api(self):
        data = self.add_to_cart(5).json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["count"], 3)  # capped by stock
        self.assertIn("drawer", data)

    def test_successful_purchase_reduces_stock_and_clears_cart(self):
        self.add_to_cart(2)
        response = self.checkout("fake")
        order = Order.objects.get()
        self.assertEqual(order.total, 4_100_000)
        self.assertEqual(order.status, Order.Status.PENDING)
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, 41_000_000)  # Rials
        self.assertTrue(response["Location"].startswith(reverse("payments:fake_gateway", args=[payment.authority])))

        page = self.client.get(response["Location"])
        self.assertContains(page, "پرداخت موفق")
        callback = self.client.get(page.context["ok_url"])
        self.assertRedirects(callback, reverse("payments:result", args=[order.number]))
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(self.product.stock, 1)
        result = self.client.get(reverse("payments:result", args=[order.number]))
        self.assertContains(result, "پرداخت با موفقیت انجام شد")
        self.assertEqual(self.client.get(reverse("cart:detail")).context["cart"].count, 0)

        # A replayed callback must not reduce stock twice.
        self.client.get(page.context["ok_url"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_canceled_payment_keeps_order_pending(self):
        self.add_to_cart(1)
        response = self.checkout("fake")
        page = self.client.get(response["Location"])
        self.client.get(page.context["cancel_url"])
        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(Payment.objects.get().status, Payment.Status.CANCELED)
        result = self.client.get(reverse("payments:result", args=[order.number]))
        self.assertContains(result, "تلاش دوباره برای پرداخت")

    def test_checkout_requires_login_and_cart(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("orders:checkout")).status_code, 302)
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("orders:checkout")), reverse("cart:detail"))

    def test_other_users_cannot_see_order(self):
        self.add_to_cart(1)
        self.checkout("fake")
        order = Order.objects.get()
        stranger = User.objects.create_user(phone="09350000000")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("payments:result", args=[order.number])).status_code, 404)


@override_settings(PAYMENT_GATEWAYS=["zarinpal"], ZARINPAL_SANDBOX=True, ZARINPAL_MERCHANT_ID="")
class ZarinPalTests(CheckoutTestMixin, TestCase):
    def test_request_and_verify(self):
        self.add_to_cart(1)
        with mock.patch("payments.gateways.requests.post", return_value=json_response({"data": {"code": 100, "authority": "A0000000000000000000000000000abc"}, "errors": []})) as post:
            response = self.checkout("zarinpal")
        self.assertEqual(response["Location"], "https://sandbox.zarinpal.com/pg/StartPay/A0000000000000000000000000000abc")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], 21_000_000)  # (2,000,000 + 100,000 shipping) × 10
        self.assertTrue(payload["callback_url"].endswith(reverse("payments:callback", args=["zarinpal"])))

        verify = json_response({"data": {"code": 100, "ref_id": 201, "card_pan": "502229******5995"}, "errors": []})
        with mock.patch("payments.gateways.requests.post", return_value=verify):
            response = self.client.get(reverse("payments:callback", args=["zarinpal"]), {"Authority": "A0000000000000000000000000000abc", "Status": "OK"})
        order = Order.objects.get()
        self.assertRedirects(response, reverse("payments:result", args=[order.number]))
        payment = Payment.objects.get()
        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertEqual(payment.ref_id, "201")
        order.refresh_from_db()
        self.assertTrue(order.is_paid)

    def test_request_error_is_reported(self):
        self.add_to_cart(1)
        error = json_response({"data": [], "errors": {"code": -9, "message": "validation error"}})
        with mock.patch("payments.gateways.requests.post", return_value=error):
            response = self.checkout("zarinpal")
        order = Order.objects.get()
        self.assertRedirects(response, order.get_absolute_url())
        self.assertEqual(Payment.objects.get().status, Payment.Status.FAILED)

    def test_failed_verification(self):
        self.add_to_cart(1)
        with mock.patch("payments.gateways.requests.post", return_value=json_response({"data": {"code": 100, "authority": "A1"}, "errors": []})):
            self.checkout("zarinpal")
        with mock.patch("payments.gateways.requests.post", return_value=json_response({"data": [], "errors": {"code": -51, "message": "failed"}})):
            self.client.get(reverse("payments:callback", args=["zarinpal"]), {"Authority": "A1", "Status": "OK"})
        self.assertEqual(Payment.objects.get().status, Payment.Status.FAILED)
        self.assertEqual(Order.objects.get().status, Order.Status.PENDING)

    def test_merchant_required_in_production(self):
        with override_settings(ZARINPAL_SANDBOX=False, ZARINPAL_MERCHANT_ID=""):
            with self.assertRaises(GatewayError):
                ZarinPalGateway()._merchant_id


@override_settings(PAYMENT_GATEWAYS=["zibal"], ZIBAL_MERCHANT="zibal")
class ZibalTests(CheckoutTestMixin, TestCase):
    def test_request_and_verify(self):
        self.add_to_cart(1)
        with mock.patch("payments.gateways.requests.post", return_value=json_response({"result": 100, "trackId": 15966442})):
            response = self.checkout("zibal")
        self.assertEqual(response["Location"], "https://gateway.zibal.ir/start/15966442")
        verify = json_response({"result": 100, "refNumber": 39432, "amount": 21_000_000, "cardNumber": "62741****44"})
        with mock.patch("payments.gateways.requests.post", return_value=verify):
            self.client.get(reverse("payments:callback", args=["zibal"]), {"trackId": "15966442", "success": "1", "status": "2"})
        self.assertEqual(Payment.objects.get().status, Payment.Status.PAID)

    def test_amount_mismatch_is_rejected(self):
        self.add_to_cart(1)
        with mock.patch("payments.gateways.requests.post", return_value=json_response({"result": 100, "trackId": 1})):
            self.checkout("zibal")
        verify = json_response({"result": 100, "refNumber": 1, "amount": 1000})
        with mock.patch("payments.gateways.requests.post", return_value=verify):
            self.client.get(reverse("payments:callback", args=["zibal"]), {"trackId": "1", "success": "1"})
        self.assertEqual(Payment.objects.get().status, Payment.Status.FAILED)
        self.assertEqual(ZibalGateway.code, "zibal")


@override_settings(PAYMENT_ALLOW_FAKE=False)
class SecurityTests(TestCase):
    def test_fake_gateway_disabled_in_production(self):
        self.assertEqual(self.client.get(reverse("payments:callback", args=["fake"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("payments:fake_gateway", args=["abc"])).status_code, 404)

    def test_unknown_authority(self):
        response = self.client.get(reverse("payments:callback", args=["zarinpal"]), {"Authority": "nope", "Status": "OK"})
        self.assertEqual(response.status_code, 404)
