from mcod.core.managers import SoftDeletableManager, SoftDeletableQuerySet


class DataSourceQuerySet(SoftDeletableQuerySet):

    def active(self):
        return self.filter(status="active")

    def inactive(self):
        return self.filter(status="inactive")


class DataSourceManager(SoftDeletableManager):
    _queryset_class = DataSourceQuerySet

    def active(self):
        return super().get_queryset().active()

    def inactive(self):
        return super().get_queryset().inactive()
