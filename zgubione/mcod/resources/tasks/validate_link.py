import json
import logging
from datetime import datetime

from celery.signals import task_prerun
from django.apps import apps
from django.utils import timezone
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task

logger = logging.getLogger("mcod")


@extended_shared_task(
    ignore_result=False,
    bind=True,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.validate_link",
)
def validate_link(self, resource_id: int, /):
    set_tag("resource_id", str(resource_id))
    Resource = apps.get_model("resources", "Resource")
    resource = Resource.objects.get(id=resource_id)
    logger.debug(f"Validating link of resource with id {resource_id}")
    task_id = self.request.id
    TaskResult = apps.get_model("resources", "TaskResult")
    task_result = TaskResult.objects.get_task(task_id)
    try:
        resource.check_link_status()
    except Exception as exc:
        result = {
            "exc_type": exc.__class__.__name__,
            "exc_message": str(exc),
            "uuid": str(resource.uuid),
            "link": resource.link,
            "format": resource.format,
            "type": resource.type,
        }
        task_result.result = json.dumps(result)
        task_result.status = "FAILURE"
        task_result.content_type = "application/json"
        task_result.content_encoding = "utf-8"
        task_result.meta = '{"children": []}'
        self.ignore_result = True  # to prevent overwriting task result when task raise exception
        raise
    else:
        task_result.status = "SUCCESS"
    finally:
        check_time: datetime = timezone.now()
        task_result.date_done = check_time
        task_result.save()
        Resource.raw.filter(pk=resource_id).update(
            link_tasks_last_status=task_result.status,
            verified=check_time,
        )
    return {
        "uuid": str(resource.uuid),
        "link": resource.link,
        "format": resource.format,
        "type": resource.type,
    }


@task_prerun.connect(sender=validate_link)
def validate_link_task_prerun_handler(sender, task_id, task, signal, **kwargs):
    """
    Role of this handler is to add PENDING task to list of resource's link tasks.

    Note:
        - cannot be moved to the beginning of the sender task because of using atomic=True
    """
    try:
        resource_id = int(kwargs["args"][0])

        Resource = apps.get_model("resources", "Resource")
        TaskResult = apps.get_model("resources", "TaskResult")

        resource = Resource.objects.get(pk=resource_id)
        result_task = TaskResult.objects.get_task(task_id)
        result_task.save()  # need to call .save() because it is not in db yet
        resource.link_tasks.add(result_task)
        Resource.raw.filter(pk=resource_id).update(link_tasks_last_status=result_task.status)
    except Exception as exc:
        logger.exception(f"Exception occurred during link task prerun handler: {exc}")
