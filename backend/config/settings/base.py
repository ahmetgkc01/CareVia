import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = False
ALLOWED_HOSTS = [
    host
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts",
    "apps.dashboard",
    "apps.clinicians",
    "apps.patients",
    "apps.appointments",
    "apps.assistant",
    "apps.auditlog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.auditlog.middleware.AuditLogMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "carevia"),
        "USER": os.getenv("POSTGRES_USER", "carevia"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "carevia"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "OPTIONS": (
            {"sslmode": os.environ["POSTGRES_SSLMODE"]}
            if os.getenv("POSTGRES_SSLMODE")
            else {}
        ),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr"
LANGUAGES = [("tr", "Türkçe"), ("en", "English")]
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "login": os.getenv("LOGIN_THROTTLE_RATE", "5/min"),
        "assistant": os.getenv("ASSISTANT_THROTTLE_RATE", "20/hour"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Carevia API",
    "DESCRIPTION": "Healthcare management portfolio API using synthetic data.",
    "VERSION": "0.1.0",
}

CORS_ALLOWED_ORIGINS = [
    origin
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin
]
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin
]
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# The assistant works in deterministic demo mode until a provider URL and model
# are configured. The embedding key can be reused without duplicating the secret.
GENAI_API_URL = os.getenv("GENAI_API_URL", "")
GENAI_API_KEY = os.getenv("GENAI_API_KEY") or os.getenv("EMBEDDING_API_KEY", "")
GENAI_MODEL = os.getenv("GENAI_MODEL", "")
GENAI_TIMEOUT_SECONDS = int(os.getenv("GENAI_TIMEOUT_SECONDS", "20"))
GENAI_INPUT_COST_PER_MILLION = float(
    os.getenv("GENAI_INPUT_COST_PER_MILLION", "0")
)
GENAI_OUTPUT_COST_PER_MILLION = float(
    os.getenv("GENAI_OUTPUT_COST_PER_MILLION", "0")
)
ASSISTANT_HISTORY_MESSAGES = int(os.getenv("ASSISTANT_HISTORY_MESSAGES", "6"))
ASSISTANT_HISTORY_MAX_CHARS = int(os.getenv("ASSISTANT_HISTORY_MAX_CHARS", "6000"))

EMBEDDING_API_URL = os.getenv(
    "EMBEDDING_API_URL",
    "https://api.openai.com/v1/embeddings",
)
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
EMBEDDING_TIMEOUT_SECONDS = int(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "20"))
KNOWLEDGE_SEARCH_LIMIT = int(os.getenv("KNOWLEDGE_SEARCH_LIMIT", "3"))
KNOWLEDGE_MAX_COSINE_DISTANCE = float(
    os.getenv("KNOWLEDGE_MAX_COSINE_DISTANCE", "0.45")
)

