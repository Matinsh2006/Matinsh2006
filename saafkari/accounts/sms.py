"""
پنل پیامکی — لایه‌ی انتزاعی ارسال پیامک و کد تایید.

با تنظیم ‎SMS_BACKEND‎ در فایل ‎.env‎ می‌توانید بین کنسول (حالت توسعه)،
کاوه‌نگار، اس‌ام‌اس‌دات‌آی‌آر و قاصدک جابه‌جا شوید؛ بدون تغییر در کد سایت.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

from core.validators import mask_phone, normalize_phone

logger = logging.getLogger(__name__)


class SMSDeliveryError(Exception):
    """خطای ارسال پیامک از سمت پنل."""


class BaseSMSBackend:
    """رابط مشترک همه‌ی پنل‌های پیامکی."""

    name = "base"

    def __init__(self, api_key: str | None = None, sender: str | None = None, template: str | None = None):
        self.api_key = api_key if api_key is not None else settings.SMS_API_KEY
        self.sender = sender if sender is not None else settings.SMS_SENDER
        self.template = template if template is not None else settings.SMS_TEMPLATE
        self.timeout = getattr(settings, "SMS_TIMEOUT", 10)

    # --------------------------------------------------------------- رابط عمومی
    def send(self, phone: str, message: str) -> bool:
        """ارسال پیامک متنی ساده."""
        raise NotImplementedError

    def send_otp(self, phone: str, code: str) -> bool:
        """ارسال کد تایید؛ پنل‌های ایرانی معمولاً الگوی اختصاصی دارند."""
        return self.send(phone, f"کد تایید شما: {code}")

    # ------------------------------------------------------------------- کمکی‌ها
    def _request(self, url: str, data: dict | None = None, headers: dict | None = None, method: str = "GET"):
        """درخواست HTTP با مدیریت خطا؛ خروجی، بدنه‌ی JSON یا متن پاسخ است."""
        body = None
        request_headers = {"Accept": "application/json", **(headers or {})}
        if method == "GET" and data:
            url = f"{url}?{urllib.parse.urlencode(data)}"
        elif data is not None:
            body = json.dumps(data).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:  # pragma: no cover - وابسته به شبکه
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise SMSDeliveryError(f"پنل پیامکی خطا داد ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - وابسته به شبکه
            raise SMSDeliveryError(f"اتصال به پنل پیامکی برقرار نشد: {exc.reason}") from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload

    def _require_api_key(self):
        if not self.api_key:
            raise SMSDeliveryError(
                "کلید پنل پیامکی تنظیم نشده است. مقدار SMS_API_KEY را در فایل .env قرار دهید."
            )


class ConsoleSMSBackend(BaseSMSBackend):
    """حالت توسعه: پیامک در ترمینال چاپ می‌شود و پنل واقعی لازم نیست."""

    name = "console"

    def send(self, phone: str, message: str) -> bool:
        phone = normalize_phone(phone)
        print("\n" + "=" * 56)
        print(f"[پیامک تستی] گیرنده: {phone}")
        print(f"متن: {message}")
        print("=" * 56 + "\n", flush=True)
        logger.info("SMS (console) to %s: %s", mask_phone(phone), message)
        return True


class MemorySMSBackend(BaseSMSBackend):
    """پنل آزمایشی برای تست‌های خودکار؛ پیام‌ها در حافظه نگه داشته می‌شوند."""

    name = "memory"
    outbox: list[dict] = []

    def send(self, phone: str, message: str) -> bool:
        self.outbox.append({"phone": normalize_phone(phone), "message": message})
        return True

    @classmethod
    def clear(cls):
        cls.outbox = []


class KavenegarSMSBackend(BaseSMSBackend):
    """پنل کاوه‌نگار — ارسال با الگوی ‎verify/lookup‎ برای کد تایید."""

    name = "kavenegar"
    base_url = "https://api.kavenegar.com/v1"

    def send(self, phone: str, message: str) -> bool:
        self._require_api_key()
        data = {"receptor": normalize_phone(phone), "message": message}
        if self.sender:
            data["sender"] = self.sender
        result = self._request(f"{self.base_url}/{self.api_key}/sms/send.json", data)
        return self._check(result)

    def send_otp(self, phone: str, code: str) -> bool:
        self._require_api_key()
        data = {"receptor": normalize_phone(phone), "token": code, "template": self.template}
        result = self._request(f"{self.base_url}/{self.api_key}/verify/lookup.json", data)
        return self._check(result)

    @staticmethod
    def _check(result) -> bool:
        status = (result or {}).get("return", {}).get("status") if isinstance(result, dict) else None
        if status != 200:
            message = (result or {}).get("return", {}).get("message", "پاسخ نامعتبر") if isinstance(result, dict) else result
            raise SMSDeliveryError(f"کاوه‌نگار: {message}")
        return True


class SmsIrBackend(BaseSMSBackend):
    """پنل ‎sms.ir‎ — ارسال کد تایید با شناسه‌ی الگو."""

    name = "smsir"
    base_url = "https://api.sms.ir/v1"

    def send(self, phone: str, message: str) -> bool:
        self._require_api_key()
        data = {"lineNumber": self.sender, "messageText": message, "mobiles": [normalize_phone(phone)]}
        result = self._request(f"{self.base_url}/send/bulk", data, headers={"X-API-KEY": self.api_key}, method="POST")
        return self._check(result)

    def send_otp(self, phone: str, code: str) -> bool:
        self._require_api_key()
        data = {
            "mobile": normalize_phone(phone),
            "templateId": int(self.template) if str(self.template).isdigit() else self.template,
            "parameters": [{"name": "CODE", "value": str(code)}],
        }
        result = self._request(f"{self.base_url}/send/verify", data, headers={"X-API-KEY": self.api_key}, method="POST")
        return self._check(result)

    @staticmethod
    def _check(result) -> bool:
        if isinstance(result, dict) and result.get("status") == 1:
            return True
        message = result.get("message") if isinstance(result, dict) else result
        raise SMSDeliveryError(f"sms.ir: {message}")


class GhasedakSMSBackend(BaseSMSBackend):
    """پنل قاصدک — ارسال ساده و کد تایید."""

    name = "ghasedak"
    base_url = "https://api.ghasedak.me/v2"

    def send(self, phone: str, message: str) -> bool:
        self._require_api_key()
        data = urllib.parse.urlencode(
            {"receptor": normalize_phone(phone), "linenumber": self.sender, "message": message}
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url}/sms/send/simple",
            data=data,
            headers={"apikey": self.api_key, "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:  # pragma: no cover
            raise SMSDeliveryError(f"قاصدک: {exc}") from exc
        if payload.get("result", {}).get("code") != 200:
            raise SMSDeliveryError(f"قاصدک: {payload.get('result', {}).get('message')}")
        return True

    def send_otp(self, phone: str, code: str) -> bool:
        self._require_api_key()
        data = {"receptor": normalize_phone(phone), "type": 1, "template": self.template, "param1": str(code)}
        result = self._request(f"{self.base_url}/verification/send/simple", data, headers={"apikey": self.api_key})
        if isinstance(result, dict) and result.get("result", {}).get("code") == 200:
            return True
        raise SMSDeliveryError(f"قاصدک: {result}")


#: نام‌های کوتاه برای راحتی تنظیم در فایل ‎.env‎
BACKEND_ALIASES = {
    "console": "accounts.sms.ConsoleSMSBackend",
    "memory": "accounts.sms.MemorySMSBackend",
    "kavenegar": "accounts.sms.KavenegarSMSBackend",
    "smsir": "accounts.sms.SmsIrBackend",
    "sms.ir": "accounts.sms.SmsIrBackend",
    "ghasedak": "accounts.sms.GhasedakSMSBackend",
}


def get_sms_backend() -> BaseSMSBackend:
    """ساخت نمونه‌ی پنل پیامکی بر اساس تنظیمات."""
    path = getattr(settings, "SMS_BACKEND", "accounts.sms.ConsoleSMSBackend")
    path = BACKEND_ALIASES.get(str(path).strip().lower(), path)
    backend_class = import_string(path)
    return backend_class()


def send_otp_sms(phone: str, code: str) -> bool:
    """ارسال کد تایید با پنل فعال؛ خطاها لاگ و به بالا پرتاب می‌شوند."""
    backend = get_sms_backend()
    logger.info("ارسال کد تایید به %s با پنل %s", mask_phone(phone), backend.name)
    return backend.send_otp(normalize_phone(phone), code)


def send_sms(phone: str, message: str) -> bool:
    """ارسال پیامک اطلاع‌رسانی (تایید نوبت، یادآوری و ...)."""
    return get_sms_backend().send(normalize_phone(phone), message)
