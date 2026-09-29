"""
Payment gateway registry. To add a new gateway (e.g. a bank IPG), create a
subclass of ``BaseGateway`` and register its dotted path in ``GATEWAYS``.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .base import BaseGateway, GatewayError, GatewayResult

GATEWAYS = {
    "fake": "apps.payments.gateways.fake.FakeGateway",
    "zarinpal": "apps.payments.gateways.zarinpal.ZarinpalGateway",
    "zibal": "apps.payments.gateways.zibal.ZibalGateway",
}
GATEWAY_TITLES = {"fake": "درگاه آزمایشی", "zarinpal": "زرین‌پال", "zibal": "زیبال"}

__all__ = ["BaseGateway", "GatewayError", "GatewayResult", "GATEWAYS", "GATEWAY_TITLES", "get_gateway"]


def get_gateway(code=None):
    code = code or settings.PAYMENT_GATEWAY
    try:
        return import_string(GATEWAYS[code])()
    except KeyError:
        raise ImproperlyConfigured(
            f"Unknown PAYMENT_GATEWAY '{code}'. Choose one of: {', '.join(GATEWAYS)}"
        ) from None
