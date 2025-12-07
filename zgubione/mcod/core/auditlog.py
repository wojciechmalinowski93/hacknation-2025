import json

from auditlog.diff import get_field_value, get_fields_in_model
from auditlog.models import LogEntry
from auditlog.registry import AuditlogModelRegistry
from django.db.models import Model
from django.db.models.signals import post_delete, post_save, pre_save
from django.utils.encoding import smart_str


def model_instance_diff(old, new):  # noqa: C901
    """
    Custom version of `auditlog.diff.model_instance_diff` - it uses `mcod.core.registries.auditlog` registry.
    """
    if not (old is None or isinstance(old, Model)):
        raise TypeError("The supplied old instance is not a valid model instance.")
    if not (new is None or isinstance(new, Model)):
        raise TypeError("The supplied new instance is not a valid model instance.")

    diff = {}

    if old is not None and new is not None:
        fields = set(old._meta.fields + new._meta.fields)
        model_fields = auditlog.get_model_fields(new._meta.model)
    elif old is not None:
        fields = set(get_fields_in_model(old))
        model_fields = auditlog.get_model_fields(old._meta.model)
    elif new is not None:
        fields = set(get_fields_in_model(new))
        model_fields = auditlog.get_model_fields(new._meta.model)
    else:
        fields = set()
        model_fields = None

    # Check if fields must be filtered
    if model_fields and (model_fields["include_fields"] or model_fields["exclude_fields"]) and fields:
        filtered_fields = []
        if model_fields["include_fields"]:
            filtered_fields = [field for field in fields if field.name in model_fields["include_fields"]]
        else:
            filtered_fields = fields
        if model_fields["exclude_fields"]:
            filtered_fields = [field for field in filtered_fields if field.name not in model_fields["exclude_fields"]]
        fields = filtered_fields

    for field in fields:
        old_value = get_field_value(old, field)
        new_value = get_field_value(new, field)

        if old_value != new_value:
            diff[field.name] = (smart_str(old_value), smart_str(new_value))

    if len(diff) == 0:
        diff = None

    return diff


def log_create(sender, instance, created, **kwargs):
    """Custom version of original `auditlog.receivers.log_create`."""
    if created:
        changes = model_instance_diff(None, instance)
        LogEntry.objects.log_create(
            instance,
            action=LogEntry.Action.CREATE,
            changes=json.dumps(changes),
        )


def log_update(sender, instance, **kwargs):
    """
    Custom version of original `auditlog.receivers.log_update` but uses `raw` model manager of sender
    in place of `objects` manager. It's required to log entry if instance's `is_removed=True`.
    """
    if instance.pk is not None:
        try:
            old = sender.raw.get(pk=instance.pk) if hasattr(sender, "raw") else sender.objects.get(pk=instance.id)
        except sender.DoesNotExist:
            pass
        else:
            new = instance
            changes = model_instance_diff(old, new)
            # Log an entry only if there are changes
            if changes:
                LogEntry.objects.log_create(
                    instance,
                    action=LogEntry.Action.UPDATE,
                    changes=json.dumps(changes),
                )


def log_delete(sender, instance, **kwargs):
    """Custom version of original `auditlog.receivers.log_delete`."""
    if instance.pk is not None:
        changes = model_instance_diff(instance, None)
        LogEntry.objects.log_create(
            instance,
            action=LogEntry.Action.DELETE,
            changes=json.dumps(changes),
        )


auditlog = AuditlogModelRegistry(custom={post_save: log_create, pre_save: log_update, post_delete: log_delete})
