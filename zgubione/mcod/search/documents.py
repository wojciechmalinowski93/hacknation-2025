from django_elasticsearch_dsl import fields

from mcod import settings
from mcod.core.api.search.analyzers import lang_exact_analyzers, lang_synonyms_analyzers
from mcod.core.db.elastic import Document, NonIndexableValue
from mcod.lib.search.fields import TranslatedSuggestField, TranslatedTextField
from mcod.watchers.models import ModelWatcher


class ExtendedDocument(Document):
    NOTES_FIELD_NAME = "notes"
    id = fields.IntegerField()
    model = fields.KeywordField()
    slug = TranslatedTextField("slug")
    title = TranslatedSuggestField("title")
    title_synonyms = TranslatedTextField("title", analyzers=lang_synonyms_analyzers)
    title_exact = TranslatedTextField("title", analyzers=lang_exact_analyzers)
    notes = TranslatedTextField(NOTES_FIELD_NAME)
    notes_synonyms = TranslatedTextField(NOTES_FIELD_NAME, analyzers=lang_synonyms_analyzers)
    notes_exact = TranslatedTextField(NOTES_FIELD_NAME, analyzers=lang_exact_analyzers)
    keywords = fields.NestedField(properties={"name": fields.KeywordField(), "language": fields.KeywordField()})
    modified = fields.DateField()
    created = fields.DateField()
    verified = fields.DateField()
    search_date = fields.DateField()
    search_type = fields.KeywordField()
    status = fields.KeywordField()
    visualization_types = fields.KeywordField(multi=True)
    subscriptions = fields.NestedField(
        properties={
            "user_id": fields.IntegerField(),
            "subscription_id": fields.IntegerField(),
        }
    )
    views_count = fields.IntegerField()

    def prepare_notes(self, instance):
        notes = getattr(instance, f"{self.NOTES_FIELD_NAME}_translated")
        return {lang_code: getattr(notes, lang_code) for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES}

    prepare_notes_synonyms = prepare_notes
    prepare_notes_exact = prepare_notes

    def prepare_model(self, instance):
        return instance._meta.model_name

    def prepare_search_date(self, instance):
        return instance.created

    def prepare_keywords(self, instance):
        return getattr(instance, "keywords_list", NonIndexableValue)

    def prepare_verified(self, instance):
        return getattr(instance, "verified", NonIndexableValue)

    def prepare_search_type(self, instance):
        return getattr(instance, "search_type", NonIndexableValue)

    def prepare_visualization_types(self, instance):
        visualization_types = getattr(instance, "visualization_types", NonIndexableValue)
        if isinstance(visualization_types, (tuple, list)) and len(visualization_types) == 0:
            visualization_types = ["none"]
        return visualization_types

    def prepare_subscriptions(self, instance):
        try:
            watcher = ModelWatcher.objects.get_from_instance(instance)
            return [
                {"user_id": subscription.user_id, "subscription_id": subscription.id}
                for subscription in watcher.subscriptions.all()
            ]
        except ModelWatcher.DoesNotExist:
            return []

    def get_queryset(self):
        return super().get_queryset().filter(status="published")
