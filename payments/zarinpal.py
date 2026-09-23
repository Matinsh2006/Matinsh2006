"""Minimal client for ZarinPal's v4 REST payment API
(see https://www.zarinpal.com/docs/paymentGateway/ for the latest reference).

Amounts are always sent/read as Toman (currency="IRT") to match the Toman
prices used elsewhere in the project (Service.price, Service.deposit_amount).

This is deliberately the "foundation" the client asked for: it works
end-to-end against the ZarinPal sandbox with no account needed, but you must
set a real ZARINPAL_MERCHANT_ID (from a verified zarinpal.com merchant
account) and ZARINPAL_SANDBOX=False before accepting real payments - and
it's worth diffing this file against ZarinPal's current docs at that point,
since payment gateway APIs do change over time.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ZarinPalError(Exception):
    """Raised for any failure talking to ZarinPal; message is safe to show."""


def _api_base_url():
    if settings.ZARINPAL_SANDBOX:
        return "https://sandbox.zarinpal.com"
    return "https://payment.zarinpal.com"


def _pay_base_url():
    if settings.ZARINPAL_SANDBOX:
        return "https://sandbox.zarinpal.com"
    return "https://www.zarinpal.com"


def _post(path, payload):
    url = f"{_api_base_url()}{path}"
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.exception("ZarinPal request to %s failed", path)
        raise ZarinPalError("ارتباط با درگاه پرداخت زرین‌پال برقرار نشد.") from exc


def request_payment(amount, description, callback_url, mobile=""):
    """Ask ZarinPal to start a payment. Returns (authority, pay_url)."""
    payload = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": amount,
        "currency": "IRT",
        "description": description,
        "callback_url": callback_url,
    }
    if mobile:
        payload["metadata"] = {"mobile": mobile}

    body = _post("/pg/v4/payment/request.json", payload)
    data = body.get("data") or {}
    if not data or data.get("code") != 100:
        errors = body.get("errors") or data.get("errors") or "خطای نامشخص از درگاه پرداخت"
        logger.error("ZarinPal payment request rejected: %s", errors)
        raise ZarinPalError(f"درخواست پرداخت پذیرفته نشد: {errors}")

    authority = data["authority"]
    pay_url = f"{_pay_base_url()}/pg/StartPay/{authority}"
    return authority, pay_url


def verify_payment(amount, authority):
    """Confirm a completed payment with ZarinPal. Returns (ref_id, card_pan)."""
    payload = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": amount,
        "currency": "IRT",
        "authority": authority,
    }
    body = _post("/pg/v4/payment/verify.json", payload)
    data = body.get("data") or {}
    # code 100 = verified just now, 101 = was already verified earlier
    if data.get("code") not in (100, 101):
        errors = body.get("errors") or "پرداخت تایید نشد"
        logger.error("ZarinPal verification rejected: %s", errors)
        raise ZarinPalError(f"پرداخت تایید نشد: {errors}")

    return data.get("ref_id"), data.get("card_pan")
