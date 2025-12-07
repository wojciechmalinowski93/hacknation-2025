from mcod.core.db.managers import TrashManager
from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet, TrashQuerySet


class ShowcaseProposalQuerySetMixin:
    def with_decision(self):
        return self.exclude(decision="")

    def without_decision(self):
        return self.filter(decision="")


class ShowcaseProposalQuerySet(ShowcaseProposalQuerySetMixin, SoftDeletableQuerySet):
    pass


class ShowcaseProposalTrashQuerySet(ShowcaseProposalQuerySetMixin, TrashQuerySet):
    pass


class ShowcaseProposalManagerMixin:
    def with_decision(self):
        return super().get_queryset().with_decision()

    def without_decision(self):
        return super().get_queryset().without_decision()


class ShowcaseManager(SoftDeletableManager):
    pass


class ShowcaseTrashManager(TrashManager):
    pass


class ShowcaseProposalManager(ShowcaseProposalManagerMixin, SoftDeletableManager):
    _queryset_class = ShowcaseProposalQuerySet


class ShowcaseProposalTrashManager(ShowcaseProposalManagerMixin, TrashManager):
    _queryset_class = ShowcaseProposalTrashQuerySet
