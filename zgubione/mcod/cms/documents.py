from django.apps import apps
from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.lib.search.fields import TranslatedTextField
from mcod.search.documents import ExtendedDocument

KBPage = apps.get_model("cms", "KBPage")
NewsPage = apps.get_model("cms", "NewsPage")


@registry.register_document
class KBPageDocument(ExtendedDocument):
    NOTES_FIELD_NAME = "body"

    html_url = fields.KeywordField(attr="full_url")

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["knowledge_base_pages"]
        settings = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_SETTINGS
        aliases = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_ALIAS

    class Django:
        model = KBPage

    def get_queryset(self):
        return KBPage.objects.filter(live=True)

    def prepare_model(self, instance):
        return "knowledge_base"

    def prepare_search_date(self, instance):
        return instance.last_published_at


@registry.register_document
class NewsPageDocument(ExtendedDocument):
    NOTES_FIELD_NAME = "body"
    author_i18n = TranslatedTextField("author")
    html_url = fields.KeywordField(attr="full_url")

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["news"]
        settings = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_SETTINGS
        aliases = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_ALIAS

    class Django:
        model = NewsPage

    def get_queryset(self):
        return NewsPage.objects.filter(live=True)

    def prepare_model(self, instance):
        return "news"
