import datetime
import json
from typing import TYPE_CHECKING, Any, Dict, Union

from django.apps import apps
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils.timezone import now

if TYPE_CHECKING:
    from mcod.resources.models import Resource
    from mcod.resources.score_computation import OptionalOpennessScoreValue


def prepare_url_task_result_for_resource(resource: "Resource") -> Dict[str, Any]:
    result = {
        "uuid": str(resource.uuid),
        "link": resource.link,
        "format": resource.format,
        "type": resource.type,
    }

    from mcod.resources.models import RESOURCE_TYPE_FILE

    if resource.type == RESOURCE_TYPE_FILE and resource.main_file:
        result["path"] = resource.main_file.path
        result["url"] = resource.file_url

    return result


def save_task_result_for_resource_after_task_failure(
    task_id: str,
    resource_id: Union[int, str],
    exception: Exception,
) -> None:
    """
    Saves information about an exception that occurred during a Celery task execution
    to a TaskResult object associated with the given resource.

    Args:
        task_id (str): The ID of the failed Celery task.
        resource_id (Union[int, str]): The ID of the resource associated with the task.
        exception (Exception): The exception that was raised during task execution.

    The saved result includes exception details, resource metadata, and task-related information.

    Note:
        This function is intended for task failures handlers. It provides a way
        to update the TaskResult object associated with the given resource using
        custom result data. Direct updates within a try-except block in a Celery
        task may not work as expected if `atomic=True` is used, since raising
        an exception would prevent the changes from being committed.

        >>> @extended_shared_task(atomic=True)
        >>> def example_task(task_id: int): ...


        >>> @task_failure.connect(sender=example_task)
        >>> def save_task_result(
        >>>     sender, task_id, exception, args, traceback, einfo, signal, **kwargs
        >>> ):
        >>>     resource_id = int(args[0])
        >>>     save_task_result_for_resource_after_task_failure(task_id, resource_id, exception)

        TaskResult will be updated regardless of exceptions in example_task,
        even if the atomic flag causes a transaction rollback.
    """
    Resource = apps.get_model("resources", "Resource")
    TaskResult = apps.get_model("resources", "TaskResult")

    resource = Resource.objects.get(pk=resource_id)
    result = {
        "exc_type": exception.__class__.__name__,
        "exc_message": str(exception),
        "uuid": str(resource.uuid),
        "link": resource.link,
        "format": resource.format,
        "type": resource.type,
    }

    result_task = TaskResult.objects.get_task(task_id)
    result_task.result = json.dumps(result)
    result_task.save()


def update_resource_verification_date(resource_pk: Union[int, str]) -> None:
    Resource = apps.get_model("resources", "Resource")
    current_datetime: datetime.datetime = now()
    Resource.raw.filter(pk=resource_pk).update(verified=Greatest(F("verified"), current_datetime))


def update_resource_openness_score(resource_pk: Union[int, str]) -> None:
    Resource = apps.get_model("resources", "Resource")
    ResourceFile = apps.get_model("resources", "ResourceFile")

    resource: "Resource" = Resource.raw.get(pk=resource_pk)
    resource_score, files_score = resource.get_openness_score()
    files_score: Dict[int, "OptionalOpennessScoreValue"]
    Resource.raw.filter(pk=resource.pk).update(openness_score=resource_score)
    for file_pk, file_openness_score in files_score.items():
        ResourceFile.objects.filter(pk=file_pk).update(openness_score=file_openness_score)
