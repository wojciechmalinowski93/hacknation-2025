import logging
import os
from pathlib import Path

import sentry_sdk
from django.apps import apps
from django.conf import settings

from mcod.core.tasks import extended_shared_task
from mcod.resources.dga_utils import (
    check_all_resource_validations_status,
    clean_up_after_main_dga_resource_creation,
    create_main_dga_file,
    create_main_dga_resource_with_dataset,
    update_or_create_aggr_dga_info_and_delete_old_main_dga,
)
from mcod.resources.exceptions import FailedValidationException, PendingValidationException

logger = logging.getLogger("mcod")


@extended_shared_task(
    max_retries=5,
    atomic=False,
    retry_countdown=20,
    retry_on_errors=(PendingValidationException,),
    bind=True,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.create_main_dga_resource_task",
)
def create_main_dga_resource_task(self) -> None:
    """
    Performs the creation and management of a main DGA Resource, divided into
    several key steps:

    1. Creation of an XLSX file containing information about all DGA resources.
    2. Creation of a Resource and a ResourceFile objects for the main DGA.
       This step also includes a check to ensure that the main DGA Dataset
       exists; if not, it is created at this point.
    3. Verification that all validation stages for the resource have been
       successfully completed. If any validation is pending, the task is
       retried according to the specified number of attempts for this task.
    4. Updating the information in the AggregatedDGAInfo table and removing the
       old Resource.

    Cleanup process:
    If the task encounters an unexpected error or if the resource does not pass
    all validations within the designated number of check attempts, the created
    Resource, ResourceFile and Dataset objects are deleted to maintain
    integrity.
    Cleans task's cache when the task succeeded.

    Raises:
        PendingValidationException: If there are still running Resource
        validation stages.

        FailedValidationException: If any Resource validation stage failed.

    Returns:
        None: Completes the task without returning any value.
    """
    logger.info("Starting main DGA resource creation.")
    Resource = apps.get_model("resources", "Resource")

    try:
        # Step 1: Main DGA file creation
        logger.info("Step 1/4: Creating Main DGA xlsx file.")
        file_path: Path = create_main_dga_file()

        # Step 2: Main DGA Resource creation
        # (also creates ResourceFile and Dataset if needed).
        logger.info("Step 2/4: Creating Main DGA resource with files.")
        new_main_dga_resource_pk: int
        new_main_dga_resource_pk, _ = create_main_dga_resource_with_dataset(file_path=file_path)
        new_main_dga_resource: Resource = Resource.objects.get(pk=new_main_dga_resource_pk)

        # Step 3: Check resource validations
        logger.info("Step 3/4: Checking resource validations.")
        check_all_resource_validations_status(new_main_dga_resource)

        # Step 4: Update Aggregated DGA Info and delete old main DGA Resource
        logger.info("Step 4/4: Updating AggregatedDGAInfo and deleting old Resource.")
        update_or_create_aggr_dga_info_and_delete_old_main_dga(new_main_dga_resource)

        logger.info("Main DGA Resource successfully created.")

        # Clean cache when task succeeded
        clean_up_after_main_dga_resource_creation(exception_occurred=False)

    # Clean created data if resource not validated on last retry or another
    # exception occurred
    except PendingValidationException:
        max_retries: int = self.max_retries
        retry: int = self.request.retries
        if retry == max_retries:
            logger.info("Cleaning after main DGA resource creation task due to " "still pending resource validation(s).")
            clean_up_after_main_dga_resource_creation(exception_occurred=True)
        raise

    except FailedValidationException:
        clean_up_after_main_dga_resource_creation(exception_occurred=True)
        raise

    except Exception as exc:
        logger.error(f"Cleaning after main DGA resource creation task due to " f"unexpected error: {exc}")
        clean_up_after_main_dga_resource_creation(exception_occurred=True)
        raise


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.clean_dga_temp_directory",
)
def clean_dga_temp_directory():
    logger.info("Cleaning DGA temp directory.")
    dga_temp_dir = settings.DGA_RESOURCE_CREATION_STAGING_ROOT
    if os.path.exists(dga_temp_dir):
        for filename in os.listdir(dga_temp_dir):
            file_path = os.path.join(dga_temp_dir, filename)
            try:
                logger.debug(f"Removing {file_path}")
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Removing {file_path} failed. Reason: {e}")
                sentry_sdk.api.capture_exception(e)
