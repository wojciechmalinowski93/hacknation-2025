from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings
from mcod.core.db.elastic import Document
from mcod.laboratory.models import LabEvent, LabReport
from mcod.lib.search.fields import TranslatedTextField


@registry.register_document
class LabEventDoc(Document):
    id = fields.IntegerField()
    title = TranslatedTextField("title")
    notes = TranslatedTextField("notes")
    event_type = fields.KeywordField()
    execution_date = fields.DateField()
    reports = fields.NestedField(
        properties={
            "type": fields.KeywordField(attr="report_type"),
            "download_url": fields.TextField(),
            "link": fields.TextField(),
        }
    )

    class Index:
        name = settings.ELASTICSEARCH_INDEX_NAMES["lab_events"]
        settings = settings.ELASTICSEARCH_DSL_INDEX_SETTINGS

    class Django:
        model = LabEvent
        related_models = [
            LabReport,
        ]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, LabReport):
            return related_instance.lab_event

    def get_queryset(self):
        return super().get_queryset().filter(status="published")
