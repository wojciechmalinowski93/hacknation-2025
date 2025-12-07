from django.utils.translation import gettext_lazy as _
from marshmallow import pre_dump

from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import (
    Aggregation,
    HighlightObjectMixin,
    ObjectAttrs,
    Relationship,
    Relationships,
    TopLevel,
)
from mcod.core.api.schemas import ExtSchema
from mcod.core.serializers import CSVSchemaRegistrator, CSVSerializer
from mcod.lib.serializers import KeywordsList, TranslatedStr
from mcod.showcases.models import Showcase
from mcod.watchers.serializers import SubscriptionMixin


class ExternalDataset(ExtSchema):
    title = fields.String()
    url = fields.String()


class ShowcaseApiRelationships(Relationships):
    datasets = fields.Nested(
        Relationship,
        many=False,
        default=[],
        _type="dataset",
        url_template="{object_url}/datasets",
        required=True,
    )
    subscription = fields.Nested(
        Relationship,
        many=False,
        _type="subscription",
        url_template="{api_url}/auth/subscriptions/{ident}",
    )

    def filter_data(self, data, **kwargs):
        if not self.context.get("is_listing", False) and "datasets" in data:
            data["datasets"] = data["datasets"].filter(status="published")
        return data


class ShowcaseApiAggs(ExtSchema):
    by_created = fields.Nested(Aggregation, many=True, attribute="_filter_by_created.by_created.buckets")
    by_modified = fields.Nested(Aggregation, many=True, attribute="_filter_by_modified.by_modified.buckets")
    by_tag = fields.Nested(Aggregation, many=True, attribute="_filter_by_tag.by_tag.inner.buckets")
    by_keyword = fields.Nested(
        Aggregation,
        many=True,
        attribute="_filter_by_keyword.by_keyword.inner.inner.buckets",
    )


class ShowcaseApiAttrs(ObjectAttrs, HighlightObjectMixin):
    category = fields.Str(attribute="showcase_category")
    category_name = fields.Method("get_category_name")
    slug = TranslatedStr()
    title = TranslatedStr()
    notes = TranslatedStr()
    author = fields.Str(faker_type="firstname")
    url = fields.Str(faker_type="url")
    image_url = fields.Str(faker_type="image_url")
    image_thumb_url = fields.Str(faker_type="image_thumb_url")
    image_alt = TranslatedStr()
    illustrative_graphics_url = fields.Str()
    illustrative_graphics_alt = TranslatedStr()
    followed = fields.Boolean(faker_type="boolean")
    keywords = KeywordsList(TranslatedStr(), faker_type="tagslist")
    views_count = fields.Integer(faker_type="integer")
    modified = fields.Str(faker_type="datetime")
    created = fields.Str(faker_type="datetime")
    has_image_thumb = fields.Bool()
    main_page_position = fields.Int()
    external_datasets = fields.Nested(ExternalDataset, many=True)
    # application showcase fields:
    is_mobile_app = fields.Bool()
    is_mobile_app_name = fields.Method("get_is_mobile_app_name")
    is_desktop_app = fields.Bool()
    is_desktop_app_name = fields.Method("get_is_desktop_app_name")
    mobile_apple_url = fields.URL()
    mobile_google_url = fields.URL()
    desktop_linux_url = fields.URL()
    desktop_macos_url = fields.URL()
    desktop_windows_url = fields.URL()

    license_type = fields.Str()
    license_type_name = fields.Method("get_license_type_name")

    class Meta:
        relationships_schema = ShowcaseApiRelationships
        object_type = "showcase"
        url_template = "{api_url}/showcases/{ident}"
        model = "showcases.Showcase"
        ordered = True

    def get_is_desktop_app_name(self, obj):
        return str(_("Desktop App")) if obj.is_desktop_app else ""

    def get_is_mobile_app_name(self, obj):
        return str(_("Mobile App")) if obj.is_mobile_app else ""

    def get_category_name(self, obj):
        return str(Showcase.CATEGORY_NAMES.get(obj.showcase_category, ""))

    def get_license_type_name(self, obj):
        return str(Showcase.LICENSE_TYPE_NAMES.get(obj.license_type, ""))


class ShowcaseApiResponse(SubscriptionMixin, TopLevel):
    class Meta:
        attrs_schema = ShowcaseApiAttrs
        aggs_schema = ShowcaseApiAggs


class ShowcaseAggregationMixin(ExtSchema):
    id = fields.String(attribute="key")
    title = fields.String()
    doc_count = fields.Integer()


class ShowcaseCategoryAggregation(ShowcaseAggregationMixin):
    @pre_dump
    def prepare_data(self, data, **kwargs):
        data["title"] = Showcase.CATEGORY_NAMES.get(data.key)
        return data


class ShowcasePlatformAggregation(ShowcaseAggregationMixin):
    @pre_dump
    def prepare_data(self, data, **kwargs):
        data["title"] = Showcase.APPLICATION_PLATFORMS.get(data.key)
        return data


class ShowcaseTypeAggregation(ShowcaseAggregationMixin):
    @pre_dump
    def prepare_data(self, data, **kwargs):
        data["title"] = Showcase.APPLICATION_TYPES_PLURAL.get(data.key)
        return data


class ShowcaseProposalCSVSerializer(CSVSerializer, metaclass=CSVSchemaRegistrator):
    id = fields.Int(data_key="id", required=True, example=77)
    category_name = fields.Str(data_key=_("Category"), example="Aplikacja")
    title = fields.Str(data_key=_("Name"), example="Propozycja aplikacji")
    notes = fields.Str(data_key=_("Notes"), default="", example="opis...")
    url = fields.Str(data_key=_("App URL"), default="", example="http://example.com")
    author = fields.Str(data_key=_("Author"), default="", example="Jan Kowalski")
    applicant_email = fields.Email(
        data_key=_("applicant email"),
        default="",
        required=False,
        example="user@example.com",
    )
    keywords = fields.Str(
        data_key=_("keywords"),
        attribute="keywords_as_str",
        default="",
        example="tag1,tag2,tag3",
    )
    report_date = fields.Date(data_key=_("report date"))
    decision_date = fields.Date(data_key=_("decision date"), default=None)
    comment = fields.Str(data_key=_("comment"), example="komentarz...", default="")
    datasets = fields.Str(
        data_key=_("datasets"),
        attribute="datasets_ids_as_str",
        example="998,999",
        default="",
    )
    external_datasets = fields.Raw(data_key=_("external datasets"), example="[]")
    showcase = fields.Int(data_key=_("Showcase"), attribute="showcase.id", default=None)

    class Meta:
        ordered = True
        model = "showcases.ShowcaseProposal"


class ShowcaseProposalAttrs(ObjectAttrs):
    title = fields.Str()
    url = fields.URL()
    applicant_email = fields.Email()

    class Meta:
        object_type = "showcaseproposal"
        path = "showcases"
        url_template = "{api_url}/showcases/suggest"


class ShowcaseProposalApiResponse(TopLevel):
    class Meta:
        attrs_schema = ShowcaseProposalAttrs
