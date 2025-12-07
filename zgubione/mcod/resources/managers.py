from typing import List

from django.apps import apps
from django.conf import settings
from django.db.models import Count, Manager, Prefetch, Q
from django.db.models.query import QuerySet

from mcod.core.db.managers import TrashManager
from mcod.core.managers import RawDBManager, RawManager, SoftDeletableManager, SoftDeletableQuerySet
from mcod.resources.tasks import delete_es_resource_tabular_data_index


class ChartQuerySet(SoftDeletableQuerySet):

    def chart_for_user(self, user):
        default = self.filter(is_default=True).last()
        if user.is_authenticated:
            user_charts = self.filter(created_by=user)
            return user_charts.filter(is_default=False).last() or user_charts.filter(is_default=True).last() or default
        return default

    def chart_to_update(self, user, is_default):
        qs = self.filter(is_default=is_default)
        return qs.filter(created_by=user).last() or (qs.last() if is_default else None)

    def published(self):
        resource_model = apps.get_model("resources.Resource")
        return self.filter(
            resource__status=resource_model.STATUS.published,
            resource__is_removed=False,
        )


class ChartManager(SoftDeletableManager):
    _queryset_class = ChartQuerySet

    def chart_for_user(self, user):
        return self.get_queryset().chart_for_user(user)

    def chart_to_update(self, user, is_default):
        return self.get_queryset().chart_to_update(user, is_default)

    def published(self):
        return self.get_queryset().published()


class PrefetchResourceFilesMixin:

    def get_files_prefetch(self):
        resource_file = apps.get_model("resources", "ResourceFile")
        main_file = Prefetch("files", resource_file.objects.filter(is_main=True), to_attr="_cached_file")
        other_files = Prefetch("files", resource_file.objects.filter(is_main=False), to_attr="_other_files")
        return main_file, other_files


class AutocompleteMixin:

    def autocomplete(self, user, query=None, forwarded=None):
        if not user.is_authenticated:
            return self.none()

        forwarded = forwarded or {}
        dataset = forwarded.pop("dataset", None) or None
        resource_id = forwarded.pop("id", None)
        kwargs = {"dataset": dataset}
        if not user.is_superuser:
            kwargs["dataset__organization_id__in"] = user.organizations.all()
        if query:
            kwargs["title__icontains"] = query
        queryset = self.filter(**kwargs)
        return queryset.exclude(id=resource_id) if resource_id else queryset


class ResourceQuerySet(AutocompleteMixin, QuerySet):
    pass


class ResourceSoftDeletableMetadataQuerySet(AutocompleteMixin, PrefetchResourceFilesMixin, SoftDeletableQuerySet):

    def confirm_delete_items(self, limit=10):
        return self.order_by("title")[:limit]

    def with_metadata(self):
        tag_model = apps.get_model("tags", "Tag")
        res_filter = Q(
            dataset__resources__status="published",
            dataset__resources__is_removed=False,
            dataset__resources__is_permanently_removed=False,
        )
        dataset_filter = Q(
            dataset__organization__datasets__status="published",
            dataset__organization__datasets__is_removed=False,
            dataset__organization__datasets__is_permanently_removed=False,
        )
        org_res_filter = Q(
            dataset__organization__datasets__resources__status="published",
            dataset__organization__datasets__resources__is_removed=False,
            dataset__organization__datasets__resources__is_permanently_removed=False,
        )
        prefetch_tags_pl = Prefetch("dataset__tags", tag_model.objects.filter(language="pl"), to_attr="tags_pl")
        prefetch_tags_en = Prefetch("dataset__tags", tag_model.objects.filter(language="en"), to_attr="tags_en")
        return (
            self.published()
            .annotate(
                resources_count=Count("dataset__resources", filter=res_filter, distinct=True),
                datasets_count=Count(
                    "dataset__organization__datasets",
                    filter=dataset_filter,
                    distinct=True,
                ),
                organization_resources_count=Count(
                    "dataset__organization__datasets__resources",
                    filter=org_res_filter,
                    distinct=True,
                ),
            )
            .prefetch_related(
                "dataset__organization",
                prefetch_tags_pl,
                prefetch_tags_en,
                "dataset__categories",
            )
            .order_by("dataset_id", "id")
        )

    def with_tabular_data(self, **kwargs):
        formats = ("csv", "tsv", "xls", "xlsx", "ods", "shp")
        query = {
            "type": "file",
        }
        pks = kwargs.get("pks")
        if pks:
            query["pk__in"] = pks
        return self.by_formats(formats).filter(**query)

    def by_formats(self, formats):
        f_q = Q(format__in=formats) | Q(files__is_main=True, files__compressed_file_format__in=formats)
        q = Q(files__isnull=False) & f_q
        return self.filter(q).distinct()

    def published(self):
        return self.filter(status="published")

    def with_prefetched_files(self):
        main_file, other_files = self.get_files_prefetch()
        return self.prefetch_related(main_file, other_files)

    def with_files(self):
        return self.exclude(Q(file__isnull=True) | Q(file=""))

    def files_details_list(self, dataset_id):
        all_resource_files = (
            self.filter(status="published", dataset_id=dataset_id)
            .with_files()
            .values("file", "csv_file", "jsonld_file", "pk", "title")
        )
        files_details = []
        for res in all_resource_files:
            res_files = [(res["file"], res["pk"], res["title"])]
            if res["csv_file"]:
                res_files.append((res["csv_file"], res["pk"], res["title"]))
            if res["jsonld_file"]:
                res_files.append((res["jsonld_file"], res["pk"], res["title"]))
            files_details.extend(res_files)
        return files_details

    def exclude_internal_links(self):
        return self.exclude(Q(link__startswith=settings.API_URL) | Q(link__startswith=settings.BASE_URL))


class AutocompleteManagerMixin:

    def autocomplete(self, user, query=None, forwarded=None):
        return super().get_queryset().autocomplete(user, query=query, forwarded=forwarded)


class ResourceManager(AutocompleteManagerMixin, SoftDeletableManager):
    _queryset_class = ResourceSoftDeletableMetadataQuerySet

    def get_queryset(self):
        return super().get_queryset().with_prefetched_files()

    def with_metadata(self):
        return self.get_queryset().with_metadata()

    def with_tabular_data(self, **kwargs):
        return self.get_queryset().with_tabular_data(**kwargs)

    def with_ext_http_links_only(self) -> QuerySet:
        return self.get_queryset().filter(link__startswith="http://").exclude_internal_links()

    def published_with_ext_links_only(self) -> QuerySet:
        return self.get_queryset().filter(status="published", link__isnull=False).exclude_internal_links()

    def with_broken_links(self) -> QuerySet:
        return self.published_with_ext_links_only().filter(link_tasks_last_status="FAILURE")

    def by_formats(self, formats):
        return self.get_queryset().by_formats(formats)

    def published(self):
        return self.get_queryset().published()

    def with_files(self):
        return self.get_queryset().with_files()

    def file_details_list(self, dataset_id):
        return self.get_queryset().file_details_list(dataset_id)

    def confirm_delete_items(self, limit=10):
        return self.get_queryset().confirm_delete_items(limit=limit)


class ResourceRawManager(AutocompleteManagerMixin, PrefetchResourceFilesMixin, RawManager):
    _queryset_class = ResourceQuerySet

    def get_queryset(self):
        main_file, other_files = self.get_files_prefetch()
        return super().get_queryset().prefetch_related(main_file, other_files)


class ResourceRawDBManager(RawDBManager):
    _queryset_class = ResourceQuerySet


class ResourceFileManager(Manager):

    def files_details_list(self, dataset_id):
        return self.filter(
            resource__dataset_id=dataset_id,
            resource__status="published",
            resource__is_removed=False,
        ).values_list("file", "resource_id", "resource__title")


class SupplementManager(SoftDeletableManager):
    pass


class ResourceTrashQuerySet(QuerySet):
    def delete(self):
        # delete tabular data indexes connected with permanently removed resources
        resources_ids: List[int] = list(self.values_list("pk", flat=True))
        delete_es_resource_tabular_data_index.s(resources_ids).apply_async_on_commit()

        self.update(is_permanently_removed=True)


class ResourceTrashManager(TrashManager):
    _queryset_class = ResourceTrashQuerySet
