from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import Case, F, Q, Value, When


class RegionQueryset(models.QuerySet):

    def count_resources(self):
        return self.annotate(
            resources_count=models.Count(
                "resource",
                filter=Q(
                    resource__status="published",
                    resource__is_removed=False,
                    resource__is_permanently_removed=False,
                ),
            )
        )

    def _filter_by_res_count(self, ids, count_val):
        count_q = Q(resources_count=count_val) if count_val == 0 else Q(resources_count__gte=count_val)
        return list(self.filter(pk__in=ids).count_resources().filter(count_q).values_list("pk", flat=True))

    def unassigned_regions(self, region_ids):
        return self._filter_by_res_count(region_ids, 0)

    def assigned_regions(self, region_ids):
        return self._filter_by_res_count(region_ids, 1)

    def all_assigned_regions(self):
        return self.count_resources().filter(Q(resources_count__gte=1) | Q(region_id=settings.DEFAULT_REGION_ID))

    def annotate_is_additional(self, default_is_additional):
        return self.annotate(
            is_additional=Case(
                When(
                    region_id=settings.DEFAULT_REGION_ID,
                    then=Value(default_is_additional),
                ),
                default=F("resourceregion__is_additional"),
                output_field=models.BooleanField(),
            )
        )


class RegionManager(models.Manager):

    def get_queryset(self):
        return RegionQueryset(self.model, using=self._db)

    def create_new_regions(self, to_create_regions):
        region = apps.get_model("regions", "region")
        to_create_regions_obj = []
        for reg_id, reg_data in to_create_regions.items():
            _bbox = reg_data["geom"]["bbox"].split(",")
            # If both bbox coordinates are the same points, ES throws 'malformed shape error',
            # so we 'enlarge' the shape a little.
            if _bbox[0] == _bbox[2] and _bbox[1] == _bbox[3]:
                coords = [Decimal(_bbox[2]), Decimal(_bbox[3])]
                edited_coords = [coord + Decimal("0.000000001") for coord in coords]
                _bbox[2] = str(edited_coords[0])
                _bbox[3] = str(edited_coords[1])
            region_props = dict(
                region_id=reg_id,
                region_type=reg_data["placetype"],
                name_pl=(reg_data["names"]["pol"][0] if reg_data["names"].get("pol") else reg_data["name"]),
                name_en=(reg_data["names"]["eng"][0] if reg_data["names"].get("eng") else reg_data["name"]),
                hierarchy_label_pl=reg_data["hierarchy_label_pl"],
                hierarchy_label_en=reg_data["hierarchy_label_en"],
                bbox=_bbox,
                lat=reg_data["geom"]["lat"],
                lng=reg_data["geom"]["lon"],
            )
            gn_id = reg_data.get("geonames_id")
            if gn_id:
                region_props["geonames_id"] = gn_id
            to_create_regions_obj.append(region(**region_props))
        created_regions = self.bulk_create(to_create_regions_obj)
        return created_regions

    def unassigned_regions(self, region_ids):
        return self.get_queryset().unassigned_regions(region_ids)

    def assigned_regions(self, region_ids):
        return self.get_queryset().assigned_regions(region_ids)

    def all_assigned_regions(self):
        return self.get_queryset().all_assigned_regions()

    def annotate_is_additional(self, default_is_additional=False):
        return self.get_queryset().annotate_is_additional(default_is_additional)

    def for_dataset_with_id(self, dataset_id, has_no_region_resources):
        q = Q(
            resourceregion__resource__dataset_id=dataset_id,
            resourceregion__resource__is_removed=False,
            resourceregion__resource__status="published",
        )
        default_is_additional = not has_no_region_resources
        q |= Q(region_id=settings.DEFAULT_REGION_ID)
        return self.get_queryset().filter(q).annotate_is_additional(default_is_additional).distinct().order_by("pk")

    def for_resource_with_id(self, resource_id, has_other_regions):
        q = Q(resourceregion__resource_id=resource_id) | Q(region_id=settings.DEFAULT_REGION_ID)
        return self.get_queryset().filter(q).annotate_is_additional(has_other_regions).order_by("pk")
