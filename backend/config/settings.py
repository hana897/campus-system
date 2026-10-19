"""
Django settings for config project.
"""

from pathlib import Path
from urllib.parse import unquote, urlparse
import os

# --------------------------------------------------
# Base Directory
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Read local secrets from backend/.env. Values already set by the shell win.
_ENV_FILE = BASE_DIR / ".env"
if _ENV_FILE.is_file():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _value = _line.split("=", 1)
        os.environ.setdefault(_key.strip(), _value.strip().strip("\"'"))


# --------------------------------------------------
# Security
# --------------------------------------------------
DEBUG = os.environ.get("DJANGO_DEBUG", "1").lower() in {"1", "true", "yes", "on"}

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "django-insecure-local-development-only"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

# Render provides the service's public hostname automatically.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in {"localhost", "127.0.0.1"}]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# --------------------------------------------------
# Installed Applications
# --------------------------------------------------
INSTALLED_APPS = [
    "accounts",
    "owners",
    "assets",
    "verification",
    "dashboard",
    "reports",
    "api",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


# --------------------------------------------------
# Middleware
# --------------------------------------------------
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


# --------------------------------------------------
# URLs
# --------------------------------------------------
ROOT_URLCONF = "config.urls"


# --------------------------------------------------
# Templates
# --------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

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


# --------------------------------------------------
# WSGI
# --------------------------------------------------
WSGI_APPLICATION = "config.wsgi.application"


# --------------------------------------------------
# Database
# --------------------------------------------------
def _build_database_settings():
    # A single DATABASE_URL (as Render shows it) overrides the PG* variables.
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        parsed = urlparse(database_url)
        os.environ["PGDATABASE"] = unquote(parsed.path.lstrip("/"))
        os.environ["PGUSER"] = unquote(parsed.username or "")
        os.environ["PGPASSWORD"] = unquote(parsed.password or "")
        os.environ["PGHOST"] = parsed.hostname or ""
        os.environ["PGPORT"] = str(parsed.port or 5432)

    pg_db = os.environ.get("PGDATABASE", "campus_securitydb")
    pg_user = os.environ.get("PGUSER", "postgres")
    pg_password = os.environ.get("PGPASSWORD", "")
    pg_host = os.environ.get("PGHOST", "localhost")
    pg_port = os.environ.get("PGPORT", "5432")

    if os.environ.get("USE_SQLITE", "0").lower() in {"1", "true", "yes", "on"}:
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }

    if not all([pg_db, pg_user, pg_host]):
        raise RuntimeError("PGDATABASE, PGUSER, and PGHOST must be configured.")

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": pg_db,
            "USER": pg_user,
            "PASSWORD": pg_password,
            "HOST": pg_host,
            "PORT": pg_port,
            "CONN_MAX_AGE": int(os.environ.get("PGCONN_MAX_AGE", "60")),
            "OPTIONS": {"connect_timeout": int(os.environ.get("PGCONNECT_TIMEOUT", "5"))},
        }
    }


DATABASES = _build_database_settings()


# --------------------------------------------------
# Password Validation
# --------------------------------------------------
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


# --------------------------------------------------
# Internationalization
# --------------------------------------------------
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# --------------------------------------------------
# Static Files
# --------------------------------------------------
STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# --------------------------------------------------
# Media Files
# --------------------------------------------------
MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# --------------------------------------------------
# Default Primary Key
# --------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------
# Custom User Model
# --------------------------------------------------
AUTH_USER_MODEL = "accounts.User"


# --------------------------------------------------
# Authentication
# --------------------------------------------------
LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = "/dashboard/"

LOGOUT_REDIRECT_URL = "/"


# --------------------------------------------------
# Session Settings
# --------------------------------------------------
# End the session when the browser closes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Session expires after 30 minutes of inactivity
SESSION_COOKIE_AGE = 1800

# Refresh the timeout after each request
SESSION_SAVE_EVERY_REQUEST = True
