import factory

from mcod.core.registries import factories_registry
from mcod.licenses import models


class LicenseFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word", locale="pl_PL")
    title = factory.Faker("text", max_nb_chars=50, locale="pl_PL")
    url = factory.Faker("url")

    @factory.post_generation
    def article_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for article in extracted:
                self.article_set.add(article)

    @factory.post_generation
    def dataset_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for dataset in extracted:
                self.dataset_set.add(dataset)

    class Meta:
        model = models.License
        django_get_or_create = ("name",)


factories_registry.register("license", LicenseFactory)
