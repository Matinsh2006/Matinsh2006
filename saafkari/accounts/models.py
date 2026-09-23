"""کاربر مبتنی بر شماره موبایل و کدهای تایید پیامکی."""
from __future__ import annotations

import datetime as dt
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.validators import mask_phone, normalize_phone, validate_iran_mobile


class UserManager(BaseUserManager):
    """مدیر کاربران با شماره موبایل به‌جای نام کاربری."""

    use_in_migrations = True

    def _create_user(self, phone, password=None, **extra_fields):
        phone = normalize_phone(phone)
        if not phone:
            raise ValueError("برای ساخت کاربر، شماره موبایل الزامی است.")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=["password", "last_login"])
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_phone_verified", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("مدیر کل باید is_staff و is_superuser داشته باشد.")
        return self._create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """کاربر سایت؛ نام کاربری همان شماره موبایل است."""

    phone = models.CharField(
        _("شماره موبایل"), max_length=11, unique=True,
        validators=[validate_iran_mobile],
        help_text=_("نام کاربری شما همین شماره موبایل است."),
        error_messages={"unique": _("کاربری با این شماره موبایل قبلاً ثبت‌نام کرده است.")},
    )
    full_name = models.CharField(_("نام و نام خانوادگی"), max_length=120, blank=True, default="")
    email = models.EmailField(_("ایمیل"), blank=True, default="")
    avatar = models.ImageField(_("تصویر پروفایل"), upload_to="avatars/%Y/%m/", blank=True, null=True)
    car_model = models.CharField(
        _("خودروی من"), max_length=120, blank=True, default="",
        help_text=_("مثال: پژو ۲۰۶ تیپ ۵ سفید"),
    )
    plate_number = models.CharField(_("شماره پلاک"), max_length=20, blank=True, default="")

    is_active = models.BooleanField(_("فعال"), default=True)
    is_staff = models.BooleanField(
        _("دسترسی به پنل مدیریت"), default=False,
        help_text=_("برای کارفرما و کارکنان مغازه فعال شود."),
    )
    is_phone_verified = models.BooleanField(_("شماره تایید شده"), default=False)
    date_joined = models.DateTimeField(_("تاریخ عضویت"), default=timezone.now)
    phone_changed_at = models.DateTimeField(_("آخرین تغییر شماره"), null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")
        ordering = ("-date_joined",)

    def __str__(self):
        return self.full_name or self.phone

    def clean(self):
        super().clean()
        self.phone = normalize_phone(self.phone)
        self.full_name = (self.full_name or "").strip()

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone) or self.phone
        super().save(*args, **kwargs)

    def get_full_name(self) -> str:
        return self.full_name or self.phone

    def get_short_name(self) -> str:
        return (self.full_name or self.phone).split(" ")[0]

    @property
    def masked_phone(self) -> str:
        return mask_phone(self.phone)

    @property
    def display_name(self) -> str:
        return self.full_name or f"کاربر {self.phone[-4:]}"


class OTPPurpose(models.TextChoices):
    """کاربرد کد تایید."""

    LOGIN = "login", _("ورود یا ثبت‌نام")
    PHONE_CHANGE = "phone_change", _("تغییر شماره موبایل")


class OTPCodeQuerySet(models.QuerySet):
    def active(self):
        return self.filter(used_at__isnull=True, expires_at__gt=timezone.now())


class OTPCode(models.Model):
    """کد یک‌بارمصرف پیامکی. کد به صورت هش‌شده ذخیره می‌شود."""

    phone = models.CharField(_("شماره موبایل"), max_length=11, db_index=True)
    purpose = models.CharField(_("کاربرد"), max_length=20, choices=OTPPurpose.choices, default=OTPPurpose.LOGIN)
    code_hash = models.CharField(_("کد (هش‌شده)"), max_length=128)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("کاربر"), null=True, blank=True,
        on_delete=models.CASCADE, related_name="otp_codes",
    )
    created_at = models.DateTimeField(_("زمان ارسال"), auto_now_add=True)
    expires_at = models.DateTimeField(_("زمان انقضا"))
    used_at = models.DateTimeField(_("زمان استفاده"), null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(_("تعداد تلاش ناموفق"), default=0)
    ip_address = models.GenericIPAddressField(_("آی‌پی درخواست"), null=True, blank=True)

    objects = OTPCodeQuerySet.as_manager()

    class Meta:
        verbose_name = _("کد تایید پیامکی")
        verbose_name_plural = _("کدهای تایید پیامکی")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["phone", "purpose", "-created_at"])]

    def __str__(self):
        return f"{mask_phone(self.phone)} — {self.get_purpose_display()}"

    # ----------------------------------------------------------------- کمکی‌ها
    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired and self.attempts < settings.OTP_MAX_ATTEMPTS

    @property
    def seconds_left(self) -> int:
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

    @property
    def resend_available_at(self) -> dt.datetime:
        return self.created_at + dt.timedelta(seconds=settings.OTP_RESEND_COOLDOWN)

    @property
    def resend_seconds_left(self) -> int:
        if not self.created_at:
            return 0
        return max(0, int((self.resend_available_at - timezone.now()).total_seconds()))

    # ------------------------------------------------------------ ساخت و بررسی
    @staticmethod
    def generate_code(length: int | None = None) -> str:
        length = length or settings.OTP_LENGTH
        lower = 10 ** (length - 1)
        upper = 10**length - 1
        return str(secrets.randbelow(upper - lower + 1) + lower)

    @classmethod
    def hourly_count(cls, phone: str) -> int:
        since = timezone.now() - dt.timedelta(hours=1)
        return cls.objects.filter(phone=normalize_phone(phone), created_at__gte=since).count()

    @classmethod
    def last_for(cls, phone: str, purpose: str) -> "OTPCode | None":
        return cls.objects.filter(phone=normalize_phone(phone), purpose=purpose).order_by("-created_at").first()

    @classmethod
    def issue(cls, phone: str, purpose: str, user=None, ip: str | None = None) -> tuple["OTPCode", str]:
        """
        ساخت کد تازه و باطل‌کردن کدهای قبلی همان شماره و کاربرد.

        خروجی: (شیء کد، کد خام برای ارسال پیامک)
        """
        phone = normalize_phone(phone)
        cls.objects.filter(phone=phone, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
        raw_code = cls.generate_code()
        otp = cls.objects.create(
            phone=phone,
            purpose=purpose,
            code_hash=make_password(raw_code),
            user=user,
            expires_at=timezone.now() + dt.timedelta(seconds=settings.OTP_TTL_SECONDS),
            ip_address=ip,
        )
        return otp, raw_code

    def check_code(self, raw_code: str) -> bool:
        """بررسی کد واردشده و ثبت تلاش ناموفق."""
        from core.jalali import to_latin_digits

        raw_code = to_latin_digits(raw_code).strip()
        if not self.is_usable:
            return False
        if check_password(raw_code, self.code_hash):
            self.used_at = timezone.now()
            self.save(update_fields=["used_at"])
            return True
        self.attempts += 1
        self.save(update_fields=["attempts"])
        return False
