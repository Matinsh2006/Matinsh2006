"""
Pluggable SMS panel backends used to deliver one-time passwords.

Select the backend with the ``SMS_BACKEND`` setting:

* ``console``     – development only; the code is written to the log.
* ``kavenegar``   – Kavenegar "verify/lookup" (pattern) API.
* ``smsir``       – SMS.ir v1 "send/verify" (template) API.
* ``melipayamak`` – Melipayamak shared-service-number (pattern) API.
* any dotted path to a subclass of :class:`BaseSMSBackend`.

Iranian operators only deliver OTP messages sent through an approved
*pattern/template*, so each provider needs the id of a template that contains
a single variable for the code.
"""
import logging

import requests
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SMSError(Exception):
    """Raised when an SMS provider refuses or fails to send a message."""


class BaseSMSBackend:
    name = "base"

    def send_otp(self, phone: str, code: str) -> None:
        raise NotImplementedError

    # -- helpers ------------------------------------------------------------
    def _post(self, url, **kwargs):
        try:
            response = requests.post(url, timeout=settings.SMS_TIMEOUT, **kwargs)
        except requests.RequestException as exc:
            raise SMSError(f"{self.name}: connection error ({exc})") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise SMSError(f"{self.name}: invalid response (HTTP {response.status_code})") from exc

    @staticmethod
    def _require(**values):
        missing = [key for key, value in values.items() if not value]
        if missing:
            raise SMSError(f"SMS panel is not configured, missing: {', '.join(missing)}")


class ConsoleSMSBackend(BaseSMSBackend):
    """Prints codes to the server log instead of sending real messages."""

    name = "console"

    def send_otp(self, phone, code):
        logger.warning("[SMS console] verification code for %s: %s", phone, code)


class KavenegarSMSBackend(BaseSMSBackend):
    """https://kavenegar.com/rest.html#sms-Lookup"""

    name = "kavenegar"
    url = "https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"

    def send_otp(self, phone, code):
        api_key = settings.KAVENEGAR_API_KEY
        template = settings.KAVENEGAR_OTP_TEMPLATE
        self._require(KAVENEGAR_API_KEY=api_key, KAVENEGAR_OTP_TEMPLATE=template)
        data = self._post(
            self.url.format(api_key=api_key),
            data={"receptor": phone, "token": code, "template": template},
        )
        result = data.get("return") or {}
        if result.get("status") != 200:
            raise SMSError(f"kavenegar: {result.get('status')} {result.get('message')}")


class SmsIrSMSBackend(BaseSMSBackend):
    """https://app.sms.ir/developer/help/verify"""

    name = "smsir"
    url = "https://api.sms.ir/v1/send/verify"

    def send_otp(self, phone, code):
        api_key = settings.SMSIR_API_KEY
        template_id = settings.SMSIR_OTP_TEMPLATE_ID
        self._require(SMSIR_API_KEY=api_key, SMSIR_OTP_TEMPLATE_ID=template_id)
        data = self._post(
            self.url,
            json={
                "mobile": phone,
                "templateId": int(template_id),
                "parameters": [{"name": settings.SMSIR_OTP_PARAM_NAME, "value": code}],
            },
            headers={"X-API-KEY": api_key, "Accept": "application/json"},
        )
        if data.get("status") != 1:
            raise SMSError(f"smsir: {data.get('status')} {data.get('message')}")


class MelipayamakSMSBackend(BaseSMSBackend):
    """Melipayamak "BaseServiceNumber" (shared service line with pattern)."""

    name = "melipayamak"
    url = "https://rest.payamak-panel.com/api/SendSMS/BaseServiceNumber"

    def send_otp(self, phone, code):
        username = settings.MELIPAYAMAK_USERNAME
        password = settings.MELIPAYAMAK_PASSWORD
        body_id = settings.MELIPAYAMAK_OTP_BODY_ID
        self._require(
            MELIPAYAMAK_USERNAME=username,
            MELIPAYAMAK_PASSWORD=password,
            MELIPAYAMAK_OTP_BODY_ID=body_id,
        )
        data = self._post(
            self.url,
            data={
                "username": username,
                "password": password,
                "to": phone,
                "bodyId": int(body_id),
                "text": code,
            },
        )
        # On success "Value" holds the long numeric id of the sent message.
        if data.get("RetStatus") != 1 or len(str(data.get("Value", ""))) < 10:
            raise SMSError(f"melipayamak: {data.get('Value')} {data.get('StrRetStatus')}")


BACKENDS = {
    "console": ConsoleSMSBackend,
    "kavenegar": KavenegarSMSBackend,
    "smsir": SmsIrSMSBackend,
    "melipayamak": MelipayamakSMSBackend,
}


def get_sms_backend() -> BaseSMSBackend:
    name = settings.SMS_BACKEND
    backend_class = BACKENDS.get(name) or import_string(name)
    return backend_class()


def is_console_backend() -> bool:
    return isinstance(get_sms_backend(), ConsoleSMSBackend)
