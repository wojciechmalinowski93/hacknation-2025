from typing import Any, Callable, Dict, Type

import pytest

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.datasets.factories import DatasetFactory
from mcod.organizations.documents import Dataset
from mcod.resources.factories import ResourceFactory


@pytest.fixture
def dataset_with_resources_factory() -> Type[Callable]:
    """Dataset and resources factory fixture."""

    def create_ds(**kwargs):
        dataset = DatasetFactory.create(**kwargs)
        ResourceFactory.create_batch(2, dataset=dataset)
        run_on_commit_events()
        return dataset

    return create_ds


@pytest.fixture
def dataset_with_resources(dataset_with_resources_factory, tmp_path, mocker) -> Dataset:
    """Create dataset with resources."""
    return dataset_with_resources_factory(mocker=mocker, tmp_path=tmp_path)


@pytest.fixture
def post_data_to_create_dataset() -> Dict[str, Any]:
    post_data = {
        "title": "some title",
        "notes": "more than 20 characters",
        "status": "published",
        "update_frequency": "yearly",
        "url": "http://www.test.pl",
        "organization": 10000,
        "has_high_value_data": False,
        "has_high_value_data_from_ec_list": False,
        "has_dynamic_data": False,
        "has_research_data": False,
        "update_notification_recipient_email": "test@example.com",
        "categories": [10001],
        "tags": [10002],
        "tags_pl": [10002],
        "resources-TOTAL_FORMS": "0",
        "resources-INITIAL_FORMS": "0",
        "resources-MIN_NUM_FORMS": "0",
        "resources-MAX_NUM_FORMS": "1000",
        "supplements-INITIAL_FORMS": "0",
        "supplements-MAX_NUM_FORMS": "10",
        "supplements-MIN_NUM_FORMS": "0",
        "supplements-TOTAL_FORMS": "0",
        "resources-2-TOTAL_FORMS": "0",
        "resources-2-INITIAL_FORMS": "0",
        "resources-2-MIN_NUM_FORMS": "0",
        "resources-2-MAX_NUM_FORMS": "1000",
        "resources-2-0-has_high_value_data": False,
        "resources-2-0-has_high_value_data_from_ec_list": False,
        "resources-2-0-has_dynamic_data": False,
        "resources-2-0-language": "pl",
        "resources-2-0-has_research_data": False,
        "resources-2-0-contains_protected_data": False,
        # nested admin required fields.
        "resources-2-0-supplements-TOTAL_FORMS": "0",
        "resources-2-0-supplements-INITIAL_FORMS": "0",
        "resources-2-0-supplements-MIN_NUM_FORMS": "0",
        "resources-2-0-supplements-MAX_NUM_FORMS": "1000",
        "resources-2-empty-supplements-TOTAL_FORMS": "0",
        "resources-2-empty-supplements-INITIAL_FORMS": "0",
        "resources-2-empty-supplements-MIN_NUM_FORMS": "0",
        "resources-2-empty-supplements-MAX_NUM_FORMS": "1000",
    }

    return post_data
