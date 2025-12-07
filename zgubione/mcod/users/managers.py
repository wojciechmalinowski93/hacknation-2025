from mcod.core.db.managers import TrashManager
from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet, TrashQuerySet


class MeetingQuerySetMixin:
    def published(self):
        return self.filter(status="published")


class MeetingQuerySet(MeetingQuerySetMixin, SoftDeletableQuerySet):
    pass


class MeetingTrashQuerySet(MeetingQuerySetMixin, TrashQuerySet):
    pass


class MeetingManager(SoftDeletableManager):
    _queryset_class = MeetingQuerySet

    def published(self):
        return super().get_queryset().published()


class MeetingTrashManager(TrashManager):
    _queryset_class = MeetingTrashQuerySet


class MeetingFileManager(SoftDeletableManager):
    _queryset_class = SoftDeletableQuerySet


class MeetingFileTrashManager(TrashManager):
    _queryset_class = TrashQuerySet
