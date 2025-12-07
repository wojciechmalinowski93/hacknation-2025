import json
import logging
import uuid
from typing import Any, Dict

from celery.result import EagerResult
from celery.states import SUCCESS
from django.apps import apps
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task
from mcod.resources.tasks.common import (
    prepare_url_task_result_for_resource,
    update_resource_openness_score,
    update_resource_verification_date,
)
from mcod.resources.tasks.process_resource_file import process_resource_res_file_task
from mcod.unleash import is_enabled

logger = logging.getLogger("mcod")


@extended_shared_task(
    ignore_result=True,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.entrypoint_process_resource_file_validation_task",
)
def entrypoint_process_resource_file_validation_task(
    resource_file_pk: int,
    update_verification_date: bool = True,
    update_file_archive: bool = False,
    update_link: bool = True,
):
    ResourceFile = apps.get_model("resources", "ResourceFile")
    Resource = apps.get_model("resources", "Resource")

    resource_file = ResourceFile.objects.get(pk=resource_file_pk)
    resource_id = resource_file.resource_id
    set_tag("resource_id", str(resource_id))

    try:
        # 1. Run file validation task
        eager_result_res_file: EagerResult = process_resource_res_file_task.s(
            resource_file_pk,
            update_file_archive=update_file_archive,
            update_link=update_link,
        ).apply()
        if eager_result_res_file.status != SUCCESS:
            logger.error(f"Failed to process resource file: pk = {resource_file_pk}")
            return

        # 2. Run file data validation task
        resource = Resource.objects.get(pk=resource_id)
        if resource:
            resource.revalidate_tabular_data(apply_on_commit=False)

        if update_link:
            # 3. Create url validation task with SUCCESS status for resource
            TaskResult = apps.get_model("resources", "TaskResult")
            Resource = apps.get_model("resources", "Resource")

            # create task result object
            resource = Resource.raw.get(pk=resource_id)
            result: Dict[str, Any] = prepare_url_task_result_for_resource(resource)
            url_task_result = TaskResult.objects.create(
                task_id=str(uuid.uuid4()),
                status=SUCCESS,
                result=json.dumps(result),
            )
            # add created task to resource's link tasks
            resource.link_tasks.add(url_task_result)

            # update resource with url task status
            Resource.raw.filter(pk=resource_id).update(link_tasks_last_status=url_task_result.status)

        if is_enabled("S67_less_updates_es_end_rdf_in_resource_processing.be"):
            # 4. Update es and rdf
            resource.update_es_and_rdf_db()

    except Exception as e:
        logger.error(f"Exception occurred during process_resource_file_validation_task: {e}")
        raise

    finally:
        update_resource_openness_score(resource_id)
        if update_verification_date:
            update_resource_verification_date(resource_id)
