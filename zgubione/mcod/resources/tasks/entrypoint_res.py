import logging

from celery.result import EagerResult
from celery.states import SUCCESS
from django.apps import apps
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task
from mcod.resources.tasks.common import (
    update_resource_openness_score,
    update_resource_verification_date,
)
from mcod.resources.tasks.process_resource_file import process_resource_res_file_task
from mcod.resources.tasks.process_resource_from_url import process_resource_from_url_task
from mcod.unleash import is_enabled

logger = logging.getLogger("mcod")


@extended_shared_task(
    ignore_result=True,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.entrypoint_process_resource_validation_task",
)
def entrypoint_process_resource_validation_task(
    resource_pk: int,
    update_verification_date: bool = True,
    update_file_archive: bool = False,
    forced_file_changed: bool = False,
) -> None:
    set_tag("resource_id", str(resource_pk))
    from mcod.resources.models import RESOURCE_TYPE_API, RESOURCE_TYPE_FILE, ResourceType

    Resource = apps.get_model("resources", "Resource")
    ResourceFile = apps.get_model("resources", "ResourceFile")
    try:
        # 1. Run url validation task
        eager_result_res_url: EagerResult = process_resource_from_url_task.s(
            resource_pk,
            forced_file_changed=forced_file_changed,
        ).apply()

        # Do not run other tasks if url task validation status is not SUCCESS or resource is imported from CKAN
        resource = Resource.raw.get(pk=resource_pk)
        if eager_result_res_url.status != SUCCESS:
            logger.error(f"Failed to process resource: pk = {resource_pk}")
            return

        resource_type: ResourceType = resource.type
        if resource_type == RESOURCE_TYPE_FILE or (resource_type == RESOURCE_TYPE_API and resource.forced_file_type):
            # 2. Run file validation task
            main_file_qs = ResourceFile.objects.filter(resource_id=resource_pk, is_main=True)
            if main_file_qs.exists():
                main_file = main_file_qs.first()
                eager_result_res_file: EagerResult = process_resource_res_file_task.s(
                    main_file.pk,
                    update_file_archive=update_file_archive,
                    update_link=False,
                ).apply()
                if eager_result_res_file.status != SUCCESS:
                    logger.error(f"Failed to process resource file: pk = {main_file.pk}")
                    return
            else:
                logger.info(f"Resource {resource_pk} has no main file")

            # 3. Run file data validation task
            resource = Resource.objects.get(pk=resource_pk)
            if resource:
                resource.revalidate_tabular_data(apply_on_commit=False)

        if is_enabled("S67_less_updates_es_end_rdf_in_resource_processing.be"):
            # 4. Update es and rdf
            resource.update_es_and_rdf_db()

    except Exception as e:
        logger.error(f"Exception occurred during process_resource_validation_task: {e}")
        raise

    finally:
        update_resource_openness_score(resource_pk)
        if update_verification_date:
            update_resource_verification_date(resource_pk)
