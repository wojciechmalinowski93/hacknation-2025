from datetime import date

from django.db import models
from modeltrans.manager import MultilingualManager


class ResourceCounter(models.Model):

    resource = models.ForeignKey("resources.Resource", on_delete=models.CASCADE)
    timestamp = models.DateField(default=date.today)
    count = models.IntegerField(default=0)

    objects = MultilingualManager()

    class Meta:
        abstract = True


class ResourceViewCounter(ResourceCounter):
    pass


class ResourceDownloadCounter(ResourceCounter):
    pass
