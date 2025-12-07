from django.db import models

from mcod.core.db.managers import PermanentlyRemovedManager, TrashManager
from mcod.core.managers import RawManager, SoftDeletableManager


class SoftDeletableModel(models.Model):
    is_removed = models.BooleanField(default=False)
    is_permanently_removed = models.BooleanField(default=False)

    class Meta:
        abstract = True

    objects = SoftDeletableManager()
    orig = models.Manager()
    raw = RawManager()
    trash = TrashManager()
    permanently_removed = PermanentlyRemovedManager()

    def delete(self, using=None, soft=True, permanent=False, *args, **kwargs):
        if soft:
            if self.is_removed:
                self.is_permanently_removed = True
            else:
                self.is_removed = True
                if permanent:
                    self.is_permanently_removed = True
            self.save(using=using)
        else:
            return super().delete(using=using, *args, **kwargs)
