# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Production environment settings module.

Tweaks the base settings so that caching mechanisms are used where possible,
and HTTPS is leveraged where possible to further secure things.
"""
from .includes.base import *  # noqa

# Caching sessions.
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Caching templates.
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    ("django.template.loaders.cached.Loader", TEMPLATE_LOADERS)
]

# The file storage engine to use when collecting static files with the
# collectstatic management command.
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Production logging facility.
root_handlers, django_handlers = [], []

if "sentry" in LOGGING["handlers"]:
    root_handlers.append("sentry")

if LOG_STDOUT:
    root_handlers.append("console")
    django_handlers.append("console")
else:
    root_handlers.append("project")
    django_handlers.append("django")

LOGGING["loggers"].update(
    {
        "": {"handlers": root_handlers, "level": "ERROR", "propagate": False},
        "django": {"handlers": django_handlers, "level": "INFO", "propagate": True},
        "django.security.DisallowedHost": {
            "handlers": django_handlers,
            "level": "CRITICAL",
            "propagate": False,
        },
    }
)

# Only set this when we're behind a reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True  # Sets X-Content-Type-Options: nosniff
SECURE_BROWSER_XSS_FILTER = True  # Sets X-XSS-Protection: 1; mode=block

# Deal with being hosted on a subpath
if subpath and subpath != "/":
    STATIC_URL = f"{subpath}{STATIC_URL}"
    MEDIA_URL = f"{subpath}{MEDIA_URL}"

ENVIRONMENT = config("ENVIRONMENT", "Utrecht")

# Set up APM
ELASTIC_APM_SERVER_URL = config("ELASTIC_APM_SERVER_URL", None)
ELASTIC_APM = {
    "SERVICE_NAME": f"Open Zaak - {ENVIRONMENT}",
    "SECRET_TOKEN": config("ELASTIC_APM_SECRET_TOKEN", "default"),
    "SERVER_URL": ELASTIC_APM_SERVER_URL,
}
if not ELASTIC_APM_SERVER_URL:
    ELASTIC_APM["ENABLED"] = False
    ELASTIC_APM["SERVER_URL"] = "http://localhost:8200"
else:
    MIDDLEWARE = ["elasticapm.contrib.django.middleware.TracingMiddleware"] + MIDDLEWARE
    INSTALLED_APPS = INSTALLED_APPS + [
        "elasticapm.contrib.django",
    ]

#
# Custom settings overrides
#
ENVIRONMENT_SHOWN_IN_ADMIN = False
