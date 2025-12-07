from mcod.core.api.schemas import ListingSchema, NumberTermSchema, StringMatchSchema
from mcod.core.api.search import fields as search_fields


class SearchHistoryApiSearchRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/searchhistories",
        doc_field_name="ID",
    )
    url = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/searchhistories",
        doc_field_name="url",
    )
    query_sentence = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/searchhistories",
        doc_field_name="query_sentence",
    )
    modified = search_fields.FilterField(
        StringMatchSchema,
        query_field="modified",
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/searchhistories",
        doc_field_name="modified",
    )
    q = search_fields.MultiMatchField(
        extra_fields=["query_sentence", "url"],
        doc_template="docs/generic/fields/query_field.html",
        doc_base_url="/searchhistories",
        doc_field_name="q",
    )
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "query_sentence": "query_sentence_keyword",
            "modified": "modified",
            "user": "user.id",
        },
        doc_base_url="/searchhistories",
    )

    class Meta:
        strict = True
        ordered = True
