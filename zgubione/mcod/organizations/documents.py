from django.apps import apps
from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.core.api.search.normalizers import keyword_uppercase
from mcod.datasets.documents import datasets_field
from mcod.lib.search.fields import TranslatedTextField
from mcod.search.documents import ExtendedDocument

Organization = apps.get_model("organizations", "Organization")
Dataset = apps.get_model("datasets", "Dataset")
Resource = apps.get_model("resources", "Resource")


@registry.register_document
class InstitutionDocument(ExtendedDocument):
    NOTES_FIELD_NAME = "description"
    image_url = fields.TextField()
    abbreviation = fields.KeywordField(normalizer=keyword_uppercase)
    postal_code = fields.KeywordField()
    city = fields.KeywordField()
    street_type = fields.KeywordField()
    street = fields.KeywordField()
    street_number = fields.KeywordField()
    flat_number = fields.KeywordField()
    email = fields.KeywordField()
    epuap = fields.KeywordField()
    fax = fields.KeywordField(attr="fax_display")
    tel = fields.KeywordField(attr="phone_display")
    electronic_delivery_address = fields.KeywordField()
    regon = fields.KeywordField()
    website = fields.KeywordField()
    institution_type = fields.KeywordField()
    published_datasets_count = fields.IntegerField()
    published_resources_count = fields.IntegerField()
    sources = fields.NestedField(
        properties={
            "title": fields.TextField(),
            "url": fields.TextField(),
            "source_type": fields.TextField(),
        }
    )

    description = TranslatedTextField("description")
    published_datasets = datasets_field()
    published_resources = fields.NestedField(
        properties={
            "id": fields.IntegerField(),
        }
    )

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["institutions"]
        settings = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_SETTINGS
        aliases = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_ALIAS

    class Django:
        model = Organization
        related_models = [Dataset, Resource]

    def prepare_model(self, instance):
        return "institution"

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Dataset):
            return related_instance.organization
        elif isinstance(related_instance, Resource):
            return related_instance.dataset.organization
