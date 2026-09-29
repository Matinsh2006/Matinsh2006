"""Zarinpal payment gateway (REST API v4). Docs: https://www.zarinpal.com/docs/"""
from django.conf import settings

from .base import BaseGateway, GatewayResult

ERROR_MESSAGES = {
    -9: "اطلاعات ارسالی به درگاه معتبر نیست.",
    -10: "مرچنت کد یا IP پذیرنده صحیح نیست.",
    -11: "مرچنت کد فعال نیست.",
    -12: "تلاش بیش از حد در زمان کوتاه؛ لطفاً کمی بعد دوباره تلاش کنید.",
    -15: "درگاه پرداخت پذیرنده به حالت تعلیق درآمده است.",
    -16: "سطح تایید پذیرنده پایین‌تر از سطح نقره‌ای است.",
    -50: "مبلغ پرداخت‌شده با مبلغ سفارش مطابقت ندارد.",
    -51: "پرداخت ناموفق بود.",
    -52: "خطای غیرمنتظره در درگاه؛ با پشتیبانی تماس بگیرید.",
    -53: "این پرداخت متعلق به این پذیرنده نیست.",
    -54: "شناسه تراکنش (Authority) نامعتبر است.",
}


class ZarinpalGateway(BaseGateway):
    code = "zarinpal"
    title = "زرین‌پال"

    @property
    def base_url(self):
        return "https://sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "https://payment.zarinpal.com"

    def is_available(self):
        return bool(settings.ZARINPAL_MERCHANT_ID)

    def request_payment(self, *, amount_rial, callback_url, description, mobile="", order_number=""):
        metadata = {key: value for key, value in {"mobile": mobile, "order_id": order_number}.items() if value}
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_rial,  # Rial is Zarinpal's default currency
            "callback_url": callback_url,
            "description": description,
            "metadata": metadata,
        }
        data = self._post(f"{self.base_url}/pg/v4/payment/request.json", payload)
        info = data.get("data") or {}
        if isinstance(info, dict) and info.get("code") == 100 and info.get("authority"):
            authority = info["authority"]
            return GatewayResult(
                ok=True,
                authority=authority,
                redirect_url=f"{self.base_url}/pg/StartPay/{authority}",
                raw=data,
            )
        return GatewayResult(ok=False, message=self._error_message(data), raw=data)

    def get_callback_authority(self, params):
        return params.get("Authority", "")

    def verify_payment(self, *, payment, amount_rial, params):
        if params.get("Status") != "OK":
            return GatewayResult(ok=False, message="پرداخت توسط شما لغو شد یا ناموفق بود.", raw=dict(params.items()))
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_rial,
            "authority": payment.authority,
        }
        data = self._post(f"{self.base_url}/pg/v4/payment/verify.json", payload)
        info = data.get("data") or {}
        # 100 = verified now, 101 = already verified earlier.
        if isinstance(info, dict) and info.get("code") in (100, 101):
            return GatewayResult(
                ok=True,
                ref_id=str(info.get("ref_id", "")),
                card_pan=info.get("card_pan") or "",
                raw=data,
            )
        return GatewayResult(ok=False, message=self._error_message(data), raw=data)

    @staticmethod
    def _error_message(data):
        errors = data.get("errors")
        code = errors.get("code") if isinstance(errors, dict) else None
        if code is None and isinstance(data.get("data"), dict):
            code = data["data"].get("code")
        return ERROR_MESSAGES.get(code, "درخواست پرداخت توسط زرین‌پال پذیرفته نشد.")
