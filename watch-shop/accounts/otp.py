"""Issuing and checking SMS one-time passwords."""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from core.utils import fa_digits

from .models import OneTimePassword
from .sms import SMSError, get_sms_backend
from .utils import to_english_digits

logger = logging.getLogger(__name__)


class OTPError(Exception):
    def __init__(self, message, *, wait_seconds=0):
        super().__init__(message)
        self.message = message
        self.wait_seconds = wait_seconds


def _hash(phone, purpose, code):
    payload = f"{phone}:{purpose}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()


def generate_code(length=None):
    length = length or settings.OTP_LENGTH
    # No leading zero: some panels treat the token as a number.
    first = str(secrets.randbelow(9) + 1)
    return first + "".join(str(secrets.randbelow(10)) for _ in range(length - 1))


def seconds_until_resend(phone, purpose):
    last = (
        OneTimePassword.objects.filter(phone=phone, purpose=purpose)
        .order_by("-created_at")
        .only("created_at")
        .first()
    )
    if not last:
        return 0
    elapsed = (timezone.now() - last.created_at).total_seconds()
    return max(0, int(settings.OTP_RESEND_SECONDS - elapsed))


def send_otp(phone, purpose, *, user=None, ip=None):
    """Create a new code for ``phone`` and deliver it through the SMS panel.

    Returns ``(otp, code)``; the plain code is only needed for tests and the
    development console backend.
    """
    now = timezone.now()
    wait = seconds_until_resend(phone, purpose)
    if wait:
        raise OTPError(
            f"لطفاً {fa_digits(wait)} ثانیه دیگر برای دریافت کد جدید تلاش کنید.", wait_seconds=wait
        )

    hour_ago = now - timedelta(hours=1)
    if OneTimePassword.objects.filter(phone=phone, created_at__gte=hour_ago).count() >= settings.OTP_MAX_PER_HOUR:
        raise OTPError("تعداد درخواست کد برای این شماره بیش از حد مجاز است. لطفاً یک ساعت دیگر تلاش کنید.")
    if ip and (
        OneTimePassword.objects.filter(ip_address=ip, created_at__gte=hour_ago).count()
        >= settings.OTP_MAX_PER_IP_HOUR
    ):
        raise OTPError("تعداد درخواست‌ها بیش از حد مجاز است. لطفاً بعداً تلاش کنید.")

    code = generate_code()
    OneTimePassword.objects.filter(phone=phone, purpose=purpose, is_used=False).update(is_used=True)
    otp = OneTimePassword.objects.create(
        phone=phone,
        purpose=purpose,
        user=user,
        code_hash=_hash(phone, purpose, code),
        ip_address=ip,
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
    )
    try:
        get_sms_backend().send_otp(phone, code)
    except SMSError as exc:
        logger.error("Sending OTP to %s failed: %s", phone, exc)
        otp.delete()
        raise OTPError("ارسال پیامک با خطا مواجه شد. لطفاً چند لحظه بعد دوباره تلاش کنید.") from exc
    return otp, code


def verify_otp(phone, purpose, code, *, user=None):
    """Validate ``code``; marks the OTP as used and returns it on success."""
    queryset = OneTimePassword.objects.filter(phone=phone, purpose=purpose, is_used=False)
    if user is not None:
        queryset = queryset.filter(user=user)
    otp = queryset.order_by("-created_at").first()
    if otp is None:
        raise OTPError("کد تاییدی برای این شماره یافت نشد. لطفاً دوباره درخواست کد دهید.")
    if otp.is_expired:
        raise OTPError("مهلت استفاده از کد به پایان رسیده است. لطفاً کد جدید دریافت کنید.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OTPError("تعداد تلاش‌های ناموفق زیاد است. لطفاً کد جدید دریافت کنید.")

    clean_code = to_english_digits(code).strip()
    if not hmac.compare_digest(otp.code_hash, _hash(phone, purpose, clean_code)):
        OneTimePassword.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1)
        remaining = settings.OTP_MAX_ATTEMPTS - otp.attempts - 1
        if remaining <= 0:
            raise OTPError("کد وارد شده صحیح نیست. لطفاً کد جدید دریافت کنید.")
        raise OTPError(f"کد وارد شده صحیح نیست. {fa_digits(remaining)} بار دیگر می‌توانید تلاش کنید.")

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return otp
