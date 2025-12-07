import json
from datetime import datetime

from auditlog.models import LogEntry as BaseLogEntry
from deepdiff import DeepDiff
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer

from mcod.core.api.search.helpers import get_document_for_model
from mcod.core.api.search.tasks import delete_document_task, update_document_task
from mcod.histories.managers import HistoryManager, LogEntryManager


class History(models.Model):
    table_name = models.CharField(max_length=255, verbose_name=_("table name"))
    row_id = models.IntegerField(verbose_name=_("row id"))
    action = models.CharField(max_length=50, verbose_name=_("action"))
    old_value = JSONField(verbose_name=_("old value"), null=True)
    new_value = JSONField(verbose_name=_("new value"), null=True)
    change_user_id = models.IntegerField(verbose_name=_("User"))
    change_timestamp = models.DateTimeField(verbose_name=_("Change timestamp"), default=datetime.now)
    message = models.TextField(verbose_name=_("message"), null=True)

    objects = HistoryManager()

    class Meta:
        db_table = "history"
        verbose_name = _("History")
        verbose_name_plural = _("Histories")

    @property
    def action_display(self):
        return self.action

    @property
    def difference(self):
        if self.action == "UPDATE":
            ddiff = DeepDiff(
                self.old_value,
                self.new_value,
                ignore_order=True,
                verbose_level=0,
                exclude_paths={"root['modified']", "root['metadata_modified']"},
            )

            if "type_changes" in ddiff:
                del ddiff["type_changes"]
            if "dictionary_item_added" in ddiff:
                del ddiff["dictionary_item_added"]
            if "values_changed" in ddiff:
                for el in ddiff["values_changed"]:
                    if "diff" in ddiff["values_changed"][el]:
                        del ddiff["values_changed"][el]["diff"]
            ddiff = ddiff.json
        else:
            ddiff = json.dumps(self.new_value, ensure_ascii=False)
        return ddiff

    @property
    def logentry_action(self):
        if self.action == "INSERT":
            return LogEntry.Action.CREATE
        elif self.action == "UPDATE":
            return LogEntry.Action.UPDATE
        elif self.action == "DELETE":
            return LogEntry.Action.DELETE

    @property
    def logentry_changes(self):
        return json.dumps(self.new_value, ensure_ascii=False) if self.new_value else ""

    @property
    def user(self):
        users = get_user_model()
        user = users.objects.get(id=self.change_user_id)
        return user

    def __str__(self):
        return f"{self.id} | {self.action} > {self.table_name} > {self.row_id}"

    def diff_prettified(self):
        response = json.loads(self.difference)
        response = json.dumps(response, sort_keys=True, indent=1, ensure_ascii=False).replace("&oacute;", "ó")
        response = response[:10000]
        formatter = HtmlFormatter(style="colorful", lineseparator="<br>")
        response = highlight(response, JsonLexer(), formatter)
        style = "<style>" + formatter.get_style_defs() + "</style>"
        return mark_safe(style + response)

    diff_prettified.short_description = _("Differences")

    @classmethod
    def get_object_history(cls, obj):
        return cls.objects.filter(table_name=obj._meta.model_name, row_id=obj.id)

    @classmethod
    def accusative_case(cls):
        return _("acc: History")

    def indexing(self):

        Document = get_document_for_model(History)

        obj = Document(
            id=self.id,
            table_name=self.table_name,
            row_id=self.row_id,
            action=self.action,
            change_user_id=self.change_user_id,
            change_timestamp=self.change_timestamp,
            message=self.message,
        )
        obj.save()
        return obj.to_dict(include_meta=True)


class LogEntry(BaseLogEntry):

    objects = LogEntryManager()

    class Meta:
        get_latest_by = "timestamp"
        ordering = ["-timestamp"]
        verbose_name = _("History")
        verbose_name_plural = _("Histories")
        proxy = True

    def __str__(self):
        return f"{self.id} | {self.action_display} > {self.table_name} > {self.object_id}"

    @property
    def action_display(self):
        return self.get_action_display().upper()

    @property
    def action_name(self):
        _name = self.action_display
        return "INSERT" if _name == "CREATE" else _name

    @property
    def change_timestamp(self):
        return self.timestamp

    @property
    def change_user_id(self):
        return self.user.id if self.user else None

    @property
    def difference(self):
        return self.changes

    @property
    def diff_prettified(self):
        response = json.loads(self.changes)
        response = json.dumps(response, sort_keys=True, indent=1, ensure_ascii=False).replace("&oacute;", "ó")
        response = response[:10000]
        formatter = HtmlFormatter(style="colorful", lineseparator="<br>")
        response = highlight(response, JsonLexer(), formatter)
        style = "<style>" + formatter.get_style_defs() + "</style>"
        return mark_safe(style + response)

    @property
    def message(self):
        return None

    @property
    def row_id(self):
        return self.object_id

    @property
    def table_name(self):
        return self.content_type.model

    @property
    def user(self):
        return self.actor

    def get_changed_value(self, field_name, default_value):
        changes = json.loads(self.changes)
        field_value = changes.get(field_name)
        if field_value is None:
            val = default_value
        elif isinstance(field_value, list):
            val = field_value[1]
            if field_name == "is_removed":
                val = val == "True"
        else:
            val = field_value
        return val

    @property
    def is_create(self):
        return self.action == self.Action.CREATE

    @property
    def is_update(self):
        return self.action == self.Action.UPDATE

    @property
    def is_delete(self):
        return self.action == self.Action.DELETE

    @classmethod
    def migrate_history(cls, from_obj, obj):
        s_ct = ContentType.objects.get_for_model(obj._meta.model)
        old_history = cls.objects.get_for_object(obj)
        history = cls.objects.get_for_object(from_obj)
        if old_history.exists():
            old_history.delete()
        for item in history:
            item.id = None
            item.content_type = s_ct
            item.object_id = obj.id
            item.object_pk = str(obj.id)
            timestamp = item.timestamp
            item.save()
            item.timestamp = timestamp  # https://stackoverflow.com/q/7499767/1845230
            item.save(update_fields=["timestamp"])


@receiver(post_save, sender=LogEntry)
@receiver(post_save, sender=BaseLogEntry)
def update_log_entry_handler(sender, instance, *args, **kwargs):
    update_document_task.s(LogEntry._meta.app_label, LogEntry._meta.object_name, instance.id).apply_async_on_commit(
        queue="history"
    )


@receiver(post_delete, sender=LogEntry)
@receiver(post_delete, sender=BaseLogEntry)
def delete_log_entry_handler(sender, instance, *args, **kwargs):
    delete_document_task.s(LogEntry._meta.app_label, LogEntry._meta.object_name, instance.id).apply_async(queue="history")
