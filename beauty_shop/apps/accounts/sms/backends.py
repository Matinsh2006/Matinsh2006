"""
SMS panel backends. Pick one with the ``SMS_BACKEND`` setting.

All real backends use the provider's *pattern / template* (خدماتی) API, which is
what Iranian operators require for sending verification codes without delay.
"""
from django.conf import settings

from .base import BaseSMSBackend, SMSError, logger

# Messages sent by ``LocmemSMSBackend`` (used in tests).
outbox = []


class ConsoleSMSBackend(BaseSMSBackend):
    """Development backend: writes the code to the server log instead of sending it."""

    def send_otp(self, phone, code):
        logger.warning("SMS (console backend) → %s | verification code: %s", phone, code)


class LocmemSMSBackend(BaseSMSBackend):
    """Test backend: keeps messages in ``apps.accounts.sms.backends.outbox``."""

    def send_otp(self, phone, code):
        outbox.append({"phone": phone, "code": code})


class KavenegarSMSBackend(BaseSMSBackend):
    """kavenegar.com — Verify Lookup API with a template containing ``%token``."""

    url = "https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"

    def send_otp(self, phone, code):
        if not settings.KAVENEGAR_API_KEY:
            raise SMSError("KAVENEGAR_API_KEY is not configured.")
        data = self._request(
            self.url.format(api_key=settings.KAVENEGAR_API_KEY),
            data={"receptor": phone, "token": code, "template": settings.KAVENEGAR_OTP_TEMPLATE},
        )
        result = data.get("return") or {}
        if result.get("status") != 200:
            raise SMSError(f"Kavenegar error {result.get('status')}: {result.get('message')}")


class SmsIrSMSBackend(BaseSMSBackend):
    """sms.ir — ``send/verify`` API with a template parameter (default ``CODE``)."""

    url = "https://api.sms.ir/v1/send/verify"

    def send_otp(self, phone, code):
        if not settings.SMSIR_API_KEY or not settings.SMSIR_OTP_TEMPLATE_ID:
            raise SMSError("SMSIR_API_KEY / SMSIR_OTP_TEMPLATE_ID are not configured.")
        data = self._request(
            self.url,
            json={
                "mobile": phone,
                "templateId": int(settings.SMSIR_OTP_TEMPLATE_ID),
                "parameters": [{"name": settings.SMSIR_OTP_PARAMETER, "value": code}],
            },
            headers={"X-API-KEY": settings.SMSIR_API_KEY, "Accept": "application/json"},
        )
        if data.get("status") != 1:
            raise SMSError(f"SMS.ir error {data.get('status')}: {data.get('message')}")


class MelipayamakSMSBackend(BaseSMSBackend):
    """melipayamak.com — shared service line (``BaseServiceNumber``) with a body id."""

    url = "https://rest.payamak-panel.com/api/SendSMS/BaseServiceNumber"

    def send_otp(self, phone, code):
        if not (settings.MELIPAYAMAK_USERNAME and settings.MELIPAYAMAK_PASSWORD and settings.MELIPAYAMAK_OTP_BODY_ID):
            raise SMSError("MELIPAYAMAK_USERNAME / PASSWORD / OTP_BODY_ID are not configured.")
        data = self._request(
            self.url,
            data={
                "username": settings.MELIPAYAMAK_USERNAME,
                "password": settings.MELIPAYAMAK_PASSWORD,
                "text": code,
                "to": phone,
                "bodyId": settings.MELIPAYAMAK_OTP_BODY_ID,
            },
        )
        if data.get("RetStatus") != 1:
            raise SMSError(f"Melipayamak error {data.get('RetStatus')}: {data.get('StrRetStatus')}")
