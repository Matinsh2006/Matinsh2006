"""لایه ارسال پیامک.

برای توسعه از بک‌اند console استفاده می‌شود و کد در ترمینال چاپ می‌گردد.
برای محیط واقعی کافی است SMS_BACKEND=kavenegar و کلید API را ست کنید.
"""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class BaseSMSBackend:
    def send(self, phone: str, message: str) -> bool:  # pragma: no cover - رابط
        raise NotImplementedError


class ConsoleSMSBackend(BaseSMSBackend):
    """پیامک را در ترمینال چاپ می‌کند (حالت دمو)."""

    def send(self, phone, message):
        logger.info("SMS → %s: %s", phone, message)
        print(f"\n[پنل پیامکی - حالت تست]\nگیرنده: {phone}\nمتن: {message}\n")
        return True


class KavenegarSMSBackend(BaseSMSBackend):
    """نمونه اتصال به پنل پیامکی کاوه‌نگار."""

    endpoint = "https://api.kavenegar.com/v1/{api_key}/sms/send.json"

    def send(self, phone, message):
        api_key = settings.SMS_API_KEY
        if not api_key:
            logger.error("کلید پنل پیامکی تنظیم نشده است.")
            return False
        params = urllib.parse.urlencode(
            {"receptor": phone, "message": message, "sender": settings.SMS_SENDER}
        )
        url = self.endpoint.format(api_key=api_key) + "?" + params
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload.get("return", {}).get("status") == 200
        except Exception as exc:  # pragma: no cover - وابسته به شبکه
            logger.exception("ارسال پیامک ناموفق بود: %s", exc)
            return False


BACKENDS = {"console": ConsoleSMSBackend, "kavenegar": KavenegarSMSBackend}


def get_sms_backend():
    return BACKENDS.get(settings.SMS_BACKEND, ConsoleSMSBackend)()


def send_sms(phone: str, message: str) -> bool:
    return get_sms_backend().send(phone, message)


def send_otp(phone: str, code: str) -> bool:
    return send_sms(phone, f"کد تایید شما: {code}\nاین کد تا {settings.OTP_EXPIRE_SECONDS // 60} دقیقه معتبر است.")
