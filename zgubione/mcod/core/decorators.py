import logging
from functools import wraps
from typing import TYPE_CHECKING, Callable, Type

import sentry_sdk
from django.db import OperationalError, ProgrammingError, connection
from django.http import HttpRequest, HttpResponse

from mcod.core.db.managers import QueryLogger
from mcod.core.metrics import (
    ADMIN_DB_QUERY_TIME_HISTOGRAM,
    DATASET_CREATED,
    ORGANIZATION_COUNT,
    ORGANIZATION_CREATED,
    RESOURCES_COUNT,
    RESOURCES_CREATED,
)

logger = logging.getLogger("mcod")


if TYPE_CHECKING:
    from mcod.datasets.models import Dataset
    from mcod.organizations.models import Organization
    from mcod.resources.models import Resource


def update_resource_metrics(method_name: str, allow_action: bool, is_bulk_delete: bool, model: Type["Resource"]):
    if method_name == "add_view" and allow_action:
        RESOURCES_CREATED.labels(source="admin").inc()
    if (method_name in {"add_view", "delete_view"} and allow_action) or is_bulk_delete:
        count_published = model.objects.filter(status="published").count()
        RESOURCES_COUNT.labels(source="all").set(model.raw_db.all().count())
        RESOURCES_COUNT.labels(source="published").set(count_published)


def update_dataset_metrics(method_name: str, allow_action: bool, is_bulk_delete=None, model: Type["Dataset"] = None):
    if (
        method_name
        in {
            "add_view",
        }
        and allow_action
    ):
        DATASET_CREATED.labels(source="admin").inc()


def update_organization_metrics(method_name: str, allow_action: bool, is_bulk_delete: bool, model: Type["Organization"]):
    if method_name == "add_view" and allow_action:
        ORGANIZATION_CREATED.labels(source="admin").inc()
    if (method_name in {"add_view", "delete_view"} and allow_action) or is_bulk_delete:
        ORGANIZATION_COUNT.labels(source="published").set(model.objects.all().count())


metric_handlers = {
    "Resource": update_resource_metrics,
    "Dataset": update_dataset_metrics,
    "Organization": update_organization_metrics,
}


def _wrap_method(original_method: Callable, method_name: str) -> Callable:
    @wraps(original_method)
    def wrapped(instance, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Wraps an admin view method to measure and record the total database query duration.

        Executes the original view method, sums up all recorded query durations, and updates a Prometheus histogram metric.
        """
        ql = QueryLogger()

        with connection.execute_wrapper(ql):
            response = original_method(instance, request, *args, **kwargs)

        try:
            duration = sum(float(q["duration"]) for q in ql.queries)
            view_label = f"{instance.__class__.__module__}.{instance.__class__.__name__}.{method_name}"
            ADMIN_DB_QUERY_TIME_HISTOGRAM.labels(admin_view=view_label).observe(duration)
        except KeyError as err:
            logger.error(f"Couldn't get `duration` attribute from ql.queries. {err}")
            sentry_sdk.api.capture_exception(err)
        except (ProgrammingError, OperationalError, AttributeError) as err:
            logger.error(err)
            sentry_sdk.api.capture_exception(err)

        delete_selected = request.POST.get("action") == "delete_selected"
        is_bulk_delete = method_name == "response_action" and delete_selected
        allow_action = request.method == "POST" and response.status_code == 302

        handler = metric_handlers.get(instance.model.__name__)

        if handler:
            handler(method_name, allow_action, is_bulk_delete, instance.model)

        return response

    return wrapped


def prometheus_monitoring(cls: Type) -> Type:
    """
    A class decorator that instruments selected Django admin view methods to record
    database query time with Prometheus metrics.
    """
    method_names = ["changelist_view", "change_view", "add_view", "delete_view", "history_view", "response_action"]

    for method_name in method_names:
        if hasattr(cls, method_name):
            original = getattr(cls, method_name)
            wrapped = _wrap_method(original, method_name)
            setattr(cls, method_name, wrapped)

    return cls
