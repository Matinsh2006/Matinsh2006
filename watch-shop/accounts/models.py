from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .utils import mask_phone, normalize_phone
from .validators import validate_iran_mobile, validate_postal_code


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")
        user = self.model(phone=normalize_phone(phone), **extra_fields)
        if password:
            user.set_password(password)
        else:
            # Customers sign in with one-time SMS codes only.
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        if not password:
            raise ValueError("مدیر کل باید رمز عبور داشته باشد.")
        return self._create_user(phone, password, **extra_fields)

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: normalize_phone(username)})


class User(AbstractBaseUser, PermissionsMixin):
    """A customer or staff member identified by their mobile number."""

    phone = models.CharField(
        "شماره موبایل",
        max_length=11,
        unique=True,
        validators=[validate_iran_mobile],
        help_text="نام کاربری هر کاربر، شماره موبایل اوست؛ مثال: 09121234567",
        error_messages={"unique": "کاربری با این شماره موبایل قبلاً ثبت شده است."},
    )
    first_name = models.CharField("نام", max_length=60, blank=True)
    last_name = models.CharField("نام خانوادگی", max_length=80, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField(
        "دسترسی به پنل مدیریت", default=False, help_text="آیا کاربر می‌تواند وارد پنل مدیریت شود؟"
    )
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)
    phone_verified_at = models.DateTimeField("زمان تایید موبایل", null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.phone

    def clean(self):
        super().clean()
        self.phone = normalize_phone(self.phone)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.phone

    @property
    def display_name(self):
        return self.get_full_name() or mask_phone(self.phone)

    @property
    def has_complete_profile(self):
        return bool(self.first_name and self.last_name)


class OneTimePassword(models.Model):
    """A hashed SMS verification code for login or phone-number change."""

    class Purpose(models.TextChoices):
        LOGIN = "login", "ورود / ثبت‌نام"
        CHANGE_PHONE = "change_phone", "تغییر شماره موبایل"

    phone = models.CharField("شماره موبایل", max_length=11, db_index=True)
    purpose = models.CharField("کاربرد", max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="otps",
    )
    attempts = models.PositiveSmallIntegerField("تعداد تلاش", default=0)
    is_used = models.BooleanField("استفاده شده", default=False)
    ip_address = models.GenericIPAddressField("آی‌پی", null=True, blank=True)
    created_at = models.DateTimeField("زمان ارسال", auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField("زمان انقضا")

    class Meta:
        verbose_name = "کد تایید پیامکی"
        verbose_name_plural = "کدهای تایید پیامکی"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_purpose_display()} - {self.phone}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


PROVINCES = [
    "آذربایجان شرقی",
    "آذربایجان غربی",
    "اردبیل",
    "اصفهان",
    "البرز",
    "ایلام",
    "بوشهر",
    "تهران",
    "چهارمحال و بختیاری",
    "خراسان جنوبی",
    "خراسان رضوی",
    "خراسان شمالی",
    "خوزستان",
    "زنجان",
    "سمنان",
    "سیستان و بلوچستان",
    "فارس",
    "قزوین",
    "قم",
    "کردستان",
    "کرمان",
    "کرمانشاه",
    "کهگیلویه و بویراحمد",
    "گلستان",
    "گیلان",
    "لرستان",
    "مازندران",
    "مرکزی",
    "هرمزگان",
    "همدان",
    "یزد",
]
PROVINCE_CHOICES = [(name, name) for name in PROVINCES]


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses", verbose_name="کاربر"
    )
    title = models.CharField("عنوان نشانی", max_length=40, default="خانه")
    recipient_name = models.CharField("نام و نام خانوادگی گیرنده", max_length=120)
    recipient_phone = models.CharField(
        "موبایل گیرنده", max_length=11, validators=[validate_iran_mobile]
    )
    province = models.CharField("استان", max_length=40, choices=PROVINCE_CHOICES, default="تهران")
    city = models.CharField("شهر", max_length=60)
    postal_code = models.CharField("کد پستی", max_length=10, validators=[validate_postal_code])
    address = models.TextField("نشانی کامل")
    plaque = models.CharField("پلاک", max_length=20, blank=True)
    unit = models.CharField("واحد", max_length=20, blank=True)
    is_default = models.BooleanField("نشانی پیش‌فرض", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نشانی"
        verbose_name_plural = "نشانی‌ها"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.city}"

    @property
    def full_address(self):
        parts = [self.province, self.city, self.address]
        if self.plaque:
            parts.append(f"پلاک {self.plaque}")
        if self.unit:
            parts.append(f"واحد {self.unit}")
        return "، ".join(parts)

    def save(self, *args, **kwargs):
        self.recipient_phone = normalize_phone(self.recipient_phone)
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        elif not Address.objects.filter(user=self.user, is_default=True).exists():
            Address.objects.filter(pk=self.pk).update(is_default=True)
            self.is_default = True
