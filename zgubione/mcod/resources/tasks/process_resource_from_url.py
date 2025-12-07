import json
import logging
from io import BytesIO
from typing import Any, Dict, Optional, Union

from celery.signals import task_failure, task_postrun, task_prerun
from django.apps import apps
from django.db.models import QuerySet
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task
from mcod.resources.tasks.common import (
    prepare_url_task_result_for_resource,
    save_task_result_for_resource_after_task_failure,
)
from mcod.unleash import is_enabled

logger = logging.getLogger("mcod")


@extended_shared_task(
    ignore_result=False,
    atomic=True,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.process_resource_from_url_task",
)
def process_resource_from_url_task(
    resource_id: int,
    /,
    forced_file_changed: bool = False,
) -> Union[str, dict]:
    """
    Downloads and processes a file for a given resource ID.

    Note:
    - If the resource is imported from CKAN, it skips processing
        and returns an empty dictionary.
    """
    set_tag("resource_id", str(resource_id))
    logger.info("Started process_resource_from_url_task task.")

    from mcod.resources.models import (
        RESOURCE_TYPE_API,
        RESOURCE_TYPE_FILE,
        RESOURCE_TYPE_WEBSITE,
        ResourceType,
    )

    Resource = apps.get_model("resources", "Resource")
    ResourceFile = apps.get_model("resources", "ResourceFile")

    resource = Resource.raw.get(id=resource_id)

    if resource.is_imported_from_ckan:
        logger.debug(f"External resource imported from {resource.dataset.source} cannot be processed!")
        return {}

    logger.debug(f"Downloading file for resource: {resource.id}")

    resource_type: ResourceType
    options: Dict[str, Any]
    resource_type, options = resource.download_file()

    res_format: Optional[str] = options["format"]  # "format" is always present in options dict

    # check only forced_api_type because forced_file_type was checked in .download_file()
    if resource_type == RESOURCE_TYPE_WEBSITE and resource.forced_api_type:
        logger.debug("Resource of type 'website' forced into type 'api'!")
        resource_type = RESOURCE_TYPE_API

    res_qs: QuerySet = Resource.raw.filter(id=resource_id)
    if resource_type == RESOURCE_TYPE_FILE:
        res_file, created = ResourceFile.objects.get_or_create(
            resource_id=resource_id,
            is_main=True,
        )
        res_filename: Optional[str] = options["filename"]  # "filename" always present in options dict for resource type = "file"
        res_content: BytesIO = options["content"]
        file_path: str = res_file.save_file(res_content, res_filename)
        ResourceFile.objects.filter(pk=res_file.pk).update(file=file_path)
        res_qs.update(format=res_format)

    else:  # API or WWW
        ResourceFile.objects.filter(resource_id=resource_id).delete()
        if forced_file_changed:
            resource.dataset.archive_files()

        res_qs.update(
            type=resource_type,
            format=res_format,
        )

    resource.refresh_from_db()
    result: Dict[str, Any] = prepare_url_task_result_for_resource(resource)
    return json.dumps(result)


@task_prerun.connect(sender=process_resource_from_url_task)
def process_resource_from_url_task_prerun_handler(sender, task_id, task, signal, **kwargs):
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


@task_postrun.connect(sender=process_resource_from_url_task)
def process_resource_from_url_task_postrun_handler(sender, task_id, task, signal, **kwargs):
    resource_id = int(kwargs["args"][0])
    try:
        Resource = apps.get_model("resources", "Resource")
        TaskResult = apps.get_model("resources", "TaskResult")

        task_result = TaskResult.objects.get_task(task_id)
        Resource.raw.filter(pk=resource_id).update(link_tasks_last_status=task_result.status)
        if not is_enabled("S67_less_updates_es_end_rdf_in_resource_processing.be"):
            resource = Resource.raw.get(pk=resource_id)
            resource.update_es_and_rdf_db()
    except Exception as exc:
        logger.exception(f"Exception occurred during process_resource_from_url_task_postrun_handler: {exc}")


@task_failure.connect(sender=process_resource_from_url_task)
def process_resource_from_url_task_failure_handler(sender, task_id, exception, args, traceback, einfo, signal, **kwargs):
    """Role of this handler is to add the exception details to corresponding task result object."""
    resource_id = int(args[0])
    save_task_result_for_resource_after_task_failure(task_id, resource_id, exception)
