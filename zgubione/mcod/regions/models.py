from decimal import Decimal

from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from modeltrans.fields import TranslationField

from mcod.core.api.search.tasks import bulk_delete_documents_task, update_related_task
from mcod.core.db.models import BaseExtendedModel
from mcod.regions.api import PeliasApi, PlaceholderApi
from mcod.regions.managers import RegionManager
from mcod.regions.signals import regions_updated

# Create your models here.


class RegionManyToManyField(models.ManyToManyField):

    def save_form_data(self, instance, data):
        pks = frozenset(data)
        main_regions, additional_regions = self.save_regions_data(pks)
        self.set_regions(instance, main_regions, additional_regions)

    def save_harvester_data(self, instance, data):
        pelias = PeliasApi()
        pks = pelias.translate_teryt_to_wof_ids(data)
        self.save_form_data(instance, pks)

    def set_regions(self, instance, main_regions, additional_regions):
        instance._original_regions = list(getattr(instance, self.attname).values_list("pk", flat=True))
        getattr(instance, self.attname).clear()
        getattr(instance, self.attname).add(*main_regions)
        getattr(instance, self.attname).add(*additional_regions, through_defaults={"is_additional": True})
        regions_updated.send("resource.Resource", instance)

    def value_from_object(self, obj):
        return (
            []
            if obj.pk is None
            else list(getattr(obj, self.attname).filter(resourceregion__is_additional=False).values_list("region_id", flat=True))
        )

    @staticmethod
    def save_regions_data(values):
        main_regions = []
        additional_regions = []
        if values:
            placeholder = PlaceholderApi()
            pelias_api = PeliasApi()
            all_regions_list, wof_teryt_mapping = pelias_api.get_regions_details_by_teryt(values)
            reg_data = placeholder.convert_to_placeholder_format(all_regions_list, wof_teryt_mapping)
            pelias_api.fill_geonames_data(reg_data, wof_teryt_mapping)
            all_regions_ids = list(reg_data.keys())
            existing_regions = Region.objects.filter(region_id__in=all_regions_ids)
            existing_regions_ids = list(existing_regions.values_list("region_id", flat=True))
            to_create_regions_ids = set(all_regions_ids).difference(set(existing_regions_ids))
            to_create_regions = {reg_id: reg_data[str(reg_id)] for reg_id in to_create_regions_ids}
            created_regions = Region.objects.create_new_regions(to_create_regions)
            all_regions = list(existing_regions) + created_regions
            for reg in all_regions:
                if str(reg.region_id) in values:
                    main_regions.append(reg)
                else:
                    additional_regions.append(reg)
        return main_regions, additional_regions


class Region(BaseExtendedModel):
    HIERARCHY_MAPPING = {
        "country": 5,
        "region": 4,
        "county": 3,
        "localadmin": 2,
        "locality": 1,
    }
    REGION_TYPES = (
        ("locality", _("locality")),
        ("localadmin", _("localadmin")),
        ("county", _("county")),
        ("region", _("region")),
        ("country", _("country")),
    )
    name = models.CharField(max_length=150, verbose_name=_("title"))
    hierarchy_label = models.CharField(max_length=250, verbose_name=_("Hierarchy label"), null=True)
    region_id = models.CharField(max_length=10)
    region_type = models.CharField(max_length=15, choices=REGION_TYPES)
    bbox = JSONField(blank=True, null=True, verbose_name=_("Boundary box"))
    lat = models.DecimalField(max_digits=10, decimal_places=8, verbose_name=_("Latitude"))
    lng = models.DecimalField(max_digits=10, decimal_places=8, verbose_name=_("Longitude"))
    geonames_id = models.PositiveIntegerField(null=True, blank=True)

    @property
    def coords(self):
        return {"lat": self.lat, "lon": self.lng}

    @property
    def wkt_bbox(self):
        return f"BBOX ({self.bbox[0]},{self.bbox[2]},{self.bbox[3]},{self.bbox[1]})"

    @property
    def envelope(self):
        return {
            "type": "envelope",
            "coordinates": [
                [Decimal(self.bbox[0]), Decimal(self.bbox[3])],
                [Decimal(self.bbox[2]), Decimal(self.bbox[1])],
            ],
        }

    @property
    def wkt_centroid(self):
        return f"POINT ({self.lat} {self.lng})"

    @property
    def geonames_url(self):
        return f"http://sws.geonames.org/{self.geonames_id}/" if self.geonames_id is not None else None

    @property
    def hierarchy_level(self):
        return self.HIERARCHY_MAPPING[self.region_type]

    def __str__(self):
        return self.hierarchy_label_i18n

    i18n = TranslationField(fields=("name", "hierarchy_label"))

    objects = RegionManager()

    class Meta:
        indexes = [GinIndex(fields=["i18n"])]


class ResourceRegion(models.Model):
    region = models.ForeignKey("regions.Region", models.CASCADE)
    resource = models.ForeignKey("resources.Resource", models.CASCADE)
    is_additional = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ("region", "resource"),
        ]


@receiver(regions_updated, sender="resource.Resource")
def update_search_regions(sender, instance, *args, **kwargs):
    if instance.is_published:
        current = set(instance.regions.values_list("pk", flat=True))
        original = set(instance._original_regions)
        new = current.difference(original)
        deleted = original.difference(current)
        if new or deleted:
            to_update = Region.objects.assigned_regions(new)
            to_delete = Region.objects.unassigned_regions(deleted)
            if to_delete:
                bulk_delete_documents_task.s("regions", "Region", to_delete).apply_async_on_commit()
            if to_update:
                update_related_task.s("regions", "Region", to_update).apply_async_on_commit()
