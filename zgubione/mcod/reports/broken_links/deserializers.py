from django.utils.translation import gettext_lazy as _
from marshmallow import validate

from mcod.core.api.schemas import CommonSchema, ListingSchema
from mcod.core.api.search import fields as search_fields


class BrokenlinksReportApiRequest(CommonSchema):
    pass


class BrokenlinksReportDataApiRequest(ListingSchema):
    q = search_fields.QueryStringField(
        all_fields=True,
        required=False,
        description="Query string",
        doc_template="docs/tables/fields/query_string.html",
    )
    sort = search_fields.SortField(
        sort_fields={
            "institution": "institution.keyword",
            "dataset": "dataset.keyword",
            "portal_data_link": "portal_data_link.keyword",
            "link": "link.keyword",
        }
    )
    per_page = search_fields.NumberField(
        missing=20,
        default=20,
        example=10,
        description="Page size. Default value is 20, max allowed page size is 100.",
        validate=validate.Range(1, 100, error=_("Invalid page size")),
        metadata={"doc_default": 20},
    )


class PublicBrokenLinksReportDownloadApiRequest(CommonSchema):
    extension = search_fields.StringField(
        _in="path", description="Report file extension - csv or xlsx", example="csv", required=True
    )
