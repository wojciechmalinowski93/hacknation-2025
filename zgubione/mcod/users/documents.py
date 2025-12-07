from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.core.db.elastic import Document
from mcod.users.models import Meeting, MeetingFile


@registry.register_document
class MeetingDoc(Document):
    id = fields.IntegerField()
    title = fields.TextField()
    description = fields.TextField()
    venue = fields.TextField()
    start_date = fields.DateField()
    start_time = fields.KeywordField(attr="start_time_str")
    end_time = fields.KeywordField(attr="end_time_str")
    materials = fields.NestedField(
        properties={
            "id": fields.IntegerField(),
            "download_url": fields.KeywordField(),
            "name": fields.KeywordField(),
        }
    )

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["meetings"]
        settings = mcs.ELASTICSEARCH_DSL_INDEX_SETTINGS

    class Django:
        model = Meeting
        related_models = [
            MeetingFile,
        ]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, MeetingFile):
            return related_instance.meeting

    def get_queryset(self):
        return super().get_queryset().published()
