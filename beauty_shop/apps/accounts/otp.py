"""Issuing and checking SMS verification codes (with rate limiting)."""
import hashlib
import hmac
import logging
import math
import secrets
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from apps.core.utils.text import to_latin_digits, to_persian_digits

from .models import OTPCode
from .sms import SMSError, send_otp_sms

logger = logging.getLogger(__name__)


class OTPError(Exception):
    """A problem whose message can be shown to the user as-is."""


class OTPThrottled(OTPError):
    def __init__(self, wait_seconds):
        self.wait_seconds = wait_seconds
        super().__init__(f"برای دریافت کد جدید لطفاً {to_persian_digits(wait_seconds)} ثانیه صبر کنید.")


def _hash(phone, purpose, code):
    message = f"{phone}:{purpose}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def generate_code(length=None):
    return "".join(secrets.choice("0123456789") for _ in range(length or settings.OTP_LENGTH))


def resend_wait_seconds(phone, purpose):
    """Seconds left before a new code may be requested for this phone/purpose."""
    last = OTPCode.objects.filter(phone=phone, purpose=purpose).order_by("-created_at").first()
    if last is None:
        return 0
    elapsed = (timezone.now() - last.created_at).total_seconds()
    return max(0, math.ceil(settings.OTP_RESEND_SECONDS - elapsed))


def has_active_code(phone, purpose, user=None):
    queryset = OTPCode.objects.filter(
        phone=phone,
        purpose=purpose,
        is_used=False,
        expires_at__gt=timezone.now(),
        attempts__lt=settings.OTP_MAX_ATTEMPTS,
    )
    if user is not None:
        queryset = queryset.filter(user=user)
    return queryset.exists()


def send_code(phone, purpose, *, user=None, ip=None):
    """
    Create a new code, invalidate older ones and send it by SMS.

    Returns the plain code so it can be displayed while testing
    (``OTP_SHOW_CODE_IN_MESSAGE``); it is never stored unhashed.
    """
    wait = resend_wait_seconds(phone, purpose)
    if wait:
        raise OTPThrottled(wait)

    hour_ago = timezone.now() - timedelta(hours=1)
    if OTPCode.objects.filter(phone=phone, created_at__gte=hour_ago).count() >= settings.OTP_MAX_PER_HOUR:
        raise OTPError("تعداد درخواست کد برای این شماره بیش از حد مجاز است. لطفاً یک ساعت دیگر تلاش کنید.")
    if ip and OTPCode.objects.filter(ip_address=ip, created_at__gte=hour_ago).count() >= settings.OTP_MAX_PER_IP_PER_HOUR:
        raise OTPError("تعداد درخواست‌ها بیش از حد مجاز است. لطفاً بعداً دوباره تلاش کنید.")

    OTPCode.objects.filter(phone=phone, purpose=purpose, is_used=False).update(is_used=True)
    code = generate_code()
    otp = OTPCode.objects.create(
        phone=phone,
        purpose=purpose,
        user=user,
        code_hash=_hash(phone, purpose, code),
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
        ip_address=ip,
    )
    try:
        send_otp_sms(phone, code)
    except SMSError:
        logger.exception("Sending verification SMS to %s failed", phone)
        otp.delete()
        raise OTPError("ارسال پیامک با خطا مواجه شد. لطفاً چند دقیقه دیگر دوباره تلاش کنید.") from None
    return code


def verify_code(phone, purpose, code, *, user=None):
    """Validate ``code``; marks it as used on success, raises ``OTPError`` otherwise."""
    code = to_latin_digits(code or "").strip()
    otp = OTPCode.objects.filter(phone=phone, purpose=purpose, is_used=False).order_by("-created_at").first()
    if otp is None or (user is not None and otp.user_id != user.pk):
        raise OTPError("کد تایید معتبری برای این شماره وجود ندارد. لطفاً کد جدید دریافت کنید.")
    if otp.is_expired:
        raise OTPError("کد تایید منقضی شده است. لطفاً کد جدید دریافت کنید.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OTPError("تعداد تلاش‌های ناموفق بیش از حد مجاز است. لطفاً کد جدید دریافت کنید.")

    if not hmac.compare_digest(otp.code_hash, _hash(phone, purpose, code)):
        OTPCode.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1)
        remaining = settings.OTP_MAX_ATTEMPTS - otp.attempts - 1
        if remaining > 0:
            raise OTPError(f"کد وارد شده صحیح نیست. ({to_persian_digits(remaining)} تلاش باقی مانده)")
        raise OTPError("کد وارد شده صحیح نیست. لطفاً کد جدید دریافت کنید.")

    # Compare-and-set so the same code can never be used twice concurrently.
    marked = OTPCode.objects.filter(pk=otp.pk, is_used=False).update(is_used=True, used_at=timezone.now())
    if not marked:
        raise OTPError("این کد قبلاً استفاده شده است. لطفاً کد جدید دریافت کنید.")
    return otp
