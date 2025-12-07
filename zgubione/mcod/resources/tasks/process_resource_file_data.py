import json
import logging
from copy import deepcopy
from typing import Any, Dict

from celery.signals import task_failure, task_postrun, task_prerun, task_success
from django.apps import apps
from elasticsearch.helpers.errors import BulkIndexError
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task
from mcod.resources.indexed_data import ResourceDataValidationError
from mcod.resources.tasks.common import save_task_result_for_resource_after_task_failure
from mcod.unleash import is_enabled

logger = logging.getLogger("mcod")


@extended_shared_task(
    ignore_result=False,
    atomic=True,
    commit_on_errors=(ResourceDataValidationError, BulkIndexError),
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.process_resource_file_data_task",
)
def process_resource_file_data_task(resource_id: int, /):
    set_tag("resource_id", str(resource_id))
    resource_model = apps.get_model("resources", "Resource")
    resource = resource_model.raw.get(id=resource_id)
    logger.info(f"process_resource_file_data_task: Resource {resource_id}")
    if not resource.data:
        raise Exception("Nieobsługiwany format danych lub błąd w jego rozpoznaniu.")
    tds = resource.tabular_data_schema
    if not tds or tds.get("missingValues") != resource.special_signs_symbols_list:
        tds = resource.data.get_schema(revalidate=True)
    if resource.from_resource and resource.from_resource.tabular_data_schema:
        old_fields = deepcopy(resource.from_resource.tabular_data_schema.get("fields"))
        for f in old_fields:
            if "geo" in f:
                del f["geo"]
        if tds.get("fields") == old_fields:
            tds = resource.from_resource.tabular_data_schema

    resource_model.objects.filter(pk=resource_id).update(tabular_data_schema=tds)
    resource = resource_model.objects.get(pk=resource_id)
    resource.data.validate()

    success, failed = resource.data.index(force=True)
    logger.info(f"process_resource_file_data_task: {success=}, {failed=}")

    return json.dumps(
        {
            "indexed": success,
            "failed": failed,
            "uuid": str(resource.uuid),
            "link": resource.link,
            "format": resource.format,
            "type": resource.type,
            "path": resource.main_file.path,
            "resource_id": resource_id,
            "url": resource.file_url,
        }
    )


@task_prerun.connect(sender=process_resource_file_data_task)
def process_resource_file_data_task_prerun_handler(sender, task_id, task, signal, **kwargs):
    """
    Role of this handler is to add PENDING task to list of resource's data tasks
    if resource is data processable.

    Note:
        - cannot be moved to the beginning of the sender task because of using atomic=True
    """
    try:
        Resource = apps.get_model("resources", "Resource")
        TaskResult = apps.get_model("resources", "TaskResult")

        resource_id = int(kwargs["args"][0])
        resource = Resource.objects.get(pk=resource_id)
        if resource.is_data_processable:
            result_task = TaskResult.objects.get_task(task_id)
            result_task.save()
            resource.data_tasks.add(result_task)
            Resource.raw.filter(pk=resource_id).update(data_tasks_last_status=result_task.status)
    except Exception as exc:
        logger.exception(f"Exception occurred during file data task prerun handler: {exc}")


@task_postrun.connect(sender=process_resource_file_data_task)
def process_resource_file_data_task_postrun_handler(sender, task_id, task, signal, **kwargs):
    resource_id = int(kwargs["args"][0])
    try:
        Resource = apps.get_model("resources", "Resource")
        TaskResult = apps.get_model("resources", "TaskResult")

        task_result = TaskResult.objects.get_task(task_id)
        resource = Resource.raw.get(pk=resource_id)

        res_update_data: Dict[str, Any] = {
            "data_tasks_last_status": task_result.status,
        }

        try:
            return_value_from_task = json.loads(kwargs["retval"]) if isinstance(kwargs["retval"], str) else {}
        except json.JSONDecodeError:
            return_value_from_task = {}
        indexed = return_value_from_task.get("indexed")

        res_update_data["has_map"] = bool(resource.data and resource.data.has_geo_data and indexed)
        res_update_data["has_table"] = bool(resource.has_tabular_format(["shp"]) and indexed)

        Resource.raw.filter(pk=resource_id).update(**res_update_data)  # we don't want signals here - just updates.

        if not is_enabled("S67_less_updates_es_end_rdf_in_resource_processing.be"):
            resource.update_es_and_rdf_db()

    except Exception as exc:
        logger.exception(f"Exception occurred during process_resource_file_data_task_postrun_handler: {exc}")


@task_success.connect(sender=process_resource_file_data_task)
def process_resource_file_data_task_success_handler(sender, result, *args, **kwargs):
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        data = {}
    indexed = data.get("indexed")
    resource_id = data.get("resource_id")
    if indexed and resource_id:
        Resource = apps.get_model("resources", "Resource")
        resource = Resource.raw.filter(id=resource_id).first()
        if resource:
            resource.increase_openness_score()
            resource.dataset.archive_files()


@task_failure.connect(sender=process_resource_file_data_task)
def process_resource_file_data_task_failure_handler(sender, task_id, exception, args, traceback, einfo, signal, **kwargs):
    """Role of this handler is to add the exception details to corresponding task result object."""
    resource_id = int(args[0])
    save_task_result_for_resource_after_task_failure(task_id, resource_id, exception)
