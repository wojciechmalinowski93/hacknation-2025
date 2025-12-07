import factory

from mcod.categories import models
from mcod.core.registries import factories_registry

DCAT_CATEGORY_CODES = [
    "AGRI",
    "ECON",
    "EDUC",
    "ENVI",
    "GOVE",
    "HEAL",
    "JUST",
    "SOCI",
    "TECH",
    "TRAN",
    "ENER",
    "INTR",
    "REGI",
]


class CategoryFactory(factory.django.DjangoModelFactory):
    code = factory.Faker("random_element", elements=DCAT_CATEGORY_CODES)
    title = factory.Faker("text", max_nb_chars=30, locale="pl_PL")
    description = factory.Faker("paragraph", nb_sentences=3, variable_nb_sentences=True, locale="pl_PL")

    class Meta:
        model = models.Category
        django_get_or_create = (
            "code",
            "title",
        )

    @factory.post_generation
    def datasets(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for dataset in extracted:
                self.datasets.add(dataset)


factories_registry.register("category", CategoryFactory)
