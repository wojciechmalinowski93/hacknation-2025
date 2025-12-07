from mcod.core.api.schemas import CommonSchema, ListingSchema
from mcod.core.api.search import fields as search_fields


class GuideApiRequest(CommonSchema):
    include = search_fields.StringField(
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
    )

    class Meta:
        strict = True
        ordered = True


class GuidesApiRequest(ListingSchema):
    pass
