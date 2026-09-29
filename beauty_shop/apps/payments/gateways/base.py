from dataclasses import dataclass, field

import requests
from django.conf import settings


class GatewayError(Exception):
    """The gateway could not be reached or returned an unreadable response."""


@dataclass
class GatewayResult:
    ok: bool
    message: str = ""
    authority: str = ""
    redirect_url: str = ""
    ref_id: str = ""
    card_pan: str = ""
    raw: dict = field(default_factory=dict)


class BaseGateway:
    """
    Interface of an online payment gateway.

    Amounts are passed in **Rial** (prices in the shop are stored in Toman).
    """

    code = ""
    title = ""

    def is_available(self):
        return True

    def request_payment(self, *, amount_rial, callback_url, description, mobile="", order_number=""):
        """Register the transaction and return a ``GatewayResult`` with ``redirect_url``."""
        raise NotImplementedError

    def get_callback_authority(self, params):
        """Extract the transaction id the gateway sends back to the callback URL."""
        raise NotImplementedError

    def verify_payment(self, *, payment, amount_rial, params):
        """Confirm the payment with the gateway (server to server)."""
        raise NotImplementedError

    def _post(self, url, payload):
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=settings.PAYMENT_REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise GatewayError(f"{self.code}: connection failed: {exc}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise GatewayError(f"{self.code}: invalid response (HTTP {response.status_code})") from exc
