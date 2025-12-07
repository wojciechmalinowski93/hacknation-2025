import time

from django.core.paginator import Paginator
from django.db import models
from django.db.models import QuerySet

from mcod.core.managers import SoftDeletableQuerySet


class QuerySetMixin:
    def get_filtered_results(self, **kwargs):
        return self.filter()

    def _get_page(self, queryset, page=1, per_page=20, **kwargs):
        paginator = Paginator(queryset, per_page)
        return paginator.get_page(page)

    def get_paginated_results(self, **kwargs):
        qs = self.get_filtered_results(**kwargs)
        return self._get_page(qs, **kwargs)


class DecisionSortableManagerMixin:
    def with_decision(self):
        return super().get_queryset().with_decision()

    def without_decision(self):
        return super().get_queryset().without_decision()


class DecisionQuerySetMixin:
    def with_decision(self):
        return self.exclude(decision="")

    def without_decision(self):
        return self.filter(decision="")


class DecisionSortableSoftDeletableQuerySet(DecisionQuerySetMixin, SoftDeletableQuerySet):
    pass


class TrashQuerySet(QuerySet):
    def delete(self):
        self.update(is_permanently_removed=True)


class DecisionSortableTrashQuerySet(DecisionQuerySetMixin, TrashQuerySet):
    pass


class TrashManager(models.Manager):
    _queryset_class = TrashQuerySet

    def get_queryset(self):
        return super().get_queryset().filter(is_removed=True, is_permanently_removed=False)


class PermanentlyRemovedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_permanently_removed=True)


class QueryLogger:
    """
    A database execution wrapper for collecting detailed information about SQL queries.

    This class can be passed to Django's `connection.execute_wrapper()` to intercept and log
    each SQL query executed during a request or operation. It records metadata such as:
    - The SQL statement
    - Parameters
    - Execution duration
    - Query status (success or error)
    - Exception details (if any)
    """

    def __init__(self):
        self.queries = []

    def __call__(self, execute, sql, params, many, context):
        current_query = {"sql": sql, "params": params, "many": many}
        start = time.perf_counter()
        try:
            result = execute(sql, params, many, context)
        except Exception:
            raise
        else:
            return result
        finally:
            duration = time.perf_counter() - start
            current_query["duration"] = duration
            self.queries.append(current_query)
