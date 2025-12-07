from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.db.models import Count, Max, Prefetch, Q

from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet
from mcod.datasets.utils import _batch_qs


class DatasetQuerySet(SoftDeletableQuerySet):

    def autocomplete(self, user, query=None):
        if not user.is_authenticated:
            return self.none()

        kwargs = {"status": self.model.STATUS.published}
        if not user.is_superuser:
            kwargs["organization_id__in"] = user.organizations.all()
        if query:
            kwargs["title__icontains"] = query
        return self.filter(**kwargs)

    def _with_metadata_prefetched(self, queryset):
        resource_model = apps.get_model("resources", "Resource")
        tag_model = apps.get_model("tags", "Tag")

        prefetch_published_resources = Prefetch(
            "resources",
            resource_model.objects.filter(status="published"),
            to_attr="published_resources",
        )

        prefetch_tags_pl = Prefetch("tags", tag_model.objects.filter(language="pl"), to_attr="tags_pl")
        prefetch_tags_en = Prefetch("tags", tag_model.objects.filter(language="en"), to_attr="tags_en")

        return queryset.prefetch_related(
            prefetch_published_resources,
            prefetch_tags_pl,
            prefetch_tags_en,
            "categories",
        ).select_related(
            "organization",
        )

    def _with_metadata_annotated(self, queryset):
        return queryset.annotate(
            published_resources__count=Count(
                "resources",
                filter=Q(
                    resources__status="published",
                    resources__is_removed=False,
                    resources__is_permanently_removed=False,
                ),
                distinct=True,
            ),
            organization_published_datasets__count=Count(
                "organization__datasets",
                filter=Q(
                    organization__datasets__status="published",
                    organization__datasets__is_removed=False,
                    organization__datasets__is_permanently_removed=False,
                ),
                distinct=True,
            ),
            organization_published_resources__count=Count(
                "organization__datasets__resources",
                filter=Q(
                    organization__datasets__resources__status="published",
                    organization__datasets__resources__is_removed=False,
                    organization__datasets__resources__is_permanently_removed=False,
                ),
                distinct=True,
            ),
        )

    def with_metadata_fetched_as_list(self):
        base_queryset = self.filter(status="published")
        queryset = self._with_metadata_prefetched(base_queryset)
        annotated_queryset = self._with_metadata_annotated(base_queryset.values("id"))

        id_to_extra_attrs = {
            dataset["id"]: {
                "published_resources__count": dataset["published_resources__count"],
                "organization_published_datasets__count": dataset["organization_published_datasets__count"],
                "organization_published_resources__count": dataset["organization_published_resources__count"],
            }
            for dataset in annotated_queryset
        }

        data = []
        for start, end, total, qs in _batch_qs(queryset):
            for dataset in qs:
                attrs = id_to_extra_attrs.get(dataset.id, {})
                for key, value in attrs.items():
                    setattr(dataset, key, value)
                data.append(dataset)

        return data

    def with_metadata_fetched(self):
        queryset = self.filter(status="published")
        queryset = self._with_metadata_prefetched(queryset)
        queryset = self._with_metadata_annotated(queryset)
        return queryset

    def datasets_to_notify(self):
        freq_updates_with_delays = {
            "yearly": {"default_delay": 7, "relative_delta": relativedelta(years=1)},
            "everyHalfYear": {
                "default_delay": 7,
                "relative_delta": relativedelta(months=6),
            },
            "quarterly": {
                "default_delay": 7,
                "relative_delta": relativedelta(months=3),
            },
            "monthly": {"default_delay": 3, "relative_delta": relativedelta(months=1)},
            "weekly": {"default_delay": 1, "relative_delta": relativedelta(days=7)},
        }
        qs = (
            self.filter(
                status="published",
                source__isnull=True,
                is_update_notification_enabled=True,
                update_frequency__in=list(freq_updates_with_delays.keys()),
            )
            .exclude(Q(resources__type="api") | Q(resources__type="website"))
            .annotate(
                max_data_date=Max(
                    "resources__data_date",
                    filter=Q(
                        resources__is_removed=False,
                        resources__is_permanently_removed=False,
                        resources__status="published",
                    ),
                )
            )
            .exclude(max_data_date__isnull=True)
        )
        q = None
        for freq, freq_details in freq_updates_with_delays.items():
            custom_delays = list(
                qs.filter(update_frequency=freq, update_notification_frequency__isnull=False)
                .exclude(update_notification_frequency=freq_details["default_delay"])
                .values_list("update_notification_frequency", flat=True)
                .distinct()
            )
            default_upcoming_date = (datetime.today().date() + relativedelta(days=freq_details["default_delay"])) - freq_details[
                "relative_delta"
            ]
            delays_q = (
                Q(update_frequency=freq)
                & (Q(update_notification_frequency__isnull=True) | Q(update_notification_frequency=freq_details["default_delay"]))
                & Q(max_data_date=default_upcoming_date)
            )
            if q is None:
                q = delays_q
            else:
                q |= delays_q
            for delay in custom_delays:
                custom_upcoming_date = (datetime.today().date() + relativedelta(days=delay)) - freq_details["relative_delta"]
                delay_q = (
                    Q(update_frequency=freq) & Q(update_notification_frequency=delay) & Q(max_data_date=custom_upcoming_date)
                )
                q |= delay_q

        return qs.filter(q).select_related("modified_by")


class DatasetManager(SoftDeletableManager):
    _queryset_class = DatasetQuerySet

    def autocomplete(self, user, query=None):
        return super().get_queryset().autocomplete(user, query=query)

    def with_metadata_fetched(self):
        return super().get_queryset().with_metadata_fetched()

    def with_metadata_fetched_as_list(self):
        return super().get_queryset().with_metadata_fetched_as_list()

    def datasets_to_notify(self):
        return super().get_queryset().datasets_to_notify()


class SupplementManager(SoftDeletableManager):
    pass
