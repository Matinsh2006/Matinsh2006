from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.utils.images import optimize_image_field
from apps.core.utils.text import normalize_phone

from .fields import PhoneNumberField, iran_mobile_validator, postal_code_validator

PROVINCES = (
    "آذربایجان شرقی", "آذربایجان غربی", "اردبیل", "اصفهان", "البرز", "ایلام", "بوشهر", "تهران",
    "چهارمحال و بختیاری", "خراسان جنوبی", "خراسان رضوی", "خراسان شمالی", "خوزستان", "زنجان",
    "سمنان", "سیستان و بلوچستان", "فارس", "قزوین", "قم", "کردستان", "کرمان", "کرمانشاه",
    "کهگیلویه و بویراحمد", "گلستان", "گیلان", "لرستان", "مازندران", "مرکزی", "هرمزگان", "همدان", "یزد",
)
PROVINCE_CHOICES = [(name, name) for name in PROVINCES]


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        phone = normalize_phone(phone)
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        if not password:
            raise ValueError("Superuser must have a password (used to log in to the admin panel).")
        return self._create_user(phone, password, **extra_fields)

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: normalize_phone(username)})


class User(AbstractBaseUser, PermissionsMixin):
    """Site user; the mobile number is the username and is verified by SMS."""

    phone = PhoneNumberField(
        "شماره موبایل",
        unique=True,
        validators=[iran_mobile_validator],
        error_messages={"unique": "کاربری با این شماره موبایل قبلاً ثبت شده است."},
    )
    first_name = models.CharField("نام", max_length=100, blank=True)
    last_name = models.CharField("نام خانوادگی", max_length=100, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    avatar = models.ImageField("تصویر پروفایل", upload_to="avatars/%Y/%m/", blank=True)
    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField(
        "دسترسی به پنل مدیریت", default=False, help_text="کاربر می‌تواند وارد پنل مدیریت شود."
    )
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)
    phone_verified_at = models.DateTimeField("آخرین تایید شماره موبایل", null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.phone

    def save(self, *args, **kwargs):
        optimize_image_field(self.avatar, max_dimension=400)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.phone

    @property
    def display_name(self):
        return self.get_full_name() or self.phone

    @property
    def is_profile_complete(self):
        return bool(self.first_name and self.last_name)


class OTPCode(models.Model):
    """A hashed one-time code sent by SMS (login/sign-up or phone change)."""

    class Purpose(models.TextChoices):
        LOGIN = "login", "ورود / ثبت‌نام"
        CHANGE_PHONE = "change_phone", "تغییر شماره موبایل"

    phone = models.CharField("شماره موبایل", max_length=11, db_index=True)
    purpose = models.CharField("کاربرد", max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    user = models.ForeignKey(
        User, verbose_name="کاربر", on_delete=models.CASCADE, null=True, blank=True, related_name="otp_codes"
    )
    attempts = models.PositiveSmallIntegerField("تعداد تلاش ناموفق", default=0)
    is_used = models.BooleanField("استفاده/باطل شده", default=False)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True, db_index=True)
    created_at = models.DateTimeField("زمان ارسال", auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField("زمان انقضا")
    used_at = models.DateTimeField("زمان استفاده", null=True, blank=True)

    class Meta:
        verbose_name = "کد تایید پیامکی"
        verbose_name_plural = "کدهای تایید پیامکی"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["phone", "purpose", "created_at"])]

    def __str__(self):
        return f"{self.phone} ({self.get_purpose_display()})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class Address(models.Model):
    user = models.ForeignKey(User, verbose_name="کاربر", on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField("عنوان آدرس", max_length=50, blank=True, help_text="مثلاً خانه یا محل کار")
    receiver_name = models.CharField("نام و نام خانوادگی گیرنده", max_length=120)
    receiver_phone = PhoneNumberField("موبایل گیرنده", validators=[iran_mobile_validator])
    province = models.CharField("استان", max_length=40, choices=PROVINCE_CHOICES)
    city = models.CharField("شهر", max_length=60)
    full_address = models.TextField("آدرس کامل پستی")
    postal_code = models.CharField("کد پستی", max_length=10, validators=[postal_code_validator])
    is_default = models.BooleanField("آدرس پیش‌فرض", default=False)
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return self.title or self.as_text()[:60]

    def save(self, *args, **kwargs):
        others = Address.objects.filter(user_id=self.user_id)
        if self.pk:
            others = others.exclude(pk=self.pk)
        if not others.exists():
            self.is_default = True
        super().save(*args, **kwargs)
        if self.is_default:
            # Built after saving so the new row's own pk is excluded.
            Address.objects.filter(user_id=self.user_id, is_default=True).exclude(pk=self.pk).update(is_default=False)

    def as_text(self):
        return f"{self.province}، {self.city}، {self.full_address}"
