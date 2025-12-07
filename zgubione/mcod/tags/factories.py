import factory

from mcod.core.registries import factories_registry
from mcod.tags import models


class TagFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word", locale="pl_PL")
    status = "published"
    language = ""

    class Meta:
        model = models.Tag
        django_get_or_create = ("name",)

    @factory.post_generation
    def datasets(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for dataset in extracted:
                self.datasets.add(dataset)

    @factory.post_generation
    def showcases(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for showcase in extracted:
                self.showcases.add(showcase)


factories_registry.register("tag", TagFactory)
