"""
Online payment gateways.

Every gateway implements the same three-step flow:

1. ``request()``  – register the payment and get the URL of the bank page;
2. the customer pays and the gateway redirects back to our callback URL;
3. ``verify()``   – server-to-server confirmation; only this marks an order paid.

Amounts are always sent in **Rials** (prices are stored in Toman × 10).
Add a new gateway by subclassing :class:`BaseGateway` and registering it in
``GATEWAY_CLASSES``.
"""
import logging
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    pass


@dataclass
class PaymentRequest:
    authority: str
    redirect_url: str
    raw: dict = field(default_factory=dict)


@dataclass
class VerifyResult:
    success: bool
    ref_id: str = ""
    card_pan: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict)


class BaseGateway:
    code = ""
    title = ""
    description = ""

    def request(self, payment, callback_url, *, description="", mobile="") -> PaymentRequest:
        raise NotImplementedError

    def authority_from_callback(self, request) -> str:
        raise NotImplementedError

    def callback_is_ok(self, request) -> bool:
        raise NotImplementedError

    def verify(self, payment, request) -> VerifyResult:
        raise NotImplementedError

    def _post(self, url, payload):
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=settings.PAYMENT_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.error("%s: connection error: %s", self.code, exc)
            raise GatewayError("ارتباط با درگاه پرداخت برقرار نشد. لطفاً دوباره تلاش کنید.") from exc
        try:
            return response.json()
        except ValueError as exc:
            logger.error("%s: invalid response (HTTP %s)", self.code, response.status_code)
            raise GatewayError("پاسخ نامعتبر از درگاه پرداخت دریافت شد.") from exc


# ---------------------------------------------------------------------------
# ZarinPal (REST v4) — https://www.zarinpal.com/docs/paymentGateway/
# ---------------------------------------------------------------------------
ZARINPAL_ERRORS = {
    -9: "اطلاعات ارسال‌شده به درگاه نامعتبر است.",
    -10: "آی‌پی یا مرچنت کد پذیرنده صحیح نیست.",
    -11: "مرچنت کد فعال نیست.",
    -12: "تلاش بیش از حد در یک بازه زمانی کوتاه.",
    -15: "درگاه پرداخت به حالت تعلیق درآمده است.",
    -16: "سطح تایید پذیرنده پایین‌تر از سطح نقره‌ای است.",
    -50: "مبلغ پرداخت‌شده با مبلغ تراکنش مغایرت دارد.",
    -51: "پرداخت ناموفق بود.",
    -52: "خطای غیرمنتظره در درگاه؛ با پشتیبانی تماس بگیرید.",
    -53: "این تراکنش متعلق به این پذیرنده نیست.",
    -54: "شناسه تراکنش (Authority) نامعتبر است.",
}


class ZarinPalGateway(BaseGateway):
    code = "zarinpal"
    title = "زرین‌پال"
    description = "پرداخت با تمام کارت‌های عضو شتاب"

    @property
    def _host(self):
        return "sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "payment.zarinpal.com"

    @property
    def _merchant_id(self):
        merchant = settings.ZARINPAL_MERCHANT_ID
        if not merchant:
            if settings.ZARINPAL_SANDBOX:
                # The sandbox accepts any 36 character UUID-like merchant id.
                return "1344b5d4-0048-11e8-94db-005056a205be"
            raise GatewayError("مرچنت کد زرین‌پال تنظیم نشده است.")
        return merchant

    @staticmethod
    def _error(data):
        errors = data.get("errors") or {}
        code = errors.get("code") if isinstance(errors, dict) else None
        return ZARINPAL_ERRORS.get(code) or (errors.get("message") if isinstance(errors, dict) else "") or "خطای درگاه زرین‌پال"

    def request(self, payment, callback_url, *, description="", mobile=""):
        payload = {
            "merchant_id": self._merchant_id,
            "amount": payment.amount,
            "callback_url": callback_url,
            "description": description or f"سفارش {payment.order.number}",
            "metadata": {"mobile": mobile, "order_id": payment.order.number} if mobile else {"order_id": payment.order.number},
        }
        data = self._post(f"https://{self._host}/pg/v4/payment/request.json", payload)
        result = data.get("data") or {}
        if isinstance(result, dict) and result.get("code") == 100 and result.get("authority"):
            authority = result["authority"]
            return PaymentRequest(authority, f"https://{self._host}/pg/StartPay/{authority}", data)
        raise GatewayError(self._error(data))

    def authority_from_callback(self, request):
        return request.GET.get("Authority", "")

    def callback_is_ok(self, request):
        return request.GET.get("Status") == "OK"

    def verify(self, payment, request):
        data = self._post(
            f"https://{self._host}/pg/v4/payment/verify.json",
            {"merchant_id": self._merchant_id, "amount": payment.amount, "authority": payment.authority},
        )
        result = data.get("data") or {}
        if isinstance(result, dict) and result.get("code") in (100, 101):
            return VerifyResult(True, str(result.get("ref_id", "")), result.get("card_pan", ""), raw=data)
        return VerifyResult(False, message=self._error(data), raw=data)


# ---------------------------------------------------------------------------
# Zibal — https://help.zibal.ir/IPG/API/
# ---------------------------------------------------------------------------
ZIBAL_RESULTS = {
    102: "مرچنت کد یافت نشد.",
    103: "مرچنت کد غیرفعال است.",
    104: "مرچنت کد نامعتبر است.",
    105: "مبلغ باید بیشتر از ۱۰۰۰ ریال باشد.",
    106: "آدرس بازگشت نامعتبر است.",
    113: "مبلغ تراکنش از سقف مجاز بیشتر است.",
    202: "سفارش پرداخت نشده یا ناموفق بوده است.",
    203: "شناسه تراکنش نامعتبر است.",
}


class ZibalGateway(BaseGateway):
    code = "zibal"
    title = "زیبال"
    description = "درگاه پرداخت امن زیبال"
    request_url = "https://gateway.zibal.ir/v1/request"
    verify_url = "https://gateway.zibal.ir/v1/verify"
    start_url = "https://gateway.zibal.ir/start/{track_id}"

    def request(self, payment, callback_url, *, description="", mobile=""):
        payload = {
            "merchant": settings.ZIBAL_MERCHANT,
            "amount": payment.amount,
            "callbackUrl": callback_url,
            "orderId": f"{payment.order.number}-{payment.pk}",
            "description": description or f"سفارش {payment.order.number}",
        }
        if mobile:
            payload["mobile"] = mobile
        data = self._post(self.request_url, payload)
        if data.get("result") == 100 and data.get("trackId"):
            track_id = str(data["trackId"])
            return PaymentRequest(track_id, self.start_url.format(track_id=track_id), data)
        raise GatewayError(ZIBAL_RESULTS.get(data.get("result")) or data.get("message") or "خطای درگاه زیبال")

    def authority_from_callback(self, request):
        return request.GET.get("trackId", "")

    def callback_is_ok(self, request):
        return request.GET.get("success") == "1"

    def verify(self, payment, request):
        try:
            track_id = int(payment.authority)
        except ValueError:
            return VerifyResult(False, message="شناسه تراکنش نامعتبر است.")
        data = self._post(self.verify_url, {"merchant": settings.ZIBAL_MERCHANT, "trackId": track_id})
        if data.get("result") in (100, 201):
            if data.get("amount") not in (None, payment.amount):
                return VerifyResult(False, message="مبلغ پرداخت‌شده با مبلغ سفارش مغایرت دارد.", raw=data)
            return VerifyResult(True, str(data.get("refNumber", "")), data.get("cardNumber", ""), raw=data)
        return VerifyResult(False, message=ZIBAL_RESULTS.get(data.get("result")) or data.get("message", ""), raw=data)


# ---------------------------------------------------------------------------
# Test gateway (development only)
# ---------------------------------------------------------------------------
class FakeGateway(BaseGateway):
    """Simulates a bank page locally so the whole purchase flow can be tested."""

    code = "fake"
    title = "درگاه آزمایشی"
    description = "فقط برای تست؛ هیچ مبلغی کسر نمی‌شود"

    def request(self, payment, callback_url, *, description="", mobile=""):
        authority = uuid.uuid4().hex
        url = reverse("payments:fake_gateway", args=[authority]) + "?" + urlencode({"callback": callback_url})
        return PaymentRequest(authority, url, {"authority": authority})

    def authority_from_callback(self, request):
        return request.GET.get("authority", "")

    def callback_is_ok(self, request):
        return request.GET.get("status") == "ok"

    def verify(self, payment, request):
        if self.callback_is_ok(request):
            return VerifyResult(True, ref_id=str(uuid.uuid4().int)[:12], card_pan="603799******1234")
        return VerifyResult(False, message="پرداخت آزمایشی لغو شد.")


GATEWAY_CLASSES = {
    ZarinPalGateway.code: ZarinPalGateway,
    ZibalGateway.code: ZibalGateway,
    FakeGateway.code: FakeGateway,
}
GATEWAY_TITLES = {code: cls.title for code, cls in GATEWAY_CLASSES.items()}


def enabled_gateways():
    gateways = []
    for code in settings.PAYMENT_GATEWAYS:
        gateway_class = GATEWAY_CLASSES.get(code)
        if gateway_class is None:
            continue
        if code == FakeGateway.code and not settings.PAYMENT_ALLOW_FAKE:
            continue
        gateways.append(gateway_class())
    return gateways


def get_gateway(code):
    for gateway in enabled_gateways():
        if gateway.code == code:
            return gateway
    raise GatewayError("درگاه پرداخت انتخاب‌شده فعال نیست.")
