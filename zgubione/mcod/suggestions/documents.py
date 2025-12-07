from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.core.db.elastic import Document
from mcod.lib.search.fields import TranslatedTextField
from mcod.suggestions.models import AcceptedDatasetSubmission, SubmissionFeedback


@registry.register_document
class AcceptedDatasetSubmissionDoc(Document):
    id = fields.IntegerField()
    is_active = fields.BooleanField()
    title = TranslatedTextField("title")
    notes = TranslatedTextField("notes")
    organization_name = TranslatedTextField("organization_name")
    potential_possibilities = TranslatedTextField("potential_possibilities")
    data_link = fields.TextField()
    comment = fields.TextField()
    submission_date = fields.DateField()
    decision = fields.TextField()
    decision_date = fields.DateField()
    published_at = fields.DateField()
    is_published_for_all = fields.BooleanField()

    feedback = fields.NestedField(properties={"user_id": fields.IntegerField(), "opinion": fields.TextField()})
    feedback_counters = fields.NestedField(
        properties={
            "plus": fields.IntegerField(),
            "minus": fields.IntegerField(),
        }
    )

    status = fields.TextField()

    def prepare_feedback(self, instance):
        return [{"user_id": fb.user.id, "opinion": fb.opinion} for fb in instance.feedback.all()]

    def prepare_feedback_counters(self, instance):
        return instance.feedback_counters

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["accepted_dataset_submissions"]
        settings = mcs.ELASTICSEARCH_DSL_INDEX_SETTINGS

    class Django:
        model = AcceptedDatasetSubmission
        related_models = [
            SubmissionFeedback,
        ]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, SubmissionFeedback):
            return related_instance.submission

    def get_queryset(self):
        return super().get_queryset().filter(status__in=AcceptedDatasetSubmission.PUBLISHED_STATUSES)
