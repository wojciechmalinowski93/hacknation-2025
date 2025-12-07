from django.conf import settings as mcs
from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod.core.api.search.analyzers import autocomplete_analyzers
from mcod.core.db.elastic import Document
from mcod.lib.search.fields import TranslatedTextField
from mcod.regions.models import Region


def regions_field(**kwargs):
    return fields.NestedField(
        properties={
            "region_id": fields.KeywordField(),
            "name": TranslatedTextField("name"),
            "hierarchy_label": TranslatedTextField("hierarchy_label"),
            "bbox": fields.GeoShapeField("wkt_bbox"),
            "coords": fields.GeoPointField(),
            "hierarchy_level": fields.IntegerField(),
        },
        **kwargs
    )


@registry.register_document
class RegionDocument(Document):
    region_id = fields.KeywordField()
    title = TranslatedTextField("name")
    hierarchy_label = TranslatedTextField("hierarchy_label", analyzers=autocomplete_analyzers)
    model = fields.KeywordField()
    created = fields.DateField()
    bbox = fields.GeoShapeField("envelope")
    hierarchy_level = fields.IntegerField()

    class Index:
        name = mcs.ELASTICSEARCH_INDEX_NAMES["regions"]
        settings = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_SETTINGS
        aliases = mcs.ELASTICSEARCH_DSL_SEARCH_INDEX_ALIAS

    class Django:
        model = Region

    def prepare_model(self, instance):
        return instance._meta.model_name

    def get_queryset(self):
        return super().get_queryset().all_assigned_regions()
