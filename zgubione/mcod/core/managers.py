from django.db import models
from django.db.models import QuerySet


class SoftDeletableQuerySet(QuerySet):
    def delete(self):
        self.update(is_removed=True)


class SoftDeletableManagerMixin:
    _queryset_class = SoftDeletableQuerySet

    def get_queryset(self):
        kwargs = {"model": self.model, "using": self._db}
        if hasattr(self, "_hints"):
            kwargs["hints"] = self._hints

        return self._queryset_class(**kwargs).filter(is_removed=False, is_permanently_removed=False)


class SoftDeletableManager(SoftDeletableManagerMixin, models.Manager):
    pass


class TrashQuerySet(QuerySet):
    def delete(self):
        self.update(is_permanently_removed=True)


class RawManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_permanently_removed=False)


class RawDBManager(models.Manager):
    """Returns all objects from DB"""

    ...
