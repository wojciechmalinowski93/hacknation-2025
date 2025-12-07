from django.utils.translation import gettext_lazy as _

from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import ExtSchema
from mcod.core.serializers import CSVSchemaRegistrator, CSVSerializer
from mcod.lib.serializers import TranslatedStr


class FeedbackCounters(ExtSchema):
    plus = fields.Int(required=True)
    minus = fields.Int(required=True)


class SubmissionAttrs(ObjectAttrs):
    title = fields.Str(required=True, example="Very important data")
    notes = fields.Str(required=True, example="We need this data to save the world")
    organization_name = fields.Str(required=False, example="ACME")
    data_link = fields.Url(required=False, example="https://duckduckgo.com")
    potential_possibilities = fields.Str(required=False)
    submission_date = fields.Date(required=True)
    decision_date = fields.Date(required=True)
    published_at = fields.DateTime(required=True)
    feedback_counters = fields.Nested(FeedbackCounters, many=False)
    my_feedback = fields.Str(required=False)

    class Meta:
        object_type = "submission"
        path = "submissions"
        url_template = "{api_url}/submissions/accepted/{ident}"


class AcceptedSubmissionAttrs(SubmissionAttrs):
    title = TranslatedStr(required=True)
    notes = TranslatedStr(required=True)
    organization_name = TranslatedStr(required=True)
    potential_possibilities = TranslatedStr(required=True)


class PublicSubmissionAttrs(AcceptedSubmissionAttrs):

    class Meta(AcceptedSubmissionAttrs.Meta):
        url_template = "{api_url}/submissions/accepted/public/{ident}"


class AcceptedSubmissionApiResponse(TopLevel):
    class Meta:
        attrs_schema = AcceptedSubmissionAttrs


class SubmissionApiResponse(TopLevel):
    class Meta:
        attrs_schema = SubmissionAttrs


class PublicSubmissionApiResponse(TopLevel):
    class Meta:
        attrs_schema = PublicSubmissionAttrs


class DatasetSubmissionCSVSerializer(CSVSerializer, metaclass=CSVSchemaRegistrator):
    id = fields.Int(data_key="id", required=True, example=77)
    title = fields.Str(data_key=_("Title"), example="Propozycja nowych danych")
    notes = fields.Str(data_key=_("Notes"), default="", example="opis...")
    organization_name = fields.Str(data_key=_("Institution name"), default="", example="Ministerstwo Cyfryzacji")
    data_link = fields.Str(data_key=_("Link to data"), default="", example="http://example.com")
    potential_possibilities = fields.Str(data_key=_("provide potential data use"), default="", example="opis...")
    comment = fields.Str(data_key=_("Comment"), example="komentarz...", default="")
    submission_date = fields.Date(data_key=_("Submission date"))
    decision = fields.Str(data_key=_("decision"), example="accepted", default=_("Decision not taken"))
    decision_date = fields.Date(data_key=_("Decision date"), default=None)
    accepted_dataset_submission = fields.Int(
        data_key=_("accepted dataset submission"),
        attribute="accepted_dataset_submission.id",
        default=None,
    )

    class Meta:
        ordered = True
        model = "suggestions.DatasetSubmission"


class DatasetCommentCSVSerializer(CSVSerializer, metaclass=CSVSchemaRegistrator):
    id = fields.Int(data_key="id", required=True, example=77)
    title = fields.Str(
        data_key=_("Title"),
        attribute="dataset.title",
        example="Przykładowy zbiór danych",
    )
    comment = fields.Str(data_key=_("text of comment"), example="Treść uwagi...")
    editor_email = fields.Str(data_key=_("editor e-mail"), example="kontakt@dane.gov.pl")
    data_url = fields.Str(
        data_key=_("comment reported for dataset"),
        example="http://dane.gov.pl/dataset/1",
    )
    data_provider_url = fields.Str(data_key=_("Data provider"), example="http://dane.gov.pl/institution/1")
    editor_comment = fields.Str(data_key=_("comment"), example="Treść komentarza edytora...")
    report_date = fields.Date(data_key=_("report date"))
    is_data_provider_error = fields.Bool(data_key=_("data provider error"), example=False)
    is_user_error = fields.Bool(data_key=_("user error"), example=False)
    is_portal_error = fields.Bool(data_key=_("portal error"), example=False)
    is_other_error = fields.Bool(data_key=_("other error"), example=False)
    decision = fields.Str(data_key=_("Decision made"), example="accepted")
    decision_date = fields.Date(data_key=_("Decision date"), default="")

    class Meta:
        ordered = True
        fields = (
            "id",
            "title",
            "comment",
            "editor_email",
            "data_url",
            "data_provider_url",
            "editor_comment",
            "report_date",
            "is_data_provider_error",
            "is_user_error",
            "is_portal_error",
            "is_other_error",
            "decision",
            "decision_date",
        )
        model = "suggestions.DatasetComment"


class ResourceCommentCSVSerializer(DatasetCommentCSVSerializer):
    title = fields.Str(data_key=_("Title"), attribute="resource.title", example="Przykładowy zasób")
    data_url = fields.Str(data_key=_("comment reported for data"), example="http://dane.gov.pl/resource/1")

    class Meta(DatasetCommentCSVSerializer.Meta):
        model = "suggestions.ResourceComment"


class AcceptedSubmissionCommentAttrs(ObjectAttrs):
    is_comment_email_sent = fields.Bool(required=True)

    class Meta:
        object_type = "comment_confirmation"


class AcceptedSubmissionCommentApiResponse(TopLevel):
    class Meta:
        attrs_schema = AcceptedSubmissionCommentAttrs
        url_template = "{api_url}/submissions/accepted/public/{ident}/comment"
