"""
تنظیمات پروژه‌ی سایت مغازه صافکاری.

مقادیر حساس از متغیرهای محیطی خوانده می‌شوند. برای اجرای محلی کافی است
فایل ‎.env.example‎ را به ‎.env‎ کپی کنید.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None):
    value = os.environ.get(key)
    return default if value is None or value == "" else value


def env_bool(key, default=False):
    value = env(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def env_list(key, default=None):
    value = env(key)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


# خواندن فایل .env در صورت وجود (بدون وابستگی خارجی)
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _value = _line.split("=", 1)
        os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))

SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-dev-key-change-me-in-production")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"] if DEBUG else [])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # اپ‌های پروژه
    "core",
    "accounts",
    "services",
    "gallery",
    "blog",
    "appointments",
    "payments",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# در صورت نصب‌نبودن whitenoise، میدل‌ور حذف می‌شود تا پروژه بالا بیاید.
try:  # pragma: no cover - وابسته به محیط
    import whitenoise  # noqa: F401
except ImportError:  # pragma: no cover
    MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
            "builtins": ["core.templatetags.persian"],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.PhoneBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG and "whitenoise.middleware.WhiteNoiseMiddleware" in MIDDLEWARE
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "core:home"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# ---------------------------------------------------------------------------
# پنل پیامکی (ارسال کد تایید)
# ---------------------------------------------------------------------------
# مقادیر مجاز: console (نمایش در ترمینال)، kavenegar، smsir، ghasedak
SMS_BACKEND = env("SMS_BACKEND", "accounts.sms.ConsoleSMSBackend" if DEBUG else "accounts.sms.KavenegarSMSBackend")
SMS_API_KEY = env("SMS_API_KEY", "")
SMS_SENDER = env("SMS_SENDER", "")
SMS_TEMPLATE = env("SMS_TEMPLATE", "verify")
SMS_TIMEOUT = int(env("SMS_TIMEOUT", "10"))

OTP_LENGTH = int(env("OTP_LENGTH", "5"))
OTP_TTL_SECONDS = int(env("OTP_TTL_SECONDS", "120"))
OTP_MAX_ATTEMPTS = int(env("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN = int(env("OTP_RESEND_COOLDOWN", "60"))
OTP_HOURLY_LIMIT = int(env("OTP_HOURLY_LIMIT", "6"))

# ---------------------------------------------------------------------------
# درگاه پرداخت (بیعانه)
# ---------------------------------------------------------------------------
# مقادیر مجاز: payments.gateways.SandboxGateway | payments.gateways.ZarinPalGateway
PAYMENT_GATEWAY = env("PAYMENT_GATEWAY", "payments.gateways.SandboxGateway")
ZARINPAL_MERCHANT_ID = env("ZARINPAL_MERCHANT_ID", "")
ZARINPAL_SANDBOX = env_bool("ZARINPAL_SANDBOX", True)
PAYMENT_CURRENCY = env("PAYMENT_CURRENCY", "IRT")  # IRT = تومان، IRR = ریال
PAYMENT_TIMEOUT = int(env("PAYMENT_TIMEOUT", "15"))

# ---------------------------------------------------------------------------
# محدودیت آپلود عکس آگهی مشتری
# ---------------------------------------------------------------------------
APPOINTMENT_MAX_PHOTOS = int(env("APPOINTMENT_MAX_PHOTOS", "8"))
APPOINTMENT_MAX_PHOTO_SIZE_MB = int(env("APPOINTMENT_MAX_PHOTO_SIZE_MB", "5"))

DATA_UPLOAD_MAX_NUMBER_FILES = 60
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# تنظیمات امنیتی حالت تولید
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}
