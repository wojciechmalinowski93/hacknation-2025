import factory

from mcod.core.registries import factories_registry
from mcod.users.factories import UserFactory
from mcod.watchers import models

_NOTIFICATION_TYPES = [i[0] for i in models.NOTIFICATION_TYPES]
_NOTIFICATION_STATUS_CHOICES = [i[0] for i in models.NOTIFICATION_STATUS_CHOICES]


class ModelWatcherFactory(factory.django.DjangoModelFactory):
    watcher_type = "model"
    object_name = factory.Sequence(lambda n: "object_%s" % n)
    object_ident = factory.Sequence(lambda n: "object_id_%s" % n)
    ref_field = "modified"
    ref_value = factory.Faker("past_date", start_date="-30d")

    class Meta:
        model = models.Watcher


class SearchQueryWatcherFactory(ModelWatcherFactory):
    watcher_type = "query"

    class Meta:
        model = models.Watcher


class SubscriptionFactory(factory.django.DjangoModelFactory):
    watcher = factory.SubFactory(ModelWatcherFactory)
    user = factory.SubFactory(UserFactory)
    name = factory.Faker("sentence", nb_words=6)

    class Meta:
        model = models.Subscription
        django_get_or_create = ("name",)

    @classmethod
    def _create(cls, model_class, *args, user=None, data=None, force_id=None, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_from_data(user, data, force_id=force_id)


class NotificationFactory(factory.django.DjangoModelFactory):
    notification_type = factory.Faker("random_element", elements=_NOTIFICATION_TYPES)
    status = factory.Faker("random_element", elements=_NOTIFICATION_STATUS_CHOICES)

    class Meta:
        model = models.Notification


factories_registry.register("model watcher", ModelWatcherFactory)
factories_registry.register("search query watcher", SearchQueryWatcherFactory)
factories_registry.register("watchers subscription", SubscriptionFactory)
factories_registry.register("notification", NotificationFactory)
