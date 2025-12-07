from django.apps import apps
from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod import settings as mcs
from mcod.harvester.serializers import DataSourceSerializer
from mcod.lib.search.fields import TranslatedKeywordField, TranslatedTextField
from mcod.regions.documents import regions_field
from mcod.search.documents import ExtendedDocument
from mcod.users.models import UserFollowingDataset

Dataset = apps.get_model("datasets", "Dataset")
Organization = apps.get_model("organizations", "Organization")
Category = apps.get_model("categories", "Category")
Tag = apps.get_model("tags", "Tag")
Resource = apps.get_model("resources", "Resource")
DataSource = apps.get_model("harvester", "DataSource")
Showcase = apps.get_model("showcases", "Showcase")


def datasets_field(**kwargs):
    return fields.NestedField(
        properties={
            "id": fields.IntegerField(),
            "title": TranslatedTextField("title"),
            "notes": TranslatedTextField("notes"),
            "category": fields.KeywordField(attr="category.title"),
            "formats": fields.KeywordField(attr="formats", multi=True),
            "downloads_count": fields.IntegerField(attr="computed_downloads_count"),
            "views_count": fields.IntegerField(attr="computed_views_count"),
            "openness_scores": fields.IntegerField(attr="openness_scores"),
            "modified": fields.DateField(),
            "slug": TranslatedKeywordField("slug"),
            "verified": fields.DateField(),
        },
        **kwargs
    )


@registry.register_document
class DatasetDocument(ExtendedDocument):
    license_chosen = fields.IntegerField()
    license_condition_db_or_copyrighted = fields.TextField()
    license_condition_personal_data = fields.TextField()
    license_condition_original = fields.BooleanField()
    license_condition_timestamp = fields.BooleanField()
    license_name = fields.TextField()
    license_description = fields.TextField()
    license_condition_custom_description = fields.TextField()
    license_condition_default_cc40 = fields.BooleanField()
    resource_modified = fields.DateField(attr="last_modified_resource")
    url = fields.KeywordField()
    source = fields.NestedField(
        properties={
            "title": fields.TextField(),
            "source_type": fields.TextField(),
            "url": fields.TextField(),
            "update_frequency": TranslatedTextField("update_frequency"),
            "last_import_timestamp": fields.DateField(),
        }
    )

    formats = fields.KeywordField(multi=True)
    types = fields.KeywordField(multi=True)
    openness_scores = fields.IntegerField(multi=True)
    institution = fields.NestedField(
        attr="organization",
        properties={
            "id": fields.IntegerField(),
            "title": TranslatedTextField("title"),
            "slug": TranslatedTextField("slug"),
        },
    )
    category = fields.NestedField(
        properties={
            "id": fields.IntegerField(attr="id"),
            "image_url": fields.KeywordField(),
            "title": TranslatedTextField("title"),
            "description": TranslatedTextField("description"),
        }
    )
    categories = fields.NestedField(
        properties={
            "id": fields.IntegerField(attr="id"),
            "image_url": fields.KeywordField(),
            "code": fields.KeywordField(),
            "title": TranslatedTextField("title"),
            "description": TranslatedTextField("description"),
        }
    )
    downloads_count = fields.IntegerField()
    image_url = fields.TextField()
    image_alt = TranslatedTextField("image_alt")

    version = fields.KeywordField()
    source_title = fields.TextField()
    source_type = fields.TextField()
    source_url = fields.TextField()

    resources = fields.NestedField(properties={"id": fields.IntegerField(), "title": TranslatedTextField("title")})
    showcases = fields.NestedField(
        attr="showcases_published",
        properties={"id": fields.IntegerField(), "title": TranslatedTextField("title")},
    )
    supplement_docs = fields.NestedField(
        properties={
            "id": fields.IntegerField(),
            "name": TranslatedTextField("name"),
            "api_file_url": fields.TextField(),
            "file_size": fields.LongField(),
            "language": fields.KeywordField(),
        }
    )

    update_frequency = fields.KeywordField()
    users_following = fields.KeywordField(attr="users_following_list", multi=True)
    last_modified_resource = fields.DateField(attr="last_modified_resource")

    license_code = fields.IntegerField()
    computed_downloads_count = fields.IntegerField()
    computed_views_count = fields.IntegerField()
    has_dynamic_data = fields.BooleanField()
    has_high_value_data = fields.BooleanField()
    has_high_value_data_from_ec_list = fields.BooleanField()
    has_research_data = fields.BooleanField()
    is_promoted = fields.BooleanField()
    regions = regions_field()

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["datasets"]
        settings = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_SETTINGS
        aliases = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_ALIAS

    class Django:
        model = Dataset
        related_models = [
            Category,
            DataSource,
            Organization,
            Resource,
            Showcase,
            UserFollowingDataset,
        ]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Resource):
            return related_instance.dataset
        if isinstance(related_instance, Category):
            return related_instance.dataset_set.filter(status="published")
        if isinstance(related_instance, Organization):
            return related_instance.datasets.filter(status="published")
        if isinstance(related_instance, DataSource):
            return related_instance.datasource_datasets.filter(status="published")
        if isinstance(related_instance, Showcase):
            return related_instance.datasets.filter(status="published")

    def prepare_search_date(self, instance):
        return instance.verified

    def prepare_source(self, instance):
        serializer = DataSourceSerializer()
        if not instance.source:
            return {}
        return serializer.dump(instance.source)
