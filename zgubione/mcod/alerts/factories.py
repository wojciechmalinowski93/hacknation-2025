import datetime

import factory
from django.utils import timezone

from mcod.alerts.models import Alert
from mcod.core.registries import factories_registry


def today():
    return timezone.now().date()


def tomorrow():
    return timezone.now().date() + datetime.timedelta(days=1)


class AlertFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=80, locale="pl_PL")
    title_en = factory.Faker("text", max_nb_chars=80)
    description = factory.Faker("paragraph", nb_sentences=5, locale="pl_PL")
    description_en = factory.Faker("paragraph", nb_sentences=5)
    start_date = factory.LazyFunction(today)
    finish_date = factory.LazyFunction(tomorrow)

    class Meta:
        model = Alert
        django_get_or_create = ("title",)


factories_registry.register("alert", AlertFactory)
