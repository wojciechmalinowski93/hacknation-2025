import factory
from django.contrib.contenttypes.models import ContentType

from mcod.core.registries import factories_registry
from mcod.datasets.models import Dataset
from mcod.histories.models import LogEntry


class LogEntryFactory(factory.django.DjangoModelFactory):
    content_type_id = factory.LazyAttribute(lambda _: ContentType.objects.get_for_model(Dataset).id)
    action = factory.Faker(
        "random_element",
        elements=[
            LogEntry.Action.CREATE,
            LogEntry.Action.UPDATE,
            LogEntry.Action.DELETE,
        ],
    )

    class Meta:
        model = LogEntry


factories_registry.register("log entry", LogEntryFactory)
