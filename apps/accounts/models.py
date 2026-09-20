import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .validators import normalize_phone, validate_iranian_phone


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError(_("شماره موبایل الزامی است."))
        phone = normalize_phone(phone)
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not password:
            raise ValueError(_("برای مدیر، رمز عبور الزامی است."))
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """کاربر فروشگاه؛ نام کاربری همان شماره موبایل است."""

    phone = models.CharField(
        _("شماره موبایل"),
        max_length=11,
        unique=True,
        validators=[validate_iranian_phone],
        help_text=_("نام کاربری شما همین شماره است."),
    )
    full_name = models.CharField(_("نام و نام خانوادگی"), max_length=150, blank=True)
    email = models.EmailField(_("ایمیل"), blank=True)
    is_active = models.BooleanField(_("فعال"), default=True)
    is_staff = models.BooleanField(_("دسترسی پنل مدیریت"), default=False)
    phone_verified = models.BooleanField(_("شماره تایید شده"), default=False)
    date_joined = models.DateTimeField(_("تاریخ عضویت"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.full_name or self.phone

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name or self.phone

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.phone


class Profile(models.Model):
    """اطلاعات تکمیلی و آدرس تحویل کاربر."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("کاربر"),
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar = models.ImageField(_("تصویر پروفایل"), upload_to="avatars/", blank=True, null=True)
    birth_date = models.DateField(_("تاریخ تولد"), blank=True, null=True)
    province = models.CharField(_("استان"), max_length=60, blank=True)
    city = models.CharField(_("شهر"), max_length=60, blank=True)
    address = models.TextField(_("آدرس پستی"), blank=True)
    postal_code = models.CharField(_("کد پستی"), max_length=10, blank=True)
    newsletter = models.BooleanField(_("دریافت پیامک تخفیف‌ها"), default=True)

    class Meta:
        verbose_name = _("پروفایل")
        verbose_name_plural = _("پروفایل‌ها")

    def __str__(self):
        return f"پروفایل {self.user}"

    @property
    def is_complete(self):
        return bool(self.user.full_name and self.address and self.city)


class OTPPurpose(models.TextChoices):
    LOGIN = "login", _("ورود / ثبت‌نام")
    CHANGE_PHONE = "change_phone", _("تغییر شماره موبایل")


class OTPCode(models.Model):
    """کد یکبارمصرف پنل پیامکی."""

    phone = models.CharField(_("شماره موبایل"), max_length=11, db_index=True)
    code = models.CharField(_("کد"), max_length=8)
    purpose = models.CharField(
        _("هدف"), max_length=20, choices=OTPPurpose.choices, default=OTPPurpose.LOGIN
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("کاربر"),
        on_delete=models.CASCADE,
        related_name="otp_codes",
        blank=True,
        null=True,
    )
    attempts = models.PositiveSmallIntegerField(_("تعداد تلاش"), default=0)
    is_used = models.BooleanField(_("مصرف شده"), default=False)
    created_at = models.DateTimeField(_("زمان ارسال"), auto_now_add=True)
    expires_at = models.DateTimeField(_("زمان انقضا"))

    class Meta:
        verbose_name = _("کد تایید")
        verbose_name_plural = _("کدهای تایید")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone} - {self.code}"

    @classmethod
    def generate(cls, phone, purpose=OTPPurpose.LOGIN, user=None):
        """کدهای قبلی را باطل و یک کد تازه می‌سازد."""
        phone = normalize_phone(phone)
        cls.objects.filter(phone=phone, purpose=purpose, is_used=False).update(is_used=True)
        length = settings.OTP_CODE_LENGTH
        code = "".join(str(secrets.randbelow(10)) for _ in range(length))
        return cls.objects.create(
            phone=phone,
            code=code,
            purpose=purpose,
            user=user,
            expires_at=timezone.now() + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
        )

    @classmethod
    def last_for(cls, phone, purpose=OTPPurpose.LOGIN):
        return cls.objects.filter(phone=normalize_phone(phone), purpose=purpose).first()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def seconds_left(self):
        return max(int((self.expires_at - timezone.now()).total_seconds()), 0)

    @property
    def can_resend(self):
        return (timezone.now() - self.created_at).total_seconds() >= settings.OTP_RESEND_SECONDS

    def verify(self, code):
        """کد ورودی را بررسی می‌کند و در صورت درستی مصرف می‌شود."""
        if self.is_used or self.is_expired:
            return False
        if self.attempts >= settings.OTP_MAX_ATTEMPTS:
            return False
        self.attempts += 1
        if self.code != str(code).strip():
            self.save(update_fields=["attempts"])
            return False
        self.is_used = True
        self.save(update_fields=["attempts", "is_used"])
        return True
