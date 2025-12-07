import os
from typing import Optional

from mcod.settings.base import *  # noqa: F403, F405

ROOT_DIR = environ.Path(__file__) - 3  # noqa: F405

TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG  # noqa: F405
INTERNAL_IPS = ("127.0.0.1", "localhost", "172.18.18.100")  # needed to use debug processor in django templates


EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"

BASE_URL = "http://test.mcod"
API_URL = "http://api.test.mcod"
ADMIN_URL = "http://admin.test.mcod"

API_URL_INTERNAL = "http://localhost"

ELASTICSEARCH_INDEX_PREFIX = "test"

ELASTICSEARCH_DSL_INDEX_SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}

ELASTICSEARCH_HISTORIES_IDX_SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}

LANGUAGE_CODE = "pl"


def get_es_index_names():
    import uuid

    index_prefix = str(uuid.uuid4())
    worker = os.environ.get("PYTEST_XDIST_WORKER", "")
    index_prefix = f"{index_prefix}-{worker}"
    return {
        "common": "test-common-{}".format(index_prefix),
        "applications": "test-applications-{}".format(index_prefix),
        "courses": "test-courses-{}".format(index_prefix),
        "datasets": "test-datasets-{}".format(index_prefix),
        "lab_events": "test-lab_events-{}".format(index_prefix),
        "institutions": "test-institutions-{}".format(index_prefix),
        "resources": "test-resources-{}".format(index_prefix),
        "histories": "test-histories-{}".format(index_prefix),
        "logentries": "test-logentries-{}".format(index_prefix),
        "searchhistories": "test-searchhistories-{}".format(index_prefix),
        "accepted_dataset_submissions": "test-accepted_dataset_submissions-{}".format(index_prefix),
        "meetings": "test-meetings-{}".format(index_prefix),
        "news": "test-news-{}".format(index_prefix),
        "knowledge_base_pages": "test-knowledge_base_pages-{}".format(index_prefix),
        "regions": "test-regions-{}".format(index_prefix),
        "showcases": "test-showcases-{}".format(index_prefix),
    }


ELASTICSEARCH_INDEX_NAMES = get_es_index_names()


def get_es_alias_name():
    import uuid

    index_prefix = str(uuid.uuid4())
    worker = os.environ.get("PYTEST_XDIST_WORKER", "")
    return f"{index_prefix}-{worker}-test-common-alias"


ELASTICSEARCH_COMMON_ALIAS_NAME = get_es_alias_name()


ELASTICSEARCH_DSL_SEARCH_INDEX_ALIAS = {
    ELASTICSEARCH_COMMON_ALIAS_NAME: {},
}


def get_email_file_path():
    import uuid

    return "/tmp/app-messages-%s" % str(uuid.uuid4())


EMAIL_FILE_PATH = get_email_file_path()
TEST_SAMPLES_PATH = str(ROOT_DIR("data/test_samples"))
TEST_CERTS_PATH = str(ROOT_DIR("data/test_certs"))
TEST_ROOT = str(ROOT_DIR("test"))

MEDIA_ROOT = str(os.path.join(TEST_ROOT, "media"))
IMAGES_MEDIA_ROOT = str(os.path.join(MEDIA_ROOT, "images"))
MEETINGS_MEDIA_ROOT = str(os.path.join(MEDIA_ROOT, "meetings"))
NEWSLETTER_MEDIA_ROOT = str(os.path.join(MEDIA_ROOT, "newsletter"))
RESOURCES_MEDIA_ROOT = str(os.path.join(MEDIA_ROOT, "resources"))
BROKEN_LINKS_CREATION_STAGING_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "broken_links_temp"))
MAIN_DGA_RESOURCE_XLSX_CREATION_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "main_dga"))
RESOURCES_FILES_TO_REMOVE_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "to_be_removed", "resources"))
REPORTS_MEDIA_ROOT = str(os.path.join(MEDIA_ROOT, "reports"))
SHOWCASES_MEDIA_ROOT = str(os.path.join(MEDIA_ROOT, "showcases"))
DCAT_VOCABULARIES_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "resources"))
METADATA_MEDIA_ROOT = str(ROOT_DIR.path(MEDIA_ROOT, "datasets", "catalog"))

# Do not use cache in tests
MAIN_DGA_RESOURCE_CREATION_CACHE_TIMEOUT = 0
MAIN_DGA_RESOURCE_XLSX_CREATION_CACHE_TIMEOUT = 0

CACHES.update({"test": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})


MEDIA_URL = "/media/"
IMAGES_URL = "%s%s" % (MEDIA_URL, "images")
MEETINGS_URL = "%s%s" % (MEDIA_URL, "meetings")
NEWSLETTER_URL = "%s%s" % (MEDIA_URL, "newsletter")
REPORTS_MEDIA = "%s%s" % (MEDIA_URL, "reports")
RESOURCES_URL = "%s%s" % (MEDIA_URL, "resources")
SHOWCASES_URL = "%s%s" % (MEDIA_URL, "showcases")

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_DEFAULT_QUEUE = "mcod"
CELERY_TASK_QUEUES = {
    Queue("test"),
}

CELERY_TASK_ROUTES = {}

SESSION_COOKIE_NAME = "test_sessionid"
SESSION_COOKIE_DOMAIN = "test.mcod"
SESSION_COOKIE_SECURE = False
API_TOKEN_COOKIE_NAME = "test_apiauthtoken"


LOGGING["loggers"]["django.db.backends"]["level"] = "INFO"
LOGGING["loggers"]["django.db.backends"]["handlers"] = ["console"]
LOGGING["loggers"]["django.request"]["level"] = "INFO"
LOGGING["loggers"]["django.request"]["handlers"] = ["console"]
LOGGING["loggers"]["django.server"]["level"] = "INFO"
LOGGING["loggers"]["django.server"]["handlers"] = ["console"]
LOGGING["loggers"]["signals"]["level"] = "INFO"
LOGGING["loggers"]["signals"]["handlers"] = ["console"]
LOGGING["loggers"]["celery.app.trace"]["level"] = "WARNING"
LOGGING["loggers"]["celery.app.trace"]["handlers"] = ["console"]
LOGGING["loggers"]["mcod"]["handlers"] = ["console"]
LOGGING["loggers"]["resource_file_processing"]["handlers"] = ["console"]

SUIT_CONFIG["LIST_PER_PAGE"] = 100

# Makes tests faster (https://brobin.me/blog/2016/08/7-ways-to-speed-up-your-django-test-suite/)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

COMPONENT = env("COMPONENT", default="admin")
ENVIRONMENT = "test"
ENABLE_CSRF = False
API_CSRF_COOKIE_DOMAINS = ["test.local", "localhost", "dane.gov.pl"]

ES_EN_SYN_FILTER_KWARGS = {
    "type": "synonym",
    "lenient": True,
    "synonyms": ["foo, bar => baz"],
}

ES_PL_SYN_FILTER_KWARGS = {
    "type": "synonym",
    "lenient": True,
    "synonyms": ["sierściuch, kot"],
}
FALCON_LIMITER_ENABLED = False

DISCOURSE_FORUM_ENABLED = False

SPARQL_ENDPOINTS = {
    "kronika": {
        "endpoint": "http://kronik.gov.pl",
        "headers": {"host": "public-api.k8s"},
    }
}

FIELD_ENCRYPTION_KEYS = ["c2d95c58322ca6ddcf8b0c304c8131f6b515ff5f3a297dcdadeda1a82cb4ec9b"]

MAIN_DGA_DATASET_OWNER_ORGANIZATION_PK = 99

# Set unique cache prefix for each pytest worker to isolate session clearing
# in a shared cache environment, preventing conflicts between workers.
worker_id: Optional[str] = os.environ.get("PYTEST_XDIST_WORKER")
if worker_id:
    CACHES["sessions"].update({"KEY_PREFIX": f"worker_{worker_id}_cache_session_"})

# update `HARVESTER_XML_VERSION_TO_SCHEMA_PATH` for XML harvester tests cases
HARVESTER_XML_VERSION_TO_SCHEMA_PATH.update(
    {"1.11_dataset_has_high_values_metadata_conflict": HARVESTER_DATA_DIR.path("xml_import_otwarte_dane_1_11.xsd").root}
)
HTTP_REQUEST_DEFAULT_TIMEOUT = 3

import socket

socket.setdefaulttimeout(HTTP_REQUEST_DEFAULT_TIMEOUT)


FALCON_MIDDLEWARES = [
    "mcod.core.api.middlewares.ContentTypeMiddleware",
    "mcod.core.api.middlewares.DebugMiddleware",
    "mcod.core.api.middlewares.LocaleMiddleware",
    "mcod.core.api.middlewares.ApiVersionMiddleware",
    "mcod.core.api.middlewares.CounterMiddleware",
    "mcod.core.api.middlewares.SearchHistoryMiddleware",
    "mcod.core.api.middlewares.PrometheusMiddleware",
]
HEALTH_CHECK = False
