from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.core.db.elastic import Document
from mcod.histories.models import LogEntry


@registry.register_document
class LogEntryDoc(Document):
    table_name = fields.TextField()
    row_id = fields.IntegerField()
    action_name = fields.TextField()
    id = fields.IntegerField()
    difference = fields.TextField()
    change_user_id = fields.IntegerField()
    change_timestamp = fields.DateField()
    message = fields.TextField()

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["logentries"]
        settings = {"number_of_shards": 3, "number_of_replicas": 1}

    class Django:
        model = LogEntry

    def get_queryset(self):
        return LogEntry.objects.for_admin_panel(exclude_models=["user"])

    def get_queryset_count(self):
        return LogEntry.objects.for_admin_panel(exclude_models=["user"]).count()
