import json
import logging
from typing import Union

from celery.signals import task_failure, task_postrun, task_prerun
from django.apps import apps
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task
from mcod.resources.archives import PasswordProtectedArchiveError, UnsupportedArchiveError
from mcod.resources.file_validation import UnknownFileFormatError, analyze_file
from mcod.resources.indexed_data import FileEncodingValidationError
from mcod.resources.tasks.common import save_task_result_for_resource_after_task_failure
from mcod.unleash import is_enabled

logger = logging.getLogger("mcod")


@extended_shared_task(
    ignore_result=False,
    atomic=True,
    commit_on_errors=(
        FileEncodingValidationError,
        UnsupportedArchiveError,
        UnknownFileFormatError,
        PasswordProtectedArchiveError,
    ),
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.process_resource_res_file_task",
)
def process_resource_res_file_task(
    resource_file_id: Union[int, str],
    update_link: bool = True,
    update_file_archive: bool = False,
):
    ResourceFile = apps.get_model("resources", "ResourceFile")
    Resource = apps.get_model("resources", "Resource")

    resource_file = ResourceFile.objects.get(pk=resource_file_id)
    res_file_queryset = ResourceFile.objects.filter(pk=resource_file_id)
    resource_id = resource_file.resource_id
    set_tag("resource_id", str(resource_id))
    (
        format_,
        file_info,
        file_encoding,
        p,
        file_mimetype,
        analyze_exc,
        extracted_format,
        extracted_mimetype,
        extracted_encoding,
    ) = analyze_file(resource_file.file.file.name)
    if not resource_file.extension and format_:
        res_file_queryset.update(file=resource_file.save_file(resource_file.file, f"{resource_file.file_basename}.{format_}"))
    res_file_queryset.update(
        format=format_,
        compressed_file_format=extracted_format,
        compressed_file_mime_type=extracted_mimetype,
        compressed_file_encoding=extracted_encoding,
        mimetype=file_mimetype,
        info=file_info,
        encoding=file_encoding,
    )

    resource = Resource.raw.get(pk=resource_id)
    update_data = {
        "format": format_,
        "type": "file",
    }
    if update_link:
        update_data["link"] = resource.file_url
    Resource.raw.filter(pk=resource_id).update(**update_data)

    if analyze_exc:
        raise analyze_exc

    resource_file.refresh_from_db()
    resource.refresh_from_db()

    resource_file.check_support()

    if resource_file.format == "csv" and resource_file.encoding is None:
        raise FileEncodingValidationError(
            [
                {
                    "code": "unknown-encoding",
                    "message": "Nie udało się wykryć kodowania pliku.",
                }
            ]
        )

    if update_file_archive:
        resource.dataset.archive_files()

    return json.dumps(
        {
            "uuid": str(resource.uuid),
            "link": resource.link,
            "format": resource_file.format,
            "type": resource.type,
            "path": resource_file.file.path,
            "url": resource.file_url,
        }
    )


@task_prerun.connect(sender=process_resource_res_file_task)
def process_resource_res_file_task_prerun_handler(sender, task_id, task, signal, **kwargs):
    """
    Role of this handler is to add PENDING task to list of resource's file tasks.

    Note:
        - cannot be moved to the beginning of the sender task because of using atomic=True
    """
    try:
        Resource = apps.get_model("resources", "Resource")
        ResourceFile = apps.get_model("resources", "ResourceFile")
        TaskResult = apps.get_model("resources", "TaskResult")

        resource_file_id = int(kwargs["args"][0])
        resource_id = ResourceFile.objects.get(pk=resource_file_id).resource_id
        set_tag("resource_id", str(resource_id))
        resource = Resource.objects.get(pk=resource_id)
        result_task = TaskResult.objects.get_task(task_id)
        result_task.save()
        resource.file_tasks.add(result_task)
        Resource.raw.filter(pk=resource_id).update(file_tasks_last_status=result_task.status)
    except Exception as exc:
        logger.exception(f"Exception occurred during file task prerun handler: {exc}")


@task_postrun.connect(sender=process_resource_res_file_task)
def process_resource_res_file_task_postrun_handler(sender, task_id, task, signal, **kwargs):
    resource_file_id = int(kwargs["args"][0])
    Resource = apps.get_model("resources", "Resource")
    ResourceFile = apps.get_model("resources", "ResourceFile")
    TaskResult = apps.get_model("resources", "TaskResult")

    resource_id = ResourceFile.objects.get(pk=resource_file_id).resource_id
    set_tag("resource_id", str(resource_id))
    try:
        task_result = TaskResult.objects.get_task(task_id)
        Resource.raw.filter(pk=resource_id).update(file_tasks_last_status=task_result.status)
        if not is_enabled("S67_less_updates_es_end_rdf_in_resource_processing.be"):
            resource = Resource.raw.get(pk=resource_id)
            resource.update_es_and_rdf_db()
    except Exception as exc:
        logger.exception(f"Exception occurred during process_resource_res_file_task_postrun_handler: {exc}")


@task_failure.connect(sender=process_resource_res_file_task)
def process_resource_res_file_task_failure_handler(sender, task_id, exception, args, traceback, einfo, signal, **kwargs):
    resource_file_id = int(args[0])
    ResourceFile = apps.get_model("resources", "ResourceFile")
    resource_id = ResourceFile.objects.get(pk=resource_file_id).resource_id
    save_task_result_for_resource_after_task_failure(task_id, resource_id, exception)
