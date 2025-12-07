import uuid

import factory
from django.utils import timezone

from mcod.academy import models
from mcod.core.registries import factories_registry
from mcod.resources.factories import get_csv_file


def today():
    return timezone.now().date()


class CourseFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=80, locale="pl_PL")
    notes = factory.Faker("paragraph", nb_sentences=5)
    venue = "Ministerstwo Cyfryzacji, ul. Królewska 27, 00-060 Warszawa"
    participants_number = factory.Faker("random_int", min=0, max=20)
    file = factory.django.FileField(from_func=get_csv_file, filename="{}.csv".format(str(uuid.uuid4())))
    status = "published"

    @factory.post_generation
    def modules(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for module in extracted:
                self.modules.add(module)

    class Meta:
        model = models.Course


class CourseModuleFactory(factory.django.DjangoModelFactory):
    type = factory.Faker(
        "random_element",
        elements=[x[0] for x in models.CourseModule.COURSE_MODULE_TYPES],
    )
    start = factory.LazyFunction(today)
    number_of_days = factory.Faker("random_int", min=1, max=2)
    course = factory.SubFactory(CourseFactory)

    class Meta:
        model = models.CourseModule


factories_registry.register("course", CourseFactory)
factories_registry.register("course module", CourseModuleFactory)
