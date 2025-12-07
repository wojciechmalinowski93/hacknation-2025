from django.utils.translation import get_language, gettext_lazy as _
from elasticsearch_dsl.query import Term
from marshmallow import ValidationError, validates

from mcod.core.api import fields as core_fields
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import (
    BooleanTermSchema,
    CommonSchema,
    DateTermSchema,
    ExtSchema,
    GeoDistanceSchema,
    GeoShapeSchema,
    ListingSchema,
    ListTermsSchema,
    NumberTermSchema,
    RegionIdTermsSchema,
    StringMatchSchema,
    StringTermSchema,
)
from mcod.core.api.search import fields as search_fields


class CategoryFilterSchema(ExtSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        search_path="category",
        nested_search=True,
        query_field="category.id",
    )

    class Meta:
        default_field = "term"


class CategoriesFilterSchema(ExtSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        search_path="categories",
        nested_search=True,
        query_field="categories.id",
    )

    class Meta:
        default_field = "term"


class InstitutionFilterSchema(ExtSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        search_path="institution",
        nested_search=True,
        query_field="institution.id",
    )

    class Meta:
        default_field = "term"


class ResourceFilterSchema(ExtSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        search_path="resource",
        nested_search=True,
        query_field="resource.id",
    )
    title = search_fields.FilterField(
        StringMatchSchema,
        search_path="resource",
        nested_search=True,
        query_field="resource.title",
    )

    class Meta:
        strict = True


class RegionsFilterSchema(ExtSchema):
    id = search_fields.FilterField(
        RegionIdTermsSchema,
        search_path="regions",
        nested_search=True,
        query_field="regions.region_id",
    )
    bbox = search_fields.FilterField(
        GeoShapeSchema,
        search_path="regions",
        nested_search=True,
        query_field="regions.bbox",
    )
    coordinates = search_fields.FilterField(
        GeoDistanceSchema,
        search_path="regions",
        nested_search=True,
        query_field="regions.coords",
    )


class DatasetAggregations(ExtSchema):
    date_histogram = search_fields.DateHistogramAggregationField(
        aggs={
            "by_modified": {"field": "modified", "size": 500},
            "by_created": {"field": "created", "size": 500},
            "by_verified": {"field": "verified", "size": 500},
        }
    )

    terms = search_fields.TermsAggregationField(
        aggs={
            "by_institution": {
                "field": "institution.id",
                "size": 500,
                "nested_path": "institution",
            },
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
            "by_format": {"size": 500, "field": "formats"},
            "by_openness_score": {"size": 500, "field": "openness_scores"},
            "by_category": {
                "field": "category.id",
                "nested_path": "category",
                "size": 100,
            },
            "by_categories": {
                "field": "categories.id",
                "nested_path": "categories",
                "size": 100,
            },
            "by_types": {"field": "types", "size": 100},
            "by_visualization_types": {"field": "visualization_types", "size": 100},
        }
    )


class DatasetApiSearchRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="ID",
    )
    title = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/datasets",
        doc_field_name="title",
        translated=True,
        search_path="title",
    )
    notes = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/datasets",
        doc_field_name="notes",
        translated=True,
        search_path="notes",
    )
    category = search_fields.FilterField(CategoryFilterSchema)
    categories = search_fields.FilterField(CategoriesFilterSchema)
    institution = search_fields.FilterField(InstitutionFilterSchema)
    tag = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="tag",
        translated=True,
        search_path="tags",
        query_field="tags",
    )
    keyword = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="keyword",
        search_path="keywords",
        query_field="keywords.name",
        condition=Term(keywords__language=get_language),
        nested_search=True,
    )
    format = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="format",
        query_field="formats",
    )
    types = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="types",
        query_field="types",
    )
    openness_score = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="openness score",
        query_field="openness_scores",
    )
    resource = search_fields.FilterField(ResourceFilterSchema)
    visualization_types = search_fields.FilterField(
        ListTermsSchema,
        query_field="visualization_types",
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="visualization types",
    )
    created = search_fields.FilterField(
        DateTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="created",
    )
    q = search_fields.MultiMatchField(
        query_fields={"title": ["title^4"], "notes": ["notes^2"]},
        nested_query_fields={
            "resources": [
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
            "verified": "verified",
        },
        doc_base_url="/datasets",
        missing="id",
    )

    facet = search_fields.FacetField(DatasetAggregations)
    include = search_fields.StringField(
        data_key="include",
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
    )
    has_dynamic_data = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="has_dynamic_data",
    )
    has_high_value_data = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="has_high_value_data",
    )
    has_high_value_data_from_ec_list = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="has_high_value_data_from_ec_list",
    )
    has_research_data = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="has_research_data",
    )
    is_promoted = search_fields.FilterField(
        BooleanTermSchema,
        doc_template="docs/generic/fields/boolean_term_field.html",
        doc_base_url="/datasets",
        doc_field_name="is_promoted",
    )

    class Meta:
        strict = True
        ordered = True


class DatasetApiRequest(CommonSchema):
    id = search_fields.NumberField(_in="path", description="Dataset ID", example="447", required=True)
    include = search_fields.StringField(
        data_key="include",
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
    )
    use_rdf_db = search_fields.NoDataField()

    class Meta:
        strict = True
        ordered = True


class DatasetResourcesDownloadApiRequest(CommonSchema):

    class Meta:
        strict = True
        ordered = True


class RdfValidationRequest:
    shacl = search_fields.StringField()


class CatalogRdfApiRequest(DatasetApiSearchRequest, RdfValidationRequest):
    class Meta:
        strict = True
        ordered = True


class DatasetRdfApiRequest(DatasetApiRequest, RdfValidationRequest):
    class Meta:
        strict = True
        ordered = True


class CreateCommentAttrs(ObjectAttrs):
    comment = core_fields.String(required=True, description="Comment body", example="Looks unpretty")

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
        attrs_schema_required = True


class LicenseApiRequest(CommonSchema):

    class Meta:
        strict = True
        ordered = True
