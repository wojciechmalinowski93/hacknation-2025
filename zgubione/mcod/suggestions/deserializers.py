from mcod.core.api import fields as core_fields
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import (
    CommonSchema,
    DateTermSchema,
    ListingSchema,
    NumberTermSchema,
    StringMatchSchema,
)
from mcod.core.api.search import fields as search_fields


class SubmissionApiRequest(CommonSchema):
    id = core_fields.Int(_in="path", description="Submission ID", example="447", required=True)

    class Meta:
        strict = True
        ordered = True


class SubmissionListRequest(ListingSchema):
    is_active = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/submissions/accepted",
    )
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/submissions/accepted",
        doc_field_name="ID",
    )
    title = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/submissions/accepted",
        doc_field_name="title",
    )
    notes = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/submissions/accepted",
    )
    organization_name = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/submissions/accepted",
    )
    submission_date = search_fields.FilterField(
        DateTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/submissions/accepted",
    )
    data_link = search_fields.FilterField(
        StringMatchSchema,
        doc_template="docs/generic/fields/string_match_field.html",
        doc_base_url="/submissions/accepted",
    )
    decision_date = search_fields.FilterField(
        DateTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/submissions/accepted",
    )

    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "title": "title.sort",
            "submission_date": "submission_date",
            "decision_date": "decision_date",
            "published_at": "published_at",
        },
        doc_base_url="/submissions/accepted",
    )


class CreateSubmissionAttrs(ObjectAttrs):
    notes = core_fields.String(description="Notes", example="Lorem Ipsum", required=True)

    class Meta:
        strict = True
        ordered = True
        object_type = "submission"


class CreateSubmissionRequest(TopLevel):
    class Meta:
        attrs_schema = CreateSubmissionAttrs
        attrs_schema_required = True


class CreateDatasetSubmissionAttrs(ObjectAttrs):
    title = core_fields.String(description="Name", example="Lorem Ipsum", required=True)
    notes = core_fields.String(description="Description", example="Lorem Ipsum", required=True)
    organization_name = core_fields.String(description="Organization", example="ACME", required=False)
    data_link = core_fields.URL(description="Link to data", example="https://dane.gov.pl", required=False)
    potential_possibilities = core_fields.String(description="potential possibilities", example="none", required=False)

    class Meta:
        strict = True
        ordered = True
        object_type = "submission"


class CreateDatasetSubmissionRequest(TopLevel):
    class Meta:
        attrs_schema = CreateDatasetSubmissionAttrs
        attrs_schema_required = True


class CreateFeedbackAttrs(ObjectAttrs):
    opinion = core_fields.String(description="Opinion", example="like", required=True)

    class Meta:
        strict = True
        ordered = True
        object_type = "feedback"


class CreateFeedbackRequest(TopLevel):
    class Meta:
        attrs_schema = CreateFeedbackAttrs
        attrs_schema_required = True


class DeleteFeedbackAttrs(ObjectAttrs):
    submission = core_fields.Int(description="Submission ID", example=12, required=True)

    class Meta:
        strict = True
        ordered = True
        object_type = "feedback"


class AcceptedSubmissionCommentAttrs(ObjectAttrs):
    comment = core_fields.String(description="Accepted submission comment", example="Lorem Ipsum", required=True)


class AcceptedSubmissionCommentApiRequest(TopLevel):
    class Meta:
        attrs_schema = AcceptedSubmissionCommentAttrs
