"""
LearnEas — Configuration Django
Plateforme de vente de cours (playlists complètes) et de PDF (seuls ou inclus dans un cours).
"""
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-secret-key-change-me")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",

    # local apps
    "apps.accounts",
    "apps.catalog",
    "apps.enrollments",
    "apps.payments",
    "apps.reviews",
    "apps.faq",
    "apps.chat",
    "apps.formations",
    "rest_framework_simplejwt.token_blacklist",
]

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

ROOT_URLCONF = "learneas.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "learneas.wsgi.application"
ASGI_APPLICATION = "learneas.asgi.application"

import dj_database_url

DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
            "NAME": config("DB_NAME", default=BASE_DIR / "db.sqlite3"),
            "USER": config("DB_USER", default=""),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default=""),
            "PORT": config("DB_PORT", default=""),
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Casablanca"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
USE_S3 = config("USE_S3", default=False, cast=bool)
REQUIRE_REMOTE_MEDIA = config("REQUIRE_REMOTE_MEDIA", default=False, cast=bool)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Railway utilise un disque éphémère par défaut : activez USE_S3 avec un bucket S3-compatible
# (AWS, Cloudflare R2, Backblaze, MinIO, etc.) pour conserver durablement les médias.
if USE_S3:
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default=None)
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 300
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "private, no-store"}
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN.rstrip('/')}/"
    elif AWS_S3_ENDPOINT_URL:
        MEDIA_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
elif not DEBUG and REQUIRE_REMOTE_MEDIA:
    raise RuntimeError("Stockage média distant requis : configurez USE_S3=True et les variables AWS/S3.")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# DRF / JWT / CORS / API docs
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # L’API LearnEas est authentifiée exclusivement par JWT.
    # Ne pas activer SessionAuthentication ici : une session Django (par exemple après
    # connexion à /admin/) ferait appliquer un contrôle CSRF aux endpoints publics
    # /api/auth/login/ et /api/auth/register/, alors que le frontend Next.js utilise JWT.
    # L’admin Django conserve sa propre authentification par session et sa protection CSRF.
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.PasswordBoundJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/hour",
        "user": "1200/hour",
        "auth": "10/min",
        "password_reset": "5/hour",
        "checkout": "20/hour",
        "media": "300/hour",
        "live": "12000/hour",
        "admin_test": "30/hour",
        "webhook": "3000/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)

SPECTACULAR_SETTINGS = {
    "TITLE": "LearnEas API",
    "DESCRIPTION": "API de la plateforme de formation en ligne LearnEas",
    "VERSION": "1.0.0",
}

STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_TEST_SECRET_KEY = config("STRIPE_TEST_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_TEST_WEBHOOK_SECRET = config("STRIPE_TEST_WEBHOOK_SECRET", default="")
YOUCANPAY_ACCESS_TOKEN = config("YOUCANPAY_ACCESS_TOKEN", default="")
YOUCANPAY_API_BASE = config("YOUCANPAY_API_BASE", default="https://youcanpay.com/api/v2")
# Le sandbox YouCan Pay est entièrement configurable. Les jetons sandbox et production sont
# volontairement séparés : une passerelle en mode test ne réutilise jamais un secret live.
YOUCANPAY_SANDBOX_ACCESS_TOKEN = config("YOUCANPAY_SANDBOX_ACCESS_TOKEN", default="")
YOUCANPAY_SANDBOX_API_BASE = config("YOUCANPAY_SANDBOX_API_BASE", default="")
GENIUSPAY_API_KEY = config("GENIUSPAY_API_KEY", default="")
GENIUSPAY_API_SECRET = config("GENIUSPAY_API_SECRET", default="")
GENIUSPAY_WEBHOOK_SECRET = config("GENIUSPAY_WEBHOOK_SECRET", default="")
GENIUSPAY_API_BASE = config("GENIUSPAY_API_BASE", default="https://geniuspay.ci/api/v1/merchant")
GENIUSPAY_SANDBOX_API_KEY = config("GENIUSPAY_SANDBOX_API_KEY", default="")
GENIUSPAY_SANDBOX_API_SECRET = config("GENIUSPAY_SANDBOX_API_SECRET", default="")
GENIUSPAY_SANDBOX_WEBHOOK_SECRET = config("GENIUSPAY_SANDBOX_WEBHOOK_SECRET", default="")
GENIUSPAY_SANDBOX_API_BASE = config("GENIUSPAY_SANDBOX_API_BASE", default="")
PAYMENT_CURRENCY = config("PAYMENT_CURRENCY", default="MAD")

# Répartition des ventes instructeurs / plateforme
PLATFORM_COMMISSION_PERCENT = config("PLATFORM_COMMISSION_PERCENT", default=15, cast=int)
MINIMUM_PAYOUT_AMOUNT = config("MINIMUM_PAYOUT_AMOUNT", default=100, cast=int)
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")

# ---------------------------------------------------------------------------
# Email — console en développement (le lien de réinitialisation s'affiche dans les
# logs du conteneur backend), SMTP réel en production via variables d'environnement.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend" if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="LearnEas <no-reply@learneas.com>")

# ---------------------------------------------------------------------------
# Redis / Celery (emails asynchrones, tâches planifiées) — service "redis" du docker-compose
# ---------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
    }
}
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# ---------------------------------------------------------------------------
# Sécurité production — activée uniquement si DEBUG=False.
# IMPORTANT : les cookies "Secure" (SESSION_COOKIE_SECURE / CSRF_COOKIE_SECURE) ne doivent être
# activés QUE si le site est réellement servi en HTTPS. Sinon le navigateur refuse de renvoyer
# ces cookies, et TOUT formulaire (dont la connexion à /admin/) échoue avec une erreur CSRF 403,
# même avec des identifiants corrects. Par défaut (installation Docker locale en http://localhost),
# USE_HTTPS reste à False. Passez USE_HTTPS=True dans votre .env uniquement si nginx/un reverse
# proxy termine bien du HTTPS devant l'application.
# ---------------------------------------------------------------------------
if not DEBUG:
    USE_HTTPS = config("USE_HTTPS", default=False, cast=bool)
    SECURE_SSL_REDIRECT = USE_HTTPS
    SESSION_COOKIE_SECURE = USE_HTTPS
    CSRF_COOKIE_SECURE = USE_HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    if USE_HTTPS:
        SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
        SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)
        SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
    CSRF_TRUSTED_ORIGINS = config(
        "CSRF_TRUSTED_ORIGINS",
        default="http://localhost,http://127.0.0.1",
        cast=Csv(),
    )


# Garde-fous de déploiement : refuser les secrets/hosts de développement en production.
if not DEBUG:
    if SECRET_KEY in {"dev-secret-key-change-me", "change-me-in-production"} or len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY invalide pour la production.")
    if "*" in ALLOWED_HOSTS:
        raise RuntimeError("ALLOWED_HOSTS='*' est interdit en production.")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"
