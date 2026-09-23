"""
Django settings for the Matinsh salon booking project.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure--c@v438lk$^ct_z!v%6ww23-rn&_wm*1$h8cm!8p3o09zp60jz",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DJANGO_DEBUG", default=True)

_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(",") if h.strip()] or ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Local apps
    "accounts",
    "salon",
    "services",
    "bookings",
    "payments",
    "gallery",
    "articles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "salon.context_processors.salon_profile",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "accounts.User"


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "fa"

TIME_ZONE = "Asia/Tehran"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Auth redirects

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "core:home"


# ---------------------------------------------------------------------------
# SMS gateway (used for phone-number verification / OTP codes)
# ---------------------------------------------------------------------------
# Swap SMS_BACKEND to a real provider once credentials are available.
# Built-in choices:
#   "accounts.sms.backends.ConsoleSmsBackend"   -> prints the code to the
#                                                   console/log (default, for
#                                                   local development)
#   "accounts.sms.backends.KavenegarSmsBackend" -> sends via kavenegar.com
SMS_BACKEND = os.environ.get("SMS_BACKEND", "accounts.sms.backends.ConsoleSmsBackend")
KAVENEGAR_API_KEY = os.environ.get("KAVENEGAR_API_KEY", "")
KAVENEGAR_SENDER = os.environ.get("KAVENEGAR_SENDER", "")
KAVENEGAR_OTP_TEMPLATE = os.environ.get("KAVENEGAR_OTP_TEMPLATE", "verify")

OTP_CODE_LENGTH = 5
OTP_EXPIRY_SECONDS = 120
OTP_RESEND_COOLDOWN_SECONDS = 60


# ---------------------------------------------------------------------------
# Payment gateway (ZarinPal) - used for taking the appointment deposit
# (بیعانه). Fill in ZARINPAL_MERCHANT_ID with a real merchant id and set
# ZARINPAL_SANDBOX=False before going live.
# ---------------------------------------------------------------------------
ZARINPAL_MERCHANT_ID = os.environ.get(
    "ZARINPAL_MERCHANT_ID", "00000000-0000-0000-0000-000000000000"
)
ZARINPAL_SANDBOX = env_bool("ZARINPAL_SANDBOX", default=True)
ZARINPAL_CALLBACK_BASE_URL = os.environ.get("ZARINPAL_CALLBACK_BASE_URL", "")

SITE_NAME = os.environ.get("SITE_NAME", "آرایشگاه متین")

# How far ahead (in days) a customer may book an appointment.
BOOKING_MAX_ADVANCE_DAYS = int(os.environ.get("BOOKING_MAX_ADVANCE_DAYS", "60"))
