import marshmallow
from django.utils.timezone import now
from marshmallow import fields
from marshmallow.schema import BaseSchema

from mcod.core.api import fields as api_fields
from mcod.core.api.jsonapi.serializers import (
    Object,
    ObjectAttrs,
    ObjectAttrsMeta,
    TopLevel,
    TopLevelLinks,
    TopLevelMeta,
)
from mcod.core.api.schemas import ExtSchema
from mcod.reports.broken_links.constants import BrokenLinksReportField


class BaseBrokenLinksSerializer(BaseSchema):
    """
    Base serializer defining all possible fields for broken links data.
    This class serves as the Single Source of Truth for field definitions.
    It uses data_keys from the ReportFields Enum to ensure consistency.
    """

    id = fields.Integer(required=True, data_key=BrokenLinksReportField.ID)
    uuid = fields.Str(default="", data_key=BrokenLinksReportField.UUID)
    title = fields.Str(required=True, data_key=BrokenLinksReportField.TITLE)
    portal_data_link = fields.Str(attribute="frontend_absolute_url", default="", data_key=BrokenLinksReportField.PORTAL_DATA_LINK)
    description = fields.Str(default="", data_key=BrokenLinksReportField.DESCRIPTION, missing="")
    link = fields.Str(default="", data_key=BrokenLinksReportField.LINK)
    error_reason = fields.Str(
        attribute="last_link_validation_error_message", default="", data_key=BrokenLinksReportField.ERROR_REASON, missing=""
    )
    converted_formats_str = fields.Str(data_key=BrokenLinksReportField.CONVERTED_FORMATS_STR, missing="")
    institution_id = fields.Str(attribute="institution.id", default="", data_key=BrokenLinksReportField.INSTITUTION_ID)
    institution = fields.Str(required=True, attribute="institution.title", data_key=BrokenLinksReportField.INSTITUTION)
    dataset = fields.Str(required=True, attribute="dataset.title", default="", data_key=BrokenLinksReportField.DATASET)
    dataset_id = fields.Str(default="", data_key=BrokenLinksReportField.DATASET_ID)
    created_by = fields.Int(attribute="created_by_id", default=None, data_key=BrokenLinksReportField.CREATED_BY, missing=None)
    created = api_fields.DateTime(default=None, format="symmetric_iso8601T", data_key=BrokenLinksReportField.CREATED)
    modified_by = fields.Int(attribute="modified_by_id", default=None, data_key=BrokenLinksReportField.MODIFIED_BY, missing=None)
    modified = api_fields.DateTime(default=None, format="symmetric_iso8601T", data_key=BrokenLinksReportField.MODIFIED)
    resource_type = fields.Str(attribute="type", default="", data_key=BrokenLinksReportField.RESOURCE_TYPE)
    method_of_sharing = fields.Str(default="", data_key=BrokenLinksReportField.METHOD_OF_SHARING)
    has_high_value_data = fields.Bool(allow_none=True, data_key=BrokenLinksReportField.HAS_HIGH_VALUE_DATA)
    has_high_value_data_from_ec_list = fields.Bool(
        allow_none=True, data_key=BrokenLinksReportField.HAS_HIGH_VALUE_DATA_FROM_EC_LIST
    )
    has_dynamic_data = fields.Bool(allow_none=True, data_key=BrokenLinksReportField.HAS_DYNAMIC_DATA)
    has_research_data = fields.Bool(allow_none=True, data_key=BrokenLinksReportField.HAS_RESEARCH_DATA)
    contains_protected_data = fields.Bool(allow_none=True, data_key=BrokenLinksReportField.CONTAINS_PROTECTED_DATA)

    class Meta:
        ordered = True


class BrokenLinksSerializer(BaseBrokenLinksSerializer):
    pass


class AdminBrokenLinksSerializer(BaseBrokenLinksSerializer):
    class Meta(BaseBrokenLinksSerializer.Meta):
        unknown = marshmallow.EXCLUDE


class PublicBrokenLinksSerializer(BaseBrokenLinksSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # All fields should be required
        for field in self.fields.values():
            field.required = True

    class Meta(BaseBrokenLinksSerializer.Meta):
        unknown = marshmallow.EXCLUDE
        fields = (
            "institution",
            "dataset",
            "title",
            "portal_data_link",
            "link",
            "error_reason",
        )


class ReportFileSchema(ExtSchema):
    file_size = api_fields.Integer()
    download_url = api_fields.Str()
    format = api_fields.Str()


class BrokenlinksReportApiAttrs(ObjectAttrs):
    rows_count = api_fields.Integer()
    update_date = api_fields.DateTime()
    files = api_fields.Nested(ReportFileSchema, many=True)

    class Meta:
        object_type = "reports"
        ordered = True


class BrokenlinksReportApiResponse(TopLevel):

    jsonapi = api_fields.Method("get_jsonapi")

    class Meta:
        attrs_schema = BrokenlinksReportApiAttrs
        meta_schema = TopLevelMeta
        links_schema = TopLevelLinks

    def get_jsonapi(self, obj):
        return {"version": "1.4"}


class BrokenlinksReportDataApiAttrsMeta(ObjectAttrsMeta):
    updated_at = api_fields.DateTime(default=now)
    row_no = api_fields.Integer()


class BrokenlinksReportDataApiMeta(TopLevelMeta):
    data_schema = api_fields.Raw()
    headers_map = api_fields.Raw()


class BrokenlinksReportDataApiAttrs(ObjectAttrs):
    institution = api_fields.Dict()
    dataset = api_fields.Dict()
    portal_data_link = api_fields.Dict()
    link = api_fields.Dict()

    class Meta:
        object_type = "row"
        ordered = True
        meta_schema = BrokenlinksReportDataApiAttrsMeta


class BrokenlinksReportDataItem(Object):
    id = api_fields.String()

    class Meta:
        attrs_schema = BrokenlinksReportDataApiAttrs

    def _get_object_url(self, data):
        try:
            return data.portal_data_link.get("val")
        except AttributeError:
            return None


class BrokenlinksReportDataApiResponse(TopLevel):

    jsonapi = api_fields.Method("get_jsonapi")

    class Meta:
        data_schema = BrokenlinksReportDataItem
        meta_schema = BrokenlinksReportDataApiMeta
        links_schema = TopLevelLinks

    def get_jsonapi(self, obj):
        return {"version": "1.4"}

    @staticmethod
    def _get_items_count(data):
        if not data:
            return 0
        return data[0].rows_count
