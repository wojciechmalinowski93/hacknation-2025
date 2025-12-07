from django.core.paginator import Paginator

from mcod.core.db.managers import TrashManager
from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet, TrashQuerySet


class OrganizationQuerySetMixin:
    def get_filtered_results(self, **kwargs):
        query = {}
        if "agents__isnull" in kwargs:
            query["agents__isnull"] = kwargs["agents__isnull"]
        if "agents__id" in kwargs:
            query["agents__id"] = kwargs["agents__id"]
        return self.filter(**query).order_by("title")

    def _get_page(self, queryset, page=1, per_page=20, **kwargs):
        paginator = Paginator(queryset, per_page)
        return paginator.get_page(page)

    def get_page(self, **kwargs):
        return self._get_page(self.filter(), **kwargs)

    def get_paginated_results(self, **kwargs):
        qs = self.get_filtered_results(**kwargs)
        return self._get_page(qs, **kwargs)

    def private(self, **kwargs):
        return self.filter(institution_type=self.model.INSTITUTION_TYPE_PRIVATE)

    def public(self, **kwargs):
        return self.exclude(institution_type=self.model.INSTITUTION_TYPE_PRIVATE)


class OrganizationQuerySet(OrganizationQuerySetMixin, SoftDeletableQuerySet):

    def autocomplete(self, user, query=None):
        if not user.is_authenticated:
            return self.none()
        kwargs = {}
        if not user.is_superuser:
            kwargs["id__in"] = user.organizations.all()
        if query:
            kwargs["title__icontains"] = query
        return self.filter(**kwargs)


class OrganizationTrashQuerySet(OrganizationQuerySetMixin, TrashQuerySet):
    pass


class OrganizationManagerMixin:
    def get_paginated_results(self, **kwargs):
        return super().get_queryset().get_paginated_results(**kwargs)

    def get_page(self, **kwargs):
        return super().get_queryset().get_page(**kwargs)

    def private(self, **kwargs):
        return super().get_queryset().private(**kwargs)

    def public(self, **kwargs):
        return super().get_queryset().public(**kwargs)


class OrganizationManager(OrganizationManagerMixin, SoftDeletableManager):
    _queryset_class = OrganizationQuerySet

    def autocomplete(self, user, query=None):
        return super().get_queryset().autocomplete(user, query=query)


class OrganizationTrashManager(OrganizationManagerMixin, TrashManager):
    _queryset_class = OrganizationTrashQuerySet
