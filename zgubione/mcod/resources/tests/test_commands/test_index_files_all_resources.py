from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from django.db.models import Max
from pytest_mock import MockerFixture

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.resources.factories import ResourceFactory
from mcod.resources.models import Resource


@pytest.fixture
def tabular_resource_for_reindex(simple_csv_file: str) -> Resource:
    res = ResourceFactory(
        type="file",
        format="csv",
        link=None,
        main_file__file=simple_csv_file,
    )
    run_on_commit_events()
    res.refresh_from_db()
    return res


@pytest.fixture
def mock_process_resource_file_data_task(mocker: MockerFixture) -> MagicMock:
    mock_task = mocker.patch(
        "mcod.resources.management.commands.index_files_all_resources.process_resource_file_data_task", mocker.MagicMock()
    )
    yield mock_task


def test_if_pk_is_to_high_no_task_gets_scheduled(
    mock_process_resource_file_data_task: MagicMock,
    tabular_resource_for_reindex: Resource,
) -> None:
    max_pk = Resource.objects.with_tabular_data().aggregate(Max("pk")).get("pk__max")
    with pytest.raises(ValueError):
        call_command("index_files_all_resources", first_pk=max_pk + 1)
    mock_process_resource_file_data_task.apply.assert_not_called()
    mock_process_resource_file_data_task.delay.assert_not_called()


def test_task_is_called(
    mock_process_resource_file_data_task: MagicMock,
    tabular_resource_for_reindex: Resource,
) -> None:
    expected_pk = tabular_resource_for_reindex.pk
    call_command(
        "index_files_all_resources",
        first_pk=expected_pk,
        last_pk=expected_pk,
        async_=True,
    )
    mock_process_resource_file_data_task.apply.assert_not_called()
    mock_process_resource_file_data_task.delay.assert_called_once_with(expected_pk)


def test_task_is_called_without_last_pk(
    mock_process_resource_file_data_task: MagicMock,
    tabular_resource_for_reindex: Resource,
) -> None:
    expected_pk = tabular_resource_for_reindex.pk
    call_command(
        "index_files_all_resources",
        first_pk=expected_pk,
        async_=True,
    )
    mock_process_resource_file_data_task.apply.assert_not_called()
    mock_process_resource_file_data_task.delay.assert_called_once_with(expected_pk)


def test_task_is_called_synchronously(
    mock_process_resource_file_data_task: MagicMock,
    tabular_resource_for_reindex: Resource,
) -> None:
    expected_pk = tabular_resource_for_reindex.pk
    call_command(
        "index_files_all_resources",
        first_pk=expected_pk,
    )
    mock_process_resource_file_data_task.apply.assert_called_once_with(
        args=(expected_pk,),
        throw=True,
    )
    mock_process_resource_file_data_task.delay.assert_not_called()
