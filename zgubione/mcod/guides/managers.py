from mcod.core.db.managers import QuerySetMixin, TrashManager
from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet, TrashQuerySet


class GuideQuerySetMixin(QuerySetMixin):
    def published(self):
        return self.filter(status="published")


class GuideQuerySet(GuideQuerySetMixin, SoftDeletableQuerySet):
    pass


class GuideTrashQuerySet(GuideQuerySetMixin, TrashQuerySet):
    pass


class GuideManagerMixin:
    def get_paginated_results(self, **kwargs):
        return super().get_queryset().get_paginated_results(**kwargs)


class GuideManager(GuideManagerMixin, SoftDeletableManager):
    _queryset_class = GuideQuerySet

    def published(self):
        return super().get_queryset().published()


class GuideTrashManager(GuideManagerMixin, TrashManager):
    _queryset_class = GuideTrashQuerySet
