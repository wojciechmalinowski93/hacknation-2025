import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Generator, List, Optional, Set, Tuple, Union
from unittest.mock import PropertyMock

import pytest
from django.core.management import call_command
from pytest_mock import MockerFixture

from mcod.datasets.management.commands.redefine_datasets_symlink import (
    Command as RedefineCommand,
    find_symlinks_in_given_path,
    get_the_latest_zip_file_or_none,
    remove_symlink,
)
from mcod.datasets.models import Dataset


def dataset_full_archive_path(dataset: Dataset, path: Path) -> Path:
    """Returns dataset full archive path."""
    return path / dataset.archive_folder_name


class TestDatasetsRedefineSymlinksCommand:
    """Test command for redefining dataset symlinks. Contains integration and unit tests.

    Attributes:
        command_name (str): The name of the command.
        command_class_path (str): The path of the command class.
    """

    command_name = "redefine_datasets_symlink"
    command_class_path = "mcod.datasets.management.commands.redefine_datasets_symlink"

    @staticmethod
    def create_symlink(tmp_path: Path, start_range: int = 1, end_range: int = 3) -> Path:
        """
        Create files and a symlink to the first one. Choosing target file for
        the symlink is arbitrary.
        Returns the path to the symlink.
        """
        for element in range(start_range, end_range):
            with open(tmp_path / f"{element}.zip", "w") as file:
                if element == start_range + 1:
                    target = file.name
                    symlink_path: Path = tmp_path / f"symlink{element}"
                    symlink_path.symlink_to(str(target))
                    return symlink_path

    def test_find_symlink_function(self, tmp_path: Path) -> None:
        """Test the find_symlink function"""
        symlink_path: Path = self.create_symlink(tmp_path)
        res: list = find_symlinks_in_given_path(tmp_path)

        assert isinstance(res, list)
        assert len(res) == 1
        assert isinstance(res[0], Path)
        assert res[0] == symlink_path

    def test_find_symlink_method_empty_list(self, tmp_path: Path) -> None:
        """Test the find_symlink function when the symlink list is empty."""
        for element in range(1, 3):
            new_path = tmp_path / f"{element}.zip"
            new_path.touch()

        res: list = find_symlinks_in_given_path(tmp_path)

        assert isinstance(res, list)
        assert len(res) == 0

    def test_remove_symlink(self, tmp_path: Path) -> None:
        """
        Test if remove_symlink function deletes the symlink. Test case includes only
        symlink removing.
        """
        symlink_path = self.create_symlink(tmp_path)
        assert symlink_path.is_symlink()
        remove_symlink(symlink_path)
        assert not symlink_path.is_symlink()

    @staticmethod
    def latest_zip(tmp_path: Path, end_range: int = 4) -> Optional[Path]:
        """Creates a zip files and return the latest file name."""
        current_time = datetime.now()
        for element in range(1, 4):
            new_path = tmp_path / f"{element}.zip"
            new_path.touch()

            # Modify a creation date, to have a difference between files.
            modification_time = current_time + timedelta(seconds=10) * element
            modification_timestamp = time.mktime(modification_time.timetuple())
            os.utime(new_path, (modification_timestamp, modification_timestamp))

            if element == end_range - 1:
                return new_path

    def test_handle_symlink_method(self, tmp_path):
        """
        Test the handle_symlink method of the RedefineCommand class.
        Basically test creates a files and symlink, and after all, handle_symlink
        method removes it.
        """
        symlink = self.create_symlink(tmp_path, 1, 3)
        symlink2 = self.create_symlink(tmp_path, 4, 6)
        RedefineCommand().remove_and_create_new_symlink(tmp_path)

        assert not symlink.is_symlink()
        assert not symlink2.is_symlink()

    def test_latest_zip_file_function(self, tmp_path) -> None:
        """
        Test if the get_the_latest_zip_file_or_none function
        returns the last zip file.
        """
        latest_file: Path = self.latest_zip(tmp_path)
        res: Path = get_the_latest_zip_file_or_none(tmp_path)
        assert latest_file == res

    def test_latest_zip_file_method_no_zip_files(self, tmp_path):
        """Test the get_the_latest_zip_file_or_none function with no zip files."""
        current_time = datetime.now()
        for element in range(1, 4):
            new_path = tmp_path / f"{element}.txt"
            new_path.touch()

            # Modify a creation date, to have a difference between files.
            modification_time = current_time + timedelta(seconds=10) * element
            modification_timestamp = time.mktime(modification_time.timetuple())
            os.utime(new_path, (modification_timestamp, modification_timestamp))

        res: Optional[Path] = get_the_latest_zip_file_or_none(tmp_path)
        assert res is None

    def test_latest_zip_file_method_empty_folder(self, tmp_path):
        """Test the get_the_latest_zip_file_or_none function when empty folder."""
        res: Optional[Path] = get_the_latest_zip_file_or_none(tmp_path)
        assert res is None

    def test_create_symlink_method(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        dataset_with_resources_factory: Callable,
    ):
        """
        Test the create_new_symlink method of the RedefineCommand class.
        WHEN create_new_symlink is called from RedefineCommand class,
        new symlink is created for GIVEN dataset archive path. As and RESULT
        we have a new symlink path with target to the latest zip file.
        """

        dataset: Dataset = dataset_with_resources_factory(tmp_path=tmp_path, mocker=mocker)
        dataset_archive_path: Path = dataset_full_archive_path(dataset, tmp_path)

        command_instance = RedefineCommand()
        command_instance.remove_and_create_new_symlink(dataset_archive_path)

        latest_file: Path = self.latest_zip(dataset_archive_path)

        mock_path = f"{self.command_class_path}.get_the_latest_zip_file_or_none"
        mocker.patch(mock_path, return_value=latest_file)

        command_instance.create_new_symlink(dataset, str(dataset_archive_path))

        res: List[Path] = find_symlinks_in_given_path(dataset_archive_path)
        symlink: Path = res[0]

        assert res
        assert Path(symlink).resolve() == latest_file

    def test_create_symlink_method_raise_file_exists_exception(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        dataset_with_resources: Dataset,
    ):
        """Test the create_new_symlink method when the symlink file already exists."""
        ds: Dataset = dataset_with_resources
        ds_archive_path: Path = tmp_path / ds.archive_folder_name

        command_instance = RedefineCommand()
        latest_file: Path = self.latest_zip(ds_archive_path)

        mock_path = f"{self.command_class_path}.get_the_latest_zip_file_or_none"
        mocker.patch(mock_path, return_value=latest_file)

        with pytest.raises(FileExistsError):
            command_instance.create_new_symlink(ds, str(ds_archive_path))

    def test_get_folders_list_method(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        dataset_with_resources_factory: Callable,
    ):
        """Test the _get_folders_list method of the RedefineCommand class."""
        ds1: Dataset = dataset_with_resources_factory(tmp_path=tmp_path, mocker=mocker)
        ds1_archive_path: Path = tmp_path / ds1.archive_folder_name

        ds2: Dataset = dataset_with_resources_factory(tmp_path=tmp_path, mocker=mocker)
        ds2_archive_path: Path = tmp_path / ds2.archive_folder_name

        self.mock_archive_path(tmp_path, mocker)

        command_instance = RedefineCommand()
        res: Union[Set[Path], Generator] = command_instance._get_folders_list()
        paths_list = [obj for obj in res]

        assert len(paths_list) == 2
        assert ds1_archive_path in paths_list
        assert ds2_archive_path in paths_list

    def mock_archive_path(self, path: Path, mocker: MockerFixture):
        """Mock the archive_path property in the RedefineCommand class."""
        mock_path = f"{self.command_class_path}.Command.archive_path"
        mocker_property = mocker.patch(mock_path, new_callable=PropertyMock)
        mocker_property.return_value = path

    def test_get_folders_list_method_options_provided(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        dataset_with_resources_factory: Callable,
    ):
        """
        Test the _get_folders_list method of the RedefineCommand class
        with options provided.
        """
        dataset1: Dataset = dataset_with_resources_factory(tmp_path=tmp_path, mocker=mocker)
        dataset2: Dataset = dataset_with_resources_factory(tmp_path=tmp_path, mocker=mocker)

        self.mock_archive_path(tmp_path, mocker)

        command_instance = RedefineCommand()
        res: Union[Set[Path], Generator] = command_instance._get_folders_list(dataset_ids=[dataset1.pk])
        paths_list = [obj for obj in res]

        assert len(paths_list) == 1
        assert dataset_full_archive_path(dataset1, tmp_path) in paths_list
        assert dataset_full_archive_path(dataset2, tmp_path) not in paths_list

    def prepare_datasets_and_zip_files(
        self,
        mocker: MockerFixture,
        dataset_with_resources_factory: Callable,
        tmp_path: Path,
    ) -> Tuple[Dataset, Path]:
        """Prepare datasets, archive paths, and latest zip files for testing."""
        self.mock_archive_path(mocker=mocker, path=tmp_path)
        dataset: Dataset = dataset_with_resources_factory(tmp_path=tmp_path, mocker=mocker)
        latest = self.latest_zip(tmp_path=dataset_full_archive_path(dataset, tmp_path))
        return dataset, latest

    def test_call_command(
        self,
        mocker: MockerFixture,
        dataset_with_resources_factory: Callable,
        tmp_path: Path,
    ):
        """
        Test the call_command method of the RedefineCommand class with no arguments.
        """

        latest1: str
        latest2: str
        dataset1: Dataset
        dataset2: Dataset

        dataset1, latest1 = self.prepare_datasets_and_zip_files(
            mocker=mocker,
            dataset_with_resources_factory=dataset_with_resources_factory,
            tmp_path=tmp_path,
        )
        dataset2, latest2 = self.prepare_datasets_and_zip_files(
            mocker=mocker,
            dataset_with_resources_factory=dataset_with_resources_factory,
            tmp_path=tmp_path,
        )

        call_command(self.command_name)

        ds1_archive_folder_symlinks = [
            entry for entry in dataset_full_archive_path(dataset1, tmp_path).iterdir() if entry.is_symlink()
        ]

        assert ds1_archive_folder_symlinks[0].resolve() == Path(latest1)

        ds2_archive_folder_symlinks = [
            entry for entry in dataset_full_archive_path(dataset2, tmp_path).iterdir() if entry.is_symlink()
        ]

        assert ds2_archive_folder_symlinks[0].resolve() == Path(latest2)

    def test_call_command_with_arguments(
        self,
        mocker: MockerFixture,
        dataset_with_resources_factory: Callable,
        tmp_path: Path,
    ):
        """Test the call_command method of the RedefineCommand class with arguments."""
        latest1: str
        latest2: str
        dataset1: Dataset
        dataset2: Dataset

        dataset1, latest1 = self.prepare_datasets_and_zip_files(
            mocker=mocker,
            dataset_with_resources_factory=dataset_with_resources_factory,
            tmp_path=tmp_path,
        )
        dataset2, latest2 = self.prepare_datasets_and_zip_files(
            mocker=mocker,
            dataset_with_resources_factory=dataset_with_resources_factory,
            tmp_path=tmp_path,
        )

        call_command(self.command_name, dataset_ids=dataset1.pk)

        ds1_archive_folder_symlinks = [
            entry for entry in dataset_full_archive_path(dataset1, tmp_path).iterdir() if entry.is_symlink()
        ]

        assert ds1_archive_folder_symlinks[0].resolve() == Path(latest1)

        ds2_archive_folder_symlinks = [
            entry for entry in dataset_full_archive_path(dataset2, tmp_path).iterdir() if entry.is_symlink()
        ]

        assert ds2_archive_folder_symlinks[0].resolve() != Path(latest2)
