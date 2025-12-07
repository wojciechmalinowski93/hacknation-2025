from unittest.mock import MagicMock, patch

import pytest

from mcod.resources.models import (
    RESOURCE_TYPE_API,
    RESOURCE_TYPE_FILE,
    RESOURCE_TYPE_WEBSITE,
    ResourceType,
)
from mcod.resources.tasks import (
    delete_es_resource_tabular_data_index,
    get_ckan_resource_format_from_url_task,
    update_data_date,
)


@pytest.mark.parametrize(
    "ids, deleted_indexes",
    [
        (20, ["resource-20"]),
        ([], []),
        ([30, 40, 50], ["resource-30", "resource-40", "resource-50"]),
    ],
)
def test_task_delete_es_resource_tabular_data_index(ids, deleted_indexes):
    """
    GIVEN one resource id or list of resource ids
    WHEN call `delete_es_resource_tabular_data_index` with these ids as parameter
    THEN function that deletes tabular data index will be called.
    """
    with patch("mcod.resources.tasks.tasks.delete_index", return_value=True) as mock_delete_index:
        delete_es_resource_tabular_data_index(ids)

        for delete_index in deleted_indexes:
            mock_delete_index.assert_any_call(delete_index)


@pytest.mark.parametrize("resource_type", [RESOURCE_TYPE_API, RESOURCE_TYPE_WEBSITE])
def test_update_data_date_does_not_revalidate_api_and_website_resource(resource_type: ResourceType):
    # GIVEN
    mock_resource = MagicMock()
    mock_resource.is_auto_data_date = True
    mock_resource.is_auto_data_date_allowed = True
    mock_resource.type = resource_type

    with patch("mcod.resources.tasks.tasks.apps.get_model") as mock_get_model, patch(
        "mcod.resources.tasks.tasks.entrypoint_process_resource_validation_task.s"
    ) as mock_process_task:

        mock_get_model.return_value.objects.filter.return_value.first.return_value = mock_resource

        # WHEN
        resource_id = 1
        update_data_date(resource_id)
        # THEN
        mock_process_task.assert_not_called()


def test_update_data_date_task_revalidates_remote_file_resource():
    # GIVEN
    mock_resource = MagicMock()
    mock_resource.is_auto_data_date = True
    mock_resource.is_auto_data_date_allowed = True
    mock_resource.type = RESOURCE_TYPE_FILE
    mock_resource.is_imported = True
    mock_resource.availability = "remote"

    with patch("mcod.resources.tasks.tasks.apps.get_model") as mock_get_model, patch(
        "mcod.resources.tasks.tasks.entrypoint_process_resource_validation_task.s"
    ) as mock_process_task:

        mock_get_model.return_value.objects.filter.return_value.first.return_value = mock_resource

        # WHEN
        resource_id = 1
        update_data_date(resource_id)
        # THEN
        mock_process_task.assert_called_once()


def test_get_ckan_resource_format_from_url_task_smoke():
    mock_resource = MagicMock()
    mock_resource.is_imported_from_ckan = True

    with patch("mcod.resources.tasks.tasks.apps.get_model") as mock_get_model:
        mock_get_model.return_value.objects.filter.return_value.only.return_value.first.return_value = mock_resource

        get_ckan_resource_format_from_url_task(mock_resource.pk)
