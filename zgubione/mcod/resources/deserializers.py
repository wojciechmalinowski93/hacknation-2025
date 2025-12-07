from django.utils.translation import gettext as _
from marshmallow import ValidationError, pre_load, validate, validates, validates_schema

from mcod.core.api import fields
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import (
    BooleanTermSchema,
    CommonSchema,
    DateTermSchema,
    ExtSchema,
    ListingSchema,
    ListTermsSchema,
    NumberTermSchema,
    StringMatchSchema,
    StringTermSchema,
)
from mcod.core.api.search import fields as search_fields
from mcod.datasets.deserializers import RdfValidationRequest


class ResourceDatasetFilterField(ExtSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        search_path="dataset",
        nested_search=True,
        query_field="dataset.id",
    )
    title = search_fields.FilterField(
        StringMatchSchema,
        search_path="dataset",
        nested_search=True,
        query_field="dataset.title",
    )

    class Meta:
        strict = True


class ResourceAggregations(ExtSchema):
    date_histogram = search_fields.DateHistogramAggregationField(
        aggs={
            "by_modified": {"field": "modified", "size": 500},
            "by_created": {"field": "created", "size": 500},
            "by_verified": {"field": "verified", "size": 500},
        }
    )
    terms = search_fields.TermsAggregationField(
        aggs={
            "by_format": {"size": 500, "field": "format"},
            "by_type": {
                "size": 500,
                "field": "type",
            },
            "by_openness_score": {"size": 500, "field": "openness_score"},
            "by_visualization_type": {"size": 500, "field": "visualization_types"},
            "by_language": {"size": 2, "field": "language"},
        }
    )


class ResourceApiSearchRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/resources",
        doc_field_name="ID",
    )
    title = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/resources",
        doc_field_name="title",
        translated=True,
        search_path="title",
    )
    description = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/resources",
        doc_field_name="description",
        translated=True,
        search_path="description",
    )
    format = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/resources",
        doc_field_name="format",
    )
    media_type = search_fields.FilterField(
        StringTermSchema,
        query_field="type",
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/resources",
        doc_field_name="media type",
    )
    type = search_fields.FilterField(
        StringTermSchema,
        query_field="type",
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/resources",
        doc_field_name="type",
    )
    visualization_type = search_fields.FilterField(
        ListTermsSchema,
        query_field="visualization_types",
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/resources",
        doc_field_name="visualization type",
    )
    openness_score = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/resources/fields/openness_score.html",
        doc_base_url="/resources",
        doc_field_name="openness score",
    )
    created = search_fields.FilterField(
        DateTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/resources",
        doc_field_name="created",
    )
    q = search_fields.MultiMatchField(
        query_fields={"title": ["title^4"], "description": ["description^2"]},
        nested_query_fields={
            "dataset": [
                "title",
            ]
        },
        doc_template="docs/generic/fields/query_field.html",
        doc_base_url="/resources",
        doc_field_name="q",
    )
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "title": "title.{lang}.raw",
            "modified": "modified",
            "created": "created",
            "verified": "verified",
            "data_date": "data_date",
            "views_count": "views_count",
        },
        doc_base_url="/resources",
    )
    dataset = search_fields.FilterField(
        ResourceDatasetFilterField,
        doc_template="docs/resources/fields/dataset.html",
        doc_base_url="/resources",
        doc_field_name="dataset",
    )
    facet = search_fields.FacetField(ResourceAggregations)
    include = search_fields.StringField(
        data_key="include",
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
    )
    has_dynamic_data = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/resources",
        doc_field_name="has_dynamic_data",
    )
    has_high_value_data = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/resources",
        doc_field_name="has_high_value_data",
    )
    has_high_value_data_from_ec_list = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/resources",
        doc_field_name="has_high_value_data_from_ec_list",
    )
    has_research_data = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/resources",
        doc_field_name="has_research_data",
    )
    contains_protected_data = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/resources",
        doc_field_name="contains_protected_data",
    )
    language = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/resources",
        doc_field_name="language",
    )

    class Meta:
        strict = True
        ordered = True


class ResourceApiRequest(CommonSchema):
    id = search_fields.NumberField(_in="path", description="Resource ID", example="447", required=True)
    include = search_fields.StringField(
        data_key="include",
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
        example="dataset",
    )

    class Meta:
        strict = True
        ordered = True


class ResourceRdfApiRequest(ResourceApiRequest, RdfValidationRequest):
    class Meta:
        strict = True
        ordered = True


class TableApiSearchRequest(ListingSchema):
    q = search_fields.QueryStringField(
        all_fields=True,
        required=False,
        doc_template="docs/tables/fields/query_string.html",
    )
    p = search_fields.TableApiMultiMatchField(
        required=False,
        description="Search phrase",
        doc_template="docs/generic/fields/query_field.html",
    )
    sort = search_fields.SortField(
        sort_fields={},
        doc_base_url="/resources",
    )
    sum = search_fields.ColumnMetricAggregationField(aggregation_type="sum")
    avg = search_fields.ColumnMetricAggregationField(aggregation_type="avg")

    class Meta:
        strict = True
        ordered = True


class TableApiRequest(CommonSchema):
    id = search_fields.StringField(
        _in="path",
        description="Row ID",
        example="a52c4405-7d0c-5166-bba9-bde651f46fb9",
        required=True,
    )

    class Meta:
        strict = True
        ordered = True


class GeoApiSearchRequest(ListingSchema):
    bbox = search_fields.BBoxField(required=False, query_field="shape")
    dist = search_fields.GeoDistanceField(required=False, query_field="point")
    q = search_fields.QueryStringField(
        all_fields=True,
        required=False,
        doc_template="docs/tables/fields/query_string.html",
    )
    sort = search_fields.SortField(doc_base_url="/resources")

    no_data = search_fields.NoDataField()

    class Meta:
        strict = True
        ordered = True


class CreateCommentAttrs(ObjectAttrs):
    comment = fields.String(required=True, description="Comment body", example="Looks unpretty")

    @validates("comment")
    def validate_comment(self, comment):
        if len(comment) < 3:
            raise ValidationError(_("Comment must be at least 3 characters long"))

    class Meta:
        strict = True
        ordered = True
        object_type = "comment"


class CreateCommentRequest(TopLevel):
    class Meta:
        attrs_schema = CreateCommentAttrs


class ChartAttrs(ObjectAttrs):
    resource_id = fields.Int(dump_only=True)
    chart = fields.Raw(required=True)
    is_default = fields.Bool()
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))

    class Meta:
        object_type = "chart"
        strict = True
        ordered = True

    @pre_load
    def prepare_data(self, data, **kwargs):
        data.setdefault("is_default", False)
        return data

    @validates_schema
    def validate_schema(self, data, **kwargs):
        chart = self.context.get("chart")
        resource = self.context["resource"]
        user = self.context["user"]
        if resource.is_chart_creation_blocked and not any([user.is_staff, user.is_superuser]):
            raise ValidationError(_("Chart creation for this resource is blocked!"))
        if data["is_default"] and not any([user.is_superuser, user.is_editor_of_organization(resource.institution)]):
            raise ValidationError(_("No permission to define chart"))
        if chart and chart.is_default != data["is_default"]:
            raise ValidationError(_("You cannot change type of chart!"))
        private_charts = resource.charts.filter(is_default=False, created_by=user)
        if chart:
            private_charts = private_charts.exclude(id=chart.id)
        if not data["is_default"] and private_charts.exists():
            raise ValidationError(_("You cannot add another private chart!"))
        charts_with_same_name = resource.charts.filter(is_default=True, name=data["name"])
        if chart:
            charts_with_same_name = charts_with_same_name.exclude(id=chart.id)
        if charts_with_same_name.exists() and data["is_default"]:
            raise ValidationError(_("You cannot put changes into chart defined by Data Provider. Please provide new chart name."))


class ChartApiRequest(TopLevel):
    class Meta:
        attrs_schema = ChartAttrs
        attrs_schema_required = True
