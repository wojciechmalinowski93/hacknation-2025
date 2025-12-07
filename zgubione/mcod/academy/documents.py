from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.academy.models import Course, CourseModule
from mcod.core.db.elastic import Document


@registry.register_document
class CourseDoc(Document):
    id = fields.IntegerField()
    title = fields.TextField()
    notes = fields.TextField()
    participants_number = fields.IntegerField()
    venue = fields.TextField()
    start = fields.DateField()
    end = fields.DateField()
    file_type = fields.KeywordField()
    file_url = fields.KeywordField()
    materials_file_type = fields.KeywordField()
    materials_file_url = fields.KeywordField()
    sessions = fields.NestedField(
        properties={
            "id": fields.IntegerField(),
            "type": fields.KeywordField(),
            "type_name": fields.KeywordField(),
            "start": fields.DateField(),
            "end": fields.DateField(),
        }
    )

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["courses"]
        settings = mcs.ELASTICSEARCH_DSL_INDEX_SETTINGS

    class Django:
        model = Course
        related_models = [
            CourseModule,
        ]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, CourseModule):
            return related_instance.course

    def get_queryset(self):
        return super().get_queryset().published()
