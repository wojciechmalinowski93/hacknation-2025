import logging
import time
from collections import defaultdict

from auditlog.models import LogEntryManager as BaseLogEntryManager
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Manager

logger = logging.getLogger("mcod")


class HistoryManager(Manager):

    @staticmethod
    def is_significant(status, is_removed):
        return status == "published" and is_removed is False

    def resources_availability_as_dict(self):
        d = defaultdict(dict)
        status = None
        is_removed = None
        h = self.filter(table_name="resource").order_by("row_id", "change_timestamp")
        p = Paginator(h, 10000)
        logger.debug("num_pages {}".format(p.num_pages))
        last_row_id = None
        for page_nr in p.page_range:
            start = time.perf_counter()
            for i, history in enumerate(p.page(page_nr)):
                date_str = history.change_timestamp.date().strftime("%Y-%m-%d")
                key = history.row_id
                inner_key = date_str
                if last_row_id != history.row_id:
                    last_row_id = history.row_id
                    status = None
                    is_removed = None
                    assert history.action == "INSERT"
                if history.action == "INSERT":
                    status = history.new_value.get("status", "draft")
                    is_removed = history.new_value.get("is_removed", True)
                    old_is_significant = self.is_significant(status, is_removed)
                    if old_is_significant:
                        d[key][inner_key] = 1
                elif history.action == "UPDATE":
                    old_is_significant = self.is_significant(status, is_removed)
                    new_status = history.new_value.get("status", status)
                    new_is_removed = history.new_value.get("is_removed", is_removed)
                    new_is_significant = self.is_significant(new_status, new_is_removed)
                    if old_is_significant != new_is_significant:
                        if new_is_significant:
                            d[key][inner_key] = 1
                        else:
                            d[key][inner_key] = 0
                    status = new_status
                    is_removed = new_is_removed
                elif history.action == "DELETE":
                    d[key][inner_key] = -1
            end = time.perf_counter()
            logger.debug("page_nr {}, time {}".format(page_nr, end - start))
        return d

    def get_history_other(
        self,
        table_name=None,
        row_id=None,
        with_unknown_user_rows=False,
        history_id=None,
    ):
        where_items = []
        if not with_unknown_user_rows:
            where_items.append('NOT ("change_user_id" = 1)')
        if row_id:
            where_items.append(f'"row_id" = {row_id}')
        if table_name:
            where_items.append(f"\"table_name\" = '{table_name}'")
        if history_id:
            where_items.append(f'"id" = {history_id}')
        sql = (
            'SELECT "id", "table_name", "row_id", "action", "old_value", "new_value", "change_user_id", '
            '"change_timestamp", "message" '
            'FROM "history_other" %(where)s ORDER BY "change_timestamp" DESC'
        ) % {
            "where": ("WHERE {}".format(" AND ".join(where_items)) if where_items else ""),
        }
        return self.raw(sql)


class LogEntryManager(BaseLogEntryManager):

    def for_admin_panel(self, exclude_models=None):
        models = [
            "application",
            "article",
            "article_category",
            "category",
            "dataset",
            "organization",
            "reports_report",
            "resource",
            "showcase",
            "supplement",
            "tag",
            "user",
            "user_following_application",
            "user_following_article",
            "user_following_dataset",
            "user_organization",
        ]
        exclude_models = exclude_models if isinstance(exclude_models, list) else []
        models = [x for x in models if x not in exclude_models]
        return self.get_queryset().filter(content_type__model__in=models).select_related("content_type")

    @staticmethod
    def is_significant(status, is_removed):
        return status == "published" and is_removed is False

    def get_availability_status(self, d, log_entry, object_id, dt, status, is_removed):
        if log_entry.is_create:
            status = log_entry.get_changed_value("status", "draft")
            is_removed = log_entry.get_changed_value("is_removed", True)
            old_is_significant = self.is_significant(status, is_removed)
            if old_is_significant:
                d[object_id][dt] = 1
        elif log_entry.is_update:
            old_is_significant = self.is_significant(status, is_removed)
            new_status = log_entry.get_changed_value("status", status)
            new_is_removed = log_entry.get_changed_value("is_removed", is_removed)
            new_is_significant = self.is_significant(new_status, new_is_removed)
            if old_is_significant != new_is_significant:
                if new_is_significant:
                    d[object_id][dt] = 1
                else:
                    d[object_id][dt] = 0
            status = new_status
            is_removed = new_is_removed
        elif log_entry.is_delete:
            d[object_id][dt] = -1
        return status, is_removed

    def resources_availability_as_dict(self):
        d = defaultdict(dict)
        status = None
        is_removed = None
        resource_type = ContentType.objects.get(app_label="resources", model="resource")
        entries = self.filter(content_type_id=resource_type.pk).order_by("object_id", "timestamp")
        p = Paginator(entries, 10000)
        logger.debug("num_pages {}".format(p.num_pages))
        last_row_id = None
        for page_nr in p.page_range:
            start = time.perf_counter()
            for i, log_entry in enumerate(p.page(page_nr)):
                date_str = log_entry.timestamp.date().strftime("%Y-%m-%d")
                current_id = log_entry.object_id
                inner_key = date_str
                if last_row_id != log_entry.object_id:
                    last_row_id = log_entry.object_id
                    status = None
                    is_removed = None
                    try:
                        assert log_entry.is_create
                    except AssertionError:
                        logger.debug(
                            f"{log_entry.get_action_display()} earlier than" f" CREATE for resource {log_entry.object_id}"
                        )
                        logger.debug(f"Timestamp: {log_entry.timestamp}")
                        logger.debug(f"Changes: {log_entry.changes}")
                        continue
                status, is_removed = self.get_availability_status(d, log_entry, current_id, inner_key, status, is_removed)
            end = time.perf_counter()
            logger.debug("page_nr {}, time {}".format(page_nr, end - start))
        return d
