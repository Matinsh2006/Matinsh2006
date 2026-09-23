from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

phone_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="شماره موبایل باید به‌صورت ۰۹xxxxxxxxx و ۱۱ رقم باشد.",
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("شماره موبایل الزامی است.")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_phone_verified", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        "شماره موبایل", max_length=11, unique=True, validators=[phone_validator]
    )
    full_name = models.CharField("نام و نام خانوادگی", max_length=150, blank=True)
    is_phone_verified = models.BooleanField("شماره تأیید شده", default=False)
    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField("دسترسی به مدیریت", default=False)
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.full_name or self.phone_number

    def get_short_name(self):
        return self.full_name or self.phone_number

    def get_full_name(self):
        return self.full_name or self.phone_number


class OTP(models.Model):
    PURPOSE_LOGIN = "login"
    PURPOSE_CHANGE_PHONE = "change_phone"
    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, "ورود / ثبت‌نام"),
        (PURPOSE_CHANGE_PHONE, "تغییر شماره موبایل"),
    ]

    phone_number = models.CharField(
        "شماره موبایل", max_length=11, validators=[phone_validator]
    )
    code = models.CharField("کد تایید", max_length=8)
    purpose = models.CharField(
        "کاربرد", max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_LOGIN
    )
    created_at = models.DateTimeField("زمان ارسال", auto_now_add=True)
    expires_at = models.DateTimeField("زمان انقضا")
    is_used = models.BooleanField("استفاده شده", default=False)
    attempts = models.PositiveSmallIntegerField("تعداد تلاش", default=0)

    class Meta:
        verbose_name = "کد تایید پیامکی"
        verbose_name_plural = "کدهای تایید پیامکی"
        ordering = ["-created_at"]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.phone_number} ({self.get_purpose_display()})"
