import datetime

import factory

from mcod.core.registries import factories_registry
from mcod.counters.models import ResourceDownloadCounter, ResourceViewCounter
from mcod.resources.factories import ResourceFactory


class ResourceViewCounterFactory(factory.django.DjangoModelFactory):
    resource = factory.SubFactory(ResourceFactory)
    count = factory.Faker("random_int", min=0, max=500)
    timestamp = factory.Faker(
        "date",
        end_datetime=datetime.date.today(),
    )

    class Meta:
        model = ResourceViewCounter


class ResourceDownloadCounterFactory(factory.django.DjangoModelFactory):
    resource = factory.SubFactory(ResourceFactory)
    count = factory.Faker("random_int", min=0, max=500)
    timestamp = factory.Faker(
        "date",
        end_datetime=datetime.date.today(),
    )

    class Meta:
        model = ResourceDownloadCounter


factories_registry.register("resource_view_counter", ResourceViewCounterFactory)
factories_registry.register("resource_download_counter", ResourceDownloadCounterFactory)
