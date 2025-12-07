from mcod.core.api.schemas import (
    DateTermSchema,
    ListingSchema,
    NumberTermSchema,
    StringMatchSchema,
    StringTermSchema,
)
from mcod.core.api.search import fields as search_fields


class LaboratoriesApiRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/laboratory",
        doc_field_name="ID",
    )
    title = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/laboratory",
        doc_field_name="title",
        translated=True,
        search_path="title",
    )
    notes = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/laboratory",
        doc_field_name="notes",
        translated=True,
        search_path="notes",
    )
    event_type = search_fields.FilterField(
        StringTermSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/laboratory",
        doc_field_name="event_type",
        query_field="event_type",
    )
    execution_date = search_fields.FilterField(
        DateTermSchema,
        query_field="execution_date",
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/laboratory",
        doc_field_name="execution_date",
    )
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "title": "title",
            "execution_date": "execution_date",
        },
        doc_base_url="/laboratory",
    )
