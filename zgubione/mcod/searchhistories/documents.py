from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.core.db.elastic import Document
from mcod.searchhistories.models import SearchHistory


@registry.register_document
class SearchHistoriesDoc(Document):
    id = fields.IntegerField()
    url = fields.TextField()
    query_sentence = fields.TextField()
    query_sentence_keyword = fields.KeywordField(attr="query_sentence")
    user = fields.NestedField(
        attr="user",
        properties={
            "id": fields.IntegerField(),
        },
    )
    modified = fields.DateField()

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["searchhistories"]
        settings = mcs.ELASTICSEARCH_DSL_INDEX_SETTINGS

    class Django:
        model = SearchHistory
