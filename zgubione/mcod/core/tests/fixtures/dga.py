from io import BytesIO
from typing import List, Tuple
from unittest.mock import PropertyMock, patch

import factory
import pandas as pd
import pytest
from django.conf import settings
from django.db.models import QuerySet

from mcod.categories.factories import CategoryFactory
from mcod.categories.models import Category
from mcod.datasets.factories import DatasetFactory
from mcod.datasets.models import Dataset
from mcod.organizations.factories import OrganizationFactory
from mcod.organizations.models import Organization
from mcod.resources.factories import (
    AggregatedDGAInfoFactory,
    DGACompliantResourceFactory,
    MainDGAResourceFactory,
    get_dga_csv_file,
)
from mcod.resources.models import AggregatedDGAInfo, Resource
from mcod.tags.factories import TagFactory
from mcod.tags.models import Tag


@pytest.fixture
def main_dga_owner_organization() -> Organization:
    return OrganizationFactory.create(pk=settings.MAIN_DGA_DATASET_OWNER_ORGANIZATION_PK)


@pytest.fixture
def main_dga_dataset_categories() -> List[Category]:
    return CategoryFactory.create_batch(
        size=len(settings.MAIN_DGA_DATASET_CATEGORIES_TITLES),
        title=factory.Iterator(settings.MAIN_DGA_DATASET_CATEGORIES_TITLES),
    )


@pytest.fixture
def main_dga_dataset_tags() -> List[Tag]:
    return TagFactory.create_batch(
        size=len(settings.MAIN_DGA_DATASET_TAGS_NAMES),
        name=factory.Iterator(settings.MAIN_DGA_DATASET_TAGS_NAMES),
    )


@pytest.fixture
def main_dga_dataset(
    main_dga_owner_organization: Organization,
    main_dga_dataset_categories: List[Category],
    main_dga_dataset_tags: List[Tag],
) -> Dataset:
    dataset: Dataset = DatasetFactory.create(
        organization=main_dga_owner_organization,
        title=settings.MAIN_DGA_DATASET_DEFAULT_TITLE,
        notes=settings.MAIN_DGA_DATASET_DEFAULT_DESC,
        has_dynamic_data=False,
        has_high_value_data=False,
        has_high_value_data_from_ec_list=False,
        has_research_data=False,
        update_frequency="daily",
        status="published",
    )
    dataset.categories.add(*main_dga_dataset_categories)
    dataset.tags.add(*main_dga_dataset_tags)
    return dataset


@pytest.fixture
def main_dga_resource(main_dga_dataset: Dataset) -> Resource:
    resource: Resource = MainDGAResourceFactory.create(dataset=main_dga_dataset)
    AggregatedDGAInfoFactory.create(resource=resource)
    return resource


@pytest.fixture
def dga_info(main_dga_owner_organization: Organization) -> AggregatedDGAInfo:
    return AggregatedDGAInfoFactory.create()


@pytest.fixture
def indexed_data_available_property_mock():
    """
    Mocks the `available` property of the IndexedData class.

    This fixture is particularly useful in tests where the `tabular_data`
    property of Resource objects needs to be accessed, but the `available`
    property would normally return `False` due to non-existent ElasticSearch
    documents associated with the Resource object.
    By mocking the `available` property, tests can simulate the condition
    where the necessary ElasticSearch documents are assumed to be present,
    allowing `tabular_data` to be accessed as if the underlying data were
    available.

    Example use-case:
        Testing functions that depend on the availability of data, where
        `available` normally returns `False`, to ensure they can handle data
        retrieval and processing correctly when data is considered 'available'.

    Yields:
        A PropertyMock object for the `available` property of IndexedData.
    """
    from mcod.resources.indexed_data import IndexedData

    with patch.object(IndexedData, "available", new_callable=PropertyMock) as mock_available:
        yield mock_available


@pytest.fixture
def dga_resources_with_df(
    indexed_data_available_property_mock,
) -> Tuple[QuerySet, pd.DataFrame]:
    """
    Fixture that creates and returns a queryset of DGA resources and a
    DataFrame with tabular data representation of those resources.
    """
    indexed_data_available_property_mock.return_value = True
    dga_resources: List[Resource] = DGACompliantResourceFactory.create_batch(5, contains_protected_data=True)
    dga_resources_queryset: QuerySet = Resource.objects.filter(id__in=[resource.id for resource in dga_resources])

    csv_file: BytesIO = get_dga_csv_file()
    csv_file.seek(0)
    csv_df: pd.DataFrame = pd.read_csv(csv_file, encoding="utf-8")
    csv_df.drop(columns="Lp.", inplace=True)

    df = pd.DataFrame()
    for resource in dga_resources:
        resource_df = csv_df.copy()
        resource_df.insert(0, "Nazwa dysponenta zasobu", resource.institution.title)
        resource_df["Warunki ponownego wykorzystywania"] = "określone w ofercie"
        df = pd.concat([df, resource_df], ignore_index=True)

    df.insert(0, "Lp.", range(1, len(df) + 1))
    return dga_resources_queryset, df
