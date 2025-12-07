import datetime
import enum
import logging
from io import BytesIO
from typing import Any, Dict, List as ListType, Optional, Tuple

import requests
from django.core.exceptions import MultipleObjectsReturned, ValidationError as DjangoValidationError
from django.utils.timezone import is_naive, make_aware
from django.utils.translation import gettext_lazy as _, override
from marshmallow import (
    EXCLUDE,
    Schema as BaseSchema,
    ValidationError,
    post_dump,
    post_load,
    pre_load,
    validate,
    validates_schema,
)
from marshmallow.fields import URL, UUID, Bool, Date, DateTime, Int, List, Method, Nested, Raw, Str

from mcod import settings
from mcod.core.api import fields
from mcod.core.api.rdf.profiles.dcat_ap import DCATDatasetDeserializer
from mcod.core.serializers import CSVSerializer
from mcod.datasets.models import Dataset
from mcod.harvester.schema_utils import get_and_validate_resource_format_from_response
from mcod.lib.metadata_validators import (
    validate_conflicting_high_value_data_flags,
    validate_high_value_data_from_ec_list_organization,
)
from mcod.regions.api import PeliasApi
from mcod.regions.exceptions import MalformedTerytCodeError
from mcod.resources.dga_constants import DGA_COLUMNS
from mcod.resources.dga_utils import (
    get_dga_resource_for_institution,
    get_dga_resources_info_from_xml_harvester_file,
    get_remote_extension_if_correct_dga_content_type,
    request_remote_dga,
    validate_contains_protected_data_with_other_metadata,
    validate_dga_file_columns,
    validate_institution_type_for_contains_protected_data,
)
from mcod.resources.link_validation import download_file
from mcod.resources.models import RESOURCE_DATA_DATE_PERIODS, Resource

logger = logging.getLogger("mcod")


class Schema(BaseSchema):

    @post_load
    def modify_data(self, data, **kwargs):
        for key, value in data.items():
            if isinstance(value, datetime.datetime):
                data[key] = make_aware(value, is_dst=False) if is_naive(value) else value
        return data


class ExtraSchema(Schema):
    key = Str()
    value = Str()


class PreProcessedSchema(Schema):

    def strip_whitespace(self, data):
        pass

    def prepare_data(self, data, **kwargs):
        return data

    @pre_load
    def preprocess_data(self, data, **kwargs):
        self.strip_whitespace(data)
        return self.prepare_data(data, **kwargs)


class DCATSchema(Schema):

    def strip_whitespace(self, data):
        for record in data:
            if record.get("title_pl"):
                record["title_pl"] = record["title_pl"].strip()
            if record.get("title_en"):
                record["title_en"] = record["title_en"].strip()
        return data

    def prepare_multi_data(self, data, **kwargs):
        return data

    @pre_load(pass_many=True)
    def preprocess_multidata(self, data, **kwargs):
        data = self.prepare_multi_data(data, **kwargs)
        return self.strip_whitespace(data)


class CategorySchema(Schema):
    description = Str()
    display_name = Str()
    uuid = UUID()
    image_url = URL(data_key="image_display_url")
    name = Str()
    title = Str()

    class Meta:
        fields = ("title", "description", "uuid", "image_url")
        unknown = EXCLUDE


class OrganizationSchema(Schema):
    created = DateTime()
    description = Str()
    uuid = Str(data_key="id")
    image_name = Str(data_key="image_url")
    slug = Str(data_key="name")
    title = Str(required=True)

    class Meta:
        fields = ("created", "description", "uuid", "image_name", "slug", "title")
        unknown = EXCLUDE


class RelationshipObjectSchema(Schema):
    id = Str()


class RelationshipSubjectSchema(Schema):
    id = Str()


class ResourceMixin:

    @validates_schema
    def validate_link(self, data, **kwargs):
        value = data.get("link")
        if value and "://" in value:
            scheme = value.split("://")[0].lower()
            if scheme != "https":
                raise ValidationError(_("Required scheme is https://"), field_name="link")


class CKANPreProcessedSchema(PreProcessedSchema):

    def strip_whitespace(self, data):
        if data.get("title"):
            data["title"] = data["title"].strip()
        if data.get("name"):
            data["name"] = data["name"].strip()


class XMLPreProcessedSchema(PreProcessedSchema):

    def strip_whitespace(self, data):
        if "title" in data and isinstance(data.get("title"), dict):
            title_en = data["title"].get("english")
            title_pl = data["title"].get("polish")
            if title_en:
                data["title"]["english"] = title_en.strip()
            if title_pl:
                data["title"]["polish"] = title_pl.strip()


class XMLSupplementSchema(XMLPreProcessedSchema):
    name_pl = Str()
    name_en = Str()
    url = URL()
    filename = Str()
    content = Raw()
    language = Str(validate=validate.OneOf(choices=["en", "pl"]))

    class Meta:
        unknown = EXCLUDE

    @validates_schema
    def validate_file(self, data, **kwargs):
        value = data.get("url")
        if value and "://" in value:
            scheme = value.split("://")[0].lower()
            if scheme != "https":
                raise ValidationError(_("Required scheme is https://"), field_name="url")
        if "download_file_exc" in self.context:
            raise ValidationError(self.context["download_file_exc"], field_name="url")
        if self.context.get("format") not in ["doc", "docx", "odt", "pdf", "txt"]:
            raise ValidationError(_("Invalid file format"), field_name="url")

    def prepare_data(self, data, **kwargs):
        if "name" in data and isinstance(data.get("name"), dict):
            data["name_en"] = data["name"].get("english", "")
            data["name_pl"] = data["name"].get("polish", "")
        options = {}
        try:
            file_type, options = download_file(data.get("url"))
            self.context["format"] = options.get("format")
        except Exception as exc:
            self.context["download_file_exc"] = str(exc)
        if "filename" in options:
            data["filename"] = options["filename"]
        if "content" in options:
            data["content"] = options["content"]
        return data


class HighValueDataFromEcValidationResult(enum.Enum):
    NO_CONFLICT = enum.auto()
    INSTITUTION_TYPE_AND_HIGH_VALUE_DATA_FROM_EC_CONFLICT = enum.auto()
    HIGH_VALUE_DATA_CONFLICT = enum.auto()


def _validate_has_high_value_data_from_ec_list(
    data: Dict[str, Any], institution_type: str
) -> HighValueDataFromEcValidationResult:
    has_high_value_data: Optional[bool] = data.get("has_high_value_data")
    has_high_value_data_from_ec_list: Optional[bool] = data.get("has_high_value_data_from_ec_list")

    try:
        validate_high_value_data_from_ec_list_organization(
            has_high_value_data_from_ec_list,
            institution_type,
        )
    except DjangoValidationError:
        return HighValueDataFromEcValidationResult.INSTITUTION_TYPE_AND_HIGH_VALUE_DATA_FROM_EC_CONFLICT

    try:
        validate_conflicting_high_value_data_flags(
            has_high_value_data,
            has_high_value_data_from_ec_list,
        )
    except DjangoValidationError:
        return HighValueDataFromEcValidationResult.HIGH_VALUE_DATA_CONFLICT

    return HighValueDataFromEcValidationResult.NO_CONFLICT


class ResourceSchema(ResourceMixin, CKANPreProcessedSchema):
    """Resource schema only for CKAN harvester"""

    mimetype = Str(allow_none=True)
    cache_last_updated = Str(allow_none=True)
    cache_url = Str(allow_none=True)
    created = DateTime()
    description = Str()
    hash = Str()
    ext_ident = Str(data_key="id", validate=validate.Length(max=36), required=True)
    modified = DateTime(data_key="last_modified", allow_none=True)
    mimetype_inner = Str(allow_none=True)
    title = Str(data_key="name", required=True)
    format = Str()
    link = URL(data_key="url")
    datastore_active = Bool()
    has_dynamic_data = Bool(allow_none=True, missing=None)
    has_high_value_data = Bool(allow_none=True, missing=None)
    has_high_value_data_from_ec_list = Bool(
        data_key="has_high_value_data_from_european_commission_list", allow_none=True, missing=None
    )
    has_research_data = Bool(allow_none=True, missing=None)
    contains_protected_data = Bool(allow_none=True, missing=False)
    package_id = UUID()
    position = Int()
    resource_type = Str(allow_none=True)
    revision_id = UUID()
    size = Str(allow_none=True)
    state = Str()
    url_type = Str(allow_none=True)

    class Meta:
        fields = (
            "created",
            "modified",
            "ext_ident",
            "title",
            "description",
            "link",
            "format",
            "has_dynamic_data",
            "has_high_value_data",
            "has_high_value_data_from_ec_list",
            "has_research_data",
            "contains_protected_data",
        )
        unknown = EXCLUDE

    def prepare_data(self, data, **kwargs):
        if "format" in data:
            value = data["format"].lower()
            data["format"] = value
        return data

    @validates_schema
    def get_resource_format(self, data: dict, **kwargs) -> None:
        """
        Automatically detects and sets the file format based on a remote resource.

        If the 'format' field is missing from the input data, this method attempts
        to fetch the file from the provided 'link' field and determine its format
        using `get_resource_format(response)`. The detected format is stored in the
        schema's context for later use (e.g., during `post_load`).
        """
        if data.get("format"):
            return
        url = data.get("link")
        if not url:
            raise ValidationError("Link cannot be empty")
        extension = get_and_validate_resource_format_from_response(url)
        self.context["format"] = extension

    @post_load
    def pass_format(self, data, **kwargs):
        """
        Injects the previously detected file format into the loaded data.

        If the format was detected earlier and stored in the schema context
        (e.g., by `get_resource_format`), this method assigns it to the 'format'
        field before returning the deserialized data.
        """
        if "format" in self.context:
            data["format"] = self.context["format"]
        return data


class TagSchema(Schema):
    uuid = UUID(data_key="id")
    name = Str()
    status = Str(data_key="state", validate=validate.OneOf(choices=["active"]))

    class Meta:
        fields = ("name", "uuid")
        unknown = EXCLUDE


class XMLTagSchema(Schema):
    name = Str(data_key="$")
    lang = Str(data_key="@lang", validate=validate.OneOf(choices=["en", "pl"]))

    class Meta:
        fields = ("name", "lang")
        unknown = EXCLUDE


class TagDCATSchema(Schema):
    name = Str()
    lang = Str(validate=validate.OneOf(choices=["en", "pl"]))

    class Meta:
        fields = ("name", "lang")
        unknown = EXCLUDE
        ordered = True


class DatasetSchema(CKANPreProcessedSchema):
    author = Str()
    author_email = Str()
    creator_user_id = UUID()
    extras = Nested(ExtraSchema, many=True)
    groups = Nested(CategorySchema, many=True)
    license_id = Str()
    license_title = Str()
    license_url = URL()
    maintainer = Str()
    maintainer_email = Str()
    created = DateTime(data_key="metadata_created")
    modified = DateTime(data_key="metadata_modified", allow_none=True)
    slug = Str(data_key="name")
    notes = Str()
    num_resources = Int()
    num_tags = Int()
    ext_ident = Str(data_key="id", validate=validate.Length(max=36), required=True)
    isopen = Bool()
    organization = Nested(OrganizationSchema, many=False, required=True)
    owner_org = UUID()
    private = Bool()
    relationships_as_object = Nested(RelationshipObjectSchema, many=True)
    relationships_as_subject = Nested(RelationshipSubjectSchema, many=True)
    resources = Nested(ResourceSchema, many=True, missing=[])
    revision_id = UUID()
    status = Str(data_key="state")
    tags = Nested(TagSchema, many=True)
    title = Str(required=True)
    type = Str()
    url = Str()
    version = Str()
    has_dynamic_data = Bool(allow_none=True, missing=None)
    has_high_value_data = Bool(allow_none=True, missing=None)
    has_high_value_data_from_ec_list = Bool(
        data_key="has_high_value_data_from_european_commission_list", allow_none=True, missing=None
    )
    has_research_data = Bool(allow_none=True, missing=None)

    class Meta:
        exclude = [
            "author",
            "author_email",
            "creator_user_id",
            "extras",
            "groups",
            "license_title",
            "license_url",
            "maintainer",
            "maintainer_email",
            "num_resources",
            "num_tags",
            "isopen",
            "owner_org",
            "private",
            "relationships_as_object",
            "relationships_as_subject",
            "revision_id",
            "type",
            "status",
            "url",
            "version",
        ]
        ordered = True
        unknown = EXCLUDE


class XMLResourceSchema(ResourceMixin, XMLPreProcessedSchema):
    ext_ident = Str(data_key="extIdent", validate=validate.Length(max=36), required=True)
    int_ident = Int(data_key="intIdent")
    status = Str(data_key="@status", validate=validate.OneOf(choices=["draft", "published"]))
    link = URL(data_key="url")
    title_pl = Str()
    title_en = Str()
    description_pl = Str()
    description_en = Str()
    availability = Str(validate=validate.OneOf(choices=["local", "remote"]))
    data_date = Date(data_key="dataDate")
    created = DateTime(data_key="created", allow_none=True)
    modified = DateTime(data_key="lastUpdateDate", allow_none=True)
    special_signs = List(Str())
    has_dynamic_data = Bool(data_key="hasDynamicData", allow_none=True, missing=None)
    has_high_value_data = Bool(data_key="hasHighValueData", allow_none=True, missing=None)
    has_high_value_data_from_ec_list = Bool(data_key="hasHighValueDataFromEuropeanCommissionList", allow_none=True, missing=None)
    has_research_data = Bool(data_key="hasResearchData", allow_none=True, missing=None)
    contains_protected_data = Bool(data_key="containsProtectedData", missing=False)
    supplements = Nested(XMLSupplementSchema, many=True)
    is_auto_data_date = Bool(data_key="isAutoDataDate")
    data_date_update_period = Str(
        data_key="dataDateUpdatePeriod",
        validate=validate.OneOf(choices=[p[0] for p in RESOURCE_DATA_DATE_PERIODS]),
    )
    automatic_data_date_start = Date(data_key="autoDataDateStart")
    automatic_data_date_end = Date(data_key="autoDataDateEnd")
    endless_data_date_update = Bool(data_key="endlessDataDateUpdate")
    regions = List(Str())

    class Meta:
        ordered = True
        unknown = EXCLUDE

    @validates_schema
    def validate_resource_format(self, data: dict, **kwargs) -> None:
        url = data.get("link")
        if url:
            get_and_validate_resource_format_from_response(url)

    def prepare_data(self, data, **kwargs):
        if "title" in data and isinstance(data.get("title"), dict):
            data["title_en"] = data["title"].get("english", "")
            data["title_pl"] = data["title"].get("polish", "")
        if "description" in data and isinstance(data.get("description"), dict):
            data["description_en"] = data["description"].get("english", "")
            data["description_pl"] = data["description"].get("polish", "")
        data["availability"] = data.get("availability", "local")
        special_signs = data.pop("specialSigns", {})
        if "specialSign" in special_signs:
            data["special_signs"] = special_signs["specialSign"]
        supplements = data.pop("supplements", {})
        if "supplement" in supplements:
            data["supplements"] = supplements["supplement"]
        regions = data.pop("regions", {})
        if "terytIdent" in regions:
            data["regions"] = regions["terytIdent"]
        return data

    @validates_schema
    def validate_int_ident(self, data, **kwargs):
        int_ident = data.get("int_ident")
        dataset_int_ident = self.context.get("dataset_int_ident")
        organization = self.context["organization"]
        if int_ident and not dataset_int_ident:
            raise ValidationError(
                _("intIdent value for related dataset is also required!"),
                field_name="int_ident",
            )
        if (
            int_ident
            and dataset_int_ident
            and organization
            and not Resource.raw.filter(
                id=int_ident,
                dataset_id=dataset_int_ident,
                dataset__organization=organization,
            ).exists()
        ):
            msg = _('Resource with id: %(r_id)s, dataset\'s id: %(d_id)s and institution "%(ins)s" was not found.') % {
                "r_id": int_ident,
                "d_id": dataset_int_ident,
                "ins": organization.title,
            }
            raise ValidationError(msg, field_name="int_ident")

    @validates_schema
    def validate_auto_data_date(self, data, **kwargs):
        err = Resource.get_auto_data_date_errors(data, True)
        if err:
            raise ValidationError(err.field_name, err.message)

    @validates_schema
    def validate_regions(self, data, **kwargs):
        regions = data.get("regions")
        if regions:
            ext_ident = data.get("ext_ident")
            pelias = PeliasApi()
            try:
                gids = pelias.convert_teryt_to_gids(regions)
            except MalformedTerytCodeError as err:
                raise ValidationError(
                    _(f"Exception occurred for resource with id {ext_ident}: {err}"),
                    field_name="regions",
                )
            places_details = pelias.place(gids)
            found_regions = []
            for reg in places_details["features"]:
                found_gid = reg["properties"]["gid"]
                gid_elems = found_gid.split(":")
                if f"{gid_elems[1]}_gid" in reg["properties"]:
                    found_regions.append(found_gid)
            if len(found_regions) != len(gids):
                found_set = set(found_regions)
                orig_set = set(gids)
                missing_gids = orig_set.difference(found_set)
                missing_ids = [gid.split(":")[2] for gid in missing_gids]
                raise ValidationError(
                    _(
                        f"Resource with id {ext_ident} has assigned unknown TERYT codes:"
                        f' {", ".join(missing_ids)}. Please check if those codes are valid'
                        f" region, county, localadmin or locality codes."
                    ),
                    field_name="regions",
                )

    @validates_schema
    def validate_has_high_value_data_from_ec_list(self, data, **kwargs):
        serializer_field_name = "has_high_value_data_from_ec_list"
        msg_institution_type_conflict = _(
            "Institution with type 'private' or 'developer' can not use field '%(field_name)s' with value true for resource."
        ) % {
            "field_name": "hasHighValueDataFromEuropeanCommissionList",
        }
        msg_high_value_data_flags_conflict = _(
            "Resource field '%(first_field)s' must have value true if field '%(second_field)s' has value true."
        ) % {
            "first_field": "hasHighValueData",
            "second_field": "hasHighValueDataFromEuropeanCommissionList",
        }

        result: HighValueDataFromEcValidationResult = _validate_has_high_value_data_from_ec_list(
            data, self.context["organization"].institution_type
        )

        if result == HighValueDataFromEcValidationResult.INSTITUTION_TYPE_AND_HIGH_VALUE_DATA_FROM_EC_CONFLICT:
            raise ValidationError(message=msg_institution_type_conflict, field_name=serializer_field_name)
        elif result == HighValueDataFromEcValidationResult.HIGH_VALUE_DATA_CONFLICT:
            raise ValidationError(message=msg_high_value_data_flags_conflict, field_name=serializer_field_name)

    @validates_schema
    def validate_contains_protected_data(self, data, **kwargs):  # noqa: C901
        contains_protected_data: bool = data["contains_protected_data"]

        if contains_protected_data:
            field_name = "contains_protected_data"
            has_dynamic_data: Optional[bool] = data.get("has_dynamic_data")
            has_high_value_data: Optional[bool] = data.get("has_high_value_data")
            has_research_data: Optional[bool] = data.get("has_research_data")
            has_high_value_data_from_ec_list: Optional[bool] = data.get("has_high_value_data_from_ec_list")

            # institution type validation
            institution_type: str = self.context["organization"].institution_type

            result_ok: bool = validate_institution_type_for_contains_protected_data(contains_protected_data, institution_type)
            if not result_ok:
                msg_institution_type_conflict = _(
                    "A 'private', 'other' or 'developer' institution cannot use true in the"
                    " 'containsProtectedData' field of a resource."
                )
                raise ValidationError(message=msg_institution_type_conflict, field_name=field_name)

            # other metadata conflict validation
            result_ok: bool = validate_contains_protected_data_with_other_metadata(
                contains_protected_data,
                has_dynamic_data,
                has_research_data,
                has_high_value_data,
                has_high_value_data_from_ec_list,
            )

            if not result_ok:
                msg_other_metadata_conflict = _(
                    "If the resource has a value of the 'containsProtectedData' field equal to true, then the fields"
                    " 'hasDynamicData', 'hasResearchData', 'hasHighValueData', 'hasHighValueDataFromEuropeanCommissionList'"
                    " must be false or not present at all."
                )
                raise ValidationError(message=msg_other_metadata_conflict, field_name=field_name)

            # url accessibility validation
            msg_url_not_accessible = _(
                "An address in the 'url' field of a resource that contains a 'containsProtectedData' field with"
                " a value equal to true is not responding."
            )
            url: str = data["link"]
            try:
                response = request_remote_dga(url)
            except requests.exceptions.RequestException:
                raise ValidationError(message=msg_url_not_accessible, field_name=field_name)

            result_ok: bool = response.status_code == 200
            if not result_ok:
                raise ValidationError(message=msg_url_not_accessible, field_name=field_name)

            # file format validation
            extension_for_remote: Optional[str] = get_remote_extension_if_correct_dga_content_type(response)
            if extension_for_remote is None:
                msg_file_format_not_dga = _(
                    "If the resource has the value of the 'containsProtectedData' field equal to true, it must point to"
                    " a file in the xls, xlsx or csv format in the 'url' field."
                )
                raise ValidationError(message=msg_file_format_not_dga, field_name=field_name)

            # DGA file columns validation
            file_data = BytesIO(response.content)
            result_ok: bool = validate_dga_file_columns(file_data, extension_for_remote)
            if not result_ok:
                msg_dga_columns_error = _(
                    "If the resource has a 'containsProtectedData' value of true, then the resource file must contain exactly "
                    "%(col_quantity)s of columns, arranged and named exactly: %(col_names)s."
                ) % {
                    "col_quantity": len(DGA_COLUMNS),
                    "col_names": ", ".join(DGA_COLUMNS),
                }
                raise ValidationError(message=msg_dga_columns_error, field_name=field_name)

            # more than 1 DGA resource in xml file validation
            dga_resources_info: ListType[Tuple] = get_dga_resources_info_from_xml_harvester_file(
                loaded_data=self.context["loaded_data"]
            )
            result_ok: bool = len(dga_resources_info) < 2
            if not result_ok:
                msg_many_dga_in_xml_file = _(
                    "There is more than 1 resource in the harvester file containing the '%(field_name)s' field with "
                    "a value equal to true."
                ) % {"field_name": "containsProtectedData"}
                conflicting_dga_details: str = ", ".join(
                    [
                        f"Zasób {i}: 'title' = {item[1]}, 'ext_ident' = {item[0]}"
                        for i, item in enumerate(dga_resources_info, start=1)
                    ]
                )
                msg_many_dga_in_xml_file = msg_many_dga_in_xml_file + " " + conflicting_dga_details
                raise ValidationError(message=msg_many_dga_in_xml_file, field_name=field_name)

            # institution DGA resource possession validation
            try:
                resource_dga_db: Optional[Resource] = get_dga_resource_for_institution(self.context["organization"].pk)
            except MultipleObjectsReturned as e:
                msg_multiple_dga_for_institution = str(e)
                raise ValidationError(message=msg_multiple_dga_for_institution, field_name=field_name)
            else:
                if resource_dga_db is not None:
                    result_ok: bool = resource_dga_db.is_added_by_harvester_with_id(self.context["source_id"])
                    if not result_ok:
                        msg_institution_owns_dga = _(
                            "The provider already has a resource in the portal that contains the '%(field_name)s' field "
                            "with a value equal to true. Resource: 'title' = %(title)s, 'id' = %(id)s."
                        ) % {"field_name": "containsProtectedData", "title": resource_dga_db.title, "id": resource_dga_db.pk}
                        raise ValidationError(message=msg_institution_owns_dga, field_name=field_name)


class XMLDatasetSchema(XMLPreProcessedSchema):
    ext_ident = Str(data_key="extIdent", validate=validate.Length(max=36), required=True)
    int_ident = Int(data_key="intIdent")
    status = Str(data_key="@status", validate=validate.OneOf(choices=["draft", "published"]))
    title_pl = Str()
    title_en = Str()
    notes_pl = Str()
    notes_en = Str()
    url = URL(allow_none=True)
    update_frequency = Str(data_key="updateFrequency")
    license = Str()
    license_chosen = Int(allow_none=True)
    license_condition_db_or_copyrighted = Str(allow_none=True)
    license_condition_modification = Bool(allow_none=True)
    license_condition_personal_data = Str(allow_none=True)
    license_condition_responsibilities = Str(allow_none=True)
    license_condition_source = Bool(allow_none=True)
    created = DateTime(data_key="created", allow_none=True)
    modified = DateTime(data_key="lastUpdateDate", allow_none=True)
    categories = List(Str())
    resources = Nested(XMLResourceSchema, many=True)
    supplements = Nested(XMLSupplementSchema, many=True)
    tags = Nested(XMLTagSchema, many=True)
    has_dynamic_data = Bool(data_key="hasDynamicData", allow_none=True, missing=None)
    has_high_value_data = Bool(data_key="hasHighValueData", allow_none=True, missing=None)
    has_high_value_data_from_ec_list = Bool(data_key="hasHighValueDataFromEuropeanCommissionList", allow_none=True, missing=None)
    has_research_data = Bool(data_key="hasResearchData", allow_none=True, missing=None)

    class Meta:
        ordered = True
        unknown = EXCLUDE

    def prepare_data(self, data, **kwargs):
        if "title" in data and isinstance(data.get("title"), dict):
            data["title_en"] = data["title"].get("english", "")
            data["title_pl"] = data["title"].get("polish", "")
        if "conditions" in data:
            data["license_condition_source"] = data["conditions"].get("source", False)
            data["license_condition_modification"] = data["conditions"].get("modification", False)
            data["license_condition_responsibilities"] = data["conditions"].get("responsibilities")
            data["license_condition_db_or_copyrighted"] = data["conditions"].get("dbOrCopyrighted")
            license_text_to_num = dict((row[1], row[0]) for row in Dataset.LICENSES)
            license_chosen_text = data["conditions"].get("dbOrCopyrightedLicenseChosen")
            data["license_chosen"] = license_text_to_num.get(license_chosen_text)
            data["license_condition_personal_data"] = data["conditions"].get("personalData")
        if "description" in data and isinstance(data.get("description"), dict):
            data["notes_en"] = data["description"].get("english", "")
            data["notes_pl"] = data["description"].get("polish", "")
        if "tags" in data:
            data["tags"] = data["tags"].get("tag", [])
        if "categories" in data:
            if "category" in data["categories"]:  # XSD SCHEMA >= 1.1
                data["categories"] = data["categories"]["category"]
            else:
                data["categories"] = [str(row) for row in data["categories"]]
        if "resources" in data:
            data["resources"] = data["resources"].get("resource", [])
        supplements = data.pop("supplements", {})
        if "supplement" in supplements:
            data["supplements"] = supplements["supplement"]
        int_ident = data.get("intIdent")
        if int_ident:
            self.context["dataset_int_ident"] = int_ident
        return data

    @validates_schema
    def validate_int_ident(self, data, **kwargs):
        int_ident = data.get("int_ident")
        organization = self.context["organization"]
        if int_ident and organization and not Dataset.raw.filter(id=int_ident, organization=organization).exists():
            msg = _('Dataset with id: %(d_id)s and institution: "%(ins)s" was not found.') % {
                "d_id": int_ident,
                "ins": organization.title,
            }
            raise ValidationError(msg, field_name="int_ident")

    @validates_schema
    def validate_license_condition_db_or_copyrighted(self, data, **kwargs):
        field_name = "license_condition_db_or_copyrighted"
        if data.get(field_name) and not data.get("license_chosen"):
            raise ValidationError(
                message=_("Field 'dbOrCopyrightedLicenseChosen' is required if field 'dbOrCopyrighted' is provided."),
                field_name=field_name,
            )

    @validates_schema
    def validate_license_chosen(self, data, **kwargs):
        field_name = "license_chosen"
        if data.get(field_name) and not data.get("license_condition_db_or_copyrighted"):
            raise ValidationError(
                message=_("Field 'dbOrCopyrighted' is required if field 'dbOrCopyrightedLicenseChosen' is provided."),
                field_name=field_name,
            )

    @validates_schema
    def validate_has_high_value_data_from_ec_list(self, data, **kwargs):
        serializer_field_name = "has_high_value_data_from_ec_list"
        msg_institution_type_conflict = _(
            "Institution with type 'private' or 'developer' can not use field '%(field_name)s' with value true for dataset."
        ) % {
            "field_name": "hasHighValueDataFromEuropeanCommissionList",
        }
        msg_high_value_data_flags_conflict = _(
            "Dataset field '%(first_field)s' must have value true if field '%(second_field)s' has value true."
        ) % {
            "first_field": "hasHighValueData",
            "second_field": "hasHighValueDataFromEuropeanCommissionList",
        }

        result: HighValueDataFromEcValidationResult = _validate_has_high_value_data_from_ec_list(
            data, self.context["organization"].institution_type
        )

        if result == HighValueDataFromEcValidationResult.INSTITUTION_TYPE_AND_HIGH_VALUE_DATA_FROM_EC_CONFLICT:
            raise ValidationError(message=msg_institution_type_conflict, field_name=serializer_field_name)
        elif result == HighValueDataFromEcValidationResult.HIGH_VALUE_DATA_CONFLICT:
            raise ValidationError(message=msg_high_value_data_flags_conflict, field_name=serializer_field_name)


class ResourceDCATSchema(ResourceMixin, DCATSchema):
    ext_ident = Str(validate=validate.Length(max=36))
    title_pl = Str()
    title_en = Str(allow_none=True)
    description_pl = Str(allow_none=True)
    description_en = Str(allow_none=True)
    created = DateTime(allow_none=True)
    modified = DateTime(allow_none=True)
    link = URL()
    format = Str()
    file_mimetype = Str(allow_none=True)

    def prepare_multi_data(self, data, **kwargs):
        for res in data:
            if res.get("modified") and not res.get("created"):
                res["created"] = res["modified"]
            if not res.get("title_pl") and res.get("title_en"):
                res["title_pl"] = res["title_en"]
        return data

    @post_load(pass_many=True)
    def postprocess_data(self, data, **kwargs):
        for res in data:
            if res["created"] is None:
                res.pop("created")
            if res["modified"] is None:
                res.pop("modified")
        return data

    class Meta:
        ordered = True
        unknown = EXCLUDE


class DatasetDCATSchema(DCATSchema):
    ext_ident = Str(validate=validate.Length(max=36))
    title_pl = Str()
    title_en = Str(allow_none=True)
    notes_pl = Str(data_key="description_pl", allow_none=True)
    notes_en = Str(data_key="description_en", allow_none=True)
    created = DateTime(allow_none=True)
    modified = DateTime(allow_none=True)
    tags = Nested(TagDCATSchema, many=True)
    resources = Nested(ResourceDCATSchema, many=True)
    categories = List(Str())
    update_frequency = Str(allow_none=True)
    license_chosen = Str(allow_none=True)

    class Meta:
        unknown = EXCLUDE
        ordered = True

    def prepare_multi_data(self, triple_store_dct, **kwargs):
        triple_store = triple_store_dct
        dataset_deserializer = DCATDatasetDeserializer(many=True)
        from_triples_data = dataset_deserializer.from_triples(triple_store)
        for dataset in from_triples_data:
            if not dataset.get("title_pl") and dataset.get("title_en"):
                dataset["title_pl"] = dataset["title_en"]
            if dataset.get("modified") and not dataset.get("created"):
                dataset["created"] = dataset["modified"]
            dataset["license_chosen"] = dataset["resources"][0]["license"]
        return from_triples_data

    @post_load(pass_many=True)
    def postprocess_data(self, data, **kwargs):
        for dataset in data:
            if dataset["created"] is None:
                dataset.pop("created")
            if dataset["modified"] is None:
                dataset.pop("modified")
        return data


class DataSourceSerializer(Schema):
    source_type = Str()
    url = URL()
    title = Str()
    last_import_timestamp = DateTime()
    update_frequency = Method("get_update_frequency")

    def get_update_frequency(self, obj):
        translations = {}
        for lang in settings.MODELTRANS_AVAILABLE_LANGUAGES:
            with override(lang):
                translations[lang] = str(obj.get_frequency_in_days_display())
        return translations


class DataSourceCSVSchema(CSVSerializer):
    # `DataSource` fields
    datasource_id = fields.Str(attribute="pk", data_key=_("Datasource - id"), default="")
    datasource_name = fields.Str(attribute="name", data_key=_("Name"), default="")
    datasource_description = fields.Str(attribute="description", data_key=_("Notes"), default="")
    datasource_source_type = fields.Str(attribute="source_type", data_key=_("Type"), default="")
    datasource_created = fields.DateTime(attribute="created", data_key=_("Created at"), default=None)
    datasource_modified = fields.DateTime(attribute="modified", data_key=_("Modified at"), default=None)
    datasource_last_activation_date = fields.DateTime(
        attribute="last_activation_date", data_key=_("Last activation date"), default=None
    )
    datasource_portal_url = fields.Str(attribute="portal_url", data_key=_("URL"), default="")
    datasource_api_url = fields.Str(attribute="api_url", data_key=_("API"), default="")
    datasource_xml_url = fields.Str(attribute="xml_url", data_key=_("XML url"), default="")
    datasource_organization = fields.Str(attribute="organization__title", data_key=_("Institution"), default="")
    datasource_frequency_in_days = fields.Integer(attribute="frequency_in_days", data_key=_("Update frequency"), required=True)
    datasource_created_by = fields.Int(attribute="created_by", data_key=_("Created by"), default=None)
    datasource_modified_by = fields.Int(attribute="modified_by", data_key=_("Modified by"), default=None)
    datasource_status = fields.Str(attribute="status", data_key=_("Status"), default="")
    datasource_institution_type = fields.Str(
        attribute="institution_type", data_key=_("Default type for newly created institutions"), default=""
    )


class DataSourceImportsCSVSchema(DataSourceCSVSchema):
    # `DataSource` fields are attached by inheritance

    # DataSourceImport fields
    datasource_import_id = fields.Integer(attribute="imports__pk", data_key=_("Import - id"), required=True)
    datasource_import_start = fields.DateTime(attribute="imports__start", data_key=_("Import - start"), default=None)
    datasource_import_end = fields.DateTime(attribute="imports__end", data_key=_("Import - end"), default=None)
    datasource_import_datasets_rejected_count = fields.Integer(
        attribute="imports__datasets_rejected_count", data_key=_("Import - number of rejected datasets"), default=0
    )
    datasource_import_datasets_count = fields.Integer(
        attribute="imports__datasets_count", data_key=_("Import - number of imported datasets"), default=0
    )
    datasource_import_datasets_created_count = fields.Integer(
        attribute="imports__datasets_created_count", data_key=_("Import - number of created datasets"), default=0
    )
    datasource_import_datasets_updated_count = fields.Integer(
        attribute="imports__datasets_updated_count", data_key=_("Import - number of updated datasets"), default=0
    )
    datasource_import_datasets_deleted_count = fields.Integer(
        attribute="imports__datasets_deleted_count", data_key=_("Import - number of deleted datasets"), default=0
    )
    datasource_import_resources_count = fields.Integer(
        attribute="imports__resources_count", data_key=_("Import - number of imported resources"), default=0
    )
    datasource_import_resources_created_count = fields.Integer(
        attribute="imports__resources_created_count", data_key=_("Import - number of created resources"), default=0
    )
    datasource_import_resources_updated_count = fields.Integer(
        attribute="imports__resources_updated_count", data_key=_("Import - number of updated resources"), default=0
    )
    datasource_import_resources_deleted_count = fields.Integer(
        attribute="imports__resources_deleted_count", data_key=_("Import - number of deleted resources"), default=0
    )
    datasource_import_status = fields.Str(attribute="imports__status", data_key=_("Import - result"), default="")
    datasource_import_error_desc = fields.Str(
        attribute="imports__error_desc", data_key=_("Import - error description"), default=""
    )

    @post_dump
    def modify_datasource_institution_type(self, data, **kwargs):
        # For harvester XML and DCAT-AP set `datasource_institution_type` as ""
        if data[_("Type")] in ["xml", "dcat"]:
            data[_("Default type for newly created institutions")] = ""
        return data

    class Meta:
        ordered = True
        unknown = EXCLUDE


class DataSourceLastImportDatasetCSVSchema(DataSourceCSVSchema):
    # `DataSource` fields are attached by inheritance

    # `DataSourceImport` fields
    datasource_import_id = fields.Integer(attribute="imports__pk", data_key=_("Import - id"), required=True)
    datasource_import_start = fields.DateTime(attribute="imports__start", data_key=_("Import - start"), default=None)
    datasource_import_end = fields.DateTime(attribute="imports__end", data_key=_("Import - end"), default=None)
    datasource_import_status = fields.Str(attribute="imports__status", data_key=_("Import - result"), default="")
    datasource_import_error_desc = fields.Str(
        attribute="imports__error_desc", data_key=_("Import - error description"), default=""
    )

    # Dataset fields
    dataset_id = fields.Integer(attribute="datasource_datasets__pk", data_key=_("Dataset - id"), required=True)
    dataset_title = fields.Str(attribute="datasource_datasets__title", data_key=_("Dataset - title"), default="")
    dataset_tmodified = fields.DateTime(attribute="datasource_datasets__modified", data_key=_("Dataset - modified"), default=None)
    dataset_organization = fields.Str(
        attribute="datasource_datasets__organization__title", data_key=_("Dataset - institution"), default=""
    )

    @post_dump
    def modify_datasource_institution_type(self, data, **kwargs):
        # For harvester XML and DCAT-AP set `datasource_institution_type` as ""
        if data[_("Type")] in ["xml", "dcat"]:
            data[_("Default type for newly created institutions")] = ""
        return data

    class Meta:
        ordered = True
        unknown = EXCLUDE
