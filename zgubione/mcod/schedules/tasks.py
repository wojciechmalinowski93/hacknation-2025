from django.apps import apps

from mcod.core.tasks import extended_shared_task
from mcod.schedules.models import Schedule


@extended_shared_task
def send_admin_notification_task(msg, notification_type):
    obj = Schedule.get_current_plan()
    count = obj.send_admin_notification(msg, notification_type) if obj else []
    return {"recipients_count": count}


@extended_shared_task
def send_schedule_notifications_task():
    obj = Schedule.get_current_plan()
    if obj:
        obj.send_schedule_notifications()
    return {}


@extended_shared_task
def update_notifications_task(user_id, data):
    user_model = apps.get_model("users", "User")
    user = user_model.objects.filter(id=user_id).first()
    if user:
        user.notifications.filter(unread=True).update(**data)
    return {}
