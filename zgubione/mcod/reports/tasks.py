import csv
import datetime
import json
import logging
import os
from collections import OrderedDict
from pathlib import Path
from time import time
from typing import Any, Dict, List

from celery import chord
from celery.signals import task_failure, task_prerun, task_success
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Count, F, OuterRef, Q, QuerySet, Subquery
from django.utils.timezone import now
from django.utils.translation import get_language
from django_celery_results.models import TaskResult

from mcod.celeryapp import app
from mcod.core.api.rdf.namespaces import NAMESPACES
from mcod.core.serializers import csv_serializers_registry as csr
from mcod.core.tasks import extended_shared_task
from mcod.core.utils import save_as_csv
from mcod.datasets.models import Dataset
from mcod.harvester.models import DataSource, DataSourceImport
from mcod.harvester.serializers import (
    DataSourceImportsCSVSchema,
    DataSourceLastImportDatasetCSVSchema,
)
from mcod.lib.rdf.store import get_sparql_store
from mcod.organizations.models import Organization
from mcod.reports.broken_links import (
    generate_admin_broken_links_report,
    generate_public_broken_links_reports,
)
from mcod.reports.broken_links.tasks_helpers import BrokenLinksIntermediaryJSON
from mcod.reports.exceptions import NoDataForReportException
from mcod.reports.models import Report, SummaryDailyReport
from mcod.resources.models import Resource
from mcod.resources.tasks import validate_link
from mcod.showcases.serializers import ShowcaseProposalCSVSerializer
from mcod.suggestions.serializers import DatasetSubmissionCSVSerializer
from mcod.users.serializers import UserLocalTimeCSVSerializer

User = get_user_model()
logger = logging.getLogger("mcod")
kronika_logger = logging.getLogger("kronika-sparql-performance")


@extended_shared_task(ignore_result=False)
def generate_harvesters_imports_report(imports_pks: List[int], model_name: str, user_id: int, file_name_postfix: str) -> str:
    if len(imports_pks) == 0:
        raise NoDataForReportException()

    app, _model = model_name.split(".")

    serializer = DataSourceImportsCSVSchema(many=True)
    queryset_result: QuerySet = (
        DataSource.objects.filter(imports__in=imports_pks)
        .prefetch_related("imports")
        .values(
            "pk",
            "name",
            "description",
            "source_type",
            "created",
            "modified",
            "last_activation_date",
            "portal_url",
            "api_url",
            "xml_url",
            "organization__title",
            "frequency_in_days",
            "created_by",
            "modified_by",
            "status",
            "institution_type",
            "imports__pk",
            "imports__start",
            "imports__end",
            "imports__status",
            "imports__error_desc",
            "imports__datasets_rejected_count",
            "imports__datasets_count",
            "imports__datasets_created_count",
            "imports__datasets_updated_count",
            "imports__datasets_deleted_count",
            "imports__resources_count",
            "imports__resources_created_count",
            "imports__resources_updated_count",
            "imports__resources_deleted_count",
        )
    )

    data: OrderedDict[str, Any] = serializer.dump(queryset_result)
    data = sorted(data, key=lambda x: x["Źródło danych - id"])
    user = User.objects.get(pk=user_id)
    file_name = f"{_model.lower()}s_{file_name_postfix}.csv"

    reports_path = os.path.join(settings.REPORTS_MEDIA_ROOT, app)
    os.makedirs(reports_path, exist_ok=True)
    file_path = os.path.join(reports_path, file_name)
    file_url_path = f"{settings.REPORTS_MEDIA}/{app}/{file_name}"

    with open(file_path, "w") as f:
        save_as_csv(f, serializer.get_csv_headers(), data)

    return json.dumps(
        {
            "model": model_name,
            "csv_file": file_url_path,
            "date": now().strftime("%Y.%m.%d %H:%M"),
            "user_email": user.email,
        }
    )


@extended_shared_task(ignore_result=False)
def generate_harvesters_last_imports_report(
    datasource_pks: List[int], model_name: str, user_id: int, file_name_postfix: str
) -> str:
    if len(datasource_pks) == 0:
        raise NoDataForReportException()
    app, _model = model_name.split(".")

    serializer = DataSourceLastImportDatasetCSVSchema(many=True)

    latest_imp_subquery: QuerySet = DataSourceImport.objects.filter(datasource=OuterRef("pk")).order_by("-pk").values("pk")[:1]
    queryset_result: QuerySet = (
        DataSource.objects.filter(
            id__in=datasource_pks, datasource_datasets__is_removed=False, datasource_datasets__is_permanently_removed=False
        )
        .annotate(latest_imp_id=Subquery(latest_imp_subquery))
        .filter(imports__id=F("latest_imp_id"))
        .prefetch_related("imports", "datasource_datasets")
        .values(
            "pk",
            "name",
            "description",
            "source_type",
            "created",
            "modified",
            "last_activation_date",
            "portal_url",
            "api_url",
            "xml_url",
            "organization__title",
            "frequency_in_days",
            "created_by",
            "modified_by",
            "status",
            "institution_type",
            "imports__pk",
            "imports__start",
            "imports__end",
            "imports__status",
            "imports__error_desc",
            "datasource_datasets__pk",
            "datasource_datasets__title",
            "datasource_datasets__modified",
            "datasource_datasets__organization__title",
        )
    )

    data: OrderedDict[str, Any] = serializer.dump(queryset_result)
    data = sorted(data, key=lambda x: x["Źródło danych - id"])

    user = User.objects.get(pk=user_id)
    file_name = f"datasourcelastimports_{file_name_postfix}.csv"

    reports_path = os.path.join(settings.REPORTS_MEDIA_ROOT, app)
    os.makedirs(reports_path, exist_ok=True)
    file_path = os.path.join(reports_path, file_name)
    file_url_path = f"{settings.REPORTS_MEDIA}/{app}/{file_name}"

    with open(file_path, "w") as f:
        save_as_csv(f, serializer.get_csv_headers(), data)

    return json.dumps(
        {
            "model": model_name,
            "csv_file": file_url_path,
            "date": now().strftime("%Y.%m.%d %H:%M"),
            "user_email": user.email,
        }
    )


@extended_shared_task(ignore_result=False)
def generate_csv(pks, model_name, user_id, file_name_postfix):
    app, _model = model_name.split(".")
    model = apps.get_model(app, _model)
    serializer_cls = csr.get_serializer(model)
    if _model == "DatasetSubmission":  # TODO: how to register it in csr?
        serializer_cls = DatasetSubmissionCSVSerializer
    elif _model == "ShowcaseProposal":
        serializer_cls = ShowcaseProposalCSVSerializer
    elif _model == "User":
        serializer_cls = UserLocalTimeCSVSerializer

    if not serializer_cls:
        raise Exception("Cound not find serializer for model %s" % model_name)

    serializer = serializer_cls(many=True)
    queryset = model.objects.filter(pk__in=pks)
    data = serializer_cls(many=True).dump(queryset)
    user = User.objects.get(pk=user_id)
    file_name = f"{_model.lower()}s_{file_name_postfix}.csv"
    reports_path = os.path.join(settings.REPORTS_MEDIA_ROOT, app)
    os.makedirs(reports_path, exist_ok=True)

    file_path = os.path.join(reports_path, file_name)
    file_url_path = f"{settings.REPORTS_MEDIA}/{app}/{file_name}"

    with open(file_path, "w") as f:
        save_as_csv(f, serializer.get_csv_headers(), data)

    return json.dumps(
        {
            "model": model_name,
            "csv_file": file_url_path,
            "date": now().strftime("%Y.%m.%d %H:%M"),
            "user_email": user.email,
        }
    )


@extended_shared_task(ignore_result=False)
def create_no_resource_dataset_report():
    logger.debug("Running create_no_resource_dataset_report task.")
    app = "datasets"
    file_name_postfix = now().strftime("%Y%m%d%H%M%S.%s")
    queryset = (
        Dataset.objects.annotate(
            all_resources=Count("resources__pk"),
            unpublished_resources=Count("resources__pk", filter=Q(resources__status="draft")),
        )
        .filter(
            Q(resources__isnull=True) | Q(all_resources=F("unpublished_resources")),
            status="published",
        )
        .distinct()
    )
    serializer_cls = csr.get_serializer(Dataset)
    serializer = serializer_cls(many=True)
    data = serializer.dump(queryset)
    file_name = f"nodata_datasets_{file_name_postfix}.csv"
    reports_path = os.path.join(settings.REPORTS_MEDIA_ROOT, app)
    os.makedirs(reports_path, exist_ok=True)

    file_path = os.path.join(reports_path, file_name)
    file_url_path = f"{settings.REPORTS_MEDIA}/{app}/{file_name}"
    with open(file_path, "w") as f:
        save_as_csv(f, serializer.get_csv_headers(), data)
    return json.dumps({"file": file_url_path, "model": "datasets.Dataset"})


@task_prerun.connect(sender=generate_csv)
@task_prerun.connect(sender=generate_harvesters_imports_report)
@task_prerun.connect(sender=generate_harvesters_last_imports_report)
def append_report_task(sender, task_id, task, signal, **kwargs):
    try:
        pks, model_name, user_id, d = kwargs["args"]
        task_obj = TaskResult.objects.get_task(task_id)
        task_obj.save()
        try:
            ordered_by = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            ordered_by = None
        report = Report(model=model_name, ordered_by=ordered_by, task=task_obj)
        report.save()
    except Exception as e:
        logger.error(f"reports.task: exception on append_report_task:\n{e}")


@extended_shared_task(ignore_result=False)
def create_resources_report_task(data, headers, report_name):
    logger.debug(f"Creating resource {report_name} report.")
    app_name = "resources"
    file_name_postfix = now().strftime("%Y%m%d%H%M%S.%s")
    file_name = f"{report_name}_{file_name_postfix}.csv"
    reports_path = os.path.join(settings.REPORTS_MEDIA_ROOT, app_name)
    os.makedirs(reports_path, exist_ok=True)
    file_path = os.path.join(reports_path, file_name)
    file_url_path = f"{settings.REPORTS_MEDIA}/{app_name}/{file_name}"
    with open(file_path, "w") as f:
        w = csv.DictWriter(f, headers)
        w.writeheader()
        w.writerows(data)
    return json.dumps({"file": file_url_path, "model": "resources.Resource"})


@task_success.connect(sender=create_no_resource_dataset_report)
@task_success.connect(sender=create_resources_report_task)
def generating_monthly_report_success(sender, result, **kwargs):
    try:
        result_dict = json.loads(result)
        logger.info(f"reports.task: report generated: {result_dict.get('file')}")

        result_task = TaskResult.objects.get_task(sender.request.id)
        result_task.result = result
        result_task.status = "SUCCESS"
        result_task.save()
        result_dict["task"] = result_task
        Report.objects.create(**result_dict)
    except Exception as e:
        logger.error(f"reports.task: exception on generating_monthly_report_success:\n{e}")


@task_success.connect(sender=generate_csv)
@task_success.connect(sender=generate_harvesters_imports_report)
@task_success.connect(sender=generate_harvesters_last_imports_report)
def generating_report_success(sender, result, **kwargs):
    try:
        result_dict = json.loads(result)
        logger.info("Started task generating_report_success")
        logger.info(f"reports.task: report generated: {result_dict.get('csv_file')}")

        result_task = TaskResult.objects.get_task(sender.request.id)
        result_task.result = result
        result_task.status = "SUCCESS"
        result_task.save()

        report = Report.objects.get(task=result_task)
        report.file = result_dict.get("csv_file")
        report.save()
    except Exception as e:
        logger.error(f"reports.task: exception on generating_report_success:\n{e}")


def dict_fetch_all(cursor):
    """Return all rows from a cursor as a OrderedDict"""
    columns = [col[0] for col in cursor.description]
    return [OrderedDict(zip(columns, row)) for row in cursor.fetchall()]


def format_report_header(header: str) -> str:
    """
    Formats a header string to be more readable and conform to specific
    style requirements.
    """
    # Replace underscores with spaces and capitalize the string
    formated_header: str = header.capitalize().replace("_", " ")

    # Dictionary of specific phrases to replace
    contents_to_replace: Dict[str, str] = {
        "z wykazu ke": "z wykazu KE",
    }

    # Apply specific replacements for designated phrases
    for key, value in contents_to_replace.items():
        formated_header = formated_header.replace(key, value)
    return formated_header


@app.task(ignore_result=False)
def create_daily_resources_report():
    str_date = datetime.datetime.now().strftime("%Y_%m_%d_%H%M")
    view_name = "mv_resource_dataset_organization_report_d_hv_r_data"
    report_fields = """
            id_zasobu,
            NULL as link_zasobu,
            nazwa,
            opis,
            typ,
            format,
            formaty_po_konwersji,
            data_utworzenia_zasobu,
            data_modyfikacji_zasobu,
            stopien_otwartosci,
            zasob_posiada_dane_wysokiej_wartosci,
            zasob_posiada_dane_wysokiej_wartosci_z_wykazu_ke,
            zasob_posiada_dane_dynamiczne,
            zasob_posiada_dane_badawcze,
            zasob_zawiera_wykaz_chronionych_danych,
            liczba_wyswietlen,
            liczba_pobran,
            id_zbioru_danych,
            zbior_danych_posiada_dane_wysokiej_wartosci,
            zbior_danych_posiada_dane_wysokiej_wartosci_z_wykazu_ke,
            zbior_danych_posiada_dane_dynamiczne,
            zbior_danych_posiada_dane_badawcze,
            NULL as link_zbioru,
            data_utworzenia_zbioru_danych,
            data_modyfikacji_zbioru_danych,
            liczba_obserwujacych,
            id_instytucji,
            NULL as link_instytucji,
            tytul,
            rodzaj,
            data_utworzenia_instytucji,
            liczba_udostepnionych_zbiorow_danych
        """
    with connection.cursor() as cursor:
        cursor.execute(f"""REFRESH MATERIALIZED VIEW {view_name}""")
        cursor.execute(
            f"""
            SELECT {report_fields}
            FROM {view_name}
        """
        )
        results = dict_fetch_all(cursor)

    for r in results:
        if r["id_zasobu"]:
            r["link_zasobu"] = f"{settings.BASE_URL}/{get_language()}/dataset/{r['id_zbioru_danych']}/resource/{r['id_zasobu']}"
        if r["id_zbioru_danych"]:
            r["link_zbioru"] = f"{settings.BASE_URL}/{get_language()}/dataset/{r['id_zbioru_danych']}"
        if r["id_instytucji"]:
            r["link_instytucji"] = f"{settings.BASE_URL}/{get_language()}/institution/{r['id_instytucji']}"

    os.makedirs(Path(settings.REPORTS_MEDIA_ROOT, "daily"), exist_ok=True)
    file_path = Path(settings.REPORTS_MEDIA[1:], "daily", f"Zbiorczy_raport_dzienny_{str_date}.csv")
    save_path = Path(settings.REPORTS_MEDIA_ROOT, "daily", f"Zbiorczy_raport_dzienny_{str_date}.csv")

    with open(save_path, "w") as f:
        results_new_format: List[OrderedDict] = [
            OrderedDict({format_report_header(k): v for k, v in element.items()}) for element in results
        ]
        w = csv.DictWriter(f, results_new_format[0].keys())
        w.writeheader()
        w.writerows(results_new_format)

    SummaryDailyReport.objects.create(
        file=file_path,
        ordered_by_id=1,
    )

    return {}


@extended_shared_task
def check_kronika_connection_performance():
    logger.info("Executing check_kronika_connection_performance task")
    format_ = "json"
    store = get_sparql_store(readonly=True, return_format=format_, external_sparql_endpoint="kronika")
    query = "SELECT ?s ?p ?o WHERE {?s a dcat:distribution}"
    log_msg = f'Sending query "{query}" to kronika sparql api;'
    try:
        start = time()
        response = store.query(query, initNs=NAMESPACES)
        end = time()
        if isinstance(response, tuple):
            log_msg += f"Kronika SPARQL api returned status code {response[0]}. Details: {response[1]};"
        time_delta = end - start
        try:
            result = json.loads(response.serialize(format=format_, encoding="utf-8"))
            res_count = len(result["results"]["bindings"])
        except AttributeError:
            res_count = 0
        log_msg += f"Request execution took {time_delta:.4f} seconds; Query returned {res_count} items;"
        kronika_logger.info(log_msg)
    except Exception as err:
        kronika_logger.error(f"{log_msg} Exception occurred while sending request to kronika api: {err};")


@extended_shared_task(ignore_result=False)
def generate_admin_broken_links_report_task(json_file_id: str):
    """Fetches broken links data from JSON file and generates Admin Broken Links reports."""
    intermediary_json = BrokenLinksIntermediaryJSON(json_file_id)
    base_json_data: List[Dict[str, Any]] = intermediary_json.load()
    report_file_path_url: str = generate_admin_broken_links_report(base_json_data)
    return json.dumps({"file": report_file_path_url, "model": "resources.Resource"})


@task_success.connect(sender=generate_admin_broken_links_report_task)
def admin_broken_links_report_generation_success_handler(sender, result, **kwargs):
    """
    Set task result object on success and creates `Report` object for generated
    Admin Broken Links report - this makes it visible in PA.
    """
    try:
        result_dict = json.loads(result)
        logger.info("Admin Broken Links report generated.")

        result_task = TaskResult.objects.get_task(sender.request.id)
        result_task.result = result
        result_task.status = "SUCCESS"
        result_task.save()
        result_dict["task"] = result_task
        Report.objects.create(**result_dict)
    except Exception as e:
        logger.error(f"reports.task: exception on generating_monthly_report_success:\n{e}")


@extended_shared_task
def generate_public_broken_links_reports_task(json_file_id: str):
    """Fetches broken links data from JSON file and generates Public Broken Links reports."""
    intermediary_json = BrokenLinksIntermediaryJSON(json_file_id)
    base_json_data: List[Dict[str, Any]] = intermediary_json.load()
    generate_public_broken_links_reports(base_json_data)


@extended_shared_task(ignore_result=False)
def generate_broken_links_reports_task():
    """
    Fetches resources with broken links and triggers the report generation process.

    This task serves as the entry point for creating broken links reports. It queries
    the database for all resources with known broken links, exports this data to a
    temporary JSON file, and then initiates a Celery chain to generate the admin
    and public-facing reports based on that file.
    """
    # Create intermediary JSON file containing resources broken links data for reports
    intermediary_json = BrokenLinksIntermediaryJSON()
    intermediary_json.delete_old_json_files()
    intermediary_json.dump()
    file_id: str = intermediary_json.id

    # Define a Celery chain: generate the admin report first, then the public reports
    # The path to the JSON file is passed as an argument to the tasks
    abl_task_sig = generate_admin_broken_links_report_task.si(file_id)
    pbl_task_sig = generate_public_broken_links_reports_task.si(file_id)
    workflow = abl_task_sig | pbl_task_sig

    # Asynchronously execute the report generation workflow
    workflow.apply_async()


@extended_shared_task(ignore_result=False)
def validate_resources_links():
    """
    Triggers the validation of external links for all published resources.

    This task gathers all published resources containing external links and creates
    a separate validation task for each one. These tasks are executed in parallel
    using a Celery chord. After all validation tasks have completed, a callback
    triggers the generation of broken links reports:
    - Admin Broken Links report (visible via PA)
    - Public Broken Links report (visible via OD frontend site)

    This ensures that the reports are always generated,
    even if some of the validation subtasks fail.
    """

    # Fetch all published resources that have external links to be validated.
    qs: QuerySet = Resource.objects.published_with_ext_links_only()

    if settings.BROKEN_LINKS_EXCLUDE_DEVELOPERS:
        qs = qs.exclude(dataset__organization__institution_type=Organization.INSTITUTION_TYPE_DEVELOPER)

    resources_ids: List[int] = list(qs.values_list("pk", flat=True))

    # Prepare a list of individual validation subtasks, one for each resource.
    subtasks = [validate_link.s(res_id) for res_id in resources_ids]

    # Define the callback task to be executed after all validations are finished.
    # The .on_error handler ensures that the report generation task runs even if
    # some of the link validation subtasks fail.
    # https://docs.celeryq.dev/en/v5.3.0/userguide/canvas.html#:~:text=You%20can%20also%20add%20error%20callbacks%20using%20the%20on_error%20method%3A

    callback = generate_broken_links_reports_task.si().on_error(generate_broken_links_reports_task.si())

    # Execute the validation tasks in parallel. The callback will be triggered
    # once all subtasks are complete.
    chord(subtasks, callback).apply_async()


@task_failure.connect(sender=generate_csv)
@task_failure.connect(sender=create_no_resource_dataset_report)
@task_failure.connect(sender=validate_resources_links)
@task_failure.connect(sender=create_resources_report_task)
@task_failure.connect(sender=generate_harvesters_imports_report)
@task_failure.connect(sender=generate_harvesters_last_imports_report)
def generating_report_failure(sender, task_id, exception, args, traceback, einfo, signal, **kwargs):
    logger.debug(f"generating report failed with:\n{exception}")
    try:
        result_task = TaskResult.objects.get_task(task_id)
        result_task.status = "FAILURE"
        result_task.save()
    except Exception as e:
        logger.error(f"reports.task: exception on generating_report_failure:\n{e}")
