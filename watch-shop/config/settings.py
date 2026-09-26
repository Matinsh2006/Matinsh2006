"""
Django settings for the watch shop.

Every secret or environment-specific value is read from environment variables,
optionally loaded from a local `.env` file (see `.env.example`).
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Tiny `.env` loader so the project has no extra dependency for it."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key, default=0):
    value = os.environ.get(key)
    return int(value) if value not in (None, "") else default


def env_list(key, default=""):
    return [item.strip() for item in env(key, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", True)

SECRET_KEY = env("SECRET_KEY") or ("django-insecure-dev-only-key" if DEBUG else None)
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is off.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Public base URL (e.g. https://example.ir). Used to build payment callback
# URLs when the app runs behind a proxy. Falls back to the request host.
SITE_URL = env("SITE_URL", "").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    # Local apps
    "core",
    "accounts",
    "catalog",
    "cart",
    "orders",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
                "core.context_processors.shop",
                "cart.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database: SQLite by default, PostgreSQL when DB_ENGINE=postgres
# ---------------------------------------------------------------------------
if env("DB_ENGINE", "sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "watchshop"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication (phone-number based users)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "core:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fa-ir"
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
# Let Django itself serve uploaded media when no web server (nginx) is in
# front of it, e.g. on small PaaS deployments.
SERVE_MEDIA = env_bool("SERVE_MEDIA", DEBUG)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

# ---------------------------------------------------------------------------
# Security (production)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days

# ---------------------------------------------------------------------------
# SMS panel (OTP)
# ---------------------------------------------------------------------------
# console | kavenegar | smsir | melipayamak | dotted.path.to.Backend
SMS_BACKEND = env("SMS_BACKEND", "console")
SMS_TIMEOUT = env_int("SMS_TIMEOUT", 10)

KAVENEGAR_API_KEY = env("KAVENEGAR_API_KEY", "")
KAVENEGAR_OTP_TEMPLATE = env("KAVENEGAR_OTP_TEMPLATE", "")

SMSIR_API_KEY = env("SMSIR_API_KEY", "")
SMSIR_OTP_TEMPLATE_ID = env("SMSIR_OTP_TEMPLATE_ID", "")
SMSIR_OTP_PARAM_NAME = env("SMSIR_OTP_PARAM_NAME", "CODE")

MELIPAYAMAK_USERNAME = env("MELIPAYAMAK_USERNAME", "")
MELIPAYAMAK_PASSWORD = env("MELIPAYAMAK_PASSWORD", "")
MELIPAYAMAK_OTP_BODY_ID = env("MELIPAYAMAK_OTP_BODY_ID", "")

OTP_LENGTH = env_int("OTP_LENGTH", 5)
OTP_TTL_SECONDS = env_int("OTP_TTL_SECONDS", 120)
OTP_RESEND_SECONDS = env_int("OTP_RESEND_SECONDS", 60)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_MAX_PER_HOUR = env_int("OTP_MAX_PER_HOUR", 6)
OTP_MAX_PER_IP_HOUR = env_int("OTP_MAX_PER_IP_HOUR", 20)
# Show the OTP in a flash message (only effective with the console backend).
OTP_DEBUG_SHOW_CODE = env_bool("OTP_DEBUG_SHOW_CODE", DEBUG)

# ---------------------------------------------------------------------------
# Payment gateways
# ---------------------------------------------------------------------------
# Enabled gateways, first one is the default: zarinpal, zibal, fake
PAYMENT_GATEWAYS = env_list("PAYMENT_GATEWAYS", "fake,zarinpal,zibal" if DEBUG else "zarinpal")
# The fake gateway marks orders as paid without real money; never enable it
# on a public production site.
PAYMENT_ALLOW_FAKE = env_bool("PAYMENT_ALLOW_FAKE", DEBUG)
PAYMENT_TIMEOUT = env_int("PAYMENT_TIMEOUT", 15)

ZARINPAL_MERCHANT_ID = env("ZARINPAL_MERCHANT_ID", "")
ZARINPAL_SANDBOX = env_bool("ZARINPAL_SANDBOX", True)

# "zibal" is Zibal's public test merchant.
ZIBAL_MERCHANT = env("ZIBAL_MERCHANT", "zibal")

# ---------------------------------------------------------------------------
# Map (store location)
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
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "accounts": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "payments": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
