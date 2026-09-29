"""Zibal payment gateway. Docs: https://help.zibal.ir/IPG/API/ — merchant "zibal" is the sandbox."""
from django.conf import settings

from .base import BaseGateway, GatewayResult

ERROR_MESSAGES = {
    102: "مرچنت یافت نشد.",
    103: "مرچنت غیرفعال است.",
    104: "مرچنت نامعتبر است.",
    105: "مبلغ باید بیشتر از ۱٬۰۰۰ ریال باشد.",
    106: "آدرس بازگشت (callbackUrl) نامعتبر است.",
    113: "مبلغ تراکنش از سقف مجاز بیشتر است.",
    202: "سفارش پرداخت نشده یا پرداخت ناموفق بوده است.",
    203: "شناسه تراکنش (trackId) نامعتبر است.",
}


class ZibalGateway(BaseGateway):
    code = "zibal"
    title = "زیبال"
    base_url = "https://gateway.zibal.ir"

    def is_available(self):
        return bool(settings.ZIBAL_MERCHANT)

    def request_payment(self, *, amount_rial, callback_url, description, mobile="", order_number=""):
        payload = {
            "merchant": settings.ZIBAL_MERCHANT,
            "amount": amount_rial,
            "callbackUrl": callback_url,
            "description": description,
            "orderId": order_number,
            "mobile": mobile,
        }
        data = self._post(f"{self.base_url}/v1/request", payload)
        if data.get("result") == 100 and data.get("trackId"):
            track_id = str(data["trackId"])
            return GatewayResult(
                ok=True, authority=track_id, redirect_url=f"{self.base_url}/start/{track_id}", raw=data
            )
        return GatewayResult(ok=False, message=self._error_message(data), raw=data)

    def get_callback_authority(self, params):
        return str(params.get("trackId", ""))

    def verify_payment(self, *, payment, amount_rial, params):
        if params.get("success") != "1":
            return GatewayResult(ok=False, message="پرداخت توسط شما لغو شد یا ناموفق بود.", raw=dict(params.items()))
        try:
            track_id = int(payment.authority)
        except (TypeError, ValueError):
            return GatewayResult(ok=False, message="شناسه تراکنش نامعتبر است.")
        data = self._post(f"{self.base_url}/v1/verify", {"merchant": settings.ZIBAL_MERCHANT, "trackId": track_id})
        # 100 = verified now, 201 = already verified earlier.
        if data.get("result") in (100, 201):
            paid_amount = data.get("amount")
            if paid_amount is not None and int(paid_amount) != amount_rial:
                return GatewayResult(ok=False, message="مبلغ پرداخت‌شده با مبلغ سفارش مطابقت ندارد.", raw=data)
            return GatewayResult(
                ok=True,
                ref_id=str(data.get("refNumber") or ""),
                card_pan=data.get("cardNumber") or "",
                raw=data,
            )
        return GatewayResult(ok=False, message=self._error_message(data), raw=data)

    @staticmethod
    def _error_message(data):
        return ERROR_MESSAGES.get(data.get("result"), data.get("message") or "درخواست پرداخت توسط زیبال پذیرفته نشد.")
