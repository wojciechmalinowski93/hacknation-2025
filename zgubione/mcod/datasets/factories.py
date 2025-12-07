import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import factory
from pytest_mock import MockerFixture

from mcod.categories.factories import CategoryFactory
from mcod.core.registries import factories_registry
from mcod.datasets import models
from mcod.datasets.models import Dataset
from mcod.licenses.factories import LicenseFactory
from mcod.organizations.factories import OrganizationFactory

_UPDATE_FREQUENCY = [i[0] for i in models.UPDATE_FREQUENCY]

# `notApplicable` - deprecated value of update_frequency - OTD-1231
_UPDATE_FREQUENCY.remove("notApplicable")


class DatasetFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("text", max_nb_chars=100, locale="pl_PL")
    slug = factory.Faker("slug")
    notes = factory.Faker("paragraph", nb_sentences=3, variable_nb_sentences=True, locale="pl_PL")
    url = factory.Faker("url")
    views_count = factory.Faker("random_int", min=0, max=500)
    update_frequency = factory.Faker("random_element", elements=_UPDATE_FREQUENCY)
    category = factory.SubFactory(CategoryFactory)
    license = factory.SubFactory(LicenseFactory)
    organization = factory.SubFactory(OrganizationFactory)
    image = factory.Faker("file_name", extension="png")

    @classmethod
    def create(cls, **kwargs) -> Dataset:
        """Override build in method to use a mocked tmp path for storage location"""
        tmp_path: Optional[Path] = kwargs.pop("tmp_path", None)
        mocker: Optional[MockerFixture] = kwargs.pop("mocker", None)
        if tmp_path and mocker:
            mocker_object = "mcod.core.storages.DatasetsArchivesStorage.location"
            mocker.patch(mocker_object, return_value=tmp_path, new_callable=mocker.PropertyMock)
        return super().create(**kwargs)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)

    @factory.post_generation
    def resources(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for resource in extracted:
                self.resources.add(resource)

    @factory.post_generation
    def showcases(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for showcase in extracted:
                self.showcases.add(showcase)

    class Meta:
        model = models.Dataset
        django_get_or_create = ("title",)


class SupplementFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("text", max_nb_chars=200, locale="pl_PL")
    file = factory.django.FileField(
        from_func=lambda: BytesIO(b"Some text"),
        filename="{}.txt".format(str(uuid.uuid4())),
    )
    dataset = factory.SubFactory(DatasetFactory)
    order = 0
    language = "pl"

    class Meta:
        model = models.Supplement


factories_registry.register("dataset", DatasetFactory)
factories_registry.register("supplement", SupplementFactory)
