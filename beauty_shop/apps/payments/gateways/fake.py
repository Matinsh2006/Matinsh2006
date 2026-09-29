"""
Built-in test gateway: shows a local page with "successful" and "cancel" buttons.

It lets you test the whole checkout flow without a merchant account. It is
disabled automatically when ``DEBUG=False`` (unless explicitly allowed).
"""
import secrets

from django.conf import settings
from django.urls import reverse

from .base import BaseGateway, GatewayResult


def fake_gateway_allowed():
    return settings.DEBUG or settings.PAYMENT_ALLOW_FAKE_IN_PRODUCTION


class FakeGateway(BaseGateway):
    code = "fake"
    title = "درگاه آزمایشی"

    def is_available(self):
        return fake_gateway_allowed()

    def request_payment(self, *, amount_rial, callback_url, description, mobile="", order_number=""):
        authority = secrets.token_urlsafe(16)
        return GatewayResult(
            ok=True,
            authority=authority,
            redirect_url=reverse("payments:fake_gateway", kwargs={"authority": authority}),
            raw={"amount": amount_rial, "description": description},
        )

    def get_callback_authority(self, params):
        return params.get("authority", "")

    def verify_payment(self, *, payment, amount_rial, params):
        if not fake_gateway_allowed():
            return GatewayResult(ok=False, message="درگاه آزمایشی غیرفعال است.")
        if params.get("status") != "OK":
            return GatewayResult(ok=False, message="پرداخت توسط شما لغو شد.", raw=dict(params.items()))
        return GatewayResult(
            ok=True,
            ref_id=str(10**9 + secrets.randbelow(9 * 10**9)),
            card_pan="603799******1234",
            raw=dict(params.items()),
        )
