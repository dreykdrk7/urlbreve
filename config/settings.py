"""Django settings for urlbreve.

The project reads configuration from the process environment only. It does not
load a local .env file at runtime; .env.example is documentation for operators.
"""

from pathlib import Path
from urllib.parse import parse_qsl, urlparse
import os


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def database_from_url(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use postgres:// or postgresql://")

    options = dict(parse_qsl(parsed.query))
    config: dict[str, object] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
    }
    if options:
        config["OPTIONS"] = options
    return config


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0,testserver",
)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

URLBREVE_ANONYMOUS_API_ENABLED = env_bool(
    "URLBREVE_ANONYMOUS_API_ENABLED",
    default=True,
)
URLBREVE_RATE_LIMITING_ENABLED = env_bool(
    "URLBREVE_RATE_LIMITING_ENABLED",
    default=True,
)
URLBREVE_ANONYMOUS_DAILY_LIMIT = env_int("URLBREVE_ANONYMOUS_DAILY_LIMIT", 20)
URLBREVE_AUTHENTICATED_DAILY_LIMIT = env_int(
    "URLBREVE_AUTHENTICATED_DAILY_LIMIT",
    100,
)
URLBREVE_API_KEY_DAILY_LIMIT = env_int("URLBREVE_API_KEY_DAILY_LIMIT", 200)
URLBREVE_REPORT_SESSION_DAILY_LIMIT = env_int(
    "URLBREVE_REPORT_SESSION_DAILY_LIMIT",
    10,
)
URLBREVE_REPORT_HONEYPOT_ENABLED = env_bool(
    "URLBREVE_REPORT_HONEYPOT_ENABLED",
    default=True,
)
URLBREVE_PASSWORD_GATE_SESSION_LIMIT = env_int(
    "URLBREVE_PASSWORD_GATE_SESSION_LIMIT",
    5,
)
URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_ENABLED = env_bool(
    "URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_ENABLED",
    default=True,
)
URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_LIMIT = env_int(
    "URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_LIMIT",
    20,
)
URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_SECONDS = env_int(
    "URLBREVE_PASSWORD_GATE_LINK_COOLDOWN_SECONDS",
    300,
)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "links",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

database_url = os.environ.get("DATABASE_URL")
if database_url:
    DATABASES = {"default": database_from_url(database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "urlbreve"),
            "USER": os.environ.get("POSTGRES_USER", "urlbreve"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "urlbreve"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5433"),
        }
    }


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

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "home"
