from prometheus_client import Counter, Gauge, Histogram

# Admin metrics
ADMIN_DB_QUERY_TIME_HISTOGRAM = Histogram(
    "django_admin_db_query_duration_seconds", "Total DB time for Django Admin requests", ["admin_view"]
)


# Models metrics
RESOURCES_CREATED = Counter("resources_created_total", "Total number of Resource objects created", ["source"])
RESOURCES_COUNT = Gauge("resources_total", "Current number of Resource objects", ["source"])

DATASET_CREATED = Counter("dataset_created_total", "Total number of Dataset objects created", ["source"])

ORGANIZATION_CREATED = Counter(
    "organization_created_total",
    "Total number of Organization objects created",
    ["source"],
)
ORGANIZATION_COUNT = Gauge("organization_total", "Total number of Organization objects", ["source"])


# API metrics
API_REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "http_status"])
API_REQUEST_LATENCY_HISTOGRAM = Histogram("http_request_duration_seconds", "Request latency", ["method", "endpoint"])
API_ERROR_COUNT = Counter("http_errors_total", "Total HTTP 5xx errors", ["method", "endpoint", "status_code"])
API_DB_QUERY_TIME_HISTOGRAM = Histogram("falcon_db_query_duration_seconds", "DB query duration for Falcon API requests", ["path"])


# General metrics
CMS_UP = Gauge("cms_up", "Health status of CMS (1 = up, 0 = down)", ["url"])
DJANGO_ADMIN_UP = Gauge("django_admin_up", "Health status of Django Admin (1 = up, 0 = down)", ["url"])
