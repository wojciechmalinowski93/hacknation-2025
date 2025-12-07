from mcod.core.db.managers import (
    DecisionSortableManagerMixin,
    DecisionSortableSoftDeletableQuerySet,
    DecisionSortableTrashQuerySet,
    TrashManager,
)
from mcod.core.managers import SoftDeletableManager


class AcceptedDatasetSubmissionManagerMixin:
    def active(self):
        return super().get_queryset().active()

    def inactive(self):
        return super().get_queryset().inactive()


class AcceptedDatasetSubmissionQuerySetMixin:
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)


class AcceptedDatasetSubmissionQuerySet(AcceptedDatasetSubmissionQuerySetMixin, DecisionSortableSoftDeletableQuerySet):
    pass


class AcceptedDatasetSubmissionTrashQuerySet(AcceptedDatasetSubmissionQuerySetMixin, DecisionSortableTrashQuerySet):
    pass


class DatasetCommentManager(DecisionSortableManagerMixin, SoftDeletableManager):
    _queryset_class = DecisionSortableSoftDeletableQuerySet


class DatasetCommentTrashManager(DecisionSortableManagerMixin, TrashManager):
    _queryset_class = DecisionSortableTrashQuerySet


class DatasetSubmissionManager(DecisionSortableManagerMixin, SoftDeletableManager):
    _queryset_class = DecisionSortableSoftDeletableQuerySet


class DatasetSubmissionTrashManager(DecisionSortableManagerMixin, TrashManager):
    _queryset_class = DecisionSortableTrashQuerySet


class AcceptedDatasetSubmissionManager(AcceptedDatasetSubmissionManagerMixin, DatasetSubmissionManager):
    _queryset_class = AcceptedDatasetSubmissionQuerySet


class AcceptedDatasetSubmissionTrashManager(AcceptedDatasetSubmissionManagerMixin, DatasetSubmissionTrashManager):
    _queryset_class = AcceptedDatasetSubmissionTrashQuerySet


class ResourceCommentManager(DecisionSortableManagerMixin, SoftDeletableManager):
    _queryset_class = DecisionSortableSoftDeletableQuerySet


class ResourceCommentTrashManager(DecisionSortableManagerMixin, TrashManager):
    _queryset_class = DecisionSortableTrashQuerySet
