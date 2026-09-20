"""مقدمات درگاه پرداخت.

معماری به‌گونه‌ای است که با تعریف یک کلاس جدید و افزودن آن به GATEWAYS،
هر درگاه ایرانی (زرین‌پال، آیدی‌پی، پی‌پینگ و ...) قابل اتصال است.
حالت پیش‌فرض «dummy» یک درگاه شبیه‌سازی‌شده داخلی برای دموست.
"""
import json
import logging
import urllib.request
from dataclasses import dataclass, field

from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


@dataclass
class GatewayResult:
    success: bool
    redirect_url: str = ""
    authority: str = ""
    ref_id: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict)


class BaseGateway:
    name = "base"

    def __init__(self, request=None):
        self.request = request

    def callback_url(self, payment):
        path = reverse("payments:callback", args=[payment.pk])
        if self.request is not None:
            return self.request.build_absolute_uri(path)
        return path

    def start(self, payment) -> GatewayResult:  # pragma: no cover - رابط
        raise NotImplementedError

    def verify(self, payment, data) -> GatewayResult:  # pragma: no cover - رابط
        raise NotImplementedError


class DummyGateway(BaseGateway):
    """درگاه شبیه‌سازی‌شده برای توسعه و دمو (بدون تراکنش واقعی)."""

    name = "dummy"

    def start(self, payment):
        authority = f"DEMO-{payment.pk:08d}"
        return GatewayResult(
            success=True,
            authority=authority,
            redirect_url=reverse("payments:sandbox", args=[payment.pk]),
            message="هدایت به درگاه آزمایشی",
        )

    def verify(self, payment, data):
        if data.get("status") == "OK":
            return GatewayResult(
                success=True, ref_id=f"DEMO{payment.pk}{payment.amount % 10000}", message="پرداخت آزمایشی موفق"
            )
        return GatewayResult(success=False, message="پرداخت توسط کاربر لغو شد.")


class ZarinpalGateway(BaseGateway):
    """اتصال به زرین‌پال (مبالغ به ریال ارسال می‌شوند)."""

    name = "zarinpal"

    @property
    def base_url(self):
        return (
            "https://sandbox.zarinpal.com/pg/"
            if settings.ZARINPAL_SANDBOX
            else "https://payment.zarinpal.com/pg/"
        )

    def _post(self, url, payload):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def start(self, payment):
        if not settings.ZARINPAL_MERCHANT_ID:
            return GatewayResult(success=False, message="شناسه پذیرنده (Merchant ID) تنظیم نشده است.")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": payment.amount * 10,  # تومان → ریال
            "callback_url": self.callback_url(payment),
            "description": f"پرداخت سفارش {payment.order.ref_code}",
            "metadata": {"mobile": payment.order.phone},
        }
        try:
            data = self._post(self.base_url + "v4/payment/request.json", payload)
        except Exception as exc:  # pragma: no cover - وابسته به شبکه
            logger.exception("خطا در اتصال به زرین‌پال: %s", exc)
            return GatewayResult(success=False, message="ارتباط با درگاه پرداخت برقرار نشد.")

        body = data.get("data") or {}
        if body.get("code") == 100:
            authority = body["authority"]
            return GatewayResult(
                success=True,
                authority=authority,
                redirect_url=f"{self.base_url}StartPay/{authority}",
                raw=data,
            )
        errors = data.get("errors") or {}
        return GatewayResult(
            success=False, message=errors.get("message", "درخواست پرداخت پذیرفته نشد."), raw=data
        )

    def verify(self, payment, data):
        if data.get("Status") != "OK":
            return GatewayResult(success=False, message="پرداخت توسط کاربر لغو شد.")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": payment.amount * 10,
            "authority": data.get("Authority", payment.authority),
        }
        try:
            result = self._post(self.base_url + "v4/payment/verify.json", payload)
        except Exception as exc:  # pragma: no cover - وابسته به شبکه
            logger.exception("خطا در تایید تراکنش: %s", exc)
            return GatewayResult(success=False, message="تایید تراکنش انجام نشد.")

        body = result.get("data") or {}
        if body.get("code") in (100, 101):
            return GatewayResult(success=True, ref_id=str(body.get("ref_id", "")), raw=result)
        errors = result.get("errors") or {}
        return GatewayResult(
            success=False, message=errors.get("message", "تراکنش تایید نشد."), raw=result
        )


GATEWAYS = {"dummy": DummyGateway, "zarinpal": ZarinpalGateway}


def get_gateway(request=None, name=None):
    gateway_class = GATEWAYS.get(name or settings.PAYMENT_GATEWAY, DummyGateway)
    return gateway_class(request=request)
