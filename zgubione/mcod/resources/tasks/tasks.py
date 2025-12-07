import logging
from typing import List, Optional, Set, Tuple, Union

import pytz
import requests
from celery.signals import task_postrun
from constance import config
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.utils.timezone import now
from django_elasticsearch_dsl import Index
from elasticsearch.exceptions import (
    ConnectionError as ElasticsearchConnectionError,
    ElasticsearchException,
)
from sentry_sdk import set_tag
from urllib3.exceptions import NewConnectionError

from mcod.core.tasks import FIVE_MINUTES, extended_shared_task
from mcod.lib.db_utils import IndexConsistency, get_db_and_es_inconsistencies
from mcod.lib.file_format_from_response import get_resource_format_from_response
from mcod.resources.archives import ArchiveReader
from mcod.resources.file_validation import analyze_file
from mcod.resources.link_validation import check_link_scheme
from mcod.resources.tasks.entrypoint_res import entrypoint_process_resource_validation_task

logger = logging.getLogger("mcod")


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.send_resource_comment",
)
def send_resource_comment(resource_id, comment):
    set_tag("resource_id", str(resource_id))
    model = apps.get_model("resources", "Resource")
    resource = model.objects.get(pk=resource_id)
    resource.send_resource_comment_mail(comment)
    return {"resource": resource_id}


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.update_resource_has_table_has_map_task",
)
def update_resource_has_table_has_map_task(resource_id):
    set_tag("resource_id", str(resource_id))
    resource_model = apps.get_model("resources", "Resource")
    obj = resource_model.raw.filter(id=resource_id).first()
    result = {"resource_id": resource_id}
    if obj:
        data = {}
        has_table = bool(obj.tabular_data)
        has_map = bool(obj.geo_data)
        if has_table != obj.has_table:
            data["has_table"] = has_table
        if has_map != obj.has_map:
            data["has_map"] = has_map
        if data:
            resource_model.raw.filter(id=resource_id).update(**data)
            result.update(data)
    return result


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.update_resource_validation_results_task",
)
def update_resource_validation_results_task(resource_id):
    set_tag("resource_id", str(resource_id))
    resource_model = apps.get_model("resources", "Resource")
    obj = resource_model.raw.filter(id=resource_id).first()
    result = {"resource_id": resource_id}
    if obj:
        data = {}
        data_task = obj.data_tasks.last()
        file_task = obj.file_tasks.last()
        link_task = obj.link_tasks.last()
        if data_task:
            data["data_tasks_last_status"] = data_task.status
        if file_task:
            data["file_tasks_last_status"] = file_task.status
        if link_task:
            data["link_tasks_last_status"] = link_task.status
        if data:
            resource_model.raw.filter(id=resource_id).update(**data)
            result.update(data)
    return result


@extended_shared_task(
    ignore_result=False,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.check_link_protocol",
)
def check_link_protocol(resource_id, link, title, organization_title, resource_type):
    set_tag("resource_id", str(resource_id))
    logger.debug(f"Checking link {link} of resource with id {resource_id}")
    returns_https, change_required = check_link_scheme(link)
    https_status = "NIE"
    if returns_https:
        https_status = "TAK"
    elif not returns_https and change_required:
        https_status = "Wymagana poprawa"
    return {
        "Https": https_status,
        "Id": resource_id,
        "Nazwa": title,
        "Typ": resource_type,
        "Instytucja": organization_title,
    }


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.process_resource_data_indexing_task",
)
def process_resource_data_indexing_task(resource_id):
    set_tag("resource_id", str(resource_id))
    resource_model = apps.get_model("resources", "Resource")
    obj = resource_model.objects.with_tabular_data(pks=[resource_id]).first()
    if obj:
        success, failed = obj.data.index(force=True)
        return {"resource_id": resource_id, "indexed": success, "failed": failed}
    return {}


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.update_data_date",
)
def update_data_date(resource_id):
    """See also mcod.resources.models.handle_resource_post_save()"""
    set_tag("resource_id", str(resource_id))
    Resource = apps.get_model("resources", "Resource")
    res_q = Resource.objects.filter(pk=resource_id)
    res = res_q.first()
    if res.is_auto_data_date and res.is_auto_data_date_allowed:
        warsaw_tz = pytz.timezone(settings.TIME_ZONE)
        current_now = now().astimezone(warsaw_tz)
        current_dt = current_now.date()
        res_q.update(data_date=current_dt)
        logger.debug(f"Updated data date for resource with id {resource_id} with date {current_dt}")
        res.update_dataset_verified(verified=current_now)
        logger.debug(f"Updated dataset verified for {res.type} resource with id {resource_id} with date {current_now}")
        if res.type in ["api", "website"]:
            res.update_es_and_rdf_db()
        elif res.is_linked:
            entrypoint_process_resource_validation_task.s(res.id, update_file_archive=True).apply_async()
        return {"current_date": current_dt}
    return {"current_date": None}


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.update_last_day_data_date",
)
def update_last_day_data_date(resource_id):
    update_data_date(resource_id)


@task_postrun.connect(sender=update_last_day_data_date)
def reschedule_last_day_of_month_dd_update(sender, task_id, task, signal, **kwargs):
    resource_id = int(kwargs["args"][0])
    Resource = apps.get_model("resources", "Resource")
    resource = Resource.objects.get(pk=resource_id)
    result = kwargs["result"]
    current_date = result.get("current_date")
    if current_date:
        new_schedule_date = current_date + relativedelta(months=1)
        new_schedule_date = resource.correct_last_moth_day(new_schedule_date)
        resource.schedule_crontab_data_date_update(new_schedule_date)


@extended_shared_task(
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.update_resource_with_archive_format",
)
def update_resource_with_archive_format(res_file_id):
    # Called only from command update_resources_format - consider removal
    ResourceFile = apps.get_model("resources", "ResourceFile")
    Resource = apps.get_model("resources", "Resource")
    rf = ResourceFile.objects.get(pk=res_file_id)
    results = {
        "resource_id": rf.resource_id,
        "resource_file_id": res_file_id,
    }
    set_tag("resource_id", str(rf.resource_id))
    with ArchiveReader(rf.file.file.name) as archive:
        if len(archive) > 1:
            logger.debug(f"ResourceFile[{res_file_id}] has more than 1 file compressed, skipping.")
            return results
        logger.debug(f"Updating file details of ResourceFile[{res_file_id}] for Resource with id {rf.resource_id}")
        (
            format,
            file_info,
            file_encoding,
            p,
            file_mimetype,
            analyze_exc,
            extracted_format,
            extracted_mimetype,
            extracted_encoding,
        ) = analyze_file(rf.file.file.name)
        ResourceFile.objects.filter(pk=res_file_id).update(
            format=format,
            mimetype=file_mimetype,
            encoding=file_encoding,
            compressed_file_format=extracted_format,
            compressed_file_mime_type=extracted_mimetype,
            compressed_file_encoding=extracted_encoding,
            info=file_info,
        )
        res = Resource.objects.filter(pk=rf.resource_id)
        obj = res.first()
        old_format = obj.format
        res.update(format=format)
        obj.update_es_and_rdf_db()
        results["old_format"] = old_format
        results["new_format"] = format
    return results


def delete_index(index_name: str) -> bool:
    index = Index(index_name)
    if index.exists():
        result = index.delete()
        if result.get("acknowledged") is True:
            return True
    return False


@extended_shared_task(
    max_retries=5,
    atomic=False,
    retry_countdown=60,
    retry_on_errors=(ElasticsearchException,),
    bind=True,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.delete_es_resource_tabular_data_index",
)
def delete_es_resource_tabular_data_index(self, resource_ids: Union[int, List[int]]):
    """
    Task which removes tabular data index for resource when resource is permanently deleted.
    F.e. for resource with id=123 removed index will be `resource-123`.
    """
    logger.info("Started delete_es_resource_tabular_data_index task.")
    es_index_deleted: bool = False

    if isinstance(resource_ids, int):
        resource_ids: List[int] = [resource_ids]

    for resource_id in resource_ids:
        index_name = f"resource-{resource_id}"
        result = delete_index(index_name)
        if result:
            es_index_deleted = True
            logger.info(f"Tabular data index {index_name} deleted.")
    if not es_index_deleted:
        logger.info("No tabular data index deleted.")
    logger.info("Finished delete_es_resource_tabular_data_index task.")


def _get_resources_ids_for_organization(organization_id: int) -> List[int]:
    Resource = apps.get_model("resources", "resource")

    organization_resources_ids: List[int] = Resource.raw.filter(dataset__organization_id=organization_id).values_list(
        "id", flat=True
    )
    return organization_resources_ids


@extended_shared_task(
    max_retries=3,
    atomic=False,
    retry_countdown=60,
    retry_on_errors=(ElasticsearchException,),
    bind=True,
    name="mcod.resources.tasks.delete_es_resource_tabular_data_indexes_for_organization",
)
def delete_es_resource_tabular_data_indexes_for_organization(self, organization_id: int):
    """
    Task which removes tabular data indexes for resources belonging to the organization with id `organization_id`.
    Tabular data indexes are deleted for all not permanently deleted resources.
    """

    Resource = apps.get_model("resources", "Resource")
    logger.info(f"Started deleting tabular data indexes for organization id={organization_id}")
    es_index_deleted: bool = False

    resources_ids: List[int] = _get_resources_ids_for_organization(organization_id)

    for resource_id in resources_ids:
        index_name = f"resource-{resource_id}"
        result = delete_index(index_name)
        if result:
            logger.info(f"Tabular data index for resource id={resource_id} deleted.")
            es_index_deleted = True
            resource: Optional[Resource] = Resource.raw.filter(pk=resource_id).first()
            if resource:
                resource.has_table = False
                resource.save()
    if not es_index_deleted:
        logger.info(f"No tabular data index deleted for organization id={organization_id}.")
    logger.info(f"Finished deleting tabular data indexes for organization id={organization_id}")


@extended_shared_task(
    max_retries=5,
    retry_on_errors=(NewConnectionError, ElasticsearchConnectionError),
    retry_countdown=FIVE_MINUTES,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.compare_postgres_and_elasticsearch_consistency_task",
)
def compare_postgres_and_elasticsearch_consistency_task(
    models_to_check: Tuple[str],
) -> None:
    """
    Compare the existence consistency between Postgres and ElasticSearch for
    given models. Send email with consistency check result.

    Args:
        models_to_check (Tuple[str]): A tuple of model identifiers to check for consistency.
            Each element should follow the pattern "<django_application_label>.<django_model_name>".
            Example: ("resources.Resource", "datasets.Dataset")
    """
    if not models_to_check:
        logger.info("No models to check consistency for.")
        return

    logger.info(f"Starting compare consistency between Postgres and ElasticSearch for: {models_to_check}")

    error_msg = ""  # errors details which will be sent as email message
    for model in models_to_check:
        app_label, model_name = model.split(".")
        try:
            db_and_es_inconsistencies: List[IndexConsistency] = get_db_and_es_inconsistencies(app_label, model_name)
        except Exception as e:
            logger.error(f"Could not check consistency for {model}: {e}")
            # Add info about failed consistency check to email error message.
            error_msg += f"Could not check consistency for {model}. Error details: {e}"
            continue

        for inconsistency in db_and_es_inconsistencies:
            only_db_model_ids: Set[int] = inconsistency.only_db_ids
            only_es_model_ids: Set[int] = inconsistency.only_es_ids

            if only_db_model_ids:
                error_msg += (
                    f"{len(only_db_model_ids)} {model_name} objects present in "
                    f"PostgreSQL but not in ElasticSearch index"
                    f" {inconsistency.index_name}.\n"
                )
                error_msg += f"{model_name} ids: {only_db_model_ids}\n\n"

            if only_es_model_ids:
                error_msg += (
                    f"{len(only_es_model_ids)} documents for {model_name} present in "
                    f"ElasticSearch index {inconsistency.index_name} but not in PostgreSQL.\n"
                )
                error_msg += f"{model_name} ids: {only_es_model_ids}\n\n"

    if error_msg:
        logger.info("Database and ElasticSearch are inconsistent or an exception occurred.")
    else:
        logger.info("Database and ElasticSearch are consistent.")

    # Send email
    email_message = error_msg or "Database and ElasticSearch are consistent."
    recipients: List[str] = settings.DB_ES_CONSISTENCY_EMAIL_RECIPIENTS.split(",")

    logger.info(f"Sending email to {recipients}.")
    send_mail(
        subject="Postgres and ElasticSearch consistency check - Otwarte Dane.",
        message=email_message,
        from_email=config.NO_REPLY_EMAIL,
        recipient_list=recipients,
    )


@extended_shared_task(
    ignore_result=False,
    time_limit=360,
    # TODO(OTD-1446): Tasks' names aren't necessarily the same as import paths - check with Celery logs
    name="mcod.resources.tasks.get_ckan_resource_format_from_url_task",
)
def get_ckan_resource_format_from_url_task(resource_pk: int) -> Tuple[bool, int, str, Optional[str], Optional[str]]:
    """Returns success, pk, url, resource_format (ie. file extension), error_msg (if an error occurred)"""
    set_tag("resource_id", str(resource_pk))
    Resource = apps.get_model("resources", "Resource")
    resource = Resource.objects.filter(pk=resource_pk).only("link").first()
    url: str = resource.link

    success: bool = False
    if not resource.is_imported_from_ckan:
        return success, resource_pk, url, None, f"Not a CKAN resource: {resource_pk}"

    try:
        response = requests.get(
            url,
            stream=True,
            allow_redirects=True,
            verify=False,
            timeout=settings.HTTP_REQUEST_DEFAULT_TIMEOUT,
        )
    except Exception as exc:
        return success, resource_pk, url, None, str(exc)
    else:
        success = True

    return success, resource_pk, url, get_resource_format_from_response(response), None
