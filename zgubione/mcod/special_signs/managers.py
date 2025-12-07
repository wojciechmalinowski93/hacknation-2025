from mcod.core.db.managers import TrashManager
from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet


class SpecialSignQuerySet(SoftDeletableQuerySet):

    def published(self):
        return self.filter(status="published")


class SpecialSignManagerMixin:
    _queryset_class = SpecialSignQuerySet

    def published(self):
        return super().get_queryset().published()


class SpecialSignManager(SpecialSignManagerMixin, SoftDeletableManager):
    pass


class SpecialSignTrashManager(SpecialSignManagerMixin, TrashManager):
    pass
