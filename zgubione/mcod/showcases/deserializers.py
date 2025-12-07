from django.utils.translation import get_language, gettext_lazy as _
from elasticsearch_dsl.query import Term
from marshmallow import ValidationError, post_load, pre_load, validate, validates, validates_schema

from mcod import settings
from mcod.core.api import fields as core_fields
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import (
    CommonSchema,
    ExtSchema,
    ListingSchema,
    NumberTermSchema,
    StringMatchSchema,
    StringTermSchema,
)
from mcod.core.api.search import fields as search_fields
from mcod.showcases.models import ShowcaseProposal


class ShowcaseAggs(ExtSchema):
    date_histogram = search_fields.DateHistogramAggregationField(
        aggs={
            "by_modified": {"field": "modified", "size": 500},
            "by_created": {"field": "created", "size": 500},
        }
    )

    terms = search_fields.TermsAggregationField(
        aggs={
            "by_tag": {
                "field": "tags",
                "nested_path": "tags",
                "size": 500,
                "translated": True,
            },
            "by_keyword": {
                "field": "keywords.name",
                "filter": {"keywords.language": get_language},
                "nested_path": "keywords",
                "size": 500,
            },
        }
    )


class ShowcasesApiRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/showcases",
        doc_field_name="ID",
    )
    title = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/showcases",
        doc_field_name="title",
        translated=True,
        search_path="title",
    )
    notes = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/showcases",
        doc_field_name="notes",
        translated=True,
        search_path="notes",
    )
    has_image_thumb = search_fields.TermsField()

    tag = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/showcases",
        doc_field_name="tag",
        translated=True,
        search_path="tags",
        query_field="tags",
    )

    keyword = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/showcases",
        doc_field_name="keyword",
        search_path="keywords",
        query_field="keywords.name",
        condition=Term(keywords__language=get_language),
        nested_search=True,
    )

    q = search_fields.MultiMatchField(
        query_fields={"title": ["title^4"], "notes": ["notes^2"]},
        nested_query_fields={
            "datasets": [
                "title",
            ]
        },
    )
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "title": "title.{lang}.sort",
            "modified": "modified",
            "created": "created",
            "views_count": "views_count",
            "main_page_position": "main_page_position",
        },
        doc_base_url="/showcases",
    )

    facet = search_fields.FacetField(ShowcaseAggs)
    is_featured = search_fields.ExistsField("main_page_position")

    class Meta:
        strict = True
        ordered = True


class ShowcaseApiRequest(CommonSchema):
    id = search_fields.NumberField(_in="path", description="Showcase ID", example="447", required=True)

    class Meta:
        strict = True
        ordered = True


class ExternalResourceSchema(ExtSchema):
    title = core_fields.Str(required=False)
    url = core_fields.Url(required=False)


class CreateShowcaseProposalAttrs(ObjectAttrs):
    category = core_fields.Str(
        required=True,
        validate=validate.OneOf(
            choices=ShowcaseProposal.CATEGORIES,
            error=_("Invalid value! Possible values: %(values)s") % {"values": ShowcaseProposal.CATEGORIES},
        ),
    )
    license_type = core_fields.Str(required=False)
    applicant_email = core_fields.Email(required=True)
    author = core_fields.Str(required=True, validate=validate.Length(max=50))
    title = core_fields.Str(
        required=True,
        faker_type="showcase title",
        example="Some Showcase",
        validate=validate.Length(max=300),
    )
    url = core_fields.Url(required=True)
    notes = core_fields.Str(required=True, validate=validate.Length(max=3000))
    image = core_fields.Base64String(required=False, default=None, max_size=settings.IMAGE_UPLOAD_MAX_SIZE)
    illustrative_graphics = core_fields.Base64String(required=False, default=None, max_size=settings.IMAGE_UPLOAD_MAX_SIZE)
    image_alt = core_fields.Str(required=False, default=None)
    datasets = core_fields.List(core_fields.Str(), required=False, default=[])
    external_datasets = core_fields.Nested(ExternalResourceSchema, required=False, default={}, many=True)
    keywords = core_fields.List(core_fields.Str(), default="", required=False)
    comment = core_fields.String(required=False, description="Comment body", example="Looks unpretty", default="")
    # application specific fields.
    is_mobile_app = core_fields.Boolean()
    mobile_apple_url = core_fields.Str()
    mobile_google_url = core_fields.Str()
    is_desktop_app = core_fields.Boolean()
    desktop_linux_url = core_fields.Str()
    desktop_macos_url = core_fields.Str()
    desktop_windows_url = core_fields.Str()

    is_personal_data_processing_accepted = core_fields.Boolean(required=True)
    is_terms_of_service_accepted = core_fields.Boolean(required=True)

    class Meta:
        strict = True
        ordered = True
        object_type = "showcaseproposal"

    @post_load
    def postprocess_data(self, data, **kwargs):
        if data.get("category") == "other":
            data["license_type"] = ""
        return data

    @pre_load
    def prepare_data(self, data, **kwargs):
        data["datasets"] = [x.replace("dataset-", "") for x in data.get("datasets", []) if x]
        return data

    @validates("mobile_apple_url")
    def validate_mobile_apple_url(self, value):
        if value:
            validate.URL()(value)

    @validates("mobile_google_url")
    def validate_mobile_google_url(self, value):
        if value:
            validate.URL()(value)

    @validates("desktop_linux_url")
    def validate_desktop_linux_url(self, value):
        if value:
            validate.URL()(value)

    @validates("desktop_macos_url")
    def validate_desktop_macos_url(self, value):
        if value:
            validate.URL()(value)

    @validates("desktop_windows_url")
    def validate_desktop_windows_url(self, value):
        if value:
            validate.URL()(value)

    @validates("is_personal_data_processing_accepted")
    def validate_is_personal_data_processing_accepted(self, value):
        if not value:
            raise ValidationError(_("This field is required"))

    @validates("is_terms_of_service_accepted")
    def validate_is_terms_of_service_accepted(self, value):
        if not value:
            raise ValidationError(_("This field is required"))

    @validates_schema
    def validate_data(self, data, **kwargs):
        errors = {}
        is_mobile_app = data.get("is_mobile_app")
        is_desktop_app = data.get("is_desktop_app")
        mobile_apple_url = data.get("mobile_apple_url")
        mobile_google_url = data.get("mobile_google_url")
        desktop_linux_url = data.get("desktop_linux_url")
        desktop_macos_url = data.get("desktop_macos_url")
        desktop_windows_url = data.get("desktop_windows_url")
        msg_template = _("Passing at least one of: %(items)s is required!")
        mobile_urls = [mobile_apple_url, mobile_google_url]
        if is_mobile_app and not any(mobile_urls):
            errors["is_mobile_app"] = msg_template % {"items": "mobile_apple_url, mobile_google_url"}
        desktop_urls = [desktop_linux_url, desktop_macos_url, desktop_windows_url]
        if is_desktop_app and not any(desktop_urls):
            errors["is_desktop_app"] = msg_template % {"items": "desktop_linux_url, desktop_macos_url, desktop_windows_url"}
        category = data.get("category")
        license_type = data.get("license_type")
        if category in ("app", "www") and not license_type:
            errors["license_type"] = _("Invalid value! Possible values: %(values)s") % {"values": ShowcaseProposal.LICENSE_TYPES}
        if errors:
            raise ValidationError(errors)


class CreateShowcaseProposalRequest(TopLevel):
    class Meta:
        attrs_schema = CreateShowcaseProposalAttrs
        attrs_schema_required = True
