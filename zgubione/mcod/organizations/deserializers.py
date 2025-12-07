from mcod.core.api.schemas import (
    CommonSchema,
    ExtSchema,
    ListingSchema,
    NumberTermSchema,
    StringMatchSchema,
    StringTermSchema,
)
from mcod.core.api.search import fields as search_fields


class InstitutionApiAggregations(ExtSchema):
    date_histogram = search_fields.DateHistogramAggregationField(
        aggs={
            "by_modified": {"field": "modified", "size": 500},
            "by_created": {"field": "created", "size": 500},
            "by_verified": {"field": "verified", "size": 500},
        }
    )
    terms = search_fields.TermsAggregationField(
        aggs={
            "by_city": {
                "field": "city",
                "size": 500,
            },
            "by_institution_type": {"field": "institution_type", "size": 10},
        }
    )


class InstitutionApiSearchRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="ID",
    )
    slug = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="slug",
        translated=True,
        search_path="slug",
    )
    city = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="city",
    )
    regon = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="regon",
    )
    street = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="street",
    )
    postal_code = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="postal code",
    )

    email = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="email address",
    )
    org_type = search_fields.FilterField(
        StringTermSchema,
        data_key="type",
        query_field="institution_type",
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="type",
    )
    tel = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="tel",
    )
    fax = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="fax",
    )
    website = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/institutions",
        doc_field_name="website",
    )

    title = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/institutions",
        doc_field_name="title",
        translated=True,
        search_path="title",
    )
    description = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/institutions",
        doc_field_name="description",
        translated=True,
        search_path="title",
    )

    q = search_fields.MultiMatchField(
        query_fields={"title": ["title^4"], "description": ["description^2"]},
        nested_query_fields={
            "published_datasets": [
                "title",
            ]
        },
        doc_template="docs/generic/fields/query_field.html",
        doc_base_url="/institutions",
        doc_field_name="q",
    )
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "title": "title.{lang}.sort",
            "city": "city.{lang}",
            "modified": "modified",
            "created": "created",
        },
        doc_base_url="/institutions",
    )
    facet = search_fields.FacetField(InstitutionApiAggregations)
    include = search_fields.StringField(
        data_key="include",
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
    )

    class Meta:
        strict = True
        ordered = True


class InstitutionApiRequest(CommonSchema):
    id = search_fields.NumberField(_in="path", description="Institution ID", example="44", required=True)
    include = search_fields.StringField(
        data_key="include",
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
    )

    class Meta:
        strict = True
        ordered = True
