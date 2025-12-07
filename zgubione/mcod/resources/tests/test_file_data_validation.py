import csv
import os
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import factory
import pytest
from celery import Task
from django.conf import settings

import mcod
from mcod.resources.factories import (
    ResourceCsvFactory,
    ResourceFactory,
    ResourceJsonFactory,
    ResourceTxtFactory,
    ResourceXlsxFactory,
)
from mcod.resources.indexed_data import ResourceDataValidationError
from mcod.resources.models import Resource
from mcod.resources.tasks import process_resource_file_data_task
from mcod.resources.tasks.entrypoint_res import entrypoint_process_resource_validation_task
from mcod.resources.tasks.entrypoint_res_file import (
    entrypoint_process_resource_file_validation_task,
)


def test_smoke_resource_data_validation():
    res = ResourceFactory.create(
        type="file",
        format="xlsx",
        main_file__file=factory.django.FileField(
            from_path=os.path.join(settings.TEST_SAMPLES_PATH, "plik_testowy.xlsx"),
            filename="plik_testowy.xlsx",
        ),
    )
    res.data.validate()


@pytest.mark.parametrize(
    ("csv_delimiter", "header", "row_values", "validation_error_expected"),
    [
        # correct CSV file structure
        (",", ["Column_1", "Column_2"], ["Value_1", "Value_2"], False),
        (";", ["Column_1", "Column_2"], ["Value_1", "Value_2"], False),
        # incorrect CSV file structure - additional value compared to the header
        (",", ["Column_1", "Column_2"], ["Value_1", "Value_2", "Value_3"], True),
        (";", ["Column_1", "Column_2"], ["Value_1", "Value_2", "Value_3"], True),
        # incorrect CSV file structure - no second value compared to the header
        (",", ["Column_1", "Column_2"], ["Value_1"], True),
        (";", ["Column_1", "Column_2"], ["Value_1"], True),
        # correct CSV file structure - only one column
        (",", ["Column_1"], ["Value_1"], False),
        (";", ["Column_1"], ["Value_1"], False),
        # only one column - incorrect CSV file structure - comma treated as default separator - RFC-4180
        (",", ["Column_1"], ["Value_1", "Value_2"], True),
        # only one column - correct CSV file structure - semicolon not treated as default separator
        (";", ["Column_1"], ["Value_1", "Value_2"], False),
    ],
)
def test_process_resource_file_data_task_for_csv_files(
    csv_delimiter: str, header: List[str], row_values: List[str], validation_error_expected: bool
):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Given
        temp_file_path: Path = Path(temp_dir, "test.csv")
        with open(temp_file_path, "w") as f:
            writer = csv.writer(f, delimiter=csv_delimiter)
            writer.writerow(header)
            writer.writerow(row_values)

        res: Resource = ResourceFactory.create(
            type="file",
            format="csv",
            main_file__file=factory.django.FileField(
                from_path=temp_file_path,
                filename="test.csv",
            ),
        )

        # When and Then
        if validation_error_expected:
            with pytest.raises(ResourceDataValidationError):
                process_resource_file_data_task(res.id)
        else:
            assert process_resource_file_data_task(res.id)


@pytest.mark.parametrize(
    "entry_point, resource_factory, data_validation_expected",
    [
        (entrypoint_process_resource_file_validation_task, ResourceCsvFactory, True),
        (entrypoint_process_resource_file_validation_task, ResourceXlsxFactory, True),
        (entrypoint_process_resource_file_validation_task, ResourceTxtFactory, False),
        (entrypoint_process_resource_file_validation_task, ResourceJsonFactory, False),
        (entrypoint_process_resource_validation_task, ResourceCsvFactory, True),
        (entrypoint_process_resource_validation_task, ResourceXlsxFactory, True),
        (entrypoint_process_resource_validation_task, ResourceTxtFactory, False),
        (entrypoint_process_resource_validation_task, ResourceJsonFactory, False),
    ],
)
def test_resource_data_validation_task_call_only_for_processable_resources(
    entry_point: Task, resource_factory: ResourceFactory, data_validation_expected: bool
):
    # GIVEN
    resource: Resource = resource_factory.create()
    mock_sig = MagicMock()
    with patch.object(mcod.resources.models.process_resource_file_data_task, "s", return_value=mock_sig) as mock_s:
        # WHEN
        if entry_point is entrypoint_process_resource_file_validation_task:
            entry_point(resource.files.first().id)
        elif entry_point is entrypoint_process_resource_validation_task:
            entry_point(resource.id)

        # THEN
        if data_validation_expected:
            args, kwargs = mock_s.call_args
            assert resource.is_data_processable
            assert args == (resource.id,)
            assert mock_s.call_count == 1
        else:
            assert not resource.is_data_processable
            assert mock_s.call_count == 0
