"""
Django settings for the beauty shop project.

All environment-specific values are read from environment variables
(or from a ``.env`` file next to ``manage.py``). See ``.env.example``.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Minimal .env loader: KEY=VALUE lines, ``#`` comments, optional quotes."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_env_file(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key, default=0):
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def env_list(key, default=None):
    value = os.environ.get(key)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me-in-production")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # Project apps
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.blog",
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
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
                "apps.cart.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database (SQLite by default, PostgreSQL when DB_ENGINE=postgresql)
# ---------------------------------------------------------------------------
if env("DB_ENGINE", "sqlite").lower() in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "beauty_shop"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / env("SQLITE_NAME", "db.sqlite3"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication (phone number is the username)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
            if env_bool("DJANGO_STATIC_MANIFEST", False)
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Uploaded images larger than this are resized (keeps pages light on mobile).
IMAGE_MAX_DIMENSION = env_int("IMAGE_MAX_DIMENSION", 1600)

# ---------------------------------------------------------------------------
# Security (production)
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
    CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False)
    if env_bool("DJANGO_BEHIND_PROXY", True):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Admin panel path (change it in production, e.g. "manage-7fa2/").
ADMIN_URL = env("DJANGO_ADMIN_URL", "admin/")

# Header holding the real client IP when running behind nginx (e.g. HTTP_X_REAL_IP).
# Leave empty to use REMOTE_ADDR. Used for per-IP rate limiting of SMS codes.
CLIENT_IP_HEADER = env("CLIENT_IP_HEADER", "")

# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------
SHOP_CURRENCY_LABEL = "تومان"
CART_SESSION_KEY = "cart"
CART_MAX_QUANTITY_PER_ITEM = env_int("CART_MAX_QUANTITY_PER_ITEM", 10)
PRODUCTS_PER_PAGE = env_int("PRODUCTS_PER_PAGE", 12)
ARTICLES_PER_PAGE = env_int("ARTICLES_PER_PAGE", 9)

# ---------------------------------------------------------------------------
# SMS panel & one-time passwords
# ---------------------------------------------------------------------------
# Available backends:
#   apps.accounts.sms.backends.ConsoleSMSBackend      (development: prints the code)
#   apps.accounts.sms.backends.KavenegarSMSBackend    (kavenegar.com – verify/lookup)
#   apps.accounts.sms.backends.SmsIrSMSBackend        (sms.ir – send/verify)
#   apps.accounts.sms.backends.MelipayamakSMSBackend  (melipayamak.com – shared service line)
SMS_BACKEND = env("SMS_BACKEND", "apps.accounts.sms.backends.ConsoleSMSBackend")
SMS_TIMEOUT = env_int("SMS_TIMEOUT", 10)

KAVENEGAR_API_KEY = env("KAVENEGAR_API_KEY", "")
KAVENEGAR_OTP_TEMPLATE = env("KAVENEGAR_OTP_TEMPLATE", "verify")

SMSIR_API_KEY = env("SMSIR_API_KEY", "")
SMSIR_OTP_TEMPLATE_ID = env("SMSIR_OTP_TEMPLATE_ID", "")
SMSIR_OTP_PARAMETER = env("SMSIR_OTP_PARAMETER", "CODE")

MELIPAYAMAK_USERNAME = env("MELIPAYAMAK_USERNAME", "")
MELIPAYAMAK_PASSWORD = env("MELIPAYAMAK_PASSWORD", "")
MELIPAYAMAK_OTP_BODY_ID = env("MELIPAYAMAK_OTP_BODY_ID", "")

OTP_LENGTH = env_int("OTP_LENGTH", 5)
OTP_EXPIRE_SECONDS = env_int("OTP_EXPIRE_SECONDS", 120)
OTP_RESEND_SECONDS = env_int("OTP_RESEND_SECONDS", 120)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_MAX_PER_HOUR = env_int("OTP_MAX_PER_HOUR", 6)
OTP_MAX_PER_IP_PER_HOUR = env_int("OTP_MAX_PER_IP_PER_HOUR", 20)
# Shows the code in a flash message – handy while testing with the console backend.
# Never enabled when DEBUG is off (it would let anyone log in with any number).
OTP_SHOW_CODE_IN_MESSAGE = DEBUG and env_bool("OTP_SHOW_CODE_IN_MESSAGE", True)

# ---------------------------------------------------------------------------
# Payment gateway
# ---------------------------------------------------------------------------
# fake      → built-in test gateway (never use in production)
# zarinpal  → zarinpal.com (set ZARINPAL_MERCHANT_ID)
# zibal     → zibal.ir     (set ZIBAL_MERCHANT, "zibal" is the sandbox merchant)
PAYMENT_GATEWAY = env("PAYMENT_GATEWAY", "fake")
PAYMENT_ALLOW_FAKE_IN_PRODUCTION = env_bool("PAYMENT_ALLOW_FAKE_IN_PRODUCTION", False)
PAYMENT_REQUEST_TIMEOUT = env_int("PAYMENT_REQUEST_TIMEOUT", 15)

ZARINPAL_MERCHANT_ID = env("ZARINPAL_MERCHANT_ID", "")
ZARINPAL_SANDBOX = env_bool("ZARINPAL_SANDBOX", True)

ZIBAL_MERCHANT = env("ZIBAL_MERCHANT", "zibal")

# ---------------------------------------------------------------------------
# Map (Leaflet). Any XYZ tile server can be used.
# ---------------------------------------------------------------------------
MAP_TILE_URL = env("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
MAP_TILE_ATTRIBUTION = env(
    "MAP_TILE_ATTRIBUTION",
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "loggers": {
        "apps": {"handlers": ["console"], "level": env("APP_LOG_LEVEL", "INFO")},
    },
}
