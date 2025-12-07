from datetime import date

import pytz
from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.timezone import datetime, timedelta

from mcod.core.tasks import extended_shared_task


@extended_shared_task
def update_model_watcher_task(app_name, model_name, instance_id, obj_state="updated"):
    from mcod.watchers.models import OBJ_STATE_2_NOTIFICATION_TYPES

    ModelWatcher = apps.get_model("watchers", "ModelWatcher")
    try:
        model = apps.get_model(app_name, model_name.title())
        if hasattr(model, "raw"):
            instance = model.raw.get(pk=instance_id)
        else:
            instance = model.objects.get(pk=instance_id)
    except model.DoesNotExist:
        return {}

    try:
        if obj_state in (
            "m2m_added",
            "m2m_cleaned",
            "m2m_removed",
            "m2m_updated",
            "m2m_restored",
        ):
            prev_value = instance.tracker.previous("ref_value")
            _type = OBJ_STATE_2_NOTIFICATION_TYPES[obj_state]
            watcher = ModelWatcher.objects.get_from_instance(instance)
            model_watcher_updated_task.s(watcher.id, _type, prev_value).apply_async()
        else:
            ModelWatcher.objects.update_from_instance(instance, obj_state=obj_state)
    except ModelWatcher.DoesNotExist:
        return {}


@extended_shared_task
def remove_user_notifications_task(user_id, data):
    Notification = apps.get_model("watchers", "Notification")
    qs = Notification.objects.filter(subscription__user_id=user_id)
    ids = [int(item["id"]) for item in data]
    if ids:
        qs = qs.filter(pk__in=ids)
        qs.delete()
    return {}


@extended_shared_task
def update_notifications_task(user_id, data):
    Notification = apps.get_model("watchers", "Notification")
    qs = Notification.objects.filter(subscription__user_id=user_id)
    for item in data:
        qs.filter(pk=int(item["id"])).update(**item["attributes"])

    return {}


@extended_shared_task
def update_notifications_status_task(user_id, status="read"):
    Notification = apps.get_model("watchers", "Notification")
    _status = "new" if status == "read" else "read"
    qs = Notification.objects.filter(subscription__user_id=user_id, status=_status)
    qs.update(status=status)
    return {}


@extended_shared_task
def model_watcher_updated_task(watcher_id, notification_type, prev_value):
    ModelWatcher = apps.get_model("watchers", "ModelWatcher")
    Notification = apps.get_model("watchers", "Notification")
    watcher = ModelWatcher.objects.get(pk=watcher_id)
    if watcher.is_active or notification_type in "object_removed":
        notifications = [
            Notification(
                subscription=subscription,
                notification_type=notification_type,
                status="new",
                ref_value=watcher.ref_value,
            )
            for subscription in watcher.subscriptions.all()
        ]
        Notification.objects.bulk_create(notifications)
    return {}


@extended_shared_task
def update_query_watchers_task():
    SearchQueryWatcher = apps.get_model("watchers", "SearchQueryWatcher")
    SearchQueryWatcher.objects.reload()
    return {}


@extended_shared_task
def query_watcher_updated_task(watcher_id, notification_type, prev_value):
    SearchQueryWatcher = apps.get_model("watchers", "SearchQueryWatcher")
    Notification = apps.get_model("watchers", "Notification")
    watcher = SearchQueryWatcher.objects.get(pk=watcher_id, is_active=True)
    notifications = [
        Notification(
            subscription=subscription,
            notification_type=notification_type,
            status="new",
            ref_value=watcher.ref_value,
        )
        for subscription in watcher.subscriptions.all()
    ]
    Notification.objects.bulk_create(notifications)
    return {}


@extended_shared_task
def send_report_from_subscriptions():
    User = get_user_model()
    date_till = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=pytz.utc)
    date_from = date_till - timedelta(days=1)
    for user in User.objects.filter(state="active"):
        user.send_subscriptions_report(date_from, date_till)
    return {}
