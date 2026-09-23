import random

from django.conf import settings
from django.utils import timezone

from .models import OTP
from .sms import send_otp_sms


class OTPError(Exception):
    """Base class for OTP related errors; message is safe to show to users."""


class OTPCooldownError(OTPError):
    def __init__(self, wait_seconds):
        self.wait_seconds = wait_seconds
        super().__init__("لطفاً کمی صبر کنید و دوباره تلاش کنید.")


class OTPInvalidError(OTPError):
    pass


class OTPExpiredError(OTPError):
    pass


def _generate_code():
    length = settings.OTP_CODE_LENGTH
    return "".join(random.choices("0123456789", k=length))


def request_otp(phone_number, purpose):
    """Create a new OTP code and send it by SMS, respecting the resend cooldown."""
    cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
    recent = (
        OTP.objects.filter(phone_number=phone_number, purpose=purpose)
        .order_by("-created_at")
        .first()
    )
    if recent:
        elapsed = (timezone.now() - recent.created_at).total_seconds()
        if elapsed < cooldown:
            raise OTPCooldownError(int(cooldown - elapsed))

    code = _generate_code()
    expires_at = timezone.now() + timezone.timedelta(seconds=settings.OTP_EXPIRY_SECONDS)
    otp = OTP.objects.create(
        phone_number=phone_number,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
    )
    send_otp_sms(phone_number, code)
    return otp


def verify_otp(phone_number, purpose, code):
    """Validate a submitted code for phone_number/purpose, marking it used on success."""
    otp = (
        OTP.objects.filter(phone_number=phone_number, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if not otp:
        raise OTPInvalidError("کد معتبری برای این شماره ثبت نشده است. دوباره درخواست دهید.")

    otp.attempts += 1
    otp.save(update_fields=["attempts"])

    if otp.is_expired():
        raise OTPExpiredError("کد تایید منقضی شده است. دوباره درخواست دهید.")
    if otp.attempts > 5:
        raise OTPInvalidError("تعداد تلاش‌های مجاز به پایان رسید. دوباره درخواست دهید.")
    if otp.code != code:
        raise OTPInvalidError("کد تایید نادرست است.")

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return True
