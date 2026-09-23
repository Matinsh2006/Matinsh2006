"""منطق صدور و بررسی کد تایید پیامکی (به همراه محدودیت ارسال)."""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from core.validators import normalize_phone

from .models import OTPCode
from .sms import SMSDeliveryError, get_sms_backend, send_otp_sms


@dataclass
class OTPResult:
    """نتیجه‌ی درخواست ارسال کد."""

    ok: bool
    otp: OTPCode | None = None
    error: str = ""
    debug_code: str = ""


def client_ip(request) -> str | None:
    """آی‌پی واقعی کاربر با در نظر گرفتن پراکسی."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def request_otp(phone: str, purpose: str, user=None, ip: str | None = None) -> OTPResult:
    """
    صدور کد تازه با رعایت محدودیت‌ها و ارسال آن با پنل پیامکی.

    محدودیت‌ها: فاصله‌ی زمانی بین دو ارسال و سقف تعداد ارسال در ساعت.
    """
    phone = normalize_phone(phone)
    if not phone:
        return OTPResult(False, error="شماره موبایل معتبر نیست.")

    previous = OTPCode.last_for(phone, purpose)
    if previous and previous.resend_seconds_left > 0 and previous.used_at is None:
        return OTPResult(
            False, otp=previous,
            error=f"برای ارسال دوباره‌ی کد، {previous.resend_seconds_left} ثانیه صبر کنید.",
        )
    if OTPCode.hourly_count(phone) >= settings.OTP_HOURLY_LIMIT:
        return OTPResult(False, error="تعداد درخواست کد تایید بیش از حد مجاز است. یک ساعت دیگر تلاش کنید.")

    otp, raw_code = OTPCode.issue(phone, purpose, user=user, ip=ip)
    try:
        send_otp_sms(phone, raw_code)
    except SMSDeliveryError as exc:
        otp.delete()
        return OTPResult(False, error=str(exc))

    debug_code = ""
    backend_name = getattr(get_sms_backend(), "name", "")
    if settings.DEBUG and backend_name in {"console", "memory"}:
        # فقط در حالت توسعه، کد برای راحتی آزمایش نمایش داده می‌شود.
        debug_code = raw_code
    return OTPResult(True, otp=otp, debug_code=debug_code)


def verify_otp(phone: str, purpose: str, code: str) -> tuple[bool, str]:
    """بررسی کد واردشده. خروجی: (درست بود؟، پیام خطا)"""
    phone = normalize_phone(phone)
    otp = OTPCode.last_for(phone, purpose)
    if otp is None:
        return False, "کدی برای این شماره ارسال نشده است. دوباره درخواست دهید."
    if otp.used_at is not None:
        return False, "این کد قبلاً استفاده شده است. کد تازه بگیرید."
    if otp.is_expired:
        return False, "مهلت کد تمام شده است. روی «ارسال دوباره» بزنید."
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False, "تعداد تلاش‌های ناموفق زیاد بود. کد تازه بگیرید."
    if otp.check_code(code):
        return True, ""
    remaining = max(0, settings.OTP_MAX_ATTEMPTS - otp.attempts)
    return False, f"کد واردشده درست نیست. {remaining} تلاش دیگر باقی مانده است."
