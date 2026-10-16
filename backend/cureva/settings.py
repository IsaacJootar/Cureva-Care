"""
Django settings for Cureva Care.

Locked stack (cureva-docs/04-architecture-and-stack.md):
  Python + Django + DRF, PostgreSQL, django-q2 jobs, JWT credentials for the
  decoupled Next.js frontend, magic-link + Google SSO auth owned by Django.

Secrets are read from the environment only, never from platform_settings and
never committed (cureva-docs/07-security-privacy-access.md). Admin-tunable
operational values live in the platform_settings table instead.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
# Load backend/.env if present (local dev). In production, real env vars win.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# --- Applications ---------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_q",
]

# The five service-boundary apps (cureva-docs/04-architecture-and-stack.md).
# They deploy together but keep strict ownership: nothing outside Register
# Intake writes a source row; nothing outside Maternal Projection writes a
# Woman/Episode/Event.
LOCAL_APPS = [
    "identity_access",
    "register_intake",
    "maternal_projection",
    "intelligence",
    "reporting",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cureva.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cureva.wsgi.application"
ASGI_APPLICATION = "cureva.asgi.application"

# --- Database -------------------------------------------------------------
# PostgreSQL only (locked). Local dev points at the isolated Cureva container
# on port 5434 (infra/docker-compose.yml).
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://cureva:cureva_dev_pw@127.0.0.1:5434/cureva",
    )
}

# --- Custom user ----------------------------------------------------------
AUTH_USER_MODEL = "identity_access.User"

AUTH_PASSWORD_VALIDATORS = []  # No passwords exist in this product (magic-link / SSO only).

# --- Internationalization -------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"  # Nigeria-focused deployment (NDPA 2023 context).
USE_I18N = True
USE_TZ = True

# --- Static files ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    # Scoped throttles for the auth endpoints (07-security-privacy-access.md:
    # login and magic-link-request are rate-limited per email and per IP).
    "DEFAULT_THROTTLE_RATES": {
        "magic_link": "5/min",
        "session_exchange": "20/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- CORS -----------------------------------------------------------------
# Only the Cureva Next.js frontend origin(s) may call the API with credentials
# (cureva-docs/05-api-routes.md).
FRONTEND_ORIGIN = env("FRONTEND_ORIGIN", default="http://localhost:3000")
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
CORS_ALLOW_CREDENTIALS = True

# --- Background jobs (django-q2) ------------------------------------------
# Database-backed ORM broker — no Redis/Celery (locked stack).
Q_CLUSTER = {
    "name": "cureva",
    "workers": 2,
    "timeout": 600,
    "retry": 1200,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
    "catch_up": False,
}

# --- Email (magic-link delivery) ------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@cureva.care")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# --- Auth: magic-link + Google SSO (Django owns both) ---------------------
MAGIC_LINK_TTL_MINUTES = env.int("MAGIC_LINK_TTL_MINUTES", default=15)  # single-use, short-lived (07-security-privacy-access.md); prod keeps 15, local dev may widen via .env
# Links are single-use in production. Local dev MAY set this False in .env to
# make a sign-in link reusable until it expires (convenient for repeated manual
# testing). Never ship False — it removes a security property.
MAGIC_LINK_SINGLE_USE = env.bool("MAGIC_LINK_SINGLE_USE", default=True)
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")

# --- External services (secrets; never in platform_settings) --------------
# OCR/vision provider. The pilot default in the docs is Claude, but the
# provider is swappable behind `extraction_engine` (open decision #8). The
# active provider is chosen by EXTRACTION_PROVIDER, or auto-detected from
# whichever key is configured (OpenAI preferred when both are set).
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_VISION_MODEL = env("ANTHROPIC_VISION_MODEL", default="claude-sonnet-5-5")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_VISION_MODEL = env("OPENAI_VISION_MODEL", default="gpt-4o")
EXTRACTION_PROVIDER = env("EXTRACTION_PROVIDER", default="auto")  # auto|openai|claude
TERMII_API_KEY = env("TERMII_API_KEY", default="")
TERMII_SENDER_ID = env("TERMII_SENDER_ID", default="Cureva")

# --- Object storage (S3-compatible; MinIO in dev) -------------------------
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="http://127.0.0.1:9102")
S3_ACCESS_KEY = env("S3_ACCESS_KEY", default="cureva")
S3_SECRET_KEY = env("S3_SECRET_KEY", default="cureva_dev_pw")
S3_BUCKET = env("S3_BUCKET", default="cureva-sources")
S3_REGION = env("S3_REGION", default="us-east-1")

# --- Logging: never log PHI (07-security-privacy-access.md) ---------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
