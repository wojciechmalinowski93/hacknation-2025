from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest
import pytz
from django.utils import timezone

from mcod.datasets.factories import DatasetFactory
from mcod.datasets.models import Dataset
from mcod.harvester.factories import CKANDataSourceFactory
from mcod.resources.factories import IsolatedResourceFactory, ResourceFactory, ResourceTrashFactory
from mcod.resources.tasks import update_data_date

NOW = datetime.now()
NOW_A_DAY_AGO = NOW - timedelta(days=1)
NOW_TWO_DAYS_AGO = NOW - timedelta(days=2)
NOW_AT_MIDNIGHT = datetime.combine(NOW.date(), time(0, 0))
YESTERDAY_AT_MIDNIGHT = datetime.combine(NOW_A_DAY_AGO.date(), time(0, 0))


def test_new_dataset_has_verified_same_as_created(dataset):
    assert dataset.verified == dataset.created


def test_dataset_verified_changed_and_is_resource_modified_after_publishing_resource(dataset):
    # Given
    dataset_verified_before = dataset.verified
    # When
    resource = IsolatedResourceFactory(dataset=dataset)
    dataset.refresh_from_db()
    assert dataset.resources.count() == 1
    # Then
    assert dataset.verified != dataset_verified_before
    assert dataset.verified == resource.modified


def test_dataset_verified_not_changed_after_add_draft_resource(dataset):
    # Given
    dataset_verified_before = dataset.verified
    # When
    ResourceFactory(dataset=dataset, status="draft")
    dataset.refresh_from_db()
    assert dataset.resources.count() == 1
    # Then
    assert dataset.verified == dataset_verified_before


def test_dataset_verified_changed_and_is_resource_modified_after_delete_published_resource(dataset):
    # Given
    resource = ResourceFactory(dataset=dataset)
    dataset.refresh_from_db()
    dataset_verified_before = dataset.verified
    # When
    resource.delete()
    dataset.refresh_from_db()
    assert dataset.resources.count() == 0
    # Then
    assert dataset.verified != dataset_verified_before
    assert dataset.verified == resource.modified


def test_dataset_verified_not_changed_after_delete_draft_resource(dataset):
    # Given
    resource = ResourceFactory(dataset=dataset, status="draft")
    dataset.refresh_from_db()
    dataset_verified_before = dataset.verified
    # When
    resource.delete()
    dataset.refresh_from_db()
    assert dataset.resources.count() == 0
    # Then
    assert dataset.verified == dataset_verified_before


def test_dataset_verified_changed_and_is_resource_modified_after_change_to_draft_published_resource(dataset):
    # Given
    resource = ResourceFactory(dataset=dataset)
    dataset.refresh_from_db()
    dataset_verified_before = dataset.verified
    # When
    resource.status = "draft"
    resource.save()
    assert not resource.is_published
    dataset.refresh_from_db()
    # Then
    assert dataset.verified != dataset_verified_before
    assert dataset.verified == resource.modified


def test_dataset_verified_changed_and_is_resource_modified_after_publishing_a_draft_resource(dataset):
    # Given
    resource = ResourceFactory(dataset=dataset, status="draft")
    dataset.refresh_from_db()
    dataset_verified_before = dataset.verified
    # When
    resource.status = "published"
    resource.save()
    assert resource.is_published
    dataset.refresh_from_db()
    # Then
    assert dataset.verified != dataset_verified_before
    assert dataset.verified == resource.modified


def test_dataset_verified_changed_and_is_resource_modified_after_restoring_the_published_resource(dataset):
    # Given
    resource = ResourceTrashFactory(dataset=dataset)
    dataset.refresh_from_db()
    dataset_verified_before = dataset.verified
    # When
    resource.is_removed = False
    resource.save()
    dataset.refresh_from_db()
    # Then
    assert dataset.verified != dataset_verified_before
    assert dataset.verified == resource.modified


def test_dataset_verified_not_changed_after_restoring_the_draft_resource(dataset):
    # Given
    resource = ResourceTrashFactory(dataset=dataset, status="draft")
    dataset.refresh_from_db()
    dataset_verified_before = dataset.verified
    # When
    resource.is_removed = False
    resource.save()
    dataset.refresh_from_db()
    # Then
    assert dataset.verified == dataset_verified_before


def test_dataset_verified_not_changed_after_revalidate_resource(dataset):
    # Given
    resource = ResourceFactory(dataset=dataset)
    dataset.refresh_from_db()
    dataset_verified_before = dataset.verified
    # When
    resource.revalidate()
    dataset.refresh_from_db()
    # Then
    assert dataset.verified == dataset_verified_before


@pytest.mark.parametrize("resource_type", ["api", "website", "file"])
def test_dataset_verified_changed_after_periodic_updating_resource(resource_type: str):
    """Test 1.a and 2.a.7 from OTD-867"""
    # Given
    mocked_now = timezone.datetime(2025, 11, 14, 12, 34, 56, tzinfo=pytz.UTC)
    with patch("mcod.resources.tasks.tasks.now", return_value=mocked_now):
        resource = ResourceFactory(
            type=resource_type,
            is_auto_data_date=True,
            automatic_data_date_start=NOW.date(),
            endless_data_date_update=True,
            data_date_update_period="daily",
        )
        dataset = Dataset.objects.get(pk=resource.dataset.id)
        dataset_verified_before = dataset.verified
        # When
        update_data_date.s(resource.id).apply()
        resource.refresh_from_db()
        dataset.refresh_from_db()
        # Then
        assert dataset.verified != dataset_verified_before
        assert dataset.verified == mocked_now


def test_dataset_verified_changed_and_is_max_created_after_importing_ckan_resource_without_auto_data_date():
    # Given
    dataset = DatasetFactory(source=CKANDataSourceFactory())
    dataset_verified_before = dataset.verified
    # When
    ResourceFactory(dataset=dataset, created=NOW_TWO_DAYS_AGO, data_date=NOW_TWO_DAYS_AGO.date())
    ResourceFactory(dataset=dataset, created=NOW_A_DAY_AGO, data_date=NOW.date())
    dataset.refresh_from_db()
    assert dataset.resources.count() == 2
    # Then
    assert dataset.verified != dataset_verified_before
    assert dataset.verified == NOW_A_DAY_AGO.astimezone(dataset.verified.tzinfo)


def test_dataset_verified_not_changed_after_deleting_ckan_resource_without_auto_data_date():
    # Given
    dataset = DatasetFactory(source=CKANDataSourceFactory())
    resource = ResourceFactory(dataset=dataset, created=NOW_TWO_DAYS_AGO, data_date=NOW_A_DAY_AGO.date())
    dataset.refresh_from_db()
    assert dataset.resources.count() == 1
    dataset_verified_before = dataset.verified
    # When
    resource.delete()
    dataset.refresh_from_db()
    assert dataset.resources.count() == 0
    # Then
    assert dataset.verified == dataset_verified_before


def test_dataset_verified_changed_and_is_max_data_date_of_imported_ckan_resource_with_auto_data_date():
    # Given
    dataset = DatasetFactory(source=CKANDataSourceFactory())
    dataset_verified_before = dataset.verified
    # When
    ResourceFactory(
        dataset=dataset,
        created=NOW_TWO_DAYS_AGO,
        data_date=NOW_TWO_DAYS_AGO.date(),
        is_auto_data_date=True,
        automatic_data_date_start=NOW.date(),
        endless_data_date_update=True,
        data_date_update_period="daily",
    )
    # resource with max data_date if auto true
    ResourceFactory(
        dataset=dataset,
        created=NOW_TWO_DAYS_AGO,
        data_date=NOW_A_DAY_AGO.date(),
        is_auto_data_date=True,
        automatic_data_date_start=NOW.date(),
        endless_data_date_update=True,
        data_date_update_period="daily",
    )
    ResourceFactory(
        dataset=dataset,
        created=NOW_TWO_DAYS_AGO,
        data_date=NOW.date(),
    )
    dataset.refresh_from_db()
    assert dataset.resources.count() == 3
    # Then
    assert dataset.verified != dataset_verified_before
    assert dataset.verified == YESTERDAY_AT_MIDNIGHT.astimezone(dataset.verified.tzinfo)


def test_dataset_verified_not_changed_after_deleting_ckan_resource_with_auto_data_date():
    # Given
    dataset = DatasetFactory(source=CKANDataSourceFactory())
    resource = ResourceFactory(
        dataset=dataset,
        created=NOW_TWO_DAYS_AGO,
        data_date=NOW_TWO_DAYS_AGO.date(),
        is_auto_data_date=True,
        automatic_data_date_start=NOW.date(),
        endless_data_date_update=True,
        data_date_update_period="daily",
    )
    dataset.refresh_from_db()
    assert dataset.resources.count() == 1
    dataset_verified_before = dataset.verified
    # When
    resource.delete()
    dataset.refresh_from_db()
    assert dataset.resources.count() == 0
    # Then
    assert dataset.verified == dataset_verified_before
