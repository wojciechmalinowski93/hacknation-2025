import csv
import datetime
import glob
import json
import logging
import os
import re
import shutil
import tempfile
from calendar import monthrange
from collections import namedtuple
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Dict, Literal, Optional, Tuple, Union

import magic
import pytz
import unicodecsv
from constance import config
from csvwlib import CSVWConverter
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max, Sum
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.template.defaultfilters import filesizeformat
from django.template.loader import render_to_string
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _, override
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask
from django_celery_results.models import TaskResult as TaskResultOrig
from elasticsearch_dsl.connections import Connections
from mimeparse import parse_mime_type
from model_utils import FieldTracker

from mcod.core import model_validators, signals as core_signals, storages
from mcod.core.api.rdf import signals as rdf_signals
from mcod.core.api.rdf.tasks import update_graph_task
from mcod.core.api.search import signals as search_signals
from mcod.core.api.search.tasks import (
    bulk_delete_documents_task,
    update_related_task,
    update_with_related_task,
)
from mcod.core.choices import SOURCE_TYPE_CHOICES_FOR_ADMIN
from mcod.core.db.managers import TrashManager
from mcod.core.db.models import (
    CustomManagerForeignKey,
    ExtendedModel,
    TrashModelBase,
    update_watcher,
)
from mcod.counters.models import ResourceDownloadCounter, ResourceViewCounter
from mcod.datasets.models import BaseSupplement, Dataset
from mcod.lib.data_rules import painless_body
from mcod.lib.date_utils import date_at_midnight
from mcod.lib.model_sanitization import (
    SanitizedCharField,
    SanitizedTextField,
    SanitizedTranslationField,
)
from mcod.organizations.models import Organization
from mcod.regions.models import Region, RegionManyToManyField
from mcod.resources.archives import ArchiveReader, is_archive_file
from mcod.resources.error_mappings import messages, recommendations
from mcod.resources.file_validation import check_support, get_file_info
from mcod.resources.indexed_data import ShpData, TabularData
from mcod.resources.link_validation import check_link_status, download_file
from mcod.resources.managers import (
    ChartManager,
    ResourceFileManager,
    ResourceManager,
    ResourceRawDBManager,
    ResourceRawManager,
    ResourceTrashManager,
    SupplementManager,
)
from mcod.resources.score_computation import OptionalOpennessScoreValue, get_score
from mcod.resources.signals import (
    cancel_data_date_update,
    revalidate_resource,
    update_chart_resource,
    update_dataset_file_archive,
)
from mcod.resources.tasks import (
    delete_es_resource_tabular_data_index,
    entrypoint_process_resource_file_validation_task,
    entrypoint_process_resource_validation_task,
    process_resource_file_data_task,
)
from mcod.watchers.tasks import update_model_watcher_task

User = get_user_model()

es_connections = Connections()
es_connections.configure(**settings.ELASTICSEARCH_DSL)

STATUS_CHOICES = [("published", _("Published")), ("draft", _("Draft"))]

logger = logging.getLogger("mcod")


class ResourceDataValidationError(Exception):
    pass


def get_coltype(col, table_schema):
    fields = table_schema.get("fields")
    col_index = int(col.replace("col", "")) - 1
    return fields[col_index]["type"]


DataError = namedtuple("DataError", ["field_name", "message"])


@deconstructible
class FileValidator:
    error_messages = {
        "max_size": ("Ensure this file size is not greater than %(max_size)s." " Your file size is %(size)s."),
        "min_size": ("Ensure this file size is not less than %(min_size)s. " "Your file size is %(size)s."),
        "content_type": "Files of type %(content_type)s are not supported.",
    }

    def __call__(self, file):
        min_size = settings.RESOURCE_MIN_FILE_SIZE
        max_size = settings.RESOURCE_MAX_FILE_SIZE
        try:
            filesize = file.size
        except FileNotFoundError:
            raise ValidationError(_("File %s does not exist, please upload it again") % file.name)

        if max_size is not None and filesize > max_size:
            params = {
                "max_size": filesizeformat(max_size),
                "size": filesizeformat(filesize),
            }
            raise ValidationError(self.error_messages["max_size"], "max_size", params)

        if min_size is not None and filesize < min_size:
            params = {
                "min_size": filesizeformat(min_size),
                "size": filesizeformat(filesize),
            }
            raise ValidationError(self.error_messages["min_size"], "min_size", params)

        mime_type = magic.from_buffer(file.read(), mime=True)
        family, content_type, options = parse_mime_type(mime_type)
        file.seek(0)
        if content_type not in [ct[1] for ct in settings.SUPPORTED_CONTENT_TYPES]:
            params = {"content_type": content_type}
            raise ValidationError(self.error_messages["content_type"], "content_type", params)

    def __eq__(self, other):
        return isinstance(other, FileValidator)


RESOURCE_TYPE_WEBSITE = "website"
RESOURCE_TYPE_API = "api"
RESOURCE_TYPE_FILE = "file"
RESOURCE_TYPE = (
    (RESOURCE_TYPE_FILE, _("File")),
    (RESOURCE_TYPE_WEBSITE, _("Web Site")),
    (RESOURCE_TYPE_API, _("API")),
)
ResourceType = Literal["website", "api", "file"]

RESOURCE_TYPE_API_CHANGE = "api-change"
RESOURCE_TYPE_API_CHANGE_LABEL = _("API - change")

RESOURCE_TYPE_FILE_CHANGE = "file-change"
RESOURCE_TYPE_FILE_CHANGE_LABEL = _("File - change")

RESOURCE_FORCED_TYPE = (
    (RESOURCE_TYPE_API_CHANGE, RESOURCE_TYPE_API_CHANGE_LABEL),
    (RESOURCE_TYPE_FILE_CHANGE, RESOURCE_TYPE_FILE_CHANGE_LABEL),
)
RESOURCE_DATA_DATE_PERIODS = (
    ("daily", _("daily")),
    ("weekly", _("weekly")),
    ("monthly", _("monthly")),
)


class TaskResult(TaskResultOrig):
    @staticmethod
    def values_from_result(result, key):
        exc_message = result["exc_message"]

        for s in exc_message.lstrip("[{0").rstrip("}]").split("}, {"):
            pos = s.find(f"'{key}'")
            if pos < 0:
                raise KeyError()
            start = pos + len(key) + 4
            end = start
            escape = False
            while end < len(s):
                end += 1
                if escape:
                    escape = False
                    continue
                if s[end] == "\\":
                    escape = True
                    continue
                if s[end] == s[start]:
                    yield s[start + 1 : end]
                    break

    @staticmethod
    def find_es_parse_errors(text):
        pattern = re.compile(r"failed to parse field (\[[\w.]+\]) of type (\[[\w_]+\])")
        errors = pattern.findall(text)
        replacements = {
            "[scaled_float]": "[Liczba zmiennoprzecinkowa]",
            "[long]": "[Liczba całkowita]",
        }
        error = tuple()
        if errors:
            error = errors[0]
            if error[1] in replacements:
                error = (error[0], replacements[error[1]])
        return error

    @property
    def message(self):
        result = json.loads(self.result) if self.result else {}
        if isinstance(result, str):
            result = json.loads(result)
        exc_message = self._get_exc_message(result)
        error = self.find_es_parse_errors(exc_message)
        error_code = self._find_error_code(result)
        if exc_message.startswith("[{"):
            return [msg or "" for msg in self.values_from_result(result, "message")]
        elif error_code == "es-index-error" and error:
            return [messages.get(error_code).format(*error)]
        if error_code in ["InvalidContentType", "UnsupportedContentType"]:
            exc_message = exc_message.split(":")[-1] if ":" in exc_message else exc_message
        return [messages.get(error_code, "Nierozpoznany błąd walidacji").format(exc_message)]

    @property
    def message_error_str(self) -> str:
        """Return plain message error text."""
        last_message: Optional[list] = self.message[-1]
        return str(self.message[-1]) if last_message else ""

    @property
    def recommendation(self):
        result = json.loads(self.result) if self.result else {}

        if isinstance(result, str):
            result = json.loads(result)

        error = self.find_es_parse_errors(self._get_exc_message(result))

        try:
            codes = list(self.values_from_result(result, "code"))
        except Exception:
            codes = [self._find_error_code(result)]

        if error:
            return [recommendations.get(code).format(error[0]) for code in codes if recommendations.get(code)]

        return [recommendations.get(code, "Skontaktuj się z administratorem systemu.") for code in codes]

    def _get_exc_message(self, result):
        exc_message = result.get("exc_message", "")
        return str(exc_message) if isinstance(exc_message, list) else exc_message

    @staticmethod
    def _find_error_code(result):  # noqa:C901
        if "exc_type" not in result:
            return None

        if result["exc_message"] == "The 'file' attribute has no file associated with it.":
            return "no-file-associated"

        if result["exc_type"] == "OperationalError":
            if (
                result["exc_message"].startswith("could not connect to server: Connection refused")
                or result["exc_message"].find("remaining connection slots are reserved") > 0
            ):
                return "connection-error"

        elif result["exc_type"] == "Exception":
            if result["exc_message"] == "unknown-file-format":
                return result["exc_message"]

        elif result["exc_type"] == "InvalidResponseCode":
            if result["exc_message"] == "Resource location has been moved!":
                return "location-moved"
            if result["exc_message"].startswith("Invalid response code:"):
                if result["exc_message"].endswith("400"):
                    return "400-bad-request"
                if result["exc_message"].endswith("403"):
                    return "403-forbidden"
                if result["exc_message"].endswith("404"):
                    return "404-not-found"
                if result["exc_message"].endswith("503"):
                    return "503-service-unavailable"

        elif result["exc_type"] == "ConnectionError":
            if result["exc_message"].startswith("('Connection aborted."):
                return "connection-aborted"
            if result["exc_message"].find("Failed to establish a new connection") > -1:
                return "failed-new-connection"

        elif result["exc_type"] == "BulkIndexError":
            if result["exc_message"].find("must be between -180.0 and 180.0") > -1:
                return "longitude-error"
            if result["exc_message"].find("must be between -90.0 and 90.0") > -1:
                return "latitude-error"
            if (
                result["exc_message"].find("document(s) failed to index") > -1
                and result["exc_message"].find("mapper_parsing_exception") > -1
            ):
                return "es-index-error"
        return result["exc_type"]

    class Meta:
        proxy = True
        get_latest_by = "date_done"


class Resource(ExtendedModel):
    LANGUAGE_CHOICES = [
        ("pl", _("polish")),
        ("en", _("english")),
    ]
    LANGUAGE_NAMES = dict(LANGUAGE_CHOICES)
    SIGNALS_MAP = {
        "updated": (
            rdf_signals.update_graph,
            revalidate_resource,
            search_signals.update_document_with_related,
            core_signals.notify_updated,
        ),
        "published": (
            rdf_signals.create_graph_with_related_update,
            revalidate_resource,
            search_signals.update_document_with_related,
            core_signals.notify_published,
        ),
        "restored": (
            rdf_signals.create_graph_with_related_update,
            revalidate_resource,
            search_signals.update_document_with_related,
            core_signals.notify_restored,
        ),
        "removed": (
            rdf_signals.delete_graph_with_related_update,
            cancel_data_date_update,
            search_signals.remove_document_with_related,
            update_dataset_file_archive,
            core_signals.notify_removed,
        ),
        "post_m2m_added": (rdf_signals.update_related_graph,),
        "post_m2m_removed": (rdf_signals.update_related_graph,),
        "post_m2m_cleaned": (rdf_signals.update_related_graph,),
    }
    ext_ident = models.CharField(
        max_length=36,
        blank=True,
        editable=False,
        verbose_name=_("external identifier"),
        help_text=_("external identifier of resource taken during import process (optional)"),
    )
    availability = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        editable=False,
        verbose_name=_("availability"),
    )
    file = models.FileField(
        verbose_name=_("File"),
        storage=storages.get_storage("resources"),
        upload_to="%Y%m%d",
        max_length=2000,
        blank=True,
        null=True,
    )
    packed_file = models.FileField(
        verbose_name=_("Packed file"),
        storage=storages.get_storage("resources"),
        upload_to="%Y%m%d",
        max_length=2000,
        blank=True,
        null=True,
    )
    csv_file = models.FileField(
        verbose_name=_("File as CSV"),
        storage=storages.get_storage("resources"),
        upload_to="%Y%m%d",
        max_length=2000,
        blank=True,
        null=True,
    )
    jsonld_file = models.FileField(
        verbose_name=_("File as JSON-LD"),
        storage=storages.get_storage("resources"),
        upload_to="%Y%m%d",
        max_length=2000,
        blank=True,
        null=True,
    )
    file_mimetype = models.TextField(blank=True, null=True, editable=False, verbose_name=_("File mimetype"))
    file_info = models.TextField(blank=True, null=True, editable=False, verbose_name=_("File info"))
    file_encoding = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("File encoding"),
    )
    link = models.URLField(verbose_name=_("Resource Link"), max_length=2000, blank=True, null=True)
    title = SanitizedCharField(
        max_length=500,
        verbose_name=_("title"),
        validators=[model_validators.illegal_character_validator],
    )
    description = SanitizedTextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        validators=[model_validators.illegal_character_validator],
    )
    position = models.IntegerField(default=1, verbose_name=_("Position"))
    dataset = models.ForeignKey(
        "datasets.Dataset",
        on_delete=models.CASCADE,
        related_name="resources",
        verbose_name=_("Dataset"),
    )

    format = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name=_("Format"),
        choices=settings.SUPPORTED_FORMATS_CHOICES_WITH_ARCHIVES,
    )
    type = models.CharField(
        max_length=10,
        choices=RESOURCE_TYPE,
        default="file",
        editable=False,
        verbose_name=_("Type"),
    )
    forced_api_type = models.BooleanField(verbose_name=_("Mark resource as API"), default=False)
    forced_file_type = models.BooleanField(verbose_name=_("Mark resource as file"), default=False)
    openness_score = models.IntegerField(
        default=0,
        verbose_name=_("Openness score"),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )

    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="resources_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="resources_modified",
    )
    link_tasks = models.ManyToManyField(
        "TaskResult",
        verbose_name=_("Download Tasks"),
        blank=True,
        related_name="link_task_resources",
    )
    file_tasks = models.ManyToManyField(
        "TaskResult",
        verbose_name=_("Download Tasks"),
        blank=True,
        related_name="file_task_resources",
    )
    data_tasks = models.ManyToManyField(
        "TaskResult",
        verbose_name=_("Download Tasks"),
        blank=True,
        related_name="data_task_resources",
    )

    link_tasks_last_status = models.CharField(verbose_name=_("link tasks last status"), max_length=7, blank=True)
    file_tasks_last_status = models.CharField(verbose_name=_("file tasks last status"), max_length=7, blank=True)
    data_tasks_last_status = models.CharField(verbose_name=_("data tasks last status"), max_length=7, blank=True)
    old_file = models.FileField(
        verbose_name=_("File"),
        storage=storages.get_storage("resources"),
        upload_to="",
        max_length=2000,
        blank=True,
        null=True,
    )
    old_resource_type = models.TextField(verbose_name=_("Data type"), null=True)
    old_format = models.CharField(max_length=150, blank=True, null=True, verbose_name=_("Format"))
    old_customfields = JSONField(blank=True, null=True, verbose_name=_("Customfields"))
    old_link = models.URLField(verbose_name=_("Resource Link"), max_length=2000, blank=True, null=True)
    downloads_count = models.PositiveIntegerField(default=0)

    show_tabular_view = models.BooleanField(verbose_name=_("Tabular view"), default=True)
    has_chart = models.BooleanField(verbose_name=_("has chart?"), default=False)
    has_dynamic_data = models.NullBooleanField(verbose_name=_("dynamic data"))
    has_high_value_data = models.NullBooleanField(verbose_name=_("has high value data"))
    has_high_value_data_from_ec_list = models.NullBooleanField(verbose_name=_("has high value data from the EC list"))
    has_map = models.BooleanField(verbose_name=_("has map?"), default=False)
    has_research_data = models.NullBooleanField(verbose_name=_("has research data"))
    has_table = models.BooleanField(verbose_name=_("has table?"), default=False)
    is_chart_creation_blocked = models.BooleanField(verbose_name=_("is chart creation blocked?"), default=False)
    tabular_data_schema = JSONField(null=True, blank=True)
    data_date = models.DateField(null=True, verbose_name=_("Data date"))
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default=LANGUAGE_CHOICES[0][0],
        verbose_name=_("language version of the data"),
        db_index=True,
    )

    verified = models.DateTimeField(blank=True, default=now, verbose_name=_("Update date"))
    from_resource = models.ForeignKey("self", blank=True, null=True, on_delete=models.DO_NOTHING)
    related_resource = CustomManagerForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="related_data",
        manager_name="raw",
        verbose_name=_("related data"),
    )
    special_signs = models.ManyToManyField(
        "special_signs.SpecialSign",
        verbose_name=_("special signs"),
        blank=True,
        related_name="special_signs_resources",
    )
    regions = RegionManyToManyField(
        "regions.Region",
        blank=True,
        related_name="region_resources",
        related_query_name="resource",
        through="regions.ResourceRegion",
        verbose_name=_("Regions"),
    )
    is_auto_data_date = models.BooleanField(verbose_name=_("Automatic update"), default=False)
    data_date_update_period = models.CharField(
        verbose_name=_("Data date update period"),
        choices=RESOURCE_DATA_DATE_PERIODS,
        max_length=10,
        null=True,
        blank=True,
    )
    automatic_data_date_start = models.DateField(verbose_name=_("Data date start date update"), blank=True, null=True)
    automatic_data_date_end = models.DateField(verbose_name=_("Data date end date update"), blank=True, null=True)
    endless_data_date_update = models.BooleanField(verbose_name=_("Endless data date update"), default=False)
    contains_protected_data = models.BooleanField(verbose_name=_("Contains protected data list"), default=False)

    def __str__(self):
        return self.title

    @property
    def license_code(self):
        return self.dataset.license_code

    @property
    def update_frequency(self):
        return self.dataset.update_frequency

    @property
    def type_as_str(self):
        if self.type == RESOURCE_TYPE_API and self.forced_api_type:
            return RESOURCE_TYPE_API_CHANGE_LABEL
        elif self.type == RESOURCE_TYPE_FILE and self.forced_file_type:
            return RESOURCE_TYPE_FILE_CHANGE_LABEL
        return self.get_type_display()

    type_as_str.fget.short_description = _("Type")

    @property
    def media_type(self):
        return self.type or ""

    @property
    def data_rules(self):
        return self.tabular_data_schema

    @property
    def is_data_processable(self):
        processable_formats = ("csv", "tsv", "xls", "xlsx", "ods", "shp")
        return (
            (self.format in processable_formats or (self.main_file_compressed_format in processable_formats))
            and self.main_file
            and self.dataset.organization.institution_type != Organization.INSTITUTION_TYPE_DEVELOPER
        )

    @property
    def is_linked(self):
        if self.is_imported:
            return self.availability == "remote"
        return bool(self.link and not self.is_link_internal)

    @property
    def is_link_internal(self) -> bool:
        api_url_old: str = settings.API_URL.replace("https:", "http:")
        return bool(self.link and self.link.startswith((settings.API_URL, api_url_old)))

    @property
    def is_imported(self):
        return self.dataset.is_imported

    @property
    def source_type(self) -> Optional[str]:
        return self.dataset.source_type

    @property
    def is_imported_from_ckan(self):
        return self.dataset.is_imported_from_ckan

    @property
    def is_imported_from_xml(self):
        return self.dataset.is_imported_from_xml

    @property
    def maps_and_plots(self):
        return self.tabular_data_schema

    @property
    def category(self):
        return self.dataset.category if self.dataset else ""

    @property
    def comment_editors(self):
        emails = []
        if self.dataset.source:
            emails.extend(self.dataset.source.emails_list)
        else:
            if self.dataset.update_notification_recipient_email:
                emails.append(self.dataset.update_notification_recipient_email)
            elif self.modified_by:
                emails.append(self.modified_by.email)
            else:
                emails.extend(user.email for user in self.dataset.organization.users.all())
        return emails

    @property
    def comment_mail_recipients(self):
        return [
            config.CONTACT_MAIL,
        ] + self.comment_editors

    @property
    def csv_file_url(self):
        return self._get_api_url(self.csv_converted_file.url) if self.csv_converted_file else None

    @property
    def file_data_path(self) -> Union[Path, str]:
        if self.is_archived_file:
            _, tmp_file_path = tempfile.mkstemp()
            with ArchiveReader(self.main_file.path) as archive:
                try:
                    path = archive.extract_single()
                    shutil.move(path, tmp_file_path)
                    return tmp_file_path
                except KeyError:
                    logger.debug(f"{self.main_file.path} contains n>1 files")
        return self.main_file.path

    @property
    def is_archived_file(self):
        path = self.main_file.path if self.main_file else None
        if path:
            try:
                family, content_type, options = get_file_info(path)
            except FileNotFoundError:
                return False
            return is_archive_file(content_type)
        return False

    @property
    def is_archived_csv(self):
        return self.is_archived_file and self.main_file_compressed_format == "csv"

    def get_csv_file_internal_url(self, suffix=".utf8_encoded.csv"):
        """
        Returns absolute url to csv file for convertion to jsonld.
        During the process new csv file (with specified suffix) is created in media directory
        to meet the requirements of converter (csvwlib.utils.CSVUtils).
        """
        if self.is_archived_csv:  # archived csv file should not be converted to jsonld.
            return None
        _file = self.main_file if self.main_file and self.format == "csv" else None
        _file_utf8 = None
        if _file:  # ensure csv can be converted to json-ld: utf-8, delimiter is colon (,), etc.
            with open(_file.path, "r", encoding=self.main_file_encoding, newline="") as f:
                dialect = csv.Sniffer().sniff(f.readline())
                f.seek(0)
                reader = csv.reader(f, dialect)
                _file_utf8 = tempfile.NamedTemporaryFile(
                    mode="w",
                    dir=os.path.dirname(_file.path),
                    delete=False,
                    encoding="utf-8",
                    suffix=suffix,
                )
                writer = csv.writer(_file_utf8)
                writer.writerows((row for row in reader))
                _file_utf8.close()

        if _file_utf8:
            url = _file.url.replace(os.path.basename(_file.name), os.path.basename(_file_utf8.name))
        else:
            url = _file.url if _file else self.csv_converted_file.url if self.csv_converted_file else None
        return self._get_internal_url(url) if url else None

    def get_location(self, file_type):
        if self.is_linked:
            location = self.link
        elif file_type == "csv":
            location = self.csv_file_url
        elif file_type == "jsonld":
            location = self.jsonld_file_url
        else:
            location = self.file_url
        return location

    @property
    def jsonld_file_url(self):
        return self._get_api_url(self.jsonld_converted_file.url) if self.jsonld_converted_file else None

    @property
    def csv_file_size(self):
        try:
            return self.csv_converted_file.size if self.csv_converted_file else None
        except FileNotFoundError:
            return None

    @property
    def jsonld_file_size(self):
        try:
            return self.jsonld_converted_file.size if self.jsonld_converted_file else None
        except FileNotFoundError:
            return None

    @property
    def dataset_title_pl(self):
        return self.dataset.title_pl

    @property
    def dataset_title_en(self):
        return self.dataset.title_en

    @property
    def dataset_slug_pl(self):
        return self.dataset.slug_pl

    @property
    def dataset_slug_en(self):
        return self.dataset.slug_en

    @property
    def label_from_instance(self):
        state = _("deleted") if self.is_removed else self.STATUS[self.status]
        return f"{self.title} ({state})"

    @property
    def link_is_valid(self):
        return self.link_tasks_last_status == "SUCCESS"

    @property
    def last_link_validation_error_message(self) -> str:
        """
        Returns last link validation task error message if failed.
        Returns empty string otherwise.
        """
        newest_link_task: Optional[TaskResult] = self.link_tasks.latest()
        if newest_link_task and newest_link_task.status == "FAILURE":
            return newest_link_task.message_error_str
        return ""

    @property
    def file_is_valid(self):
        return self.file_tasks_last_status == "SUCCESS"

    @property
    def data_is_valid(self):
        return self.data_tasks_last_status == "SUCCESS"

    @property
    def file_url(self):
        if self.is_imported and self.availability != "local":
            return self.link
        if self.main_file:
            _file_url = self.main_file.url if not self.packed_file else self.packed_file.url
            return "%s%s" % (settings.API_URL, _file_url)
        return ""

    @property
    def file_basename(self):
        return self._get_basename(self.main_file.name) if self.main_file else None

    @property
    def file_extension(self):
        return self._main_file.extension

    @property
    def file_size(self):
        if self.main_file:
            try:
                return self.main_file.size
            except FileNotFoundError:
                return None

    @property
    def frontend_url(self):
        return f"/dataset/{self.dataset.id}/resource/{self.id}"

    @property
    def frontend_absolute_url(self):
        return self._get_absolute_url(self.frontend_url)

    @property
    def formats(self):
        if self.formats_list:
            return ", ".join(self.formats_list).upper()

    @property
    def converted_formats(self):
        return [rf.format for rf in self.other_files]

    @property
    def converted_formats_str(self):
        return ",".join(self.converted_formats)

    @property
    def formats_list(self):
        formats = []
        if self.format:
            formats.append(self.format)
        elif self._main_file and self._main_file.format:
            formats.append(self._main_file.format)
        formats.extend(self.converted_formats)
        return formats

    @property
    def download_url(self):
        if self.main_file or self.is_imported:
            return self._get_api_url(f"/resources/{self.ident}/file")
        return ""

    @property
    def csv_download_url(self):
        return self._get_api_url(f"/resources/{self.ident}/csv") if self.csv_converted_file else None

    @property
    def jsonld_download_url(self):
        return self._get_api_url(f"/resources/{self.ident}/jsonld") if self.jsonld_converted_file else None

    @property
    def is_indexable(self):
        if self.type == "file" and not self.file_is_valid:
            return False

        if self.type in ("api", "website") and not self.link_is_valid:
            return False

        return True

    @property
    def data(self):
        if not self._data:
            if self.main_file:
                if self.has_tabular_format():
                    self._data = TabularData(self)
                if self.format == "shp":
                    self._data = ShpData(self)

        return self._data

    @property
    def data_meta(self):
        if self.data and self.data.available:
            return dict(
                headers_map=self.data.headers_map,
                data_schema=self.data.data_schema,
            )
        return {}

    @property
    def geo_data(self):
        if self.data and self.data.available and self.data.has_geo_data:
            return self.data
        return None

    @property
    def tabular_data(self):
        if self.data and self.data.available and self.show_tabular_view:
            return self.data
        return None

    def increase_openness_score(self):
        csv_file = None
        xls_formats = ["xls", "xlsx"]
        if (
            (self.format in xls_formats or self.main_file_compressed_format in xls_formats)
            and not self.is_linked
            and self.has_data
            and self.data.table
        ):
            csv_filename = os.path.splitext(self.file_basename)[0]
            headers = self.data.table.schema.field_names
            f = BytesIO()
            csv_out = unicodecsv.writer(f, encoding="utf-8")
            csv_out.writerow(headers)
            for row in self.data.table.iter(cast=True):
                csv_out.writerow(row)
            f.seek(0)
            csv_file = self.save_file(f, f"{csv_filename}.csv")

        if csv_file:
            resource_file, _ = ResourceFile.objects.update_or_create(
                resource_id=self.pk,
                format="csv",
                is_main=False,
                defaults={"file": csv_file},
            )
            self.add_to_other_files_cache(resource_file)

        jsonld_file = self.convert_csv_to_jsonld()
        if jsonld_file:
            resource_file, _ = ResourceFile.objects.update_or_create(
                resource_id=self.pk,
                format="jsonld",
                is_main=False,
                defaults={"file": jsonld_file},
            )
            self.add_to_other_files_cache(resource_file)

    def convert_csv_to_jsonld(self):
        url = self.get_csv_file_internal_url()
        if url:
            jsonld_filename = f"{os.path.splitext(self.file_basename)[0]}.jsonld"
            logger.debug(f"Trying to convert {url} to jsonld file named {jsonld_filename}")
            try:
                graph = CSVWConverter.to_rdf(url)
                # override context to omit long list of default namespaces as @context in json-ld.
                context = dict((pfx, str(ns)) for (pfx, ns) in graph.namespaces() if pfx and pfx == "csvw")
                data = graph.serialize(format="json-ld", context=context, auto_compact=True)
                csv_original_url = self._get_api_url(self.main_file.url)
                data = data.replace(url, csv_original_url)
                pattern = f"{os.path.dirname(os.path.realpath(self.main_file.path))}/*.utf8_encoded.csv"
                tmp_files = glob.glob(pattern)
                for f in tmp_files:
                    try:
                        os.remove(f)
                        logger.debug(f"Temporary file was deleted: {f}")
                    except OSError as e:
                        logger.debug(e)
                return self.save_file(BytesIO(data.encode("utf-8")), jsonld_filename)
            except Exception as exc:
                logger.debug(exc)
                return None

    def save_file(self, content, filename):
        dt = self.created.date() if self.created else now().date()
        subdir = dt.isoformat().replace("-", "")
        dest_dir = os.path.join(self.main_file.storage.location, subdir)
        os.makedirs(dest_dir, exist_ok=True)
        file_path = os.path.join(dest_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content.read())
        return "%s/%s" % (subdir, filename)

    def revalidate(self, update_verification_date: bool = True):
        if not self.link or self.is_link_internal:
            if self._main_file:
                entrypoint_process_resource_file_validation_task.s(
                    self._main_file.pk,
                    update_verification_date=update_verification_date,
                ).apply_async_on_commit()
        else:
            entrypoint_process_resource_validation_task.s(
                self.id, update_verification_date=update_verification_date
            ).apply_async_on_commit()

    def revalidate_tabular_data(self, *, apply_on_commit: bool) -> None:
        if not self.is_data_processable:
            return
        signature = process_resource_file_data_task.s(self.id)
        if apply_on_commit:
            signature.apply_async_on_commit()
        else:
            signature.apply()

    @classmethod
    def accusative_case(cls):
        return _("acc: Resource")

    @classmethod
    def get_resources_files(cls):
        resources_files = [f.file.path for f in ResourceFile.objects.all()]
        resources_files.extend([x.packed_file.path for x in cls.raw.exclude(packed_file=None).exclude(packed_file="")])
        resources_files.extend([x.old_file.path for x in cls.raw.exclude(old_file=None).exclude(old_file="")])
        return resources_files

    @classmethod
    def get_all_files(cls, path=settings.RESOURCES_MEDIA_ROOT):
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    yield entry.path
                else:
                    yield from cls.get_all_files(entry.path)
            except OSError as error:
                print("Error calling is_file():", error)
                continue

    @classmethod
    def remove_orphaned_file(cls, file_path, removed_files_root=settings.RESOURCES_FILES_TO_REMOVE_ROOT):
        file_dirname = os.path.basename(os.path.dirname(file_path))
        file_name = os.path.basename(file_path)

        removed_files_dir = os.path.join(removed_files_root, file_dirname)
        if not os.path.exists(removed_files_dir):
            os.makedirs(removed_files_dir)

        removed_file_path = os.path.join(removed_files_dir, file_name)
        return shutil.move(file_path, removed_file_path)

    def get_openness_score(
        self, format_: Optional[str] = None
    ) -> Tuple[OptionalOpennessScoreValue, Dict[int, OptionalOpennessScoreValue]]:
        format_ = format_ or self.format
        resource_score: OptionalOpennessScoreValue = 0
        files_score: Dict[int, OptionalOpennessScoreValue] = dict()
        if format_ is None:
            return resource_score, files_score
        if self.link and not self.main_file:
            resource_score = get_score(self.link, format_)
        else:
            files_score = {f.pk: f.get_openness_score() for f in self.all_files}
            resource_score = max(files_score.values()) if files_score else resource_score
        return resource_score, files_score

    @property
    def file_size_human_readable(self):
        return self.sizeof_fmt(self.file_size or 0)

    @property
    def file_size_human_readable_or_empty_str(self):
        return self.file_size_human_readable if self.file_size else ""

    @property
    def title_as_link(self):
        return self.mark_safe(f'<a href="{self.admin_change_url}">{self.title}</a>')

    @property
    def title_truncated(self):
        title = (self.title[:100] + "..") if len(self.title) > 100 else self.title
        return title

    @property
    def has_data(self):
        try:
            next(self.data.iter(size=1))
            return True
        except Exception:
            return False

    @property
    def related_resource_published(self):
        if self.related_resource and self.related_resource.is_published and not self.related_resource.is_removed:
            return self.related_resource

    @property
    def visualization_types(self):
        result = []
        if self.is_linked:
            return result
        if self.has_chart:
            result.append("chart")
        if self.has_map:
            result.append("map")
        if self.has_table:
            result.append("table")
        return result

    @property
    def method_of_sharing(self) -> Optional[str]:
        return SOURCE_TYPE_CHOICES_FOR_ADMIN.get(self.source_type, self.source_type)

    def verify_rules(self, rules):

        if self.data:
            es_index = self.data.idx_name
            es = es_connections.get_connection()
            validation_results = {}
            for rule in rules.items():
                col, val = rule
                col_type = get_coltype(col, self.tabular_data_schema)
                mappings = self.data.idx.get_field_mapping(fields=f"{col}.*")[self.data.idx._name]["mappings"]
                mappings = mappings["doc"].keys() if "doc" in mappings else []
                col = f"{col}.val" if f"{col}.val" in mappings else col
                if col_type in ["string", "any"]:
                    col += ".keyword"
                try:
                    results = es.search(index=es_index, body=painless_body(col, val), params={"size": 5})
                except Exception:
                    results = {}
                validation_results[rule[0]] = results
            return validation_results

    _data = None

    i18n = SanitizedTranslationField(fields=("title", "description"))
    tracker = FieldTracker()
    slugify_field = "title"

    objects = ResourceManager()
    trash = ResourceTrashManager()
    raw = ResourceRawManager()
    raw_db = ResourceRawDBManager()

    class Meta:
        verbose_name = _("Resource")
        verbose_name_plural = _("Resources")
        db_table = "resource"
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]

    @property
    def chartable(self):
        if self.data and self.data.available and self.data.is_chartable:
            return self
        return None

    @property
    def institution(self):
        return self.dataset.organization

    @property
    def types(self):
        return [
            self.type,
        ]

    @property
    def map_preview(self):
        return self._get_absolute_url(f"/dataset/{self.dataset.id}/resource/{self.id}/preview/map")

    @property
    def chart_preview(self):
        return self._get_absolute_url(f"/dataset/{self.dataset.id}/resource/{self.id}/preview/chart")

    def has_tabular_format(self, extra_formats=tuple()):
        base_formats = ["csv", "tsv", "xls", "xlsx", "ods"]
        base_formats += extra_formats
        return self.format in base_formats or self.main_file_compressed_format in base_formats

    @property
    def computed_downloads_count(self):
        return ResourceDownloadCounter.objects.filter(resource_id=self.pk).aggregate(count_sum=Sum("count"))["count_sum"] or 0

    @property
    def computed_views_count(self):
        return ResourceViewCounter.objects.filter(resource_id=self.pk).aggregate(count_sum=Sum("count"))["count_sum"] or 0

    @cached_property
    def data_special_signs(self):
        return self.special_signs.order_by("name")

    @cached_property
    def special_signs_symbols_list(self):
        return list(self.special_signs.values_list("symbol", flat=True))

    @property
    def special_signs_symbols(self):
        return "\n".join([f"{x.symbol} ({x.description})" for x in self.data_special_signs])

    @cached_property
    def supplement_docs(self):
        return self.supplements.all()

    @property
    def supplements_str(self):
        return ";".join([x.name_csv for x in self.supplement_docs])

    @property
    def all_regions(self):
        return Region.objects.for_resource_with_id(self.pk, has_other_regions=self.regions.all().exists())

    @property
    def all_regions_str(self):
        return "; ".join(list(self.all_regions.values_list("hierarchy_label_i18n", flat=True)))

    def to_rdf_graph(self):
        _schema = self.get_rdf_serializer_schema()
        from collections import namedtuple

        ResourceRDF = namedtuple("ResourceRDF", ["data"])
        obj = ResourceRDF(self)
        return _schema(many=False).dump(obj)

    def as_sparql_create_query(self):
        g = self.to_rdf_graph()
        data = "".join([f"{s.n3()} {p.n3()} {o.n3()} . " for s, p, o in g.triples((None, None, None))])
        namespaces_dict = {prefix: ns for prefix, ns in g.namespaces()}
        return "INSERT DATA { %(data)s }" % {"data": data}, namespaces_dict

    def _charts_for_user(self, user, **kwargs):
        qs = self.charts.all()
        public = qs.filter(is_default=True)
        public = public.order_by("-id")[:1]
        private = qs.filter(is_default=False, created_by=user).order_by("-id")[:1] if user.is_authenticated else None
        return public.union(private).order_by("-is_default") if private else public

    def charts_for_user(self, user, **kwargs):
        queryset = self.charts.filter(is_default=True)
        if not self.is_chart_creation_blocked and user.is_authenticated:
            private = self.charts.filter(is_default=False, created_by=user).order_by("-id")[:1]
            queryset = queryset.union(private)
        queryset = queryset.order_by("-is_default", "name")
        return self._get_page(queryset, **kwargs)

    def check_link_status(self):
        return check_link_status(self.link, self.type)

    def check_support(self):
        return self._main_file.check_support()

    def download_file(self):
        return download_file(self.link, self.forced_file_type)

    def _get_page(self, queryset, page=1, per_page=20, **kwargs):
        paginator = Paginator(queryset, per_page)
        return paginator.get_page(page)

    def save_chart(self, user, data):
        return self.save_named_chart(user, data)

    def save_named_chart(self, user, data):
        return Chart.objects.create(resource=self, created_by=user, **data)

    def get_resource_type(self):
        res_type = self.type
        if self.id and self.tracker.has_changed("forced_api_type"):
            if self.forced_api_type and res_type == RESOURCE_TYPE_WEBSITE:
                res_type = RESOURCE_TYPE_API
            elif not self.forced_api_type and res_type == RESOURCE_TYPE_API:
                res_type = RESOURCE_TYPE_WEBSITE
        if self.id and self.tracker.has_changed("forced_file_type"):
            if not self.forced_file_type and res_type == RESOURCE_TYPE_FILE:
                res_type = RESOURCE_TYPE_API
            elif self.forced_file_type and res_type == RESOURCE_TYPE_API:
                res_type = RESOURCE_TYPE_FILE
        return res_type

    @property
    def is_link_updated(self):

        return any(
            [
                self.tracker.has_changed("link"),
                self.tracker.has_changed("availability"),
                self.has_forced_file_changed,
                (self.link and not self.is_link_internal and self.state_restored),
            ]
        )

    @property
    def has_forced_file_changed(self):
        changed_forced_file_type = self.tracker.has_changed("forced_file_type")
        previous_forced_file_type = self.tracker.previous("forced_file_type")
        return changed_forced_file_type and previous_forced_file_type is not None

    @property
    def main_file(self):
        return getattr(self._main_file, "file", "")

    @property
    def csv_converted_file(self):
        return self.get_other_file_by_format("csv")

    @property
    def jsonld_converted_file(self):
        return self.get_other_file_by_format("jsonld")

    @property
    def main_file_info(self):
        return getattr(self._main_file, "info", "")

    @property
    def main_file_encoding(self):
        return getattr(self._main_file, "encoding", "")

    @property
    def main_file_mimetype(self):
        return getattr(self._main_file, "mimetype", None)

    @property
    def main_file_compressed_format(self):
        return getattr(self._main_file, "compressed_file_format", None)

    @property
    def main_file_compressed_encoding(self):
        return getattr(self._main_file, "compressed_file_encoding", None)

    @property
    def _main_file(self):
        main_file = getattr(self, "_cached_file", [])
        if not main_file:
            try:
                _main_file = self.files.get(is_main=True)
            except ResourceFile.DoesNotExist:
                _main_file = None
            self._cached_file = _main_file
        else:
            _main_file = main_file[0] if isinstance(main_file, list) else main_file
        return _main_file

    @property
    def other_files(self):
        if hasattr(self, "_other_files"):  # _other_files is added if qs.iterator() is not used
            return getattr(self, "_other_files", [])
        return self.files.filter(is_main=False)

    @property
    def all_files(self):
        all_files = [self._main_file] if self._main_file else []
        all_files.extend(self.other_files)
        return all_files

    def add_to_other_files_cache(self, new_file):
        """
        Add `new_file` to `self._other_files` cache.
        If `self._other_files` already has file with the same format as `new_file`, it is replaced by `new_file`.
        """
        new_files = [file for file in getattr(self, "_other_files", []) if file.format != new_file.format]
        new_files.append(new_file)
        self._other_files = new_files

    def get_other_file_by_format(self, file_format: str):
        resource_files = [file for file in self.other_files if file.format == file_format]
        resource_file = next(iter(resource_files), None)
        return resource_file.file if resource_file else ""

    @property
    def is_published(self):
        return self.status == "published"

    @property
    def is_dga(self) -> bool:
        """
        The DGA (Data Governance Act) in the context of Resource puts
        restrictions on its editing and deletion. A.k.a. "protected data".
        For more information, see OTD-138. The DGA mechanism applies only to
        already published resources.
        """
        return self.contains_protected_data and self.is_published and not self.is_removed

    @property
    def needs_es_and_rdf_db_update(self):
        return self.is_published and not self.is_removed and not self.is_permanently_removed

    def send_resource_comment_mail(self, comment):
        context = {
            "host": settings.BASE_URL,
            "resource": self,
            "comment": comment,
            "test": bool(settings.DEBUG and config.TESTER_EMAIL),
        }
        _plain = "mails/resource-comment.txt"
        _html = "mails/resource-comment.html"
        with override("pl"):
            msg_plain = render_to_string(_plain, context=context)
            msg_html = render_to_string(_html, context=context)
            title = self.title.replace("\n", " ").replace("\r", "")
            subject = _("A comment was posted on the resource %(title)s") % {"title": title}
            self.send_mail(
                subject,
                msg_plain,
                config.SUGGESTIONS_EMAIL,
                ([config.TESTER_EMAIL] if settings.DEBUG and config.TESTER_EMAIL else self.comment_mail_recipients),
                html_message=msg_html,
            )

    def update_es_and_rdf_db(self):
        if self.needs_es_and_rdf_db_update:
            update_with_related_task.s("resources", "Resource", self.pk).apply_async()
            update_graph_task.s("resources", "Resource", self.pk).apply_async_on_commit()

    def update_dataset_verified(self, verified: datetime.datetime) -> None:
        try:
            Dataset.objects.filter(pk=self.dataset.id).update(verified=verified)
        except Exception as exc:
            logger.error(f"Cannot update dataset verified for the {self.type} resource {self.id}: {exc}")
            raise

    @property
    def regions_to_conceal(self):
        ids = list(self.all_regions.exclude(region_id=settings.DEFAULT_REGION_ID).values_list("pk", flat=True))
        return Region.objects.unassigned_regions(ids)

    @property
    def regions_to_publish(self):
        ids = list(self.all_regions.values_list("pk", flat=True))
        return Region.objects.assigned_regions(ids)

    def schedule_data_date_update(self):
        period_method = {
            "daily": "schedule_interval_data_date_update",
            "weekly": "schedule_interval_data_date_update",
            "monthly": "schedule_crontab_data_date_update",
        }
        if self.is_auto_data_date and self.is_auto_data_date_allowed:
            getattr(self, period_method[self.data_date_update_period])(schedule_date=self.automatic_data_date_start)

    def schedule_interval_data_date_update(self, *args, **kwargs):
        logger.debug(f"Scheduling interval data date update for resource with id {self.pk}")
        warsaw_tz = pytz.timezone(settings.TIME_ZONE)
        days_count, freq = (1, rrule.DAILY) if self.data_date_update_period == "daily" else (7, rrule.WEEKLY)
        schedule, _ = IntervalSchedule.objects.get_or_create(every=days_count, period=IntervalSchedule.DAYS)
        task_kwargs = {"interval": schedule}
        start_dt = datetime.datetime.combine(self.automatic_data_date_start, datetime.time(0, 5))
        localized_start = warsaw_tz.localize(start_dt)
        task_kwargs["start_time"] = localized_start
        localized_now = now().astimezone(warsaw_tz)
        if localized_start <= localized_now:
            last_run_at = localized_start
            for dt in rrule.rrule(freq, localized_start, until=localized_now):
                last_run_at = dt
            task_kwargs["last_run_at"] = last_run_at
        self._create_schedule_periodic_task(task_kwargs=task_kwargs)

    def schedule_crontab_data_date_update(self, schedule_date):
        logger.debug(f"Scheduling crontab data date update for resource with id {self.pk}")
        warsaw_tz = pytz.timezone(settings.TIME_ZONE)
        localized_today = now().astimezone(warsaw_tz).date()
        task_kwargs = {}
        if self.is_last_day_of_month(schedule_date):
            if schedule_date < localized_today:
                m_range = monthrange(localized_today.year, localized_today.month)
                month_last_day = datetime.date(localized_today.year, localized_today.month, m_range[1])
                while schedule_date < month_last_day:
                    schedule_date += relativedelta(months=1)
                    schedule_date = self.correct_last_moth_day(schedule_date)
            crontab_kwargs = {
                "minute": "30",
                "hour": "0",
                "day_of_week": "*",
                "day_of_month": str(schedule_date.day),
                "month_of_year": str(schedule_date.month),
                "timezone": pytz.timezone(settings.TIME_ZONE),
            }
            task_kwargs = {
                "one_off": True,
                "task": "mcod.resources.tasks.update_last_day_data_date",
            }
            self.cancel_data_date_update()
        else:
            crontab_kwargs = {
                "minute": "30",
                "hour": "0",
                "day_of_week": "*",
                "day_of_month": str(schedule_date.day),
                "month_of_year": "*",
                "timezone": pytz.timezone(settings.TIME_ZONE),
            }
        schedule, _ = CrontabSchedule.objects.get_or_create(**crontab_kwargs)
        task_kwargs["crontab"] = schedule
        self._create_schedule_periodic_task(task_kwargs=task_kwargs)

    def is_last_day_of_month(self, schedule_date):
        m_range = monthrange(schedule_date.year, schedule_date.month)
        day_of_month = schedule_date.day
        return m_range[1] == day_of_month

    def correct_last_moth_day(self, schedule_date):
        if not self.is_last_day_of_month(schedule_date):
            proper_last_day = monthrange(schedule_date.year, schedule_date.month)[1]
            schedule_date = schedule_date.replace(day=proper_last_day)
        return schedule_date

    def _create_schedule_periodic_task(self, task_kwargs):
        warsaw_tz = pytz.timezone(settings.TIME_ZONE)
        obj_kwargs = {
            "task": "mcod.resources.tasks.update_data_date",
            "args": json.dumps([self.pk]),
            "queue": "periodic",
        }
        obj_kwargs.update(task_kwargs)
        if self.automatic_data_date_end:
            end_dt = datetime.datetime.combine(self.automatic_data_date_end, datetime.time(1, 0))
            localized_end = warsaw_tz.localize(end_dt)
            obj_kwargs["expires"] = localized_end
        try:
            PeriodicTask.objects.update_or_create(name=self.data_date_task_name, defaults=obj_kwargs)
        except ValidationError:
            PeriodicTask.objects.get(name=self.data_date_task_name).delete()
            PeriodicTask.objects.create(name=self.data_date_task_name, **obj_kwargs)

    def cancel_data_date_update(self):
        try:
            logger.debug(f"Deleting task: {self.data_date_task_name}")
            PeriodicTask.objects.get(name=self.data_date_task_name).delete()
        except PeriodicTask.DoesNotExist:
            pass

    @property
    def data_date_task_name(self):
        return f"Data date update for resource {self.pk}."

    @staticmethod
    def get_auto_data_date_errors(data, is_xml_import=False):
        auto_data_date = data.get("is_auto_data_date")
        if not auto_data_date:
            return

        dd_start = data.get("automatic_data_date_start")
        dd_end = data.get("automatic_data_date_end")
        dd_update_period = data.get("data_date_update_period")
        dd_endless_update = data.get("endless_data_date_update")

        required_msg = _("This field is required.")

        if not dd_start:
            return DataError("automatic_data_date_start", required_msg)

        if not dd_update_period:
            return DataError("data_date_update_period", required_msg)

        if not any([dd_endless_update, dd_end]):
            return DataError(
                "automatic_data_date_end",
                _("Please provide specific date or set endless update."),
            )

        if all([dd_endless_update, dd_end]):
            return DataError(
                "automatic_data_date_end",
                _("Data date end cant be chosen when endless data date update is selected. Please choose one."),
            )

        if dd_start and dd_end and dd_end <= dd_start:
            return DataError(
                "automatic_data_date_end",
                _("Update end date cant be earlier than start date."),
            )

    def import_regions_from_harvester(self, regions):
        for f in self._meta.many_to_many:
            if f.name == "regions":
                f.save_form_data(self, regions)

    def is_added_by_harvester_with_id(self, source_id: int) -> bool:
        if self.is_imported and self.dataset.source.pk == source_id:
            return True
        return False

    @property
    def is_auto_data_date_allowed(self):
        return (
            self.type == RESOURCE_TYPE_API
            or (self.is_linked and self.type == RESOURCE_TYPE_FILE)
            or self.type == RESOURCE_TYPE_WEBSITE
        )

    def delete(self, using=None, soft=True, permanent=False, *args, **kwargs):
        if self.is_imported:
            permanent = True
            logger.debug(f"Permanent removing imported resource: {self.pk}")
        super().delete(using, soft=soft, permanent=permanent, *args, **kwargs)

        # delete tabular data index connected with permanently removed resource
        if self.is_permanently_removed:
            delete_es_resource_tabular_data_index.s(self.id).apply_async_on_commit()


class AggregatedDGAInfo(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resource = models.ForeignKey(Resource, on_delete=models.SET_NULL, null=True)
    # Statistics are currently only updated - they can be used in the future.
    views_count = models.PositiveIntegerField(default=0)
    downloads_count = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.id and AggregatedDGAInfo.objects.exists():
            raise ValidationError("There can be only one AggregatedDGAInfo instance")
        return super(AggregatedDGAInfo, self).save(*args, **kwargs)

    @property
    def main_dga_resource(self) -> Optional[Resource]:
        if self.resource and self.resource.is_published and not self.resource.is_removed:
            return self.resource
        else:
            return None

    @property
    def main_dga_dataset(self) -> Optional[Dataset]:
        if self.resource and self.resource.dataset.is_published and not self.resource.dataset.is_removed:
            return self.resource.dataset

        return None


class Chart(ExtendedModel):
    SIGNALS_MAP = {
        "updated": (update_chart_resource,),
        "published": (update_chart_resource,),
        "restored": (update_chart_resource,),
        "removed": (update_chart_resource,),
    }
    # https://docs.djangoproject.com/en/2.2/topics/db/models/#field-name-hiding-is-not-permitted
    # Czemu te pola nie mogły istnieć w tym modelu?
    slug = None
    uuid = None
    views_count = None

    name = models.CharField(max_length=200, verbose_name=_("name"), blank=True)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="charts")
    chart = JSONField()
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="chart_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="chart_modified",
    )

    tracker = FieldTracker()

    objects = ChartManager()
    trash = TrashManager()

    class Meta:
        default_manager_name = "objects"
        base_manager_name = "objects"
        db_table = "resource_chart"

    def __str__(self):
        return f"{self.id} - {self.name}" if self.name else f"{self.id}"

    @property
    def signals_map(self):
        return getattr(self, "SIGNALS_MAP", {})

    @property
    def is_private(self):
        return not self.is_default

    @property
    def organization(self):
        return self.resource.dataset.organization

    @classmethod
    def without_i18_fields(cls):
        """Hack which prevents from creation of translated fields (inherited from ExtendedModel)."""
        return True

    def can_be_updated_by(self, user):
        return (
            user.is_superuser
            or (self.is_default and user.is_editor_of_organization(self.resource.institution))
            or (not self.is_default and self.created_by_id == user.id)
        )

    def get_unique_slug(self):
        return f"chart-{self.id}"

    def is_visible_for(self, user):
        if user.is_authenticated:
            if any(
                [
                    user.is_superuser,
                    self.is_default,
                    (self.created_by_id == user.id),
                    user.is_editor_of_organization(self.organization),
                ]
            ):
                return True
        return True if self.is_default else False

    def update(self, user, data):
        self.name = data["name"]
        self.chart = data["chart"]
        self.is_default = data["is_default"]
        self.modified_by = user
        self.save()


class ResourceFile(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(
        verbose_name=_("File"),
        storage=storages.get_storage("resources"),
        upload_to="%Y%m%d",
        max_length=2000,
        blank=True,
        null=True,
    )
    format = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name=_("Format"),
        choices=settings.SUPPORTED_FORMATS_CHOICES_WITH_ARCHIVES,
    )
    compressed_file_format = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name=_("Compressed file format"),
        choices=settings.SUPPORTED_FORMATS_CHOICES_WITH_ARCHIVES,
    )
    compressed_file_mime_type = models.TextField(
        blank=True,
        null=True,
        editable=False,
        verbose_name=_("Compressed file mimetype"),
    )
    compressed_file_encoding = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Compressed file encoding"),
    )
    mimetype = models.TextField(blank=True, null=True, editable=False, verbose_name=_("File mimetype"))
    info = models.TextField(blank=True, null=True, editable=False, verbose_name=_("File info"))
    encoding = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("File encoding"),
    )
    is_main = models.BooleanField(default=False)
    openness_score = models.IntegerField(
        default=1,
        verbose_name=_("Openness score"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    tracker = FieldTracker()
    objects = ResourceFileManager()

    @property
    def file_size(self):
        try:
            return self.file.size
        except FileNotFoundError:
            return None

    @property
    def extension(self):
        return os.path.splitext(self.file.name)[1] if self.file else None

    @property
    def download_url(self):
        file_type = "file" if self.is_main else self.format
        return f"{settings.API_URL}/resources/{self.resource.ident}/{file_type}"

    @property
    def file_basename(self):
        return os.path.basename(self.file.name) if self.file else None

    def check_support(self):
        format_ = self.format if not self.compressed_file_format else self.compressed_file_format
        mimetype = self.mimetype if not self.compressed_file_mime_type else self.compressed_file_mime_type
        return check_support(format_, mimetype)

    def save_file(self, content: BinaryIO, filename: str) -> str:
        dt: datetime.date = self.resource.created.date() if self.resource.created else now().date()
        subdir: str = dt.isoformat().replace("-", "")
        dest_dir: str = os.path.join(self.file.storage.location, subdir)

        os.makedirs(dest_dir, exist_ok=True)

        file_path: str = os.path.join(dest_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content.read())
        return f"{subdir}/{filename}"

    def get_openness_score(self, format_: Optional[str] = None) -> OptionalOpennessScoreValue:
        format_ = format_ or self.compressed_file_format or self.format
        if format_ == "jsonstat":
            format_ = "json"
        if format_ is None:
            return 1
        return get_score(self.file, format_)

    @classmethod
    def without_i18_fields(cls):
        """Hack which prevents from creation of translated fields (inherited from ExtendedModel)."""
        return True

    def __str__(self):
        return self.file.name


class Supplement(BaseSupplement):
    file = models.FileField(
        verbose_name=_("file"),
        storage=storages.get_storage("resources"),
        upload_to="%Y%m%d",
        max_length=2000,
    )
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="supplements")
    objects = SupplementManager()


class ResourceTrash(Resource, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash")
        verbose_name_plural = _("Trash")


@receiver(pre_delete, sender=Chart)
def update_modified_by(sender, instance, *args, **kwargs):
    if "modified_by" in kwargs and isinstance(kwargs["modified_by"], User):
        instance.modified_by = kwargs.pop("modified_by")


@receiver(update_chart_resource, sender=Chart)
def update_chart_resource_handler(sender, instance, *args, **kwargs):
    Resource.objects.filter(id=instance.resource_id).update(
        has_chart=instance.resource.charts.filter(is_removed=False, is_permanently_removed=False, is_default=True).exists()
    )
    sender.log_debug(instance, "Reindex resource after chart updated", "update_chart_resource")
    search_signals.update_document_with_related.send(instance.resource._meta.model, instance.resource)


@receiver(pre_save, sender=Resource)
def preprocess_resource(sender, instance, *args, **kwargs):
    if instance.is_imported and not instance.data_date and instance.created:
        instance.data_date = instance.created.date()
    instance.has_chart = instance.charts.filter(is_removed=False, is_permanently_removed=False, is_default=True).exists()
    instance.type = instance.get_resource_type()


@receiver(post_save, sender=Resource)
def handle_resource_post_save(sender, instance, *args, **kwargs):
    # if dataset contains harvested resources, then dataset.verified is based on the resources'
    # data_date or created, otherwise it's based on the event date for the events described in OTD-1132
    if instance.dataset.is_imported:
        max_data_date_if_auto_true = (
            instance.dataset.resources.filter(status=Dataset.STATUS.published)
            .filter(is_auto_data_date=True)
            .only("data_date")
            .aggregate(max_data_date=Max("data_date"))
            .get("max_data_date")
        )
        if max_data_date_if_auto_true:
            new_verified = date_at_midnight(max_data_date_if_auto_true)
        else:
            max_created = (
                instance.dataset.resources.filter(status=Dataset.STATUS.published)
                .only("created")
                .aggregate(created=Max("created"))
                .get("created")
            )
            new_verified = max_created
        if new_verified:
            instance.update_dataset_verified(verified=new_verified)
    else:
        if instance.state_published or instance.state_removed or instance.state_restored:
            instance.update_dataset_verified(verified=instance.modified)

    if instance.tracker.has_changed("dataset_id"):
        dataset_id = instance.tracker.previous("dataset_id")
        if dataset_id:
            # update related ES documents for previously set dataset, if any.
            update_with_related_task.s("datasets", "Dataset", dataset_id).apply_async_on_commit()


@receiver(post_save, sender=ResourceTrash)
def update_dataset_verified_after_restoring_from_trash(sender, instance: Resource, *args, **kwargs):
    if instance.state_restored and not instance.dataset.is_imported:
        instance.update_dataset_verified(verified=instance.modified)


@receiver(revalidate_resource, sender=Resource)
def process_resource(sender, instance, *args, **kwargs):
    logger.debug("Running process_resource signal")
    sender.log_debug(instance, "Processing resource", "pre_save")
    is_auto_data_date_changed = instance.tracker.has_changed("is_auto_data_date")
    auto_data_date_fields = [
        "is_auto_data_date",
        "automatic_data_date_start",
        "data_date_update_period",
        "automatic_data_date_end",
        "endless_data_date_update",
    ]
    auto_data_date_fields_changed = any([instance.tracker.has_changed(f) for f in auto_data_date_fields])
    schedule_auto_data_date_update = instance.is_auto_data_date and (instance.state_restored or auto_data_date_fields_changed)
    cancel_auto_data_date_update = is_auto_data_date_changed and not instance.is_auto_data_date
    if schedule_auto_data_date_update:
        instance.schedule_data_date_update()
    elif cancel_auto_data_date_update:
        instance.cancel_data_date_update()
    if instance.is_link_updated:
        entrypoint_process_resource_validation_task.s(
            instance.id,
            update_file_archive=True,
            forced_file_changed=instance.has_forced_file_changed,
        ).apply_async_on_commit()

    elif instance.state_restored:
        entrypoint_process_resource_file_validation_task.s(
            instance._main_file.pk, update_file_archive=True
        ).apply_async_on_commit()
    elif instance.tracker.has_changed("dataset_id") and instance.tracker.previous("dataset_id") is not None:
        instance.dataset.archive_files()
        previous_ds = instance.tracker.previous("dataset_id")
        Dataset.objects.get(pk=previous_ds).archive_files()


@receiver(update_dataset_file_archive, sender=Resource)
def update_dataset_archive(sender, instance, *args, **kwargs):
    """
    Signal is fired, when resource has been deleted.
    Updates dataset archives when resource has been deleted.
    """
    logger.info("Running update_dataset_archive signal")
    instance.dataset.archive_files()


def update_dataset_watcher(sender, instance, *args, state=None, **kwargs):
    def inner(dataset_id, state):
        sender.log_debug(
            instance,
            f"{sender._meta.object_name} {state}",
            f"notify_{state}",
            state,
        )
        update_model_watcher_task.s(
            instance.dataset._meta.app_label,
            instance.dataset._meta.object_name,
            dataset_id,
            obj_state=state,
        ).apply_async_on_commit()

    if instance.tracker.has_changed("dataset_id"):
        inner(instance.tracker.previous("dataset_id"), "m2m_removed")
        inner(instance.dataset_id, "m2m_added")
    else:
        inner(instance.dataset_id, f"m2m_{state}")


@receiver(cancel_data_date_update, sender=Resource)
def cancel_data_date_update_schedule(sender, instance, *args, **kwargs):
    instance.cancel_data_date_update()


@receiver(post_save, sender=ResourceFile)
def process_created_file(sender, instance, created, *args, **kwargs):
    if instance.file and instance.is_main and created and instance.resource.is_published:
        entrypoint_process_resource_file_validation_task.s(instance.id, update_file_archive=True).apply_async_on_commit()


@receiver(core_signals.notify_removed, sender=Resource)
def remove_regions(sender, instance, *args, **kwargs):
    bulk_delete_documents_task.s("regions", "Region", instance.regions_to_conceal).apply_async_on_commit()


@receiver(core_signals.notify_restored, sender=Resource)
@receiver(core_signals.notify_published, sender=Resource)
def restore_regions(sender, instance, *args, **kwargs):
    update_related_task.s("regions", "Region", instance.regions_to_publish).apply_async_on_commit()


core_signals.notify_published.connect(update_watcher, sender=Resource)
core_signals.notify_restored.connect(update_watcher, sender=Resource)
core_signals.notify_updated.connect(update_watcher, sender=Resource)
core_signals.notify_removed.connect(update_watcher, sender=Resource)

core_signals.notify_published.connect(update_dataset_watcher, sender=Resource)
core_signals.notify_restored.connect(update_dataset_watcher, sender=Resource)
core_signals.notify_updated.connect(update_dataset_watcher, sender=Resource)
core_signals.notify_removed.connect(update_dataset_watcher, sender=Resource)

core_signals.notify_published.connect(update_watcher, sender=ResourceTrash)
core_signals.notify_restored.connect(update_watcher, sender=ResourceTrash)
core_signals.notify_updated.connect(update_watcher, sender=ResourceTrash)
core_signals.notify_removed.connect(update_watcher, sender=ResourceTrash)

core_signals.notify_published.connect(update_dataset_watcher, sender=ResourceTrash)
core_signals.notify_restored.connect(update_dataset_watcher, sender=ResourceTrash)
core_signals.notify_updated.connect(update_dataset_watcher, sender=ResourceTrash)
core_signals.notify_removed.connect(update_dataset_watcher, sender=ResourceTrash)
