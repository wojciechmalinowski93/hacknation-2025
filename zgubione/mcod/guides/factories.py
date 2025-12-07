import factory

from mcod.core.registries import factories_registry
from mcod.guides import models
from mcod.users.factories import AdminFactory


class GuideFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=300, locale="pl_PL")
    created_by = factory.SubFactory(AdminFactory)

    class Meta:
        model = models.Guide


class GuideItemFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=200, locale="pl_PL")
    content = factory.Faker("paragraph", nb_sentences=3, variable_nb_sentences=True, locale="pl_PL")
    route = "/"
    position = factory.Faker("random_element", elements=[x[0] for x in models.GuideItem.POSITION_CHOICES])
    order = 0
    guide = factory.SubFactory(GuideFactory)

    class Meta:
        model = models.GuideItem


factories_registry.register("guide", GuideFactory)
factories_registry.register("guide item", GuideItemFactory)
