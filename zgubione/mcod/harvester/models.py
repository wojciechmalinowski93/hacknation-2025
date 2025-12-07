import logging
import os
from collections import defaultdict
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests
import sentry_sdk
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured, MultipleObjectsReturned, ValidationError
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import validate_email
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from marshmallow import ValidationError as SchemaValidationError
from model_utils import FieldTracker
from model_utils.fields import AutoCreatedField

from mcod import settings
from mcod.categories.models import Category
from mcod.core import choices
from mcod.core.db.managers import TrashManager
from mcod.core.db.mixins import AdminMixin
from mcod.core.db.models import LogMixin, TimeStampedModel, TrashModelBase
from mcod.core.models import SoftDeletableModel
from mcod.harvester.ckan_utils import (
    CKANPartialImportError,
    format_dataset_hvd_conflict_error_details,
    format_dataset_in_trash_error_details,
    format_dataset_org_hvd_ec_conflict_error_details,
    format_invalid_license_error_details,
    format_not_dga_institution_type_error_details,
    format_org_already_has_dga_resource,
    format_org_has_more_than_one_dga_resource,
    format_organization_in_trash_error_details,
    format_res_dga_other_metadata_conflict_error_details,
    format_res_dga_url_bad_columns_error_details,
    format_res_dga_url_no_field_error_details,
    format_res_dga_url_not_accessible_error_details,
    format_res_dga_url_remote_file_extension_error_details,
    format_res_hvd_conflict_error_details,
    format_res_org_hvd_ec_conflict_error_details,
    format_too_many_dga_resources_for_organization,
)
from mcod.harvester.exceptions import CKANPartialValidationException
from mcod.harvester.managers import DataSourceManager
from mcod.harvester.utils import make_request, retrieve_to_file
from mcod.lib.exceptions import NoResponseException
from mcod.lib.metadata_validators import (
    validate_conflicting_high_value_data_flags,
    validate_high_value_data_from_ec_list_organization,
)
from mcod.lib.model_sanitization import SanitizedCharField, SanitizedTextField
from mcod.organizations.models import Organization
from mcod.resources.dga_utils import (
    get_dga_resource_for_institution,
    get_remote_extension_if_correct_dga_content_type,
    request_remote_dga,
    validate_contains_protected_data_with_other_metadata,
    validate_dga_file_columns,
    validate_institution_type_for_contains_protected_data,
)

logger = logging.getLogger("mcod")

ItemData = Dict[str, Any]

OLD_CATEGORY_TITLE_2_DCAT_CATEGORY_CODE = {
    "Rolnictwo": "AGRI",
    "Biznes i Gospodarka": "ECON",
    "Budżet i Finanse Publiczne": "ECON",
    "Kultura": "EDUC",
    "Nauka i Oświata": "EDUC",
    "Sport i Turystyka": "EDUC",
    "Środowisko": "ENVI",
    "Administracja Publiczna": "GOVE",
    "Zdrowie": "HEAL",
    "Bezpieczeństwo": "JUST",
    "Praca i Pomoc Społeczna": "SOCI",
    "Społeczeństwo": "SOCI",
    "Regiony i miasta": "REGI",
}


def validate_emails_list(value):
    emails_list = [x.strip() for x in value.split(",") if x]
    if not emails_list:
        raise ValidationError(_("This field is required!"))
    for item in emails_list:
        validate_email(item)


FREQUENCY_CHOICES = (
    (1, _("every day")),
    (7, _("every week")),
    (30, _("every month")),
    (90, _("every quarter")),
)

STATUS_OK = "ok"
STATUS_OK_PARTIAL = "ok-partial"
STATUS_ERROR = "error"
IMPORT_STATUS_CHOICES = (
    (STATUS_OK, "OK"),
    (STATUS_OK_PARTIAL, _("OK - partial import")),
    (STATUS_ERROR, _("Error")),
)


class DataSource(AdminMixin, LogMixin, SoftDeletableModel, TimeStampedModel):
    """Model of data source."""

    INSTITUTION_TYPE_CHOICES = Organization.INSTITUTION_TYPE_CHOICES
    SOURCE_TYPE_CHOICES = choices.SOURCE_TYPE_CHOICES
    STATUS_CHOICES = (
        ("active", _("active")),
        ("inactive", _("inactive")),
    )
    name = SanitizedCharField(max_length=255, verbose_name=_("name"))
    description = SanitizedTextField(verbose_name=_("description"))
    frequency_in_days = models.PositiveIntegerField(choices=FREQUENCY_CHOICES, default=7, verbose_name=_("frequency"))
    status = models.CharField(max_length=8, verbose_name=_("status"), choices=STATUS_CHOICES)
    license_condition_db_or_copyrighted = models.TextField(blank=True, verbose_name=_("data use rules"))
    institution_type = models.CharField(
        max_length=9,
        blank=True,
        choices=INSTITUTION_TYPE_CHOICES,
        default=INSTITUTION_TYPE_CHOICES[2][0],
        verbose_name=_("Default type for newly created institutions"),
    )
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, verbose_name=_("source type"))
    emails = models.TextField(verbose_name=_("e-mail"), validators=[validate_emails_list])
    last_activation_date = models.DateTimeField(verbose_name=_("last activation date"), null=True, blank=True)
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        related_name="category_datasources",
        verbose_name=_("category"),
        blank=True,
        null=True,
        limit_choices_to=Q(code=""),
    )

    categories = models.ManyToManyField(
        "categories.Category",
        db_table="data_source_category",
        verbose_name=_("Categories"),
        related_name="data_sources",
        related_query_name="data_source",
        blank=True,
        limit_choices_to=~Q(code=""),
    )

    created = AutoCreatedField(_("creation date"))
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.DO_NOTHING,
        related_name="created_datasources",
        verbose_name=_("created by"),
    )
    modified_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("modified by"),
        related_name="modified_datasources",
    )
    last_import_status = models.CharField(
        max_length=50,
        verbose_name=_("last import status"),
        choices=IMPORT_STATUS_CHOICES,
        blank=True,
    )
    last_import_timestamp = models.DateTimeField(verbose_name=_("last import timestamp"), null=True, blank=True)

    # CKAN related fields.
    portal_url = models.URLField(verbose_name=_("portal url"), blank=True)
    api_url = models.URLField(verbose_name=_("api url"), blank=True)

    # XML related fields.
    xml_url = models.URLField(verbose_name=_("XML url"), blank=True)
    source_hash = models.CharField(max_length=32, verbose_name=_("source hash"), blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="organization_datasources",
        verbose_name=_("Institution"),
        null=True,
        blank=True,
    )

    sparql_query = models.TextField(blank=True, null=True, verbose_name=_("Sparql query"))

    tracker = FieldTracker()
    objects = DataSourceManager()
    trash = TrashManager()

    class Meta:
        default_manager_name = "raw"
        verbose_name = _("data source")
        verbose_name_plural = _("data sources")

    def __str__(self):
        return self.name

    @property
    def categories_list_as_html(self):
        categories = self.categories.all()
        return mark_safe("<br>".join(category.title for category in categories)) if categories else "-"

    @cached_property
    def category_model(self):
        return apps.get_model("categories.Category")

    @cached_property
    def dataset_model(self):
        return apps.get_model("datasets.Dataset")

    @cached_property
    def organization_model(self):
        return apps.get_model("organizations.Organization")

    @cached_property
    def resource_model(self):
        return apps.get_model("resources.Resource")

    @cached_property
    def tag_model(self):
        return apps.get_model("tags.Tag")

    @cached_property
    def user_model(self):
        return apps.get_model("users.User")

    @cached_property
    def import_settings(self):
        try:
            return settings.HARVESTER_IMPORTERS[self.source_type]
        except KeyError:
            raise ImproperlyConfigured(f"settings.HARVESTER_SETTINGS should contain {self.source_type} key!")

    @cached_property
    def import_user(self):
        import_user_email = "automatic_import@mc.gov.pl"
        return self.user_model.objects.filter(email=import_user_email).first() or self.user_model.objects._create_user(
            email=import_user_email
        )

    @cached_property
    def import_func_kwargs(self):
        if self.is_xml:
            return {"url": self.xml_url}
        elif self.is_dcat:
            return {"api_url": self.api_url, "query": self.sparql_query}
        params = self.import_settings.get("API_URL_PARAMS")
        return {"url": f"{self.api_url}?{urlencode(params)}" if params else self.api_url}

    @cached_property
    def url(self):
        if self.is_xml:
            return self.xml_url
        elif self.is_ckan:
            return self.portal_url
        elif self.is_dcat:
            return self.api_url

    @property
    def emails_list(self):
        return list(set(filter(None, [x.strip() for x in self.emails.split(",")])))

    @property
    def is_ckan(self):
        return self.source_type == "ckan"

    @property
    def is_xml(self):
        return self.source_type == "xml"

    @property
    def is_dcat(self):
        return self.source_type == "dcat"

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def next_import_date(self):
        if self.last_import_timestamp:
            return (self.last_import_timestamp + relativedelta(days=self.frequency_in_days)).replace(
                hour=3, minute=0, second=0, microsecond=0
            )

    @property
    def title(self):
        return self.name

    @property
    def update_frequency(self):
        return next(freq[1] for freq in FREQUENCY_CHOICES if freq[0] == self.frequency_in_days)

    def _validate_ckan_type(self):
        errors = {}
        required_msg = _("This field is required.")
        if not self.portal_url:
            errors.update({"portal_url": required_msg})
        if not self.api_url:
            errors.update({"api_url": required_msg})
        if self.api_url:
            msg = _("Inaccessible API!")
            try:
                response = make_request(self.api_url)
                if not response.ok or "application/json" not in response.headers.get("Content-Type", ""):
                    errors.update({"api_url": msg})
            except Exception as exc:
                logger.debug(exc)
                errors.update({"api_url": msg})
        if errors:
            raise ValidationError(errors)

    def _validate_xml_type(self):
        required_msg = _("This field is required.")
        if not self.organization:
            raise ValidationError({"organization": required_msg})
        if self.import_settings.get("ONE_DATASOURCE_PER_ORGANIZATION", False):
            organization_datasources = DataSource.objects.filter(organization=self.organization)
            if self.id:
                organization_datasources = organization_datasources.exclude(id=self.id)
            if organization_datasources.exists():
                raise ValidationError({"organization": _("Data source for this institution already exists!")})
        if not self.xml_url:
            raise ValidationError({"xml_url": required_msg})

    def _validate_dcat_type(self):
        required_msg = _("This field is required.")
        if not self.organization:
            raise ValidationError({"organization": required_msg})

    def clean(self):
        if self.is_ckan:
            self._validate_ckan_type()
        elif self.is_xml:
            self._validate_xml_type()
        elif self.is_dcat:
            self._validate_dcat_type()

    def import_needed(self):
        if not self.last_import_timestamp:
            return True
        return self.next_import_date <= timezone.now()

    def get_api_image_url(self, image_url):
        return f"{self.api_url}/uploads/group/{image_url}"

    def delete_stale_datasets(self, data):
        ext_idents = [x[0] for x in data]
        ext_idents.append("")
        objs = self.dataset_model.objects.filter(source=self).exclude(ext_ident__in=ext_idents)
        count = objs.count()
        for obj in objs:
            obj.delete(permanent=True)
        return count

    def delete_stale_resources(self, data):
        count = 0
        for item in data:
            ext_idents = [x for x in item[1]]
            ext_idents.append("")
            objs = self.resource_model.objects.filter(dataset__source=self, dataset__ext_ident=item[0]).exclude(
                ext_ident__in=ext_idents
            )
            count += objs.count()
            for obj in objs:
                obj.delete(permanent=True)
        return count

    def update_from_items(self, data):
        ds_imported = 0
        ds_created = 0
        ds_updated = 0
        r_imported = 0
        r_created = 0
        r_updated = 0
        for item in data:
            category = self._get_dataset_category(item)
            categories = self._get_dataset_categories(category, item)

            license = self._get_license(item)
            license_condition_db_or_copyrighted = self._get_license_condition_db_or_copyrighted(item)
            license_chosen = self._get_license_chosen(item)

            organization = self._get_organization(item)
            tags = self._prepare_tags(item)
            resources_data = item.pop("resources")
            item.update(
                {
                    "category": category,
                    "source": self,
                    "organization": organization,
                    "license": license,
                    "license_condition_db_or_copyrighted": license_condition_db_or_copyrighted,
                    "license_chosen": license_chosen,
                }
            )
            dataset, created = self._update_or_create_dataset(item)
            ds_imported += 1
            if dataset:
                if created:
                    ds_created += 1
                else:
                    ds_updated += 1

                dataset.tags.set(tags)
                dataset.categories.set(categories)

                for rd in resources_data:
                    supplements = rd.pop("supplements", [])
                    resource, created = self._update_or_create_resource(dataset, rd)
                    r_imported += 1
                    if resource:
                        if created:
                            r_created += 1
                        else:
                            r_updated += 1
                        self._update_or_create_supplements(resource, supplements)
        return ds_imported, ds_created, ds_updated, r_imported, r_created, r_updated

    def _update_or_create_dataset(self, data):
        data.update({"created_by": self.import_user, "status": data.get("status", "published")})
        modified = data.pop("modified", None)
        modified = modified or data.get("created")
        int_ident = data.pop("int_ident", None)
        supplements = data.pop("supplements", [])

        if int_ident:
            created = False
            obj = self.dataset_model.raw.filter(id=int_ident, organization=data["organization"]).first()
            if obj:
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.save()
        else:
            obj, created = self.dataset_model.raw.update_or_create(
                ext_ident=data["ext_ident"], source=data["source"], defaults=data
            )
        if obj and modified:  # TODO: find a better way to save modification date with value from data.
            self.dataset_model.raw.filter(id=obj.id).update(modified=modified)
        self._update_or_create_supplements(obj, supplements)
        return obj, created

    def _get_supplement_data(self, idx, data):
        _file = SimpleUploadedFile(data["filename"], data["content"].read()) if "filename" in data and "content" in data else None
        return {
            "file": _file,
            "name_en": data["name_en"],
            "language": data["language"],
            "order": idx,
            "created_by": self.import_user,
            "modified_by": self.import_user,
        }

    def _update_or_create_supplements(self, obj, data):
        for idx, item in enumerate(data):
            defaults = self._get_supplement_data(idx, item)
            defaults["modified"] = obj.modified
            kwargs = {
                obj._meta.model_name: obj,  # obj._meta.model_name is 'dataset' or 'resource'.
                "name": item["name_pl"],
            }
            obj.supplements.model.objects.update_or_create(**kwargs, defaults=defaults)

        for supplement in obj.supplements.exclude(name_pl__in=[x["name_pl"] for x in data]):
            supplement.delete()

    def _get_dataset_category(self, data):
        if self.is_ckan:
            return self.category
        elif self.is_xml and self.xsd_schema_version < settings.XML_VERSION_MULTIPLE_CATEGORIES:
            category_ids_list = data.pop("categories", None)
            if category_ids_list:
                category_model = apps.get_model("categories.Category")
                return category_model.objects.filter(id__in=category_ids_list[:1]).first()

    def _get_dataset_categories(self, category, data):
        if self.is_ckan:
            return self.categories.all()
        elif self.is_xml:
            if self.xsd_schema_version < settings.XML_VERSION_MULTIPLE_CATEGORIES:
                old_category = category
                new_category = None
                if old_category:
                    code = OLD_CATEGORY_TITLE_2_DCAT_CATEGORY_CODE.get(old_category.title_pl)
                    new_category = Category.objects.filter(code=code).first()
                if new_category:
                    return [new_category]
            else:
                return self._get_dcat_categories(data)
        elif self.is_dcat:
            return self._get_dcat_categories(data)
        return []

    def _get_dcat_categories(self, data):
        category_codes_list = data.pop("categories", None)
        if category_codes_list:
            return Category.objects.filter(code__in=category_codes_list)

    def _get_license(self, data):
        if self.is_xml:
            name = data.pop("license", None)
            if name:
                license_model = apps.get_model("licenses.License")
                return license_model.objects.filter(name=name).first()

    def _get_license_condition_db_or_copyrighted(self, data):
        if self.is_ckan:
            return self.license_condition_db_or_copyrighted
        elif self.is_xml:
            return data.get("license_condition_db_or_copyrighted")

    def _get_license_chosen(self, data):
        if self.is_ckan:
            dataset_model = apps.get_model("datasets.Dataset")
            license_name_to_code = dict((row[1], row[0]) for row in dataset_model.LICENSES)
            license_name = settings.CKAN_LICENSES_WHITELIST.get(data.pop("license_id", None))
            license_code = license_name_to_code.get(license_name)
            return license_code
        elif self.is_xml:
            return data.get("license_chosen")
        elif self.is_dcat:
            dataset_model = apps.get_model("datasets.Dataset")
            license_name_to_code = dict((row[1], row[0]) for row in dataset_model.LICENSES)
            license_code = license_name_to_code.get(data.get("license_chosen"))
            return license_code

    @staticmethod
    def _get_file_from_url(url):
        try:
            filename, headers = retrieve_to_file(url)
            return File(open(filename, "rb"))
        except Exception as exc:
            logger.debug(exc)

    def _get_organization(self, data):
        if self.is_xml or self.is_dcat:
            return self.organization
        elif self.is_ckan:
            data = data.pop("organization", None)
            if data:
                obj = self.organization_model.raw.filter(title=data["title"]).first()
                if obj:
                    return obj
                image_name = data.pop("image_name")
                obj = self.organization_model.raw.create(
                    created_by=self.import_user,
                    institution_type=self.institution_type,
                    **data,
                )
                if image_name:
                    if image_name.startswith("http"):  # sometimes it's' full path to image (with domain name).
                        image_url = image_name
                        image_name = os.path.basename(image_url)
                    else:
                        media_url_template = self.import_settings.get("MEDIA_URL_TEMPLATE")
                        image_url = media_url_template.format(self.portal_url, image_name)
                    image = self._get_file_from_url(image_url)
                    if image:
                        obj.image.save(image_name, image)
                return obj

    def _update_or_create_resource(self, dataset, data):
        if dataset.status == self.dataset_model.STATUS.draft:  # TODO: move to SIGNAL_MAP in Dataset?
            data["status"] = self.resource_model.STATUS.draft
        data["created_by"] = self.import_user
        if "format" in data:
            data["format"] = data.get("format") or None
        modified = data.pop("modified", None)
        modified = modified or data.get("created")
        int_ident = data.pop("int_ident", None)
        special_signs = data.pop("special_signs", [])
        regions = data.pop("regions", [])
        if int_ident:
            created = False
            obj = self.resource_model.raw.filter(dataset=dataset, id=int_ident).first()
            if obj:
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.save()
        else:
            obj, created = self.resource_model.raw.update_or_create(dataset=dataset, ext_ident=data["ext_ident"], defaults=data)
        if obj and modified:  # TODO: find a better way to save modification date with value from data.
            self.resource_model.raw.filter(id=obj.id).update(modified=modified)
        obj.import_regions_from_harvester(regions)
        new_special_signs = obj.special_signs.model.objects.filter(symbol__in=special_signs)

        revalidate = False
        if set(obj.special_signs.values_list("id")) != set(new_special_signs.values_list("id")):
            revalidate = True

        obj.special_signs.set(new_special_signs)

        if revalidate:
            obj.revalidate_tabular_data(apply_on_commit=True)

        return obj, created

    def _import_from(self, path):
        parts = path.split(".")
        module = ".".join(parts[:-1])
        m = __import__(module)
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m

    def _get_ext_idents(self, data):
        dataset_ext_ident = data["ext_ident"]
        resources_ext_idents = [x["ext_ident"] for x in data["resources"]]
        return dataset_ext_ident, resources_ext_idents

    def _prepare_tags(self, data):
        tags_data = data.pop("tags", [])
        tags_ids = []
        for tag_data in tags_data:
            name = tag_data.get("name")
            if not name:
                continue
            language = tag_data.pop("lang", "pl")
            defaults = {"created_by": self.import_user}
            tag, _ = self.tag_model.objects.get_or_create(name=name, language=language, defaults=defaults)
            tags_ids.append(tag.id)
        return self.tag_model.objects.filter(id__in=tags_ids)

    def _get_item_institution_type(self, item: ItemData) -> str:
        organization = self.organization_model.raw.filter(title=item["organization"]["title"]).first()
        return organization.institution_type if organization else self.institution_type

    @staticmethod
    def _ckan_validate_item_license_id(item: ItemData) -> None:
        item_id: str = item["ext_ident"]
        license_id: str = item.get("license_id")

        if license_id not in settings.CKAN_LICENSES_WHITELIST:
            error_data = {
                "item_id": item_id,
                "license_id": license_id,
            }
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.INVALID_LICENSE_ID,
                error_data=error_data,
            )

    def _ckan_validate_item_organization_not_in_trash(self, item: ItemData) -> None:
        item_id: str = item["ext_ident"]
        item_organization_title: str = item["organization"]["title"]

        organization = self.organization_model.raw.filter(title=item_organization_title).first()
        if organization and organization.is_removed:
            error_data = {
                "item_id": item_id,
                "organization_title": item_organization_title,
            }
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.ORGANIZATION_IN_TRASH,
                error_data=error_data,
            )

    def _ckan_validate_item_dataset_not_in_trash(self, item: ItemData) -> None:
        item_id: str = item["ext_ident"]

        dataset = self.dataset_model.raw.filter(ext_ident=item.get("ext_ident"), source=self).first()
        if dataset and dataset.is_removed:
            error_data = {"item_id": item_id}
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.DATASET_IN_TRASH,
                error_data=error_data,
            )

    def _ckan_validate_item_dataset_org_ec_conflict(self, item: ItemData) -> None:
        item_id: str = item["ext_ident"]
        has_hvd_ec: Optional[bool] = item.get("has_high_value_data_from_ec_list")

        institution_type = self._get_item_institution_type(item)
        try:
            validate_high_value_data_from_ec_list_organization(
                has_hvd_ec,
                institution_type,
            )
        except ValidationError:
            error_data = {"item_id": item_id}
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.DATASET_ORG_EC_CONFLICT,
                error_data=error_data,
            )

    @staticmethod
    def _ckan_validate_item_dataset_hvd_conflict(item: ItemData) -> None:
        item_id: str = item["ext_ident"]
        has_hvd: Optional[bool] = item.get("has_high_value_data")
        has_hvd_ec: Optional[bool] = item.get("has_high_value_data_from_ec_list")

        try:
            validate_conflicting_high_value_data_flags(has_hvd, has_hvd_ec)
        except ValidationError:
            error_data = {"item_id": item_id}
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.DATASET_HVD_CONFLICT,
                error_data=error_data,
            )

    def _ckan_validate_item_resources_org_ec_conflict(self, item: ItemData) -> None:
        item_id: str = item["ext_ident"]
        institution_type = self._get_item_institution_type(item)

        resources: List[Dict[str, Any]] = item.get("resources", [])
        rejected_resources_ids: List[str] = []
        for resource in resources:
            has_hvd_ec: Optional[bool] = resource.get("has_high_value_data_from_ec_list")
            try:
                validate_high_value_data_from_ec_list_organization(
                    has_hvd_ec,
                    institution_type,
                )
            except ValidationError:
                rejected_resources_ids.append(resource["ext_ident"])

        if rejected_resources_ids:
            error_data = {
                "item_id": item_id,
                "resources_ids": rejected_resources_ids,
            }
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.RES_ORG_EC_CONFLICT,
                error_data=error_data,
            )

    @staticmethod
    def _ckan_validate_item_resources_hvd_conflict(item: ItemData) -> None:
        item_id: str = item["ext_ident"]

        resources: List[Dict[str, Any]] = item.get("resources", [])
        rejected_resources_ids: List[str] = []
        for resource in resources:
            has_hvd: Optional[bool] = resource.get("has_high_value_data")
            has_hvd_ec: Optional[bool] = resource.get("has_high_value_data_from_ec_list")
            try:
                validate_conflicting_high_value_data_flags(has_hvd, has_hvd_ec)
            except ValidationError:
                rejected_resources_ids.append(resource["ext_ident"])

        if rejected_resources_ids:
            error_data = {
                "item_id": item_id,
                "resources_ids": rejected_resources_ids,
            }
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.RES_HVD_CONFLICT,
                error_data=error_data,
            )

    @staticmethod
    def _ckan_validate_item_resources_dga_other_metadata_conflict(item: ItemData) -> None:
        item_id: str = item["ext_ident"]

        resources: List[Dict[str, Any]] = item.get("resources", [])
        rejected_resources_ids: List[str] = []
        for resource in resources:
            contains_protected_data: bool = resource["contains_protected_data"]
            has_dynamic: Optional[bool] = resource.get("has_dynamic_data")
            has_research: Optional[bool] = resource.get("has_research_data")
            has_hvd: Optional[bool] = resource.get("has_high_value_data")
            has_hvd_ec: Optional[bool] = resource.get("has_high_value_data_from_ec_list")

            result_ok: bool = validate_contains_protected_data_with_other_metadata(
                contains_protected_data, has_dynamic, has_research, has_hvd, has_hvd_ec
            )
            if not result_ok:
                rejected_resources_ids.append(resource["ext_ident"])

        if rejected_resources_ids:
            error_data = {
                "item_id": item_id,
                "resources_ids": rejected_resources_ids,
            }
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.RES_DGA_OTHER_METADATA_CONFLICT,
                error_data=error_data,
            )

    @staticmethod
    def _get_ids_of_dga_resources_for_item(item: ItemData) -> List[str]:
        resources: List[Dict[str, Any]] = item.get("resources", [])
        dga_resources_ids: List[str] = [resource["ext_ident"] for resource in resources if resource["contains_protected_data"]]
        return dga_resources_ids

    def _ckan_validate_item_resources_dga_institution_type(self, item: ItemData) -> None:
        item_id: str = item["ext_ident"]
        institution_type: str = self._get_item_institution_type(item)

        # get ids list of resources marked as DGA
        dga_resources_ids: List[str] = self._get_ids_of_dga_resources_for_item(item)
        # validate if institution is allowed to have DGA resources (if any exists)
        if dga_resources_ids:
            is_valid_institution_type: bool = validate_institution_type_for_contains_protected_data(True, institution_type)

            if not is_valid_institution_type:
                error_data = {
                    "item_id": item_id,
                    "resources_ids": dga_resources_ids,
                }
                raise CKANPartialValidationException(
                    error_code=CKANPartialImportError.NOT_DGA_INSTITUTION_TYPE,
                    error_data=error_data,
                )

    @staticmethod
    def _ckan_validate_item_resources_dga_url(item: ItemData) -> None:
        item_id: str = item["ext_ident"]
        resources: List[Dict[str, Any]] = item.get("resources", [])
        dga_resources: List[Dict[str, Any]] = list(filter(lambda x: x["contains_protected_data"] is True, resources))
        rejected_resources_ids: List[str] = []

        # url field presence validation
        for dga_resource in dga_resources:
            url: Optional[str] = dga_resource.get("link")

            if url is None:
                rejected_resources_ids.append(dga_resource["ext_ident"])
                error_data = {
                    "item_id": item_id,
                    "resources_ids": rejected_resources_ids,
                }
                raise CKANPartialValidationException(
                    error_code=CKANPartialImportError.RES_DGA_URL_NO_FIELD,
                    error_data=error_data,
                )
            # url accessibility validation
            try:
                response = request_remote_dga(url)
            except requests.exceptions.RequestException:
                rejected_resources_ids.append(dga_resource["ext_ident"])
                error_data = {
                    "item_id": item_id,
                    "resources_ids": rejected_resources_ids,
                }
                raise CKANPartialValidationException(
                    error_code=CKANPartialImportError.RES_DGA_URL_NOT_ACCESSIBLE,
                    error_data=error_data,
                )

            result_ok: bool = response.status_code == 200
            if not result_ok:
                rejected_resources_ids.append(dga_resource["ext_ident"])
                error_data = {
                    "item_id": item_id,
                    "resources_ids": rejected_resources_ids,
                }
                raise CKANPartialValidationException(
                    error_code=CKANPartialImportError.RES_DGA_URL_NOT_ACCESSIBLE,
                    error_data=error_data,
                )

            # file format validation
            extension_for_remote: Optional[str] = get_remote_extension_if_correct_dga_content_type(response)
            if extension_for_remote is None:
                rejected_resources_ids.append(dga_resource["ext_ident"])
                error_data = {
                    "item_id": item_id,
                    "resources_ids": rejected_resources_ids,
                }
                raise CKANPartialValidationException(
                    error_code=CKANPartialImportError.RES_DGA_URL_BAD_REMOTE_FILE_EXTENSION,
                    error_data=error_data,
                )

            # DGA file columns validation
            file_data: BytesIO = BytesIO(response.content)
            result_ok: bool = validate_dga_file_columns(file_data, extension_for_remote)
            if not result_ok:
                rejected_resources_ids.append(dga_resource["ext_ident"])
                error_data = {
                    "item_id": item_id,
                    "resources_ids": rejected_resources_ids,
                }
                raise CKANPartialValidationException(
                    error_code=CKANPartialImportError.RES_DGA_URL_BAD_COLUMNS,
                    error_data=error_data,
                )

    @staticmethod
    def _ckan_validate_item_org_single_dga_json(
        item: ItemData,
        dga_resources_per_organization: Dict[str, int],
    ) -> None:
        """
        Validates whether an item has any DGA resources and checks if the total number
        of DGA resources for the corresponding organization in the entire JSON file is not greater than one.
        This function raises a validation exception if an item is associated with an organization that has more than
        one DGA resource across all items.
        """
        item_dga_resources: List[Dict[str, Any]] = [
            {"ext_ident": resource["ext_ident"], "title": resource["title"]}
            for resource in item.get("resources", [])
            if resource["contains_protected_data"]
        ]

        if item_dga_resources:
            institution_title: str = item["organization"]["title"]
            dga_resources_for_organization: int = dga_resources_per_organization[institution_title]

            if dga_resources_for_organization > 1:
                error_data = {
                    "resources": item_dga_resources,
                    "item_id": item["ext_ident"],
                }
                raise CKANPartialValidationException(
                    error_code=CKANPartialImportError.TOO_MANY_DGA_RESOURCES_FOR_ORGANIZATION,
                    error_data=error_data,
                )

    def _ckan_validate_item_org_does_not_have_dga_resource(
        self,
        item: ItemData,
    ) -> None:
        """
        Validates whether an item's Organization does not have any DGA Resources in database.
        This function raises a validation exception if an item's Organization already has existing
        DGA Resource in database which is not created by the same DataSource.

        Note: We allow the existence of a DGA Resource for the Organization, which was created
        by the same DataSource, due to the possibility of replacing Resources that are flagged as "contains_protected_data".
        A separate validation function (_ckan_validate_item_org_single_dga_json)
        is responsible for validating the number of resources marked as DGA
        for an Organization in the entire JSON file.
        """
        # Check if Organization exists
        org = Organization.objects.filter(title=item["organization"]["title"]).first()
        if org is None:
            return

        # Get DGA Resource for existing Organization
        item_id: str = item["ext_ident"]
        resource_model = apps.get_model("resources", "Resource")
        try:
            org_dga_resource: Optional[resource_model] = get_dga_resource_for_institution(org.pk)
        except MultipleObjectsReturned as e:
            error_data = {"item_id": item_id, "error_msg": str(e)}
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.ORGANIZATION_HAS_MORE_THAN_ONE_DGA_RES,
                error_data=error_data,
            )

        # If Organization's DGA Resource exists and is not created by this DataSource, then raise exception
        if org_dga_resource and not org_dga_resource.is_added_by_harvester_with_id(self.pk):
            item_id: str = item["ext_ident"]
            item_dga_resources_ids: List[str] = self._get_ids_of_dga_resources_for_item(item)
            error_data = {
                "item_id": item_id,
                "item_dga_resources_ids": item_dga_resources_ids,
                "existing_dga_resource_id": org_dga_resource.pk,
                "existing_dga_resource_title": org_dga_resource.title,
            }
            raise CKANPartialValidationException(
                error_code=CKANPartialImportError.ORGANIZATION_ALREADY_HAS_DGA_RESOURCE,
                error_data=error_data,
            )

    @staticmethod
    def _get_error_description_formatters() -> Dict[CKANPartialImportError, Callable[[List[Dict[str, Any]]], str]]:
        """
        Initializes and returns a mapping of validation error codes to their
        corresponding error description formatting functions.

        Each function generates a detailed error description for all items
        (datasets) that encountered the specific error type during the
        CKAN partial validation process.

        These descriptions are later used to provide comprehensive error
        details in HTML format.

        Returns:
            dict: A dictionary mapping error codes (CKANPartialImportError) to
                  their respective error description formatting functions.
        """
        error_description_functions = {
            CKANPartialImportError.INVALID_LICENSE_ID: format_invalid_license_error_details,
            CKANPartialImportError.ORGANIZATION_IN_TRASH: format_organization_in_trash_error_details,
            CKANPartialImportError.DATASET_IN_TRASH: format_dataset_in_trash_error_details,
            # High Value Data (HVD) error description formatters
            CKANPartialImportError.DATASET_ORG_EC_CONFLICT: format_dataset_org_hvd_ec_conflict_error_details,
            CKANPartialImportError.DATASET_HVD_CONFLICT: format_dataset_hvd_conflict_error_details,
            CKANPartialImportError.RES_ORG_EC_CONFLICT: format_res_org_hvd_ec_conflict_error_details,
            CKANPartialImportError.RES_HVD_CONFLICT: format_res_hvd_conflict_error_details,
            # Contains Protected Data (DGA) error description formatters
            CKANPartialImportError.RES_DGA_OTHER_METADATA_CONFLICT: format_res_dga_other_metadata_conflict_error_details,
            CKANPartialImportError.NOT_DGA_INSTITUTION_TYPE: format_not_dga_institution_type_error_details,
            CKANPartialImportError.RES_DGA_URL_NO_FIELD: format_res_dga_url_no_field_error_details,
            CKANPartialImportError.RES_DGA_URL_NOT_ACCESSIBLE: format_res_dga_url_not_accessible_error_details,
            CKANPartialImportError.RES_DGA_URL_BAD_REMOTE_FILE_EXTENSION: format_res_dga_url_remote_file_extension_error_details,
            CKANPartialImportError.RES_DGA_URL_BAD_COLUMNS: format_res_dga_url_bad_columns_error_details,
            CKANPartialImportError.TOO_MANY_DGA_RESOURCES_FOR_ORGANIZATION: format_too_many_dga_resources_for_organization,  # noqa: E501
            CKANPartialImportError.ORGANIZATION_ALREADY_HAS_DGA_RESOURCE: format_org_already_has_dga_resource,
            CKANPartialImportError.ORGANIZATION_HAS_MORE_THAN_ONE_DGA_RES: format_org_has_more_than_one_dga_resource,
        }
        return error_description_functions

    def _get_number_of_dga_resources_per_organization(self, items: List[ItemData]) -> Dict[str, int]:
        """
        The function returns information about numbers of dga resources for all organizations mentioned in items.

        Returns:
        Dict[str, int]: A dictionary where the keys are organization titles (str) and the values are
                        the accumulated count of DGA resources (int) for each organization.
        """
        dga_resources_per_organization: Dict[str, int] = {}

        for item in items:
            dga_resources_ids: List[str] = self._get_ids_of_dga_resources_for_item(item)
            count_dga_resources: int = len(dga_resources_ids)

            organization_title: str = item["organization"]["title"]
            dga_resources_per_organization[organization_title] = (
                dga_resources_per_organization.get(organization_title, 0) + count_dga_resources
            )

        return dga_resources_per_organization

    def _validate_ckan_item(
        self,
        item: ItemData,
        dga_per_organization: Dict[str, int],
    ) -> None:
        self._ckan_validate_item_license_id(item)
        self._ckan_validate_item_organization_not_in_trash(item)
        self._ckan_validate_item_dataset_not_in_trash(item)
        # HVD validations
        self._ckan_validate_item_dataset_org_ec_conflict(item)
        self._ckan_validate_item_dataset_hvd_conflict(item)
        self._ckan_validate_item_resources_org_ec_conflict(item)
        self._ckan_validate_item_resources_hvd_conflict(item)
        # DGA validations
        self._ckan_validate_item_resources_dga_institution_type(item)
        self._ckan_validate_item_resources_dga_other_metadata_conflict(item)
        self._ckan_validate_item_org_single_dga_json(item, dga_per_organization)
        self._ckan_validate_item_org_does_not_have_dga_resource(item)
        self._ckan_validate_item_resources_dga_url(item)

    def _ckan_items_partial_validation(self, items: List[ItemData]) -> Tuple[List[ItemData], int, str]:
        """
        Performs CKAN partial validation on a list of items.

        Checks each item against various criteria such as license ID validity,
        organization and dataset are not in trash, high-value data (HVD)
        conflicts, etc.

        Args:
            items: List of items to validate.

        Returns:
            A tuple containing:
            - List of accepted items.
            - Number of rejected items.
            - Aggregated error description as HTML string which be displayed in
              Admin Panel DataSourceImport details.
        """
        # Process and validate each item in the input list.
        # Items that pass all validations are added to the accepted_items list.
        # For items that fail validation, the specific error and item data
        # (necessary for error description formatter) are recorded in items_errors.
        accepted_items: List[ItemData] = []
        items_errors: Dict[CKANPartialImportError, List[ItemData]] = defaultdict(list)

        # some validation must be done regarding all items
        number_of_dga_resources_per_organization: Dict[str, int] = self._get_number_of_dga_resources_per_organization(items)

        for item in items:
            try:
                self._validate_ckan_item(
                    item,
                    dga_per_organization=number_of_dga_resources_per_organization,
                )
            except CKANPartialValidationException as exc:
                items_errors[exc.error_code].append(exc.error_data)
            else:
                accepted_items.append(item)

        error_description_functions = self._get_error_description_formatters()
        # Generate error descriptions for each encountered error type.
        # Iterate through the error_description_functions dictionary:
        #   - For each error code that has associated error data.
        #   - Call the corresponding formatting function with the error data.
        #   - Append the resulting error description to the list.
        # This process creates a comprehensive list of all error descriptions.
        # TODO: Are they XSS safe?
        error_descriptions: List[str] = []
        for code, get_error_desc in error_description_functions.items():
            items_error_data: List[ItemData] = items_errors[code]
            if items_error_data:
                error_desc: str = get_error_desc(items_error_data)
                error_descriptions.append(error_desc)

        # Combine all error descriptions into a single string and calculate
        # the total number of rejected items.
        error_desc: str = "<br>".join(str(error) for error in error_descriptions)
        rejected_items_count: int = sum([len(errors) for errors in items_errors.values()])

        return accepted_items, rejected_items_count, error_desc

    def import_data(self):  # noqa: C901
        logger.info("Starting import_data method.")
        if not self.is_active:
            logger.debug(f'Cannot import data. Data source "{self}" is not active!')
            return
        data = None
        error_desc = ""
        start = timezone.now()
        import_func_path = self.import_settings.get("IMPORT_FUNC", "mcod.harvester.utils.fetch_data")
        import_func = self._import_from(import_func_path)
        schema_path = self.import_settings.get("SCHEMA")
        schema_class = self._import_from(schema_path)
        try:
            data = import_func(**self.import_func_kwargs)
        except NoResponseException as exc:
            sentry_sdk.capture_exception(exc)
            error_desc = exc
        except Exception as exc:
            error_desc = exc
        try:
            schema = schema_class(many=True)
            schema.context["organization"] = self.organization
            if self.is_ckan:
                schema.context["new_institution_type"] = self.institution_type
            if self.is_xml:
                # to provide data for validation in mcod/harvester/serializers.py
                schema.context["loaded_data"] = data
                schema.context["source_id"] = self.pk
            items = schema.load(data) if data else []
        except SchemaValidationError as err:
            items = []
            error_desc = err.messages
            if isinstance(error_desc, dict):
                error_desc = repr(error_desc)

        ds_rejected = 0
        if items and self.is_ckan:
            items, ds_rejected, error_desc = self._ckan_items_partial_validation(items)

        dsi = DataSourceImport.objects.create(
            datasource=self,
            start=start,
            error_desc=error_desc,
            datasets_rejected_count=ds_rejected,
        )
        self.last_import_timestamp = dsi.start
        self.save()
        self.xsd_schema_version = getattr(data, "xsd_schema_version", None)

        imported_ext_idents = [self._get_ext_idents(item) for item in items]

        ds_imported, ds_created, ds_updated, r_imported, r_created, r_updated = self.update_from_items(items)

        r_deleted = 0
        ds_deleted = 0
        if not dsi.is_failed:
            r_deleted = self.delete_stale_resources(imported_ext_idents)
            ds_deleted = self.delete_stale_datasets(imported_ext_idents)
        dsi.datasets_count = ds_imported
        dsi.datasets_created_count = ds_created
        dsi.datasets_updated_count = ds_updated
        dsi.datasets_deleted_count = ds_deleted
        dsi.datasets_rejected_count = ds_rejected
        dsi.resources_count = r_imported
        dsi.resources_created_count = r_created
        dsi.resources_updated_count = r_updated
        dsi.resources_deleted_count = r_deleted
        dsi.end = timezone.now()
        dsi.save()
        self.last_import_status = dsi.status
        self.save()


class DataSourceTrash(DataSource, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash (Data Sources)")
        verbose_name_plural = _("Trash (Data Sources)")


class DataSourceImport(TimeStampedModel):
    """Model of data source import."""

    datasource = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="imports",
        verbose_name=_("data source"),
    )
    start = models.DateTimeField(verbose_name=_("start"))
    end = models.DateTimeField(verbose_name=_("end"), null=True, blank=True)
    status = models.CharField(
        max_length=50,
        verbose_name=_("status"),
        choices=IMPORT_STATUS_CHOICES,
        blank=True,
    )
    error_desc = models.TextField(verbose_name=_("error description"), blank=True)
    datasets_rejected_count = models.PositiveIntegerField(verbose_name=_("number of rejected datasets"), null=True, blank=True)
    datasets_count = models.PositiveIntegerField(verbose_name=_("number of imported datasets"), null=True, blank=True)
    datasets_created_count = models.PositiveIntegerField(verbose_name=_("number of created datasets"), null=True, blank=True)
    datasets_updated_count = models.PositiveIntegerField(verbose_name=_("number of updated datasets"), null=True, blank=True)
    datasets_deleted_count = models.PositiveIntegerField(verbose_name=_("number of deleted datasets"), null=True, blank=True)
    resources_count = models.PositiveIntegerField(verbose_name=_("number of imported resources"), null=True, blank=True)
    resources_created_count = models.PositiveIntegerField(verbose_name=_("number of created resources"), null=True, blank=True)
    resources_updated_count = models.PositiveIntegerField(verbose_name=_("number of updated resources"), null=True, blank=True)
    resources_deleted_count = models.PositiveIntegerField(verbose_name=_("number of deleted resources"), null=True, blank=True)
    is_report_email_sent = models.BooleanField(verbose_name=_("Is report email sent?"), default=False)

    class Meta:
        verbose_name = _("data source import")
        verbose_name_plural = _("data source imports")

    def __str__(self):
        return "{} - start {}".format(self.datasource.name, self.start_local_txt)

    @property
    def start_local(self):
        return timezone.localtime(self.start)

    @property
    def start_local_txt(self):
        return self.start_local.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def end_local(self):
        return timezone.localtime(self.end)

    @property
    def is_failed(self):
        return self.status == STATUS_ERROR

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.status = STATUS_OK
        if self.error_desc:
            self.status = STATUS_OK_PARTIAL if self.datasets_rejected_count else STATUS_ERROR
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
