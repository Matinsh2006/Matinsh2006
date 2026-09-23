"""SMS provider backends used to deliver OTP verification codes.

This mirrors the pattern Django uses for EMAIL_BACKEND: point
``settings.SMS_BACKEND`` at the dotted path of one of these classes (or a
new one you write for a different provider) and the rest of the app does
not need to change.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseSmsBackend:
    def send_otp(self, phone_number, code):
        raise NotImplementedError


class ConsoleSmsBackend(BaseSmsBackend):
    """Prints the OTP code instead of sending it - used for local development
    and demos when no real SMS panel account is configured yet."""

    def send_otp(self, phone_number, code):
        message = f"[پیامک شبیه‌سازی‌شده] کد تایید {phone_number}: {code}"
        print(message)
        logger.info(message)
        return {"simulated": True}


class KavenegarSmsBackend(BaseSmsBackend):
    """Sends the OTP via Kavenegar's Verify Lookup API (https://kavenegar.com).

    Requires KAVENEGAR_API_KEY and, if the template expects extra tokens, a
    matching KAVENEGAR_OTP_TEMPLATE created in the Kavenegar panel.
    """

    API_URL = "https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"

    def send_otp(self, phone_number, code):
        api_key = settings.KAVENEGAR_API_KEY
        if not api_key:
            raise RuntimeError(
                "KAVENEGAR_API_KEY تنظیم نشده است. مقدار آن را در فایل .env وارد کنید."
            )
        url = self.API_URL.format(api_key=api_key)
        payload = {
            "receptor": phone_number,
            "token": code,
            "template": settings.KAVENEGAR_OTP_TEMPLATE,
        }
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        status = data.get("return", {}).get("status")
        if status != 200:
            message = data.get("return", {}).get("message", "خطای ناشناخته از سرویس پیامک")
            raise RuntimeError(f"ارسال پیامک ناموفق بود: {message}")
        return data
