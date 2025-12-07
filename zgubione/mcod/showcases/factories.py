import factory

from mcod.core.registries import factories_registry
from mcod.showcases.models import Showcase, ShowcaseProposal


class ShowcaseFactory(factory.django.DjangoModelFactory):
    category = "app"
    license_type = "free"
    title = factory.Faker("text", max_nb_chars=80, locale="pl_PL")
    title_en = factory.Faker("text", max_nb_chars=80)
    notes = factory.Faker("paragraph", nb_sentences=5, locale="pl_PL")
    author = factory.Faker("name")
    url = factory.Faker("url")
    views_count = factory.Faker("random_int", min=0, max=500)
    image = factory.django.ImageField(color="blue")
    illustrative_graphics = factory.django.ImageField(color="blue")

    @factory.post_generation
    def datasets(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for dataset in extracted:
                self.datasets.add(dataset)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)

    class Meta:
        model = Showcase
        django_get_or_create = ("title",)


class ShowcaseProposalFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=80, locale="pl_PL")
    notes = factory.Faker("paragraph", nb_sentences=5, locale="pl_PL")
    author = factory.Faker("name")
    url = factory.Faker("url")
    image = factory.django.ImageField(color="blue")
    illustrative_graphics = factory.django.ImageField(color="blue")
    showcase = factory.SubFactory(ShowcaseFactory)

    class Meta:
        model = ShowcaseProposal
        django_get_or_create = ("title",)

    @factory.post_generation
    def datasets(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for dataset in extracted:
                self.datasets.add(dataset)


factories_registry.register("showcase", ShowcaseFactory)
factories_registry.register("showcaseproposal", ShowcaseProposalFactory)
