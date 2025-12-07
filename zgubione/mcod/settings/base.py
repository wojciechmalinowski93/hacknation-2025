import string
from collections import OrderedDict
from datetime import date

import environ
import sentry_sdk
from bokeh.util.paths import bokehjsdir
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from kombu import Queue
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from wagtail.embeds.oembed_providers import all_providers

from mcod.lib.sentry_falcon import (
    FalconIntegration,
)  # Update to Sentry's integration when

# https://github.com/getsentry/sentry-python/pull/1297 will be merged and released


env = environ.Env()
ROOT_DIR = environ.Path(__file__) - 3
try:
    env.read_env(ROOT_DIR.file(".env"))
except FileNotFoundError:
    pass

APPS_DIR = ROOT_DIR.path("mcod")

DATA_DIR = ROOT_DIR.path("data")

SCHEMAS_DIR = DATA_DIR.path("schemas")

HARVESTER_DATA_DIR = DATA_DIR.path("harvester")

SHACL_SHAPES_DIR = DATA_DIR.path("shacl")

SPEC_DIR = DATA_DIR.path("spec")

LOGS_DIR = str(ROOT_DIR.path("logs"))

DATABASE_DIR = str(ROOT_DIR.path("database"))

COMPONENT = env("COMPONENT", default="admin")

ENVIRONMENT = env("ENVIRONMENT", default="prod")

ENABLE_MONTHLY_REPORTS = env.bool("ENABLE_MONTHLY_REPORTS", False)

ENABLE_CREATE_XML_METADATA_REPORT = env.bool("ENABLE_CREATE_XML_METADATA_REPORT", True)

UPDATE_TASKS_CELERY_BEAT_TIME = env("UPDATE_TASKS_CELERY_BEAT_TIME", default="")

NOTEBOOKS_DIR = env("NOTEBOOKS_DIR", default=str(ROOT_DIR.path("notebooks/notebooks")))

NOTEBOOK_ARGUMENTS = ["--config", "mcod/settings/jupyter_config.py"]

DEBUG = env.bool("DEBUG", False) or env.bool("TEST_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="xb2rTZ57yOY9iCdqR7W+UAWnU")

NEWSLETTER_REMOVE_INACTIVE_TIMEOUT = 60 * 60 * 24  # after 24h.

INSTALLED_APPS = [
    "mcod.hacks",
    "wagtail.contrib.redirects",
    "wagtail.contrib.modeladmin",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.core",
    "wagtail.api.v2",
    "hypereditor",
    "wagtailvideos",
    "modelcluster",
    "taggit",
    "rest_framework",
    "dal",
    "dal_select2",
    "dal_admin_filters",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "admin_confirm",
    "suit",
    "django_elasticsearch_dsl",
    "ckeditor",
    "ckeditor_uploader",
    "rules.apps.AutodiscoverRulesConfig",
    "nested_admin",
    "django_celery_results",
    "django_celery_beat",
    "localflavor",
    "django.contrib.admin",
    "constance",
    "constance.backends.database",
    "rangefilter",
    "modeltrans",
    "celery_progress",
    "django_extensions",
    "channels",
    "notifications",
    "django_admin_multiple_choice_list_filter",
    "auditlog",
    #"logingovpl",
    # Our apps
    "mcod.core",
    "mcod.organizations",
    "mcod.categories",
    "mcod.tags",
    "mcod.applications",
    "mcod.articles",
    "mcod.datasets",
    "mcod.resources",
    "mcod.users",
    "mcod.licenses",
    "mcod.counters",
    "mcod.histories",
    "mcod.searchhistories",
    "mcod.reports",
    "mcod.alerts",
    "mcod.watchers",
    "mcod.suggestions",
    "mcod.newsletter",
    "mcod.harvester",
    "mcod.cms",
    "mcod.laboratory",
    "mcod.academy",
    "mcod.pn_apps",
    "mcod.schedules",
    "mcod.guides",
    "mcod.special_signs",
    "mcod.discourse",
    "mcod.regions",
    "mcod.showcases",
    "mcod.lost_and_found",
]

CMS_MIDDLEWARE = ["mcod.cms.middleware.CounterMiddleware"] if COMPONENT == "cms" else []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "mcod.cms.middleware.SiteMiddleware",
    *CMS_MIDDLEWARE,
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "mcod.lib.middleware.PostgresConfMiddleware",
    "mcod.lib.middleware.APIAuthTokenMiddleware",
    "mcod.lib.middleware.ComplementUserDataMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
]

ROOT_URLCONF = "mcod.urls"

PN_APPS_URLCONF = "mcod.pn_apps.urls"

WSGI_APPLICATION = "mcod.wsgi.application"
ASGI_APPLICATION = "mcod.routing.application"

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["dane.gov.pl", "admin.dane.gov.pl", "cms.dane.gov.pl", "api.dane.gov.pl"],
)

FIXTURE_DIRS = (str(ROOT_DIR.path("fixtures")),)

ADMINS = [tuple(x.split(":")) for x in env.list("DJANGO_ADMINS", default=["admin:admin@example.com"])]

ADMIN_URL = r"^$"

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
    "mcod.lib.hashers.PBKDF2SHA512PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("email", "fullname"), "max_similarity": 0.6},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "mcod.lib.password_validators.McodPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
        "OPTIONS": {"password_list_path": str(DATA_DIR.path("common-passwords.txt.gz"))},
    },
]

AUTHENTICATION_BACKENDS = [
    "rules.permissions.ObjectPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
]


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="mcod"),
        "USER": env("POSTGRES_USER", default="mcod"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="mcod"),
        "HOST": env("POSTGRES_HOST", default="mcod-db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": env.int("CONN_MAX_AGE", default=0),
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEBUG_EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env("EMAIL_PORT", default=465)
EMAIL_USE_SSL = env("EMAIL_USE_SSL", default="yes") in ("yes", "1", "true")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DATA_UPLOAD_MAX_NUMBER_FIELDS = env("DATA_UPLOAD_MAX_NUMBER_FIELDS", default=10000)

XML_VERSION_SINGLE_CATEGORY = "1.0-rc1"
XML_VERSION_MULTIPLE_CATEGORIES = "1.1"
HARVESTER_XML_VERSION_TO_SCHEMA_PATH = {
    "1.0-rc1": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_0_rc1.xsd").root,
    "1.1": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_1.xsd").root,
    "1.2": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_2.xsd").root,
    "1.3": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_3.xsd").root,
    "1.4": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_4.xsd").root,
    "1.5": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_5.xsd").root,
    "1.6": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_6.xsd").root,
    "1.7": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_7.xsd").root,
    "1.8": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_8.xsd").root,
    "1.9": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_9.xsd").root,
    "1.10": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_10.xsd").root,
    "1.11": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_11.xsd").root,
    "1.12": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_12.xsd").root,
    "1.13": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_13.xsd").root,
}

HARVESTER_IMPORTERS = {
    "ckan": {
        "MEDIA_URL_TEMPLATE": "{}/uploads/group/{}",
        "SCHEMA": "mcod.harvester.serializers.DatasetSchema",
    },
    "xml": {
        "IMPORT_FUNC": "mcod.harvester.utils.fetch_xml_data",
        "SCHEMA": "mcod.harvester.serializers.XMLDatasetSchema",
        "ONE_DATASOURCE_PER_ORGANIZATION": False,
    },
    "dcat": {
        "IMPORT_FUNC": "mcod.harvester.utils.fetch_dcat_data",
        "SCHEMA": "mcod.harvester.serializers.DatasetDCATSchema",
    },
}

HTTP_REQUEST_DEFAULT_HEADERS = {
    "User-Agent": "Otwarte Dane",
}
HTTP_REQUEST_DEFAULT_TIMEOUT = 180

HTTP_REQUEST_DEFAULT_PARAMS = {
    "stream": True,
    "allow_redirects": True,
    "verify": False,
    "timeout": HTTP_REQUEST_DEFAULT_TIMEOUT,
    "headers": HTTP_REQUEST_DEFAULT_HEADERS,
}

# pwgen -ny 64
JWT_SECRET_KEY = env(
    "JWT_SECRET_KEY",
    default="aes_oo7ooSh8phiayohvah0ZieH3ailahh9ieb6ahthah=hing7AhJu7eexeiHoo",
)
JWT_ISS = "Chancellery of the Prime Minister"
JWT_AUD = "dane.gov.pl"
JWT_ALGORITHMS = [
    "HS256",
]
JWT_VERIFY_CLAIMS = ["signature", "exp", "nbf", "iat"]
JWT_REQUIRED_CLAIMS = ["exp", "iat", "nbf"]
JWT_HEADER_PREFIX = "Bearer"
JWT_LEEWAY = 0

AUTH_USER_MODEL = "users.User"

TIME_ZONE = "Europe/Warsaw"
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True

TEMPLATE_DIRS = [
    str(APPS_DIR.path("templates")),
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": TEMPLATE_DIRS,
        "OPTIONS": {
            "debug": DEBUG,
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "constance.context_processors.config",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "mcod.core.contextprocessors.settings",
                "mcod.alerts.contextprocessors.active_alerts",
            ],
        },
    },
]

FORM_RENDERER = "mcod.lib.forms.renderers.TemplatesRenderer"

STATIC_ROOT = str(ROOT_DIR("statics"))
STATIC_URL = "/static/"
STATICFILES_FINDERS = [
    "mcod.lib.staticfiles_finders.StaticRootFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django.contrib.staticfiles.finders.FileSystemFinder",
]

STATICFILES_DIRS = [bokehjsdir()]

MEDIA_ROOT = str(ROOT_DIR("media"))
ACADEMY_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "academy"))
IMAGES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "images"))
MEETINGS_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "meetings"))
NEWSLETTER_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "newsletter"))
RESOURCES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "resources"))
DATASETS_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "datasets"))
REPORTS_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "reports"))
SHOWCASES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "showcases"))
LABORATORY_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "lab_reports"))
RESOURCES_FILES_TO_REMOVE_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "to_be_removed", "resources"))
DCAT_VOCABULARIES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "dcat", "vocabularies"))
METADATA_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "datasets", "catalog"))
DGA_RESOURCE_CREATION_STAGING_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "dga_temp"))
BROKEN_LINKS_CREATION_STAGING_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "broken_links_temp"))
MAIN_DGA_RESOURCE_XLSX_CREATION_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "main_dga"))

MEDIA_URL = "/media/"
ACADEMY_URL = "%s%s" % (MEDIA_URL, "academy")
MEETINGS_URL = "%s%s" % (MEDIA_URL, "meetings")
NEWSLETTER_URL = "%s%s" % (MEDIA_URL, "newsletter")
RESOURCES_URL = "%s%s" % (MEDIA_URL, "resources")
DATASETS_URL = "%s%s" % (MEDIA_URL, "datasets")
SHOWCASES_URL = "%s%s" % (MEDIA_URL, "showcases")
IMAGES_URL = "%s%s" % (MEDIA_URL, "images")
REPORTS_MEDIA = "%s%s" % (MEDIA_URL, "reports")
LABORATORY_URL = "%s%s" % (MEDIA_URL, "lab_reports")
DCAT_VOCABULARIES_URL = "%s%s" % (MEDIA_URL, "dcat/vocabularies")

CKEDITOR_UPLOAD_PATH = "ckeditor/"

LOCALE_PATHS = [
    str(ROOT_DIR.path("translations", "system")),
    str(ROOT_DIR.path("translations", "custom")),
    str(ROOT_DIR.path("translations", "cms")),
]


LANGUAGE_CODE = "pl"

LANGUAGE_COOKIE_NAME = "mcod_language"

LANGUAGES = [
    ("pl", _("Polish")),
    ("en", _("English")),
]

LANG_TO_LOCALE = {"pl": "pl_PL.UTF-8", "en": "en_GB.UTF-8"}

LANGUAGE_CODES = [lang[0] for lang in LANGUAGES]

MODELTRANS_AVAILABLE_LANGUAGES = ("pl", "en")

MODELTRANS_FALLBACK = {
    "default": (LANGUAGE_CODE,),
}

USE_RDF_DB = env("USE_RDF_DB", default="no") in ("yes", "1", "true")
FUSEKI_URL = env("FUSEKI_URL", default="http://mcod-rdfdb:3030")
FUSEKI_DATASET = env("FUSEKI_DATASET_1", default="ds")
SPARQL_QUERY_ENDPOINT = f"{FUSEKI_URL}/{FUSEKI_DATASET}/query"
SPARQL_UPDATE_ENDPOINT = f"{FUSEKI_URL}/{FUSEKI_DATASET}/update"
SPARQL_USER = env("SPARQL_USER", default="admin")
SPARQL_PASSWORD = env("ADMIN_PASSWORD", default="Britenet.1")
SPARQL_CACHE_TIMEOUT = env("SPARQL_CACHE_TIMEOUT", default=60)  # in secs.
REDIS_URL = env("REDIS_URL", default="redis://mcod-redis:6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "%s/0" % REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "%s/1" % REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    # https://docs.wagtail.io/en/stable/advanced_topics/performance.html#caching-image-renditions
    "renditions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "%s/2" % REDIS_URL,
        "TIMEOUT": 600,
        "OPTIONS": {"MAX_ENTRIES": 1000},
    },
}

CMS_API_CACHE_TIMEOUT = env("CMS_API_CACHE_TIMEOUT", default=3600)  # 1 hour.

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "sessions"
SESSION_COOKIE_PREFIX = env("SESSION_COOKIE_PREFIX", default=None)
SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default="dane.gov.pl")
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE", default="yes") in (
    "yes",
    "1",
    "true",
)
SESSION_COOKIE_AGE = env("SESSION_COOKIE_AGE", default=14400)  # 4h
SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_PATH = "/"

SESSION_COOKIE_NAME = "sessionid"
if SESSION_COOKIE_PREFIX:
    SESSION_COOKIE_NAME = SESSION_COOKIE_PREFIX + "_" + SESSION_COOKIE_NAME

API_TOKEN_COOKIE_NAME = "apiauthtoken"
if SESSION_COOKIE_PREFIX:
    API_TOKEN_COOKIE_NAME = SESSION_COOKIE_PREFIX + "_" + API_TOKEN_COOKIE_NAME

JWT_EXPIRATION_DELTA = SESSION_COOKIE_AGE + 2

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

USER_STATE_CHOICES = (
    ("active", _("Active")),
    ("pending", _("Pending")),
    ("blocked", _("Blocked")),
)

USER_STATE_LIST = [choice[0] for choice in USER_STATE_CHOICES]

SUIT_CONFIG = {
    "ADMIN_NAME": _("Open Data - Administration Panel"),
    "HEADER_DATE_FORMAT": "l, j. F Y",
    "HEADER_TIME_FORMAT": "H:i",  # 18:42
    "SHOW_REQUIRED_ASTERISK": True,
    "CONFIRM_UNSAVED_CHANGES": True,
    "SEARCH_URL": "",
    "MENU_OPEN_FIRST_CHILD": True,  # Default True
    "MENU_EXCLUDE": ("auth.group",),
    "MENU": [
        {
            "label": "Dane",
            "models": [
                {
                    "model": "datasets.dataset",
                    "admin_url": "/datasets/dataset",
                    "app_name": "datasets",
                    "label": _("Datasets"),
                    "icon": "icon-database",
                },
                {
                    "model": "resources.resource",
                    "label": _("Resources"),
                    "icon": "icon-file-cloud",
                },
                {
                    "model": "organizations.organization",
                    "label": _("Institutions"),
                    "icon": "icon-building",
                },
                {
                    "model": "applications.application",
                    "permissions": "auth.add_user",
                    "label": _("Applications"),
                    "icon": "icon-cupe-black",
                },
                {
                    "model": "showcases.showcase",
                    "permissions": "auth.add_user",
                    "label": _("PoCoTo"),
                    "icon": "icon-cupe-black",
                },
                {
                    "model": "suggestions.AcceptedDatasetSubmission",
                    "label": _("Data suggestions"),
                    "permissions": "auth.add_user",
                },
            ],
            "icon": "icon-file",
        },
        {
            "label": _("Users"),
            "url": "/users/user",
            "icon": "icon-lock",
            "orig_url": "/users/user",
        },
        {
            "label": _("Reports"),
            "app": "reports",
            "models": [
                {
                    "model": "reports.dashboard",
                    "label": pgettext_lazy("Metabase Dashboards", "Dashboards"),
                },
                {"model": "reports.userreport", "label": _("Users reports")},
                {"model": "reports.resourcereport", "label": _("Resources")},
                {"model": "reports.datasetreport", "label": _("Datasets")},
                {"model": "reports.organizationreport", "label": _("Institutions")},
                {"model": "reports.monitoringreport", "label": _("Monitoring")},
                {"model": "reports.summarydailyreport", "label": _("Daily Reports")},
                {"model": "reports.datasourceimportreport", "label": _("Data Sources")},
            ],
            "permissions": "auth.add_user",
            "icon": "icon-tasks",
        },
        {
            "label": _("Alerts"),
            "url": "/alerts/alert",
            "permissions": "auth.add_user",
            "icon": "icon-bullhorn",
            "orig_url": "/alerts/alert",
        },
        {
            "label": _("Newsletter"),
            "url": "/newsletter/newsletter/",
            "permissions": "auth.add_user",
            "icon": "icon-envelope",
            "orig_url": "/newsletter/newsletter/",
        },
        {
            "label": _("Data Sources"),
            "url": "/harvester/datasource/",
            "permissions": "auth.add_user",
            "icon": "icon-bullhorn",
            "orig_url": "/harvester/datasource/",
        },
        {
            "label": pgettext_lazy("Dashboard", "Dashboard"),
            "url": "",
            "permissions": "is_logged_academy_or_labs_admin",
            "icon": "icon-list-alt",
            "models": [
                {
                    "label": _("Open Data Lab"),
                    "model": "laboratory.labevent",
                    "admin_url": "laboratory/labevent",
                    "app_name": "laboratory",
                    "permissions": (
                        "laboratory.view_labevent",
                        "laboratory.view_labreport",
                    ),
                },
                {
                    "label": _("Open Data Academy"),
                    "url": "/academy/course",
                    "permissions": ("academy.view_course",),
                },
                {
                    "model": "users.meeting",
                    "permissions": ("auth.add_user",),
                },
            ],
        },
        {
            "label": _("Portal guide"),
            "url": "/guides/guide",
            "permissions": "auth.add_user",
            "icon": "icon-bullhorn",
            "orig_url": "/guides/guide",
        },
        {
            "label": _("Monitoring"),
            "permissions": "auth.add_user",
            "models": [
                {
                    "model": "applications.applicationproposal",
                    "permissions": "auth.add_user",
                    "url": "/applications/applicationproposal/?decision=not_taken",
                },
                {
                    "model": "showcases.showcaseproposal",
                    "permissions": "auth.add_user",
                    "label": "Propozycje PoCoTo",
                    "url": "/showcases/showcaseproposal/?decision=not_taken",
                },
                {
                    "label": _("Data suggestions"),
                    "model": "suggestions.datasetsubmission",
                    "url": "/suggestions/datasetsubmission/?decision=not_taken",
                },
                {
                    "model": "suggestions.datasetcomment",
                    "permissions": "auth.add_user",
                    "url": "/suggestions/datasetcomment/?decision=not_taken",
                },
                {
                    "model": "suggestions.resourcecomment",
                    "permissions": "auth.add_user",
                    "url": "/suggestions/resourcecomment/?decision=not_taken",
                },
            ],
        },
        {
            "label": _("Configuration"),
            "url": "/constance/config",
            "permissions": "auth.add_user",
            "icon": "icon-cog",
            "orig_url": "/constance/config",
        },
    ],
    "LIST_PER_PAGE": 20,
    # CUSTOM SETTINGS
    "APPS_SKIPPED_IN_DASHBOARD": [
        "alerts",
        "constance",
        "django_celery_results",
    ],
}

SPECIAL_CHARS = " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"

CKEDITOR_CONFIGS = {
    "default": {
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline"],
            [
                "NumberedList",
                "BulletedList",
                "-",
                "Outdent",
                "Indent",
                "-",
                "JustifyLeft",
                "JustifyCenter",
                "JustifyRight",
                "JustifyBlock",
            ],
            ["Link", "Unlink"],
            [
                "Attachments",
            ],
            ["RemoveFormat", "Source"],
        ],
        "height": 300,
        "width": "100%",
    },
    "alert_description": {
        "toolbar": "Custom",
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline"],
        ],
        "height": 300,
        "width": "100%",
    },
    "data_source_description": {
        "toolbar": "Custom",
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline"],
        ],
        "height": 100,
        "width": "100%",
    },
    "licenses": {
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline"],
            [
                "NumberedList",
                "BulletedList",
                "-",
                "Outdent",
                "Indent",
                "-",
                "JustifyLeft",
                "JustifyCenter",
                "JustifyRight",
                "JustifyBlock",
            ],
            ["Link", "Unlink"],
            [
                "Attachments",
            ],
            ["RemoveFormat", "Source"],
        ],
        "height": 150,
        "width": "100%",
    },
}

CKEDITOR_ALLOW_NONIMAGE_FILES = True

TOKEN_EXPIRATION_TIME = env("TOKEN_EXPIRATION_TIME", default=72)  # In hours

PER_PAGE_LIMIT = 200
PER_PAGE_DEFAULT = 20

ELASTICSEARCH_HOSTS = env("ELASTICSEARCH_HOSTS", default="mcod-elasticsearch-1:9200")

ELASTICSEARCH_DSL = {
    "default": {
        "hosts": ELASTICSEARCH_HOSTS.split(","),
        "http_auth": "user:changeme",
        "timeout": 100,
    },
}

ELASTICSEARCH_COMMON_ALIAS_NAME = "common_alias"

ELASTICSEARCH_INDEX_NAMES = OrderedDict(
    {
        "applications": "applications",
        "courses": "courses",
        "institutions": "institutions",
        "datasets": "datasets",
        "resources": "resources",
        "regions": "regions",
        "searchhistories": "searchhistories",
        "histories": "histories",
        "logentries": "logentries",
        "lab_events": "lab_events",
        "accepted_dataset_submissions": "accepted_dataset_submissions",
        "meetings": "meetings",
        "knowledge_base_pages": "knowledge_base_pages",
        "showcases": "showcases",
        "news": "news",
    }
)

ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = "mcod.core.api.search.signals.AsyncSignalProcessor"

ELASTICSEARCH_DSL_INDEX_SETTINGS = {"number_of_shards": 1, "number_of_replicas": 1}

ELASTICSEARCH_DSL_SEARCH_INDEX_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "max_result_window": 40000,
}

ELASTICSEARCH_DSL_SEARCH_INDEX_ALIAS = {
    ELASTICSEARCH_COMMON_ALIAS_NAME: {},
}

ELASTICSEARCH_HISTORIES_IDX_SETTINGS = {"number_of_shards": 3, "number_of_replicas": 1}

ELASTICSEARCH_INDEX_PREFIX = ""

CELERY_BROKER_URL = "amqp://%s" % str(env("RABBITMQ_HOST", default="mcod-rabbitmq:5672"))

CELERY_RESULT_BACKEND = "django-db"
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_STORE_EAGER_RESULT = True

CELERY_TASK_DEFAULT_QUEUE = "default"

CELERY_TASK_QUEUES = {
    Queue("default"),
    Queue("harvester"),
    Queue("resources"),
    Queue("indexing"),
    Queue("indexing_data"),
    Queue("periodic"),
    Queue("newsletter"),
    Queue("notifications"),
    Queue("search_history"),
    Queue("watchers"),
    Queue("history"),
    Queue("graphs"),
    Queue("datasets"),
    Queue("archiving"),
    Queue("reports"),
    Queue("discourse"),
    Queue("showcases"),
}

CELERY_TASK_ROUTES = {
    "mcod.core.api.rdf.tasks.update_graph_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.create_graph_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.create_graph_with_related_update_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.update_graph_with_related_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.update_graph_with_conditional_related_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.update_related_graph_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.delete_graph_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.delete_graph_with_related_update_task": {"queue": "graphs"},
    "mcod.core.api.rdf.tasks.delete_sub_graphs": {"queue": "graphs"},
    "mcod.core.api.search.tasks.bulk_delete_documents_task": {"queue": "indexing"},
    "mcod.core.api.search.tasks.delete_document_task": {"queue": "indexing"},
    "mcod.core.api.search.tasks.delete_with_related_task": {"queue": "indexing"},
    "mcod.core.api.search.tasks.delete_related_documents_task": {"queue": "indexing"},
    "mcod.core.api.search.tasks.null_field_in_related_task": {"queue": "indexing"},
    "mcod.core.api.search.tasks.update_document_task": {"queue": "indexing"},
    "mcod.core.api.search.tasks.update_related_task": {"queue": "indexing"},
    "mcod.core.api.search.tasks.update_with_related_task": {"queue": "indexing"},
    "mcod.datasets.tasks.archive_resources_files": {"queue": "archiving"},
    "mcod.datasets.tasks.change_archive_symlink_name": {"queue": "datasets"},
    "mcod.datasets.tasks.send_dataset_comment": {"queue": "notifications"},
    "mcod.discourse.tasks.user_sync_task": {"queue": "discourse"},
    "mcod.discourse.tasks.user_logout_task": {"queue": "discourse"},
    "mcod.harvester.tasks.import_data_task": {"queue": "harvester"},
    "mcod.harvester.tasks.harvester_supervisor": {"queue": "harvester"},
    "mcod.harvester.tasks.validate_xml_url_task": {"queue": "harvester"},
    "mcod.newsletter.tasks.remove_inactive_subscription": {"queue": "newsletter"},
    "mcod.newsletter.tasks.send_newsletter_mail": {"queue": "newsletter"},
    "mcod.newsletter.tasks.send_subscription_confirm_mail": {"queue": "newsletter"},
    "mcod.reports.tasks.create_daily_resources_report": {"queue": "reports"},
    "mcod.reports.tasks.create_resources_report_task": {"queue": "reports"},
    "mcod.reports.tasks.generate_csv": {"queue": "reports"},
    "mcod.reports.tasks.generate_harvesters_imports_report": {"queue": "reports"},
    "mcod.reports.tasks.generate_harvesters_last_imports_report": {"queue": "reports"},
    "mcod.reports.tasks.link_validation_success_callback": {"queue": "reports"},
    "mcod.reports.tasks.link_validation_error_callback": {"queue": "reports"},
    "mcod.reports.tasks.generate_broken_links_reports_task": {"queue": "reports"},
    "mcod.reports.tasks.generate_admin_broken_links_report_task": {"queue": "reports"},
    "mcod.reports.tasks.generate_public_broken_links_reports_task": {"queue": "reports"},
    "mcod.resources.tasks.check_link_protocol": {"queue": "resources"},
    "mcod.resources.tasks.create_main_dga_resource_task": {"queue": "resources"},
    "mcod.resources.tasks.delete_es_resource_tabular_data_index": {"queue": "indexing_data"},
    "mcod.resources.tasks.delete_es_resource_tabular_data_indexes_for_organization": {"queue": "indexing_data"},
    "mcod.resources.tasks.entrypoint_process_resource_file_validation_task": {"queue": "resources"},
    "mcod.resources.tasks.entrypoint_process_resource_validation_task": {"queue": "resources"},
    "mcod.resources.tasks.get_ckan_resource_format_from_url_task": {"queue": "resources"},
    "mcod.resources.tasks.process_resource_data_indexing_task": {"queue": "indexing_data"},
    "mcod.resources.tasks.process_resource_file_data_task": {"queue": "resources"},
    "mcod.resources.tasks.process_resource_file_task": {"queue": "resources"},
    "mcod.resources.tasks.process_resource_from_url_task": {"queue": "resources"},
    "mcod.resources.tasks.process_resource_res_file_task": {"queue": "resources"},
    "mcod.resources.tasks.send_resource_comment": {"queue": "notifications"},
    "mcod.resources.tasks.update_resource_has_table_has_map_task": {"queue": "resources"},
    "mcod.resources.tasks.update_resource_validation_results_task": {"queue": "resources"},
    "mcod.resources.tasks.update_data_date": {"queue": "resources"},
    "mcod.resources.tasks.update_last_day_data_date": {"queue": "resources"},
    "mcod.resources.tasks.update_resource_with_archive_format": {"queue": "resources"},
    "mcod.resources.tasks.validate_link": {"queue": "resources"},
    "mcod.schedules.tasks.send_admin_notification_task": {"queue": "notifications"},
    "mcod.schedules.tasks.update_notifications_task": {"queue": "notifications"},
    "mcod.showcases.tasks.create_showcase_proposal_task": {"queue": "showcases"},
    "mcod.showcases.tasks.create_showcase_task": {"queue": "showcases"},
    "mcod.showcases.tasks.generate_logo_thumbnail_task": {"queue": "showcases"},
    "mcod.showcases.tasks.send_showcase_proposal_mail_task": {"queue": "showcases"},
    "mcod.suggestions.tasks.create_accepted_dataset_suggestion_task": {"queue": "notifications"},
    "mcod.suggestions.tasks.create_data_suggestion": {"queue": "notifications"},
    "mcod.suggestions.tasks.create_dataset_suggestion": {"queue": "notifications"},
    "mcod.suggestions.tasks.send_dataset_suggestion_mail_task": {"queue": "notifications"},
    "mcod.suggestions.tasks.send_data_suggestion": {"queue": "notifications"},
    "mcod.suggestions.tasks.send_accepted_submission_comment": {"queue": "notifications"},
    "mcod.users.tasks.send_registration_email_task": {"queue": "notifications"},
    "mcod.watchers.tasks.model_watcher_updated_task": {"queue": "watchers"},
    "mcod.watchers.tasks.remove_user_notifications_task": {"queue": "watchers"},
    "mcod.watchers.tasks.update_model_watcher_task": {"queue": "watchers"},
    "mcod.watchers.tasks.update_notifications_status_task": {"queue": "watchers"},
    "mcod.watchers.tasks.update_notifications_task": {"queue": "watchers"},
    "mcod.watchers.tasks.query_watcher_updated_task": {"queue": "watchers"},
}

CELERY_SINGLETON_BACKEND_URL = REDIS_URL

RESOURCE_MIN_FILE_SIZE = 1024
RESOURCE_MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1024 MB

FIXTURE_DIRS = [
    str(ROOT_DIR("fixtures")),
]

LOGSTASH_HOST = env("LOGSTASH_HOST", default="mcod-logstash")
STATS_LOG_LEVEL = env("STATS_LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "console": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        },
        "stats": {"format": "%(asctime)s;%(name)s;%(levelname)s;%(message)s"},
        "signals-console-formatter": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s\n"
            "[%(signal)s] sender:%(sender)s, instance:%(instance)s, id:%(instance_id)s"
        },
    },
    "handlers": {
        "signals-console-handler": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "signals-console-formatter",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "logstash-admin": {
            "level": "DEBUG",
            "class": "logstash.UDPLogstashHandler",
            "host": LOGSTASH_HOST,
            "port": 5959,
            "version": 1,
            "message_type": f"admin-{ENVIRONMENT}" if ENVIRONMENT else "admin",
            "fqdn": False,
            "tags": [f"admin-{ENVIRONMENT}"] if ENVIRONMENT else None,
        },
        "logstash-signals": {
            "level": "DEBUG",
            "class": "logstash.UDPLogstashHandler",
            "host": LOGSTASH_HOST,
            "port": 5959,
            "version": 1,
            "message_type": f"signals-{ENVIRONMENT}" if ENVIRONMENT else "signals",
            "fqdn": False,
            "tags": [f"signals-{ENVIRONMENT}"] if ENVIRONMENT else None,
        },
        "logstash-tasks": {
            "level": "DEBUG",
            "class": "logstash.UDPLogstashHandler",
            "host": LOGSTASH_HOST,
            "port": 5959,
            "version": 1,
            "message_type": f"tasks-{ENVIRONMENT}" if ENVIRONMENT else "tasks",
            "fqdn": False,
            "tags": [f"tasks-{ENVIRONMENT}"] if ENVIRONMENT else None,
        },
        "stats-log": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": f"{LOGS_DIR}/stats.log",
            "formatter": "stats",
        },
        "kibana-statistics": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": f"{LOGS_DIR}/kibana_statistics.log",
            "formatter": "console",
        },
        "kronika-sparql-performance": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": f"{LOGS_DIR}/kronika_performance.log",
            "formatter": "console",
        },
        # Check if these are required
        "mail-admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "mcod-api": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["mail-admins", "logstash-admin"],
            "propagate": False,
        },
        "django.templates": {
            "handlers": [
                "logstash-admin",
            ],
            "level": "ERROR",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["mail-admins", "logstash-admin"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["mail-admins", "logstash-admin"],
            "level": "DEBUG",
            "propagate": False,
        },
        "signals": {
            "handlers": ["signals-console-handler", "logstash-signals"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery.app.trace": {
            "handlers": ["console", "logstash-tasks"],
            "level": "DEBUG",
            "propagate": True,
        },
        "mcod": {
            "handlers": [
                "console",
            ],
            "level": "DEBUG",
            "propagate": False,
        },
        "kibana-statistics": {
            "handlers": [
                "kibana-statistics",
            ],
            "level": "DEBUG",
            "propagate": False,
        },
        "resource_file_processing": {
            "handlers": [
                "console",
            ],
            "level": "DEBUG",
            "propagate": False,
        },
        "stats-queries": {
            "handlers": [
                "stats-log",
            ],
            "level": "DEBUG",
            "propagate": True,
        },
        "stats-profile": {
            "handlers": [
                "stats-log",
            ],
            "level": STATS_LOG_LEVEL,
            "propagate": True,
        },
        "kronika-sparql-performance": {
            "handlers": [
                "kronika-sparql-performance",
            ],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

CELERYD_HIJACK_ROOT_LOGGER = False

APM_SERVER_URL = env("APM_SERVER_URL", default=None)

# Disable APM for ASGI (ws component)
APM_SERVICES = ["api", "admin", "cms", "celery"]

if APM_SERVER_URL and COMPONENT in APM_SERVICES:
    INSTALLED_APPS += [
        "elasticapm.contrib.django",
    ]

    ELASTIC_APM = {
        "DEBUG": True,
        "SERVICE_NAME": f"{ENVIRONMENT}-{COMPONENT}",
        "SERVER_URL": APM_SERVER_URL,
        "CAPTURE_BODY": "errors",
        "FILTER_EXCEPTION_TYPES": [
            "falcon.errors.HTTPNotFound",
            "falcon.errors.HTTPMethodNotAllowed",
            "falcon.errors.HTTPUnauthorized",
            "falcon.errors.HTTPBadRequest",
            "falcon.errors.HTTPUnprocessableEntity",
            "falcon.errors.HTTPForbidden",
        ],
        "DJANGO_TRANSACTION_NAME_FROM_ROUTE": True,
    }

    LOGGING["handlers"]["elasticapm"] = {
        "level": "WARNING",
        "class": "elasticapm.contrib.django.handlers.LoggingHandler",
    }

    LOGGING["loggers"]["elasticapm.errors"] = {
        "handlers": [
            "console",
        ],
        "level": "DEBUG",
        "propagate": False,
    }

    TEMPLATES[0]["OPTIONS"]["context_processors"] += [
        "mcod.core.contextprocessors.apm",
        "elasticapm.contrib.django.context_processors.rum_tracing",
    ]

SUPPORTED_CONTENT_TYPES = [
    # (family, type, extensions, default openness score)
    ("application", "atom+xml", ("xml",), 3),
    ("application", "csv", ("csv",), 3),
    ("application", "epub+zip", ("epub",), 1),
    ("application", "excel", ("xls",), 2),
    ("application", "geo+json", ("geojson",), 3),
    ("application", "gml+xml", ("xml",), 3),
    ("application", "gpx+xml", ("gpx",), 3),
    ("application", "json", ("json",), 3),
    ("application", "mspowerpoint", ("ppt", "pot", "ppa", "pps", "pwz"), 1),
    ("application", "msword", ("doc", "docx", "dot", "wiz"), 1),
    ("application", "pdf", ("pdf",), 1),
    ("application", "postscript", ("pdf", "ps"), 1),
    ("application", "powerpoint", ("ppt", "pot", "ppa", "pps", "pwz"), 1),
    ("application", "rtf", ("rtf",), 1),
    ("application", "shapefile", ("shp",), 3),
    ("application", "vnd.api+json", ("json",), 3),
    ("application", "vnd.geo+json", ("geojson",), 3),
    ("application", "vnd.google-earth.kml+xml", ("kml",), 3),
    ("application", "vnd.google-earth.kmz", ("kmz",), 3),
    ("application", "vnd.ms-excel", ("xls", "xlsx", "xlb"), 2),
    ("application", "vnd.ms-excel.12", ("xls", "xlsx", "xlb"), 2),
    ("application", "vnd.ms-excel.sheet.macroEnabled.12", ("xls", "xlsx", "xlb"), 2),
    ("application", "vnd.ms-powerpoint", ("ppt", "pot", "ppa", "pps", "pwz"), 1),
    ("application", "vnd.ms-word", ("doc", "docx", "dot", "wiz"), 1),
    ("application", "vnd.oasis.opendocument.chart", ("odc",), 1),
    ("application", "vnd.oasis.opendocument.formula", ("odf",), 3),
    ("application", "vnd.oasis.opendocument.graphics", ("odg",), 3),
    ("application", "vnd.oasis.opendocument.image", ("odi",), 2),
    ("application", "vnd.oasis.opendocument.presentation", ("odp",), 1),
    ("application", "vnd.oasis.opendocument.spreadsheet", ("ods",), 3),
    ("application", "vnd.oasis.opendocument.text", ("odt",), 1),
    (
        "application",
        "vnd.openxmlformats-officedocument.presentationml.presentation",
        ("pptx",),
        1,
    ),
    (
        "application",
        "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ("xlsx",),
        2,
    ),
    (
        "application",
        "vnd.openxmlformats-officedocument.wordprocessingml.document",
        ("docx",),
        1,
    ),
    ("application", "vnd.visio", ("vsd",), 1),
    ("application", "x-abiword", ("abw",), 1),
    ("application", "x-csv", ("csv",), 3),
    ("application", "x-excel", ("xls", "xlsx", "xlb"), 2),
    ("application", "x-rtf", ("rtf",), 1),
    ("application", "xhtml+xml", ("html", "htm"), 3),
    ("application", "xml", ("xml",), 3),
    ("application", "x-tex", ("tex",), 3),
    (
        "application",
        "x-texinfo",
        (
            "texi",
            "texinfo",
        ),
        3,
    ),
    ("application", "x-dbf", ("dbf",), 3),
    (
        "application",
        "x-grib",
        (
            "grib",
            "grib2",
        ),
        2,
    ),
    (
        "application",
        "x-wsdl",
        (
            "xml",
            "wsdl",
        ),
        3,
    ),
    ("application", "netcdf", ("nc",), 2),
    ("image", "bmp", ("bmp",), 1),
    ("image", "gif", ("gif",), 2),
    ("image", "jpeg", ("jpeg", "jpg", "jpe"), 1),
    ("image", "png", ("png",), 1),
    ("image", "svg+xml", ("svg",), 3),
    ("image", "tiff", ("tiff", "tif"), 1),
    ("image", "tiff;application=geotiff", ("geotiff",), 3),
    ("image", "webp", ("webp",), 2),
    ("image", "x-tiff", ("tiff",), 1),
    ("image", "x-ms-bmp", ("bmp",), 1),
    ("image", "x-portable-pixmap", ("ppm",), 2),
    ("image", "x-xbitmap", ("xbm",), 2),
    ("text", "csv", ("csv",), 3),
    ("text", "html", ("html", "htm"), 3),
    ("text", "xhtml+xml", ("html", "htm"), 3),
    ("text", "plain", ("txt", "rd", "md", "bat"), 1),
    ("text", "richtext", ("rtf",), 1),
    ("text", "tab-separated-values", ("tsv",), 3),
    ("text", "xml", ("xml", "wsdl", "xpdl", "xsl"), 3),
    # RDF
    ("application", "ld+json", ("jsonld",), 4),
    ("application", "rdf+xml", ("rdf",), 4),
    ("application", "rdfa+xml", ("rdfa",), 4),
    ("text", "n3", ("n3",), 4),
    ("text", "turtle", ("ttl", "turtle"), 4),
    ("application", "nt-triples", ("nt", "nt11", "ntriples"), 4),
    (
        "application",
        "n-quads",
        (
            "nq",
            "nquads",
        ),
        4,
    ),
    ("application", "trix", ("trix",), 4),
    ("application", "trig", ("trig",), 4),
]

CONTENT_TYPE_TO_EXTENSION_MAP = [(x[0], x[1], x[2]) for x in SUPPORTED_CONTENT_TYPES]
CONTENT_TYPE_TO_EXTENSION_MAP.extend([("application", "zip", ("zip",))])

ARCHIVE_RAR_CONTENT_TYPES = {
    "rar",
    "vnd.rar",
    "x-rar",
    "x-rar-compressed",
}

ARCHIVE_ZIP_CONTENT_TYPES = {
    "zip",
    "x-zip-compressed",
}

ARCHIVE_7Z_CONTENT_TYPES = {
    "x-7z-compressed",
}

ARCHIVE_CONTENT_TYPES = {
    *ARCHIVE_RAR_CONTENT_TYPES,
    *ARCHIVE_ZIP_CONTENT_TYPES,
    *ARCHIVE_7Z_CONTENT_TYPES,
    "bzip2",
    "gzip",
    "x-bzip",
    "x-bzip2",
    "x-gzip",
    "x-tar",
}

ARCHIVE_EXTENSIONS = {"bz", "bz2", "gz", "rar", "tar", "zip", "7z"}

ARCHIVE_TYPE_TO_EXTENSIONS = {
    "gzip": "gz",
    "x-gzip": "gz",
    "bzip2": "bz2",
    "x-bzip2": "bz2",
    "x-bzip": "bz",
    "zip": "zip",
    "x-zip-compressed": "zip",
    "vnd.rar": "rar",
    "x-rar-compressed": "rar",
    "x-rar": "rar",
    "rar": "rar",
    "x-7z-compressed": "7z",
    "x-tar": "tar",
}

ALLOWED_CONTENT_TYPES = [x[1] for x in SUPPORTED_CONTENT_TYPES] + list(ARCHIVE_CONTENT_TYPES)
ALLOWED_SUPPLEMENT_MIMETYPES = env.list(
    "ALLOWED_SUPPLEMENT_MIMETYPES",
    default=[
        # .doc, .docx
        "application/msword",
        "application/vnd.ms-word",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        # .pdf
        "application/pdf",
        # .txt
        "text/plain",
        # .odt
        "application/vnd.oasis.opendocument.text",
    ],
)
RESTRICTED_FILE_TYPES = env.list(
    "RESTRICTED_FILE_TYPES",
    default=[
        "asp",
        "aspx",
        "bat",
        "cgi",
        "com",
        "exe",
        "jsp",
        "php",
    ],
)


def _supported_formats(with_archives=False):
    data = []
    for item in SUPPORTED_CONTENT_TYPES:
        data.extend(item[2])
    if with_archives:
        data.extend(ARCHIVE_EXTENSIONS)
    return sorted(list(set(data)))


def _supported_formats_choices(with_archives=False):
    return [(i, i.upper()) for i in _supported_formats(with_archives=with_archives)]


SUPPORTED_FORMATS = _supported_formats()
SUPPORTED_FORMATS_WITH_ARCHIVES = _supported_formats(with_archives=True)
SUPPORTED_FORMATS_CHOICES = _supported_formats_choices()
SUPPORTED_FORMATS_CHOICES_WITH_ARCHIVES = _supported_formats_choices(with_archives=True)

SUPPORTED_FILE_EXTENSIONS = [x[0] for x in _supported_formats_choices()]
SUPPORTED_FILE_EXTENSIONS.extend(ARCHIVE_EXTENSIONS)
SUPPORTED_FILE_EXTENSIONS = [f".{x}" for x in SUPPORTED_FILE_EXTENSIONS if x not in RESTRICTED_FILE_TYPES]

FILE_UPLOAD_MAX_MEMORY_SIZE = 1073741824  # 1Gb
FILE_UPLOAD_PERMISSIONS = 0o644

IMAGE_UPLOAD_MAX_SIZE = 10 * 1024**2
THUMB_SIZE = (200, 1024)

COUNTED_MODELS = {
    "applications.Application": {"status": "published"},
    "resources.Resource": {"status": "published"},
    "cms.NewsPage": {"live": True},
}
SEARCH_PATH = "/search"

JSONAPI_SCHEMA_PATH = str(DATA_DIR.path("jsonapi.config.json"))
JSONSTAT_SCHEMA_PATH = str(DATA_DIR.path("json_stat_schema_2_0.json"))
JSONSTAT_V1_ALLOWED = env("JSONSTAT_V1_ALLOWED", default="yes") in ("yes", "1", "true")
GPX_11_SCHEMA_PATH = str(DATA_DIR.path("gpx_xsd_1_1.xsd"))
GPX_10_SCHEMA_PATH = str(DATA_DIR.path("gpx_xsd_1_0.xsd"))

DATE_BASE_FORMATS = [
    "yyyy-MM-dd",
    "yyyy-MM-dd HH:mm",
    "yyyy-MM-dd HH:mm:ss",
    "yyyy-MM-dd HH:mm:ss.SSSSSS",
    "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
    "yyyy.MM.dd",
    "yyyy.MM.dd HH:mm",
    "yyyy.MM.dd HH:mm:ss",
    "yyyy.MM.dd HH:mm:ss.SSSSSS",
    "yyyy.MM.dd'T'HH:mm:ss.SSSSSS",
    "yyyy/MM/dd",
    "yyyy/MM/dd HH:mm",
    "yyyy/MM/dd HH:mm:ss",
    "yyyy/MM/dd HH:mm:ss.SSSSSS",
    "yyyy/MM/dd'T'HH:mm:ss.SSSSSS",
    "dd-MM-yyyy",
    "dd-MM-yyyy HH:mm",
    "dd-MM-yyyy HH:mm:ss",
    "dd-MM-yyyy HH:mm:ss.SSSSSS",
    "dd-MM-yyyy'T'HH:mm:ss.SSSSSS",
    "dd.MM.yyyy",
    "dd.MM.yyyy HH:mm",
    "dd.MM.yyyy HH:mm:ss",
    "dd.MM.yyyy HH:mm:ss.SSSSSS",
    "dd.MM.yyyy'T'HH:mm:ss.SSSSSS",
    "dd/MM/yyyy",
    "dd/MM/yyyy HH:mm",
    "dd/MM/yyyy HH:mm:ss",
    "dd/MM/yyyy HH:mm:ss.SSSSSS",
    "dd/MM/yyyy'T'HH:mm:ss.SSSSSS",
    "yyyy-MM-dd'T'HH:mm:ss",
    "yyyy.MM.dd'T'HH:mm:ss",
    "yyyy/MM/dd'T'HH:mm:ss",
    "dd-MM-yyyy'T'HH:mm:ss",
    "dd.MM.yyyy'T'HH:mm:ss",
    "dd/MM/yyyy'T'HH:mm:ss",
    "yyyy-MM-dd'T'HH:mm",
    "yyyy.MM.dd'T'HH:mm",
    "yyyy/MM/dd'T'HH:mm",
    "dd-MM-yyyy'T'HH:mm",
    "dd.MM.yyyy'T'HH:mm",
    "dd/MM/yyyy'T'HH:mm",
]

TIME_BASE_FORMATS = ["HH:mm", "HH:mm:ss", "HH:mm:ss.SSSSSS"]

METABASE_DASHBOARDS_ENABLED = env("METABASE_DASHBOARDS_ENABLED", default="no") in (
    "yes",
    1,
    "true",
)

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_DATABASE_PREFIX = "constance:mcod:"
CONSTANCE_DATABASE_CACHE_BACKEND = "default"

CONSTANCE_CONFIG = {
    "NO_REPLY_EMAIL": (
        "no-reply@dane.gov.pl",
        "Adres email z którego wysyłane są maile z następującymi powiadomieniami z aplikacji:\n- utworzenie propozycji nowych danych\n- utworzenie zgłoszenia PoCoTo\n- przypomnienie o dacie aktualizacji zbioru danych",
        str,
    ),  # noqa: E501
    "CONTACT_MAIL": (
        "kontakt@dane.gov.pl",
        "Adres email na który wysyłane są maile z powiadomieniami z aplikacji",
        str,
    ),
    "SUGGESTIONS_EMAIL": (
        "uwagi@dane.gov.pl",
        "Adres email z którego wysyłane są maile z komentarzami/uwagami do zbiorów, zasobów i zaakceptowanych propozycji nowych danych",
        str,
    ),  # noqa: E501
    "ACCOUNTS_EMAIL": (
        "konta@dane.gov.pl",
        "Adres email z którego do użytkownika wysyłane są maile do przypomnienia hasła oraz aktywacji konta po rejestracji",
        str,
    ),  # noqa: E501
    "FOLLOWINGS_EMAIL": (
        "obserwowane@dane.gov.pl",
        "Adres email z którego do użytkownika wysyłane są maile z informacjami dotyczącymi aktywności obserwowanych obiektów",
        str,
    ),  # noqa: E501
    "NEWSLETTER_EMAIL": (
        "newsletter@dane.gov.pl",
        "Adres email z którego do użytkownika wysyłane są maile związane z newsletterem",
        str,
    ),  # noqa: E501
    "TESTER_EMAIL": (
        "no-reply@dane.gov.pl",
        "Adres email na który wysyłane są maile z powiadomieniami z aplikacji (tylko w trybie DEBUG - środowiska deweloperskie)",
        str,
    ),  # noqa: E501
    "MANUAL_URL": (
        "https://dane.gov.pl/article/1226",
        "Adres www przewodnika dla dostawców widocznego w stopce panelu administracyjnego.",
        str,
    ),  # noqa: E501
    "DATE_FORMATS": (
        "||".join(DATE_BASE_FORMATS),
        "Dozwolone formaty dla pól typu 'date' oraz 'datetime' (dane tabelaryczne)",
        str,
    ),  # noqa: E501
    "TIME_FORMATS": (
        "||".join(TIME_BASE_FORMATS),
        "Dozwolone formaty dla pól typu 'time' (dane tabelaryczne)",
        str,
    ),  # noqa: E501
    "CATALOG__TITLE_PL": (
        "Portal z danymi publicznymi",
        'Wartość pola Catalog -> <dct:title xml:lang="pl"> w API (końcówka /catalog.rdf)',
        str,
    ),  # noqa: E501
    "CATALOG__TITLE_EN": (
        "Poland's Open Data Portal",
        'Wartość pola Catalog -> <dct:title xml:lang="en"> w API (końcówka /catalog.rdf)',
        str,
    ),  # noqa: E501
    "CATALOG__DESCRIPTION_PL": (
        "Dane o szczególnym znaczeniu dla rozwoju innowacyjności w państwie i rozwoju społeczeństwa informacyjnego w jednym miejscu",
        'Wartość pola Catalog -> <dct:description xml:lang="pl"> w API (końcówka /catalog.rdf)',
        str,
    ),  # noqa: E501
    "CATALOG__DESCRIPTION_EN": (
        "Data of particular importance for the development of innovation in the country and the development of the information society gathered in one location",
        'Wartość pola Catalog -> <dct:description xml:lang="en"> w API (końcówka /catalog.rdf)',
        str,
    ),  # noqa: E501
    "CATALOG__ISSUED": (
        date(2014, 4, 30),
        "Wartość pola Catalog -> <dct:issued> w API (końcówka /catalog.rdf)",
        date,
    ),
    "CATALOG__PUBLISHER__NAME_PL": (
        "KPRM",
        'Wartość pola CatalogPublisher -> <foaf:name xml:lang="pl"> w API (końcówka /catalog.rdf)',
        str,
    ),  # noqa: E501
    "CATALOG__PUBLISHER__NAME_EN": (
        "KPRM",
        'Wartość pola CatalogPublisher -> <foaf:name xml:lang="en"> w API (końcówka /catalog.rdf)',
        str,
    ),  # noqa: E501
    "CATALOG__PUBLISHER__EMAIL": (
        "kontakt@dane.gov.pl",
        "Wartość pola CatalogPublisher -> <foaf:mbox> w API (końcówka /catalog.rdf)",
        str,
    ),  # noqa: E501
    "CATALOG__PUBLISHER__HOMEPAGE": (
        "https://dane.gov.pl",
        "Wartość pola CatalogPublisher -> <foaf:homepage> w API (końcówka /catalog.rdf)",
        str,
    ),  # noqa: E501
    "DATASET__CONTACT_POINT__FN": (
        "KPRM",
        "Wartość pola VcardKind -> <vcard:fn> w API (końcówka /catalog.rdf)",
        str,
    ),
    "DATASET__CONTACT_POINT__HAS_EMAIL": (
        "mailto:kontakt@dane.gov.pl",
        "Wartość pola VcardKind -> <vcard:hasEmail> w API (końcówka /catalog.rdf)",
        str,
    ),  # noqa: E501
}

# Recipients of email containing DB and ElasticSearch inconsistency information
# Multiple email addresses can be provided (separated by commas)
DB_ES_CONSISTENCY_EMAIL_RECIPIENTS: str = env("DB_ES_CONSISTENCY_EMAIL_RECIPIENTS", default="")

METABASE_DASHBOARDS_FIELDSET = []
if METABASE_DASHBOARDS_ENABLED:
    CONSTANCE_CONFIG["METABASE_DASHBOARDS"] = (
        "",
        'JSON, Lista obiektów zawierających atrybuty "name" i "id" - nazwę oraz id dashboardu w metabase. Przykład:\n[{"name":"Użytkownicy","id":15}]',
        str,
    )  # noqa: E501
    METABASE_DASHBOARDS_FIELDSET = [("Metabase", ("METABASE_DASHBOARDS",))]

CONSTANCE_CONFIG_FIELDSETS = OrderedDict(
    (
        ("URLs", ("MANUAL_URL",)),
        (
            "Mails",
            (
                "NO_REPLY_EMAIL",
                "CONTACT_MAIL",
                "SUGGESTIONS_EMAIL",
                "ACCOUNTS_EMAIL",
                "FOLLOWINGS_EMAIL",
                "NEWSLETTER_EMAIL",
            ),
        ),
        ("Development", ("TESTER_EMAIL",)),
        ("Dates", ("DATE_FORMATS", "TIME_FORMATS")),
        *METABASE_DASHBOARDS_FIELDSET,
        (
            "RDF",
            (
                "CATALOG__TITLE_PL",
                "CATALOG__TITLE_EN",
                "CATALOG__DESCRIPTION_PL",
                "CATALOG__DESCRIPTION_EN",
                "CATALOG__ISSUED",
                "CATALOG__PUBLISHER__NAME_PL",
                "CATALOG__PUBLISHER__NAME_EN",
                "CATALOG__PUBLISHER__EMAIL",
                "CATALOG__PUBLISHER__HOMEPAGE",
                "DATASET__CONTACT_POINT__FN",
                "DATASET__CONTACT_POINT__HAS_EMAIL",
            ),
        ),
    )
)

SHOW_GENERATE_RAPORT_BUTTOON = env("SHOW_GENERATE_RAPORT_BUTTOON", default="yes") in [
    "yes",
    "1",
    "true",
]

TEST_RUNNER = "django.test.runner.DiscoverRunner"

BASE_URL = env("BASE_URL", default="https://www.dane.gov.pl")
API_URL = env("API_URL", default="https://api.dane.gov.pl")
ADMIN_URL = env("ADMIN_URL", default="https://admin.dane.gov.pl")
CMS_URL = env("CMS_URL", default="https://cms.dane.gov.pl")
DYNAMIC_DATA_MANUAL_URL = env(
    "DYNAMIC_DATA_MANUAL_URL",
    default="/pl/knowledgebase/useful-materials/dane-dynamiczne",
)
HIGH_VALUE_DATA_MANUAL_URL = env(
    "HIGH_VALUE_DATA_MANUAL_URL",
    default="/pl/knowledgebase/useful-materials/dane-o-wysokiej-wartosci",
)
HIGH_VALUE_DATA_FROM_EC_LIST_MANUAL_URL = env(
    "HIGH_VALUE_DATA_FROM_EC_LIST_MANUAL_URL",
    default="/pl/knowledgebase/useful-materials/dane-wysokiej-wartosci-z-wykazu-ke",
)
RESEARCH_DATA_MANUAL_URL = env(
    "RESEARCH_DATA_MANUAL_URL",
    default="/pl/knowledgebase/useful-materials/dane-badawcze",
)
PROTECTED_DATA_MANUAL_URL = env("PROTECTED_DATA_MANUAL_URL", default="/pl/dga/information")
TOURPICKER_URL = f"{BASE_URL}?tourPicker=1"
API_URL_INTERNAL = env("API_URL_INTERNAL", default="http://mcod-api:8000")

# Main DGA Resource creation task related constants
MAIN_DGA_RESOURCE_XLSX_CREATION_CACHE_TIMEOUT = 60 * 60  # 60 minutes

# Set None to prevent release cache before deleting created objects if any
# exception will occur. Cache will be released when the task is completed
# in `clean_up_after_main_dga_resource_creation` method.
MAIN_DGA_RESOURCE_CREATION_CACHE_TIMEOUT = None
MAIN_DGA_DATASET_OWNER_ORGANIZATION_PK = env("MAIN_DGA_DATASET_OWNER_ORGANIZATION_PK", default=333)
MAIN_DGA_RESOURCE_DEFAULT_TITLE = "Wykaz chronionych danych"
MAIN_DGA_RESOURCE_DEFAULT_DESC = (
    f"Wykaz zasobów chronionych danych Ministerstwa Cyfryzacji raport zbiorczy "
    f"- Akt o zarządzaniu danymi. Dostęp do chronionych danych wymienionych w "
    f"wykazie jest możliwy wyłącznie na wniosek. Warunki ponownego "
    f"wykorzystywania zostaną określone indywidualnie w ofercie "
    f"(po złożeniu wniosku). Format oraz rozmiar danych wskazane w wykazie "
    f"mogą ulec zmianie. Więcej na temat dostępu do chronionych danych "
    f"(w tym jak złożyć wniosek) dowiesz się w Punkcie informacyjnym pod "
    f'adresem: <a href="{BASE_URL}/pl/dga/information">{BASE_URL}/pl/dga/information</a>'
)
MAIN_DGA_DATASET_DEFAULT_TITLE = "Wykaz zasobów chronionych danych DGA – raport zbiorczy"
MAIN_DGA_DATASET_DEFAULT_DESC = (
    f"Wykaz zasobów chronionych danych raport zbiorczy. Dane w tym zasobie "
    f"odzwierciedlają właściwy wykaz chronionych danych umieszczony w zakładce "
    f"Punkt informacyjny - Wykaz chronionych danych. Dostęp do chronionych "
    f"danych wymienionych w wykazie jest możliwy wyłącznie na wniosek. "
    f"Warunki ponownego wykorzystywania zostaną określone indywidualnie w "
    f"ofercie (po złożeniu wniosku). Format oraz rozmiar danych wskazane w "
    f"wykazie mogą ulec zmianie. Więcej na temat dostępu do chronionych "
    f"danych (w tym jak złożyć wniosek) dowiesz się w Punkcie informacyjnym "
    f"dostępnym pod adresem: "
    f'<a href="{BASE_URL}/pl/dga/information">{BASE_URL}/pl/dga/information</a>'
)
MAIN_DGA_XLSX_FILE_NAME_PREFIX = "Wykaz zasobów chronionych DGA – wykaz zbiorczy – Ministerstwo Cyfryzacji"
MAIN_DGA_XLSX_WORKSHEET_NAME = "Arkusz 1"
MAIN_DGA_DATASET_UPDATE_NOTIFICATION_EMAIL = "chronionedane@cyfra.gov.pl"
MAIN_DGA_DATASET_CATEGORIES_TITLES = ["Rząd i sektor publiczny"]
MAIN_DGA_DATASET_TAGS_NAMES = [
    "DGA",
    "wykaz zasobów chronionych danych",
    "akt o zarządzaniu danymi",
    "chronione dane",
]

PASSWORD_RESET_PATH = "/user/reset-password/%s/"
EMAIL_VALIDATION_PATH = "/user/verify-email/%s/"

VERIFICATION_RULES = (
    (
        "numeric",
        _("Numeric"),
        "Wymaga się stosowania kropki dziesiętnej (a nie przecinka) w zapisie ułamków dziesiętnych, bez żadnych "
        "dodatkowych separatorów (np. oddzielających tysiące); dopuszczalny jest tzw. zapis naukowy",
    ),
    (
        "regon",
        "REGON",
        "Wymagany format: ciąg 9  lub 14 cyfr, bez spacji lub łączników",
    ),
    ("nip", "NIP", "Wymagany format: ciąg 10 cyfr, bez spacji lub łączników"),
    ("krs", "KRS", "Wymagany format: ciąg 10 cyfr, bez spacji lub łączników"),
    (
        "uaddress",
        _("Universal address"),
        """
    Wymagany format: ciąg kodów oddzielonych separatorem &quot;|&quot; lub &quot;;&quot;:
- kodu pocztowego (tzw. PNA) bez myślnika (5 cyfr)
- identyfikatora terytorialnego TERC (7 lub 6 cyfr)
- identyfikatora miejscowości podstawowej SIMC (7 cyfr)
- identyfikatora miejscowości SIMC (7 cyfr)
- identyfikatora katalogu ulic ULIC (5 cyfr)
- współrzędnych geodezyjnych x (w metrach)
- współrzędnych geodezyjnych y (w metrach)
- numeru budynku
Przykłady:
00184|146501|0918123|0918123|04337|489147.9218|636045.6562|5A|
40035;2469011;0937474;0937474;16466;265394;501512;6;

    """,
    ),
    ("pna", _("PNA code"), "Wymagany format: xx-xxx"),
    (
        "address_feature",
        _("Address feature"),
        "Wymagane wartości: ul. (ulica), al. (aleja), pl. (plac), skwer, bulw. (bulwar), rondo, park, rynek, szosa, "
        "droga, os. (osiedle), ogród, wyspa, wyb. (wybrzeże), inne",
    ),
    (
        "phone",
        _("Phone number"),
        "W polskiej strefie numeracyjnej zaleca się zapisywanie numeru telefonu jako ciągu 9 cyfr, bez wyróżniania "
        "tzw. numeru kierunkowego miejscowości. Dopuszczalne jest stosowanie prefiksu międzynarodowego poprzedzonego "
        "znakiem plus „+” – struktura xxxxxxxxx/ lub +48xxxxxxxxx. Nie stosuje się spacji, nawiasów i łączników ani "
        "podobnych znaków pełniących role separatorów.",
    ),
    ("bool", _("Field of logical values"), "Wymagane wartości: True, False"),
    #     ("date", _("Date"), """Wymagany format zapisu dat:
    # a) yyyy-mm-dd;
    # """),
    #     ("time", _("Time"), """Wymagany format zapisu czasu:
    # a) hh:mm:ss
    # b) hh:mm
    # """),
    #     ("datetime", _("DateTime"), """
    # Wymagane formaty łącznego zapisu dat i czasu:
    # a) yyyy-mm-ddThh:mm
    # b) yyyy-mm-ddThh:mm:ss
    # c) yyyy-mm-dd hh:mm (spacja między datą a czasem)
    # d) yyyy-mm-dd hh:mm:ss (spacja między datą a czasem)
    # """),
)

DATA_TYPES = (
    ("integer", _("Integer"), ""),
    ("number", _("Float"), ""),
    ("string", _("String"), ""),
    ("boolean", _("Logic value (True/False)"), ""),
    ("date", _("Date"), ""),
    ("time", _("Time"), ""),
    ("datetime", _("DateTime"), ""),
    ("any", _("Any type"), ""),
)

RESOURCE_VALIDATION_TOOL_ENABLED = True

ENABLE_SUBSCRIPTIONS_EMAIL_REPORTS = True

# WAGTAIL CONFIG
WAGTAIL_SITE_NAME = "Otwarte Dane"

UNLEASH_URL = "https://flags.dane.gov.pl/api"

GEO_TYPES = {
    "": [
        ("label", _("Label"), _("Describes the presented data. Required item.")),
    ],
    "geographical coordinates": [
        (
            "l",
            _("Longitude"),
            "Dla zestawu danych mapowych “współrzędne geograficzne” należy obowiązkowo wybrać trzy elementy z listy: "
            "„długość geograficzna”, „szerokość geograficzna” oraz „etykieta” (opis punktu, który ma się pojawić na "
            "mapie). Współrzędne geograficzne są przetwarzane zgodnie z układem współrzędnych WGS84. Kolumny zawierające "
            "współrzędne geograficzne muszą być typu numerycznego",
        ),
        (
            "b",
            _("Latitude"),
            "Dla zestawu danych mapowych “współrzędne geograficzne” należy obowiązkowo wybrać trzy elementy z listy: "
            "„długość geograficzna”, „szerokość geograficzna” oraz „etykieta” (opis punktu, który ma się pojawić na "
            "mapie). Współrzędne geograficzne są przetwarzane zgodnie z układem współrzędnych WGS84. Kolumny zawierające "
            "współrzędne geograficzne muszą być typu numerycznego",
        ),
    ],
    "universal address": [
        (
            "uaddress",
            _("Universal address"),
            "Dla zestawu danych mapowych “adres uniwersalny“ należy obowiązkowo wybrać dwa elementy z listy: "
            "„adres uniwersalny” oraz “etykieta” (opis punktu, który ma się pojawić na mapie).",
        ),
    ],
    "address": [
        (
            "place",
            _("Place"),
            "Dla zestawu danych mapowych “adres” należy obowiązkowo wybrać trzy elementy z listy: „miejscowość”, "
            "„kod pocztowy” oraz „etykieta” (opis punktu, który ma się pojawić na mapie). Elementy ulica i numer "
            "domu są opcjonalne.",
        ),
        (
            "street",
            _("Street"),
            "Dla zestawu danych mapowych “adres” należy obowiązkowo wybrać trzy elementy z listy: „miejscowość”, "
            "„kod pocztowy” oraz „etykieta” (opis punktu, który ma się pojawić na mapie). Elementy ulica i numer "
            "domu są opcjonalne.",
        ),
        (
            "house_number",
            _("House number"),
            "Dla zestawu danych mapowych “adres” należy obowiązkowo wybrać trzy elementy z listy: „miejscowość”, "
            "„kod pocztowy” oraz „etykieta” (opis punktu, który ma się pojawić na mapie). Elementy ulica i numer "
            "domu są opcjonalne.",
        ),
        (
            "postal_code",
            _("Postal code"),
            "Dla zestawu danych mapowych “adres” należy obowiązkowo wybrać trzy elementy z listy: „miejscowość”, "
            "„kod pocztowy” oraz „etykieta” (opis punktu, który ma się pojawić na mapie). Elementy ulica i numer "
            "domu są opcjonalne.",
        ),
    ],
}

CMS_RICH_TEXT_FIELD_FEATURES = [
    "bold",
    "italic",
    "h2",
    "h3",
    "h4",
    "titled_link",
    "ol",
    "ul",
    "superscript",
    "subscript",
    "strikethrough" "document-link",
    "email-link",
    "lang-pl",
    "lang-en",
]

WAGTAILADMIN_RICH_TEXT_EDITORS = {
    "default": {
        "WIDGET": "wagtail.admin.rich_text.DraftailRichTextArea",
        "OPTIONS": {
            "features": [
                "bold",
                "italic",
                "h2",
                "h3",
                "h4",
                "ol",
                "ul",
                "hr",
                "image",
                "embed",
                "titled_link",
                "document-link",
                "email-link",
                "lang-en",
                "lang-pl",
            ]
        },
    },
}

GEOCODER_URL = env("GEOCODER_URL", default="http://geocoder.mcod.local")
GEOCODER_USER = env("GEOCODER_USER", default="geouser")
GEOCODER_PASS = env("GEOCODER_PASS", default="1234")
PLACEHOLDER_URL = env("PLACEHOLDER_URL", default="http://placeholder.mcod.local")

MAX_TAG_LENGTH = 100

WAGTAILDOCS_DOCUMENT_MODEL = "cms.CustomDocument"
WAGTAILIMAGES_IMAGE_MODEL = "cms.CustomImage"
WAGTAILADMIN_GLOBAL_PAGE_EDIT_LOCK = True

EXPORT_FORMAT_TO_MIMETYPE = {
    "csv": "text/csv",
    "xlsx": "application/vnd.ms-excel",
    "xml": "application/xml",
}

RDF_FORMAT_TO_MIMETYPE = {
    "jsonld": "application/ld+json",
    "xml": "application/rdf+xml",
    "rdf": "application/rdf+xml",
    "rdfa": "application/rdfa+xml",
    "n3": "text/n3",
    "ttl": "text/turtle",
    "turtle": "text/turtle",
    "nt": "application/n-triples",
    "nt11": "application/n-triples",
    "ntriples": "application/n-triples",
    "nq": "application/n-quads",
    "nquads": "application/n-quads",
    "trix": "application/trix",
    "trig": "application/trig",
}

RDF_MIMETYPES = list(set(RDF_FORMAT_TO_MIMETYPE.values()))

JSONAPI_FORMAT_TO_MIMETYPE = {
    "ja": "application/vnd.api+json; ext=bulk",
    "json": "application/vnd.api+json; ext=bulk",
    "jsonapi": "application/vnd.api+json; ext=bulk",
    "json-api": "application/vnd.api+json; ext=bulk",
}

JSONAPI_MIMETYPES = ["application/vnd.api+json; ext=bulk", "application/vnd.api+json"]

dailymotion = {
    "endpoint": "http://www.dailymotion.com/api/oembed/",
    "urls": [r"^http(?:s)?://[-\w]+\.dailymotion\.com/.+$"],
}

youtube = {
    "endpoint": "https://www.youtube.com/oembed",
    "urls": [
        r"^https?://(?:[-\w]+\.)?youtube\.com/watch.+$",
        r"^https?://(?:[-\w]+\.)?youtube\.com/v/.+$",
        r"^https?://youtu\.be/.+$",
        r"^https?://(?:[-\w]+\.)?youtube\.com/user/.+$",
        r"^https?://(?:[-\w]+\.)?youtube\.com/[^#?/]+#[^#?/]+/.+$",
        r"^https?://m\.youtube\.com/index.+$",
        r"^https?://(?:[-\w]+\.)?youtube\.com/profile.+$",
        r"^https?://(?:[-\w]+\.)?youtube\.com/view_play_list.+$",
        r"^https?://(?:[-\w]+\.)?youtube\.com/playlist.+$",
    ],
}

OD_EMBED = {
    "urls": [
        r"^https?://cms\.(?:(?:dev|int|szkolenia)\.)?dane\.gov\.pl/admin/videos/\d+/?$",
    ]
}

WAGTAILEMBEDS_FINDERS = [
    {
        "class": "wagtail.embeds.finders.oembed",
        "providers": [dailymotion, youtube] + all_providers,
    },
    {"class": "mcod.cms.embed.finders.ODEmbedFinder", "providers": [OD_EMBED]},
]

HYPER_EDITOR = {"IMAGE_API_URL": "%s/hypereditor/chooser-api/images/" % CMS_URL}

HYPER_EDITOR_EXCLUDE_BLOCKS = ["contentbox", "tab", "slider"]

# CSRF config:
ENABLE_CSRF = True
CSRF_SECRET_LENGTH = 32
CSRF_TOKEN_LENGTH = 2 * CSRF_SECRET_LENGTH
CSRF_ALLOWED_CHARS = string.ascii_letters + string.digits
API_CSRF_COOKIE_NAME = "mcod_csrf_token"
API_CSRF_HEADER_NAME = "X-MCOD-CSRF-TOKEN"
API_CSRF_TRUSTED_ORIGINS = [
    "dane.gov.pl",
]
API_CSRF_COOKIE_DOMAINS = env("API_CSRF_COOKIE_DOMAINS", default=SESSION_COOKIE_DOMAIN).split(",")

# ELASTICSEARCH SYNONYMS
ES_EN_SYN_FILTER_KWARGS = {
    "type": "synonym",
    "lenient": True,
    "format": "wordnet",
    "synonyms_path": "synonyms/en_wn_s.pl",
}

ES_PL_SYN_FILTER_KWARGS = {
    "type": "synonym",
    "lenient": True,
    "format": "solr",
    "synonyms_path": "synonyms/pl_synonyms.txt",
}
DEACTIVATE_ACCEPTED_DATASET_SUBMISSIONS_PUBLISHED_DAYS_AGO = 90
DESCRIPTION_FIELD_MAX_LENGTH = 10000
DESCRIPTION_FIELD_MIN_LENGTH = 20

SHACL_SHAPES = {
    "deprecateduris": SHACL_SHAPES_DIR.path("dcat-ap_2.1.0_shacl_deprecateduris.ttl").root,
    "imports": SHACL_SHAPES_DIR.path("dcat-ap_2.1.0_shacl_imports.ttl").root,
    "mdr-vocabularies": SHACL_SHAPES_DIR.path("dcat-ap_2.1.0_shacl_mdr-vocabularies.shape.ttl").root,
    "mdr_imports": SHACL_SHAPES_DIR.path("dcat-ap_2.1.0_shacl_mdr_imports.ttl").root,
    "range": SHACL_SHAPES_DIR.path("dcat-ap_2.1.0_shacl_range.ttl").root,
    "shapes": SHACL_SHAPES_DIR.path("dcat-ap_2.1.0_shacl_shapes.ttl").root,
    "shapes_recommended": SHACL_SHAPES_DIR.path("dcat-ap_2.1.0_shacl_shapes_recommended_modified.ttl").root,
}

NOTIFICATIONS_NOTIFICATION_MODEL = "schedules.Notification"

SHACL_UNSUPPORTED_MIMETYPES = ["application/n-quads", "application/trix"]

STATS_THEME_COOKIE_NAME = "mcod_stats_theme"

# Falcon settings
FALCON_CACHING_ENABLED = env("FALCON_CACHING_ENABLED", default="yes") in (
    "yes",
    1,
    "true",
)
FALCON_LIMITER_ENABLED = env("FALCON_LIMITER_ENABLED", default="yes") in (
    "yes",
    1,
    "true",
)
# https://falcon-limiter.readthedocs.io/en/latest/#rate-limit-string-notation
FALCON_LIMITER_DEFAULT_LIMITS = env("FALCON_LIMITER_DEFAULT_LIMITS", default="5 per minute,2 per second")
FALCON_LIMITER_SPARQL_LIMITS = env("FALCON_LIMITER_SPARQL_LIMITS", default="20 per minute,1 per second")

FALCON_MIDDLEWARES = [
    "mcod.core.api.middlewares.ContentTypeMiddleware",
    "mcod.core.api.middlewares.DebugMiddleware",
    "mcod.core.api.middlewares.LocaleMiddleware",
    "mcod.core.api.middlewares.ApiVersionMiddleware",
    "mcod.core.api.middlewares.CounterMiddleware",
    "mcod.core.api.middlewares.SearchHistoryMiddleware",
    "mcod.core.api.middlewares.PrometheusMiddleware",
    "mcod.core.api.middlewares.DjangoDBConnectionMiddleware",
]

DISCOURSE_HOST = env("DISCOURSE_HOST", default="http://forum.mcod.local")
DISCOURSE_SYNC_HOST = env("DISCOURSE_SYNC_HOST", default="http://forum.mcod.local")
DISCOURSE_API_USER = env("DISCOURSE_API_USER", default="system")
DISCOURSE_API_KEY = env("DISCOURSE_API_KEY", default="")
DISCOURSE_SSO_SECRET = env("DISCOURSE_SSO_SECRET", default="")
DISCOURSE_SSO_REDIRECT = env("DISCOURSE_SSO_REDIRECT", default=f"{DISCOURSE_HOST}/session/sso_login")
DISCOURSE_CONNECT_URL = f"{ADMIN_URL}/discourse/connect/start"
DISCOURSE_LOGOUT_REDIRECT = f"{BASE_URL}/pl/user/logout"

LICENSES_LINKS = {
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY-NC 4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "CC BY-NC-SA 4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "CC BY-ND 4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
    "CC BY-NC-ND 4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
}
CKAN_LICENSES_WHITELIST = {
    "cc-zero": "CC0 1.0",
    "cc-by": "CC BY 4.0",
    "cc-by-sa": "CC BY-SA 4.0",
    "cc-nc": "CC BY-NC 4.0",
}

CSV_CATALOG_BATCH_SIZE = env("CSV_CATALOG_BATCH_SIZE", default=20000)

DISCOURSE_FORUM_ENABLED = env("DISCOURSE_FORUM_ENABLED", default=True)

SPARQL_ENDPOINTS = {
    "kronika": {
        "query_endpoint": env("KRONIKA_SPARQL_URL", default="http://kronika.mcod.local"),
        "returnFormat": "json",
    }
}

MATOMO_SITE_IDS = {
    "dev": "2",
    "int": "3",
    "preprod": "4",
    "prod": "5",
}

if ENVIRONMENT in MATOMO_SITE_IDS:
    MATOMO_URL = env("MATOMO_URL", default="stats.dane.gov.pl")
    MATOMO_SITE_ID = env("MATOMO_SITE_ID", default=MATOMO_SITE_IDS[ENVIRONMENT])

METABASE_URL = env("METABASE_URL", default="http://metabase.mcod.local")
METABASE_API_KEY = env("METABASE_API_KEY", default="")

KIBANA_URL = env("KIBANA_URL", default="http://kibana.mcod.local")
ZABBIX_API = {
    "user": env("ZABBIX_API_USER", default="user"),
    "password": env("ZABBIX_API_PASSWORD", default=""),
    "url": env("ZABBIX_API_URL", default="http://zabbix.mcod.local"),
}

DEFAULT_REGION_ID = 85633723

DATASET_ARCHIVE_FILES_TASK_DELAY = env("DATASET_ARCHIVE_FILES_TASK_DELAY", default=180)
DATASET_IS_PROMOTED_LIMIT = env("DATASET_IS_PROMOTED_LIMIT", default=5)

ALLOWED_MINIMUM_SPACE = 1024 * 1024 * 1024 * env("ALLOWED_MINIMUM_FREE_GB", default=20)

WAGTAILVIDEOS_VIDEO_MODEL = "cms.CustomVideo"

X_FRAME_OPTIONS = "SAMEORIGIN"

#  https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

PRIVATE_LICENSES_ARTICLE_URL = env(
    "PRIVATE_LICENSES_ARTICLE_URL",
    default="/pl/page/opis-warunkow-i-licencji-dla-dostawcow-sektora-prywatnego",
)
PUBLIC_LICENSES_ARTICLE_URL = env(
    "PUBLIC_LICENSES_ARTICLE_URL",
    default="/pl/page/opis-warunkow-i-licencji-dla-dostawcow-sektora-publicznego",
)


ENABLE_SENTRY = env("ENABLE_SENTRY", default="no") in ["yes", "1", "true"]

SENTRY_SDK_KWARGS = {
    "admin": {
        "dsn": env("ADMIN_SENTRY_DSN", default="http://token@127.0.0.1:9000/1"),
        "integrations": [DjangoIntegration()],
        "traces_sample_rate": env("ADMIN_SAMPLE_RATE", default=1.0),
        "send_default_pii": True,
        "environment": ENVIRONMENT,
    },
    "cms": {
        "dsn": env("CMS_SENTRY_DSN", default="http://token@127.0.0.1:9000/2"),
        "integrations": [DjangoIntegration()],
        "traces_sample_rate": env("CMS_SAMPLE_RATE", default=1.0),
        "send_default_pii": True,
        "environment": ENVIRONMENT,
    },
    "celery": {
        "dsn": env("CELERY_SENTRY_DSN", default="http://token@127.0.0.1:9000/3"),
        "integrations": [CeleryIntegration()],
        "traces_sample_rate": env("CELERY_SAMPLE_RATE", default=1.0),
        "environment": ENVIRONMENT,
    },
    "api": {
        "dsn": env("API_SENTRY_DSN", default="http://token@127.0.0.1:9000/4"),
        "integrations": [FalconIntegration()],
        "traces_sample_rate": env("API_SAMPLE_RATE", default=1.0),
        "environment": ENVIRONMENT,
    },
    "ws": {
        "dsn": env("WS_SENTRY_DSN", default="http://token@127.0.0.1:9000/5"),
        "traces_sample_rate": env("WS_SAMPLE_RATE", default=1.0),
        "environment": ENVIRONMENT,
    },
}

if COMPONENT in ["admin", "cms", "celery"] and ENABLE_SENTRY:
    sentry_sdk.init(**SENTRY_SDK_KWARGS[COMPONENT])


USERS_TEST_LOGINGOVPL = env.bool("USERS_TEST_LOGINGOVPL", default=False)
LOGINGOVPL_ISSUER = env("LOGINGOVPL_ISSUER", default="CA_INT_LOGIN")
LOGINGOVPL_SSO_URL = env("LOGINGOVPL_SSO_URL", default="https://int.login.gov.pl/login/SingleSignOnService")
LOGINGOVPL_ASSERTION_CONSUMER_URL = env("LOGINGOVPL_ASSERTION_CONSUMER_URL", default="http://127.0.0.1/idp")
LOGINGOVPL_ENC_KEY = env("LOGINGOVPL_ENC_KEY", default="pki/logingovpl_int_enc.key.pem")
LOGINGOVPL_ENC_CERT = env("LOGINGOVPL_ENC_CERT", default="pki/logingovpl_int_enc.crt.pem")

LOGINGOVPL_ARTIFACT_RESOLVE_URL = env(
    "LOGINGOVPL_ARTIFACT_RESOLVE_URL",
    default="https://int.login.gov.pl/login-services/idpArtifactResolutionService",
)
LOGINGOVPL_SL_URL = env(
    "LOGINGOVPL_SL_URL",
    default="https://int.login.gov.pl/login-services/singleLogoutService",
)

FIELD_ENCRYPTION_KEYS = env.list("FIELD_ENCRYPTION_KEYS", default=list())
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="https://dane.gov.pl")

HEALTH_STATUS_SLEEP_TIME = env.int("HEALTH_STATUS_SLEEP_TIME", default=600)  # default 10min
HEALTH_CHECK = env.bool("HEALTH_CHECK", default=True)

BROKEN_LINKS_EXCLUDE_DEVELOPERS = env.bool("BROKEN_LINKS_EXCLUDE_DEVELOPERS", True)
