"""
لایه‌ی درگاه پرداخت.

ساختار به‌گونه‌ای است که با تنظیم ‎PAYMENT_GATEWAY‎ در ‎.env‎ بتوان بدون
تغییر کد، از درگاه آزمایشی داخلی به درگاه واقعی (زرین‌پال) سوییچ کرد.
برای افزودن درگاه تازه کافی است از ‎BaseGateway‎ ارث‌بری کنید.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from django.conf import settings
from django.urls import reverse
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    """نتیجه‌ی درخواست پرداخت."""

    ok: bool
    redirect_url: str = ""
    authority: str = ""
    error: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class VerifyResult:
    """نتیجه‌ی تایید پرداخت پس از بازگشت از درگاه."""

    ok: bool
    ref_id: str = ""
    card_pan: str = ""
    error: str = ""
    cancelled: bool = False
    raw: dict = field(default_factory=dict)


class GatewayError(Exception):
    """خطای ارتباط با درگاه پرداخت."""


class BaseGateway:
    """رابط مشترک همه‌ی درگاه‌ها."""

    name = "base"
    label = "درگاه پرداخت"

    def __init__(self):
        self.timeout = getattr(settings, "PAYMENT_TIMEOUT", 15)
        self.currency = getattr(settings, "PAYMENT_CURRENCY", "IRT")

    def request_payment(self, payment, callback_url: str) -> RequestResult:
        """آغاز پرداخت و گرفتن نشانی انتقال کاربر به درگاه."""
        raise NotImplementedError

    def verify(self, payment, params: dict) -> VerifyResult:
        """تایید پرداخت با اطلاعات بازگشتی از درگاه."""
        raise NotImplementedError

    # ------------------------------------------------------------------ کمکی‌ها
    def amount_for_gateway(self, payment) -> int:
        """مبلغ بر حسب واحد موردنیاز درگاه (ریال یا تومان)."""
        return payment.amount if self.currency == "IRT" else payment.amount_rial

    def _post_json(self, url: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:  # pragma: no cover - وابسته به شبکه
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            try:
                return json.loads(detail)
            except json.JSONDecodeError:
                raise GatewayError(f"درگاه پرداخت خطا داد ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - وابسته به شبکه
            raise GatewayError(f"اتصال به درگاه برقرار نشد: {exc.reason}") from exc
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise GatewayError("پاسخ درگاه قابل خواندن نبود.") from exc


class SandboxGateway(BaseGateway):
    """
    درگاه آزمایشی داخلی.

    بدون نیاز به مرچنت‌کد، صفحه‌ای شبیه درگاه بانکی نشان می‌دهد تا کل
    چرخه‌ی «رزرو ← پرداخت بیعانه ← بازگشت و تایید» قابل آزمایش باشد.
    """

    name = "sandbox"
    label = "درگاه آزمایشی (تست)"

    def request_payment(self, payment, callback_url: str) -> RequestResult:
        authority = f"SBX-{payment.invoice_number}"
        url = reverse("payments:sandbox", kwargs={"invoice": payment.invoice_number})
        return RequestResult(ok=True, redirect_url=url, authority=authority, raw={"sandbox": True})

    def verify(self, payment, params: dict) -> VerifyResult:
        if params.get("result") == "cancel":
            return VerifyResult(ok=False, cancelled=True, error="پرداخت توسط کاربر لغو شد.")
        if params.get("result") != "ok":
            return VerifyResult(ok=False, error="پرداخت ناموفق بود.")
        return VerifyResult(
            ok=True,
            ref_id=params.get("ref_id") or f"TEST{payment.invoice_number}",
            card_pan="6037-****-****-1234",
            raw={"sandbox": True, **params},
        )


class ZarinPalGateway(BaseGateway):
    """
    درگاه زرین‌پال (نسخه ۴).

    برای فعال‌سازی، ‎ZARINPAL_MERCHANT_ID‎ را در ‎.env‎ قرار دهید و مقدار
    ‎PAYMENT_GATEWAY=payments.gateways.ZarinPalGateway‎ را تنظیم کنید.
    """

    name = "zarinpal"
    label = "زرین‌پال"

    @property
    def base_url(self) -> str:
        return "https://sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "https://api.zarinpal.com"

    @property
    def start_pay_url(self) -> str:
        return "https://sandbox.zarinpal.com/pg/StartPay/" if settings.ZARINPAL_SANDBOX else "https://www.zarinpal.com/pg/StartPay/"

    def _require_merchant(self):
        if not settings.ZARINPAL_MERCHANT_ID:
            raise GatewayError("مرچنت‌کد زرین‌پال تنظیم نشده است. ZARINPAL_MERCHANT_ID را در .env بگذارید.")

    def request_payment(self, payment, callback_url: str) -> RequestResult:
        try:
            self._require_merchant()
        except GatewayError as exc:
            return RequestResult(ok=False, error=str(exc))
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": self.amount_for_gateway(payment),
            "currency": self.currency,
            "callback_url": callback_url,
            "description": payment.description or f"بیعانه نوبت {payment.invoice_number}",
            "metadata": {"mobile": payment.user.phone},
        }
        try:
            response = self._post_json(f"{self.base_url}/pg/v4/payment/request.json", payload)
        except GatewayError as exc:
            return RequestResult(ok=False, error=str(exc))

        data = response.get("data") or {}
        if data.get("code") in (100, 101) and data.get("authority"):
            authority = data["authority"]
            return RequestResult(
                ok=True, authority=authority,
                redirect_url=f"{self.start_pay_url}{authority}", raw=response,
            )
        errors = response.get("errors") or {}
        message = errors.get("message") if isinstance(errors, dict) else str(errors)
        return RequestResult(ok=False, error=message or "درخواست پرداخت پذیرفته نشد.", raw=response)

    def verify(self, payment, params: dict) -> VerifyResult:
        try:
            self._require_merchant()
        except GatewayError as exc:
            return VerifyResult(ok=False, error=str(exc))
        status = (params.get("Status") or params.get("status") or "").upper()
        authority = params.get("Authority") or params.get("authority") or payment.authority
        if status != "OK":
            return VerifyResult(ok=False, cancelled=True, error="پرداخت توسط کاربر لغو شد.")

        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": self.amount_for_gateway(payment),
            "authority": authority,
        }
        try:
            response = self._post_json(f"{self.base_url}/pg/v4/payment/verify.json", payload)
        except GatewayError as exc:
            return VerifyResult(ok=False, error=str(exc))

        data = response.get("data") or {}
        # کد ۱۰۰ یعنی تایید موفق و ۱۰۱ یعنی قبلاً تایید شده است.
        if data.get("code") in (100, 101):
            return VerifyResult(
                ok=True, ref_id=str(data.get("ref_id", "")),
                card_pan=str(data.get("card_pan", "")), raw=response,
            )
        errors = response.get("errors") or {}
        message = errors.get("message") if isinstance(errors, dict) else str(errors)
        return VerifyResult(ok=False, error=message or "تایید پرداخت ناموفق بود.", raw=response)


#: نام‌های کوتاه برای تنظیم آسان در ‎.env‎
GATEWAY_ALIASES = {
    "sandbox": "payments.gateways.SandboxGateway",
    "test": "payments.gateways.SandboxGateway",
    "zarinpal": "payments.gateways.ZarinPalGateway",
}


def get_gateway() -> BaseGateway:
    """ساخت نمونه‌ی درگاه فعال بر اساس تنظیمات."""
    path = getattr(settings, "PAYMENT_GATEWAY", "payments.gateways.SandboxGateway")
    path = GATEWAY_ALIASES.get(str(path).strip().lower(), path)
    return import_string(path)()
