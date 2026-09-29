from unittest import mock
from urllib.parse import urlencode

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalog.models import Product
from apps.core.testing import make_address, make_product, make_user
from apps.orders.models import Order
from apps.orders.services import create_order
from apps.payments.gateways import GatewayError, get_gateway
from apps.payments.models import Payment


class FakeCart:
    """Minimal stand-in for the session cart used by ``create_order``."""

    def __init__(self, items):
        self._items = items

    def items(self):
        return self._items

    def clear(self):
        self._items = []


def make_order(user, product, quantity=2):
    from apps.cart.cart import CartItem

    return create_order(user, FakeCart([CartItem(product, quantity)]), make_address(user))


def mocked_response(payload):
    return mock.Mock(status_code=200, json=mock.Mock(return_value=payload))


@override_settings(PAYMENT_GATEWAY="fake", PAYMENT_ALLOW_FAKE_IN_PRODUCTION=True)
class FakeGatewayFlowTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(price=100000, stock=5)
        self.order = make_order(self.user, self.product)
        self.client.force_login(self.user)

    def start(self):
        response = self.client.post(reverse("payments:start", args=[self.order.number]))
        payment = self.order.payments.latest("created_at")
        return response, payment

    def callback(self, payment, status="OK", authority=None):
        query = urlencode({"authority": authority or payment.authority, "status": status})
        return self.client.get(f"{reverse('payments:callback', args=[payment.uuid])}?{query}")

    def test_successful_payment_marks_order_paid_once(self):
        response, payment = self.start()
        self.assertEqual(payment.status, Payment.Status.REDIRECTED)
        self.assertEqual(payment.amount, self.order.total)
        self.assertEqual(self.client.get(response["Location"]).status_code, 200)  # test gateway page

        response = self.callback(payment)
        self.assertContains(response, "پرداخت با موفقیت انجام شد")
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertTrue(payment.ref_id)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertIsNotNone(self.order.paid_at)
        self.assertEqual((self.product.stock, self.product.sold_count), (3, 2))

        # Refreshing the callback page must not reduce the stock again.
        self.callback(payment)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        # A paid order cannot be paid again.
        self.client.post(reverse("payments:start", args=[self.order.number]))
        self.assertEqual(self.order.payments.count(), 1)

    def test_cancelled_payment_keeps_order_pending_and_allows_retry(self):
        _, payment = self.start()
        response = self.callback(payment, status="NOK")
        self.assertContains(response, "پرداخت ناموفق بود")
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        _, retry = self.start()
        self.assertNotEqual(retry.pk, payment.pk)

    def test_tampered_authority_is_rejected(self):
        _, payment = self.start()
        self.callback(payment, authority="something-else")
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_only_owner_can_start_payment(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.post(reverse("payments:start", args=[self.order.number])).status_code, 404)

    def test_out_of_stock_order_is_not_sent_to_gateway(self):
        Product.objects.filter(pk=self.product.pk).update(stock=1)
        response = self.client.post(reverse("payments:start", args=[self.order.number]))
        self.assertRedirects(response, self.order.get_absolute_url())
        self.assertFalse(self.order.payments.exists())

    def test_network_error_during_verify_is_retryable(self):
        _, payment = self.start()
        with (
            mock.patch("apps.payments.gateways.fake.FakeGateway.verify_payment", side_effect=GatewayError("timeout")),
            self.assertLogs("apps.payments.services", "ERROR"),
        ):
            response = self.callback(payment)
        self.assertContains(response, "در انتظار تایید پرداخت")
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REDIRECTED)
        self.callback(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)


@override_settings(PAYMENT_GATEWAY="fake", PAYMENT_ALLOW_FAKE_IN_PRODUCTION=False, DEBUG=False)
class FakeGatewayDisabledInProductionTests(TestCase):
    def test_fake_gateway_is_refused(self):
        user = make_user()
        order = make_order(user, make_product(stock=5))
        self.client.force_login(user)
        response = self.client.post(reverse("payments:start", args=[order.number]))
        self.assertRedirects(response, order.get_absolute_url(), fetch_redirect_response=False)
        self.assertFalse(order.payments.exists())
        self.assertEqual(self.client.get(reverse("payments:fake_gateway", args=["abc"])).status_code, 404)


@override_settings(ZARINPAL_MERCHANT_ID="00000000-0000-0000-0000-000000000000", ZARINPAL_SANDBOX=True)
class ZarinpalTests(TestCase):
    def setUp(self):
        self.gateway = get_gateway("zarinpal")

    def test_request_success(self):
        payload = {"data": {"code": 100, "authority": "A0000000000000000000000000000abc"}, "errors": []}
        with mock.patch("requests.post", return_value=mocked_response(payload)) as post:
            result = self.gateway.request_payment(amount_rial=500000, callback_url="https://shop/cb/", description="x", mobile="09120000000", order_number="123")
        self.assertTrue(result.ok)
        self.assertEqual(result.redirect_url, "https://sandbox.zarinpal.com/pg/StartPay/A0000000000000000000000000000abc")
        sent = post.call_args.kwargs["json"]
        self.assertEqual((sent["amount"], sent["callback_url"], sent["metadata"]["mobile"]), (500000, "https://shop/cb/", "09120000000"))

    def test_request_error(self):
        payload = {"data": [], "errors": {"code": -11, "message": "inactive"}}
        with mock.patch("requests.post", return_value=mocked_response(payload)):
            result = self.gateway.request_payment(amount_rial=500000, callback_url="https://shop/cb/", description="x")
        self.assertFalse(result.ok)
        self.assertIn("مرچنت", result.message)

    def test_verify(self):
        payment = mock.Mock(authority="A1")
        payload = {"data": {"code": 100, "ref_id": 201, "card_pan": "502229******5995"}, "errors": []}
        with mock.patch("requests.post", return_value=mocked_response(payload)) as post:
            result = self.gateway.verify_payment(payment=payment, amount_rial=500000, params={"Authority": "A1", "Status": "OK"})
        self.assertTrue(result.ok)
        self.assertEqual(result.ref_id, "201")
        self.assertEqual(post.call_args.kwargs["json"]["authority"], "A1")
        cancelled = self.gateway.verify_payment(payment=payment, amount_rial=500000, params={"Authority": "A1", "Status": "NOK"})
        self.assertFalse(cancelled.ok)


@override_settings(ZIBAL_MERCHANT="zibal")
class ZibalTests(TestCase):
    def setUp(self):
        self.gateway = get_gateway("zibal")

    def test_request_and_verify(self):
        with mock.patch("requests.post", return_value=mocked_response({"result": 100, "trackId": 15966442233})):
            result = self.gateway.request_payment(amount_rial=500000, callback_url="https://shop/cb/", description="x")
        self.assertEqual(result.redirect_url, "https://gateway.zibal.ir/start/15966442233")
        payment = mock.Mock(authority=result.authority)
        verify_payload = {"result": 100, "amount": 500000, "refNumber": 1234, "cardNumber": "62741****44"}
        with mock.patch("requests.post", return_value=mocked_response(verify_payload)):
            verified = self.gateway.verify_payment(payment=payment, amount_rial=500000, params={"success": "1", "trackId": result.authority})
        self.assertTrue(verified.ok)
        self.assertEqual(verified.ref_id, "1234")

    def test_amount_mismatch_fails(self):
        payment = mock.Mock(authority="99")
        with mock.patch("requests.post", return_value=mocked_response({"result": 100, "amount": 1000})):
            result = self.gateway.verify_payment(payment=payment, amount_rial=500000, params={"success": "1", "trackId": "99"})
        self.assertFalse(result.ok)
