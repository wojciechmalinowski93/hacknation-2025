import json
from itertools import count
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Type
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from django.test import override_settings
from pytest_mock import MockerFixture
from typing_extensions import TypeAlias

from mcod.organizations.models import Organization
from mcod.reports.broken_links import (
    generate_admin_broken_links_report,
    generate_public_broken_links_reports,
)
from mcod.reports.broken_links.constants import ReportFormat, ReportLanguage
from mcod.reports.broken_links.public import ReportFolder
from mcod.reports.broken_links.tasks_helpers import BrokenLinksIntermediaryJSON
from mcod.reports.tasks import validate_resources_links
from mcod.resources.factories import (
    ApiResourceFactory,
    BrokenLinksResourceFactory,
    ResourceFactory,
    WebResourceFactory,
)
from mcod.resources.models import Resource

Record: TypeAlias = Dict[str, Any]


def create_sample_public_broken_links_report_record(id_: int, **kwargs) -> Record:
    """Helper function that creates a dictionary representation of a public broken link record."""
    record = {
        "institution": f"Testowa Instytucja {id_}",
        "dataset": f"Zbiór Danych Testowych {id_}",
        "title": f"Dane testowe {id_}",
        "portal_data_link": f"http://dane.gov.pl/data/{id_}",
        "link": f"http://institution{id_}.pl",
        "error_reason": "Nierozpoznany błąd walidacji",
    }
    record.update(**kwargs)
    return record


@pytest.fixture
def media_root_path(tmp_path: Path) -> Generator[Path, None, None]:
    with override_settings(REPORTS_MEDIA_ROOT=tmp_path):
        yield tmp_path


class TestPublicBrokenLinks:
    """
    Tests the generation of public reports for broken links.
    """

    @pytest.mark.parametrize(
        ("visible_records_count", "ssl_errors_count", "location_errors_count"),
        [
            (7, 0, 0),  # Case with only valid input
            (10, 2, 2),  # Case with all record types
            (5, 1, 0),  # Case without location errors
            (8, 0, 6),  # Case without SSL errors
            (0, 3, 0),  # Case with only SSL errors
            (0, 0, 4),  # Case with only location errors
            (0, 0, 0),  # Case with empty input data
        ],
    )
    def test_generate_public_broken_links_reports(
        self,
        media_root_path: Path,
        visible_records_count: int,
        ssl_errors_count: int,
        location_errors_count: int,
    ):
        """
        Verifies that reports are generated correctly in all specified formats and languages (CSV/XLSX, PL/EN),
        containing only the appropriate records. Records with specific error types (SSL, location) and
        malformed data should be filtered out.
        """
        # Define paths for the generated reports and expected column headers for each language.
        public_report_en_path: Path = media_root_path / "resources" / "public" / "en"
        public_report_pl_path: Path = media_root_path / "resources" / "public" / "pl"
        public_report_en_headers = ["Publisher", "Dataset", "Data", "Link to data on the portal", "Broken link to publisher data"]
        public_report_pl_headers = [
            "Dostawca",
            "Zbiór danych",
            "Dane",
            "Link do danych na portalu",
            "Uszkodzony link do danych dostawcy",
        ]

        # GIVEN: Prepare the test data
        id_counter = count()

        # Generate records that should be visible in the final public report.
        broken_links_records: List[Record] = [
            create_sample_public_broken_links_report_record(next(id_counter)) for _ in range(visible_records_count)
        ]

        # Generate records with SSL errors, which are expected to be filtered out.
        ssl_error_records: List[Record] = [
            create_sample_public_broken_links_report_record(
                next(id_counter), error_reason="Weryfikacja certyfikatu SSL nie powiodła się."
            )
            for _ in range(ssl_errors_count)
        ]

        # Generate records with location errors, also expected to be filtered out.
        location_error_records: List[Record] = [
            create_sample_public_broken_links_report_record(
                next(id_counter), error_reason="Lokalizacja zasobu została zmieniona."
            )
            for _ in range(location_errors_count)
        ]

        # Add a record with an invalid structure to ensure the process handles malformed data gracefully.
        invalid_records: List[Record] = [{"non_existing_field": "value"}]

        # Combine all generated records into a single dataset.
        data = [*broken_links_records, *ssl_error_records, *location_error_records, *invalid_records]

        # Create the expected DataFrame, which should only contain the valid 'broken_links_records'.
        # The internal 'error_reason' column is dropped as it's not present in the public report.
        expected_report_df = pd.DataFrame(broken_links_records).drop(columns=["error_reason"], errors="ignore")
        expected_report_records = expected_report_df.to_numpy()

        # WHEN: Execute the function under test
        generate_public_broken_links_reports(data)

        # THEN: Verify the output files
        # Define all test scenarios for each language and file format combination.
        test_cases = [
            {"path": public_report_pl_path, "headers": public_report_pl_headers, "ext": "csv"},
            {"path": public_report_pl_path, "headers": public_report_pl_headers, "ext": "xlsx"},
            {"path": public_report_en_path, "headers": public_report_en_headers, "ext": "csv"},
            {"path": public_report_en_path, "headers": public_report_en_headers, "ext": "xlsx"},
        ]

        for case in test_cases:
            report_path = case["path"]
            extension = case["ext"]
            expected_headers = pd.Index(case["headers"])

            # Ensure that exactly one report file of the specified type was created.
            generated_files: List[Path] = list(report_path.glob(f"*.{extension}"))
            assert len(generated_files) == 1
            file_path: Path = generated_files[0]

            # Load the generated report into a DataFrame, handling different file formats.
            if extension == "csv":
                report_df = pd.read_csv(file_path, delimiter=";")
            else:  # xlsx
                report_df = pd.read_excel(file_path)

            # Assert that the headers and content of the report are correct.
            assert report_df.columns.equals(expected_headers)

            if expected_report_df.empty:
                # If no valid records were provided, the report should be empty.
                assert report_df.empty
            else:
                # Otherwise, the report content must match the expected records.
                assert np.array_equal(report_df.to_numpy(), expected_report_records)


@pytest.fixture
def input_data_with_expected_admin_report_content() -> Tuple[List[Record], str]:
    input_data: List[Record] = [
        {
            "id": 0,
            "uuid": "4174cea7-8a12-419a-8f6b-23306297cdd0",
            "title": "Testowy zasób 0",
            "portal_data_link": "https://dane.gov.pl/resource/0",
            "description": "To jest opis dla zasobu testowego.",
            "link": "https://instytucja.pl/dane",
            "error_reason": "Nieoczekiwany błąd",
            "converted_formats_str": "csv,json,xls,xlsx",
            "institution_id": "inst_0",
            "institution": "Przykładowa Instytucja",
            "dataset": "Zbiór danych",
            "dataset_id": "10",
            "created_by": 100,
            "created": "2025-10-21T00:03:30.000000",
            "modified_by": 1000,
            "modified": "2025-10-21T00:03:30.000000",
            "resource_type": "file",
            "method_of_sharing": "link",
            "has_high_value_data": True,
            "has_high_value_data_from_ec_list": False,
            "has_dynamic_data": None,
            "has_research_data": True,
            "contains_protected_data": False,
        },
        {
            "id": 1,
            "uuid": "4174cea7-8a12-419a-8f6b-23306297cdd1",
            "title": "Testowy zasób 1",
            "portal_data_link": "https://dane.gov.pl/resource/1",
            "description": "To jest opis dla zasobu testowego.",
            "link": "https://instytucja.pl/dane",
            "error_reason": "Nieoczekiwany błąd",
            "converted_formats_str": "csv,json,xls,xlsx",
            "institution_id": "inst_1",
            "institution": "Przykładowa Instytucja",
            "dataset": "Zbiór danych",
            "dataset_id": "10",
            "created_by": 100,
            "created": "2025-10-21T00:03:30.000001",
            "modified_by": 1000,
            "modified": "2025-10-21T00:03:30.000001",
            "resource_type": "file",
            "method_of_sharing": "link",
            "has_high_value_data": False,
            "has_high_value_data_from_ec_list": True,
            "has_dynamic_data": True,
            "has_research_data": None,
            "contains_protected_data": True,
        },
    ]

    expected_csv_content = (
        # Header
        "id;uuid;nazwa;Link do danych na portalu;opis;link;Przyczyna;formaty po konwersji;"
        "Id Instytucji;Dostawca;zbiór danych;Id zbioru;utworzony przez;utworzony;zmodyfikowany przez;zmodyfikowany;"
        "typ;Sposób udostępnienia;"
        "Zasób zawiera dane o wysokiej wartości;Zasób zawiera dane o wysokiej wartości z wykazu KE;"
        "Zasób zawiera dane dynamiczne;Zasób zawiera dane badawcze;Zawiera wykaz chronionych danych\n"
        # Row 1
        "0;4174cea7-8a12-419a-8f6b-23306297cdd0;Testowy zasób 0;https://dane.gov.pl/resource/0;"
        "To jest opis dla zasobu testowego.;https://instytucja.pl/dane;Nieoczekiwany błąd;csv,json,xls,xlsx;"
        "inst_0;Przykładowa Instytucja;Zbiór danych;10;100;2025-10-21T00:03:30.000000;1000;2025-10-21T00:03:30.000000;file;"
        "link;TAK;NIE;nie sprecyzowano;TAK;NIE\n"
        # Row 2
        "1;4174cea7-8a12-419a-8f6b-23306297cdd1;Testowy zasób 1;https://dane.gov.pl/resource/1;"
        "To jest opis dla zasobu testowego.;https://instytucja.pl/dane;Nieoczekiwany błąd;csv,json,xls,xlsx;"
        "inst_1;Przykładowa Instytucja;Zbiór danych;10;100;2025-10-21T00:03:30.000001;1000;2025-10-21T00:03:30.000001;file;"
        "link;NIE;TAK;TAK;nie sprecyzowano;TAK\n"
    )

    return input_data, expected_csv_content


class TestAdminBrokenLinks:

    @pytest.mark.parametrize("with_invalid_data", [True, False])
    def test_generate_admin_broken_links_reports(
        self,
        input_data_with_expected_admin_report_content,
        tmp_path: Path,
        with_invalid_data: bool,
    ):
        # GIVEN
        # Input data and expected csv report content.
        input_data, expected_csv_content = input_data_with_expected_admin_report_content
        if with_invalid_data:
            # Add invalid data structure which should be omitted.
            input_data.append({"not_valid_key": "not_valid_value"})

        # Report path should not exist
        report_path: Path = tmp_path / "broken_links"
        assert not report_path.exists()

        # WHEN call te report generation function
        with patch("mcod.reports.broken_links.admin._get_report_root_path") as mock_get_root:
            mock_get_root.return_value = report_path
            generate_admin_broken_links_report(input_data)

        # THEN report csv file should be created with expected content
        generated_files: List[Path] = list(report_path.glob("*.csv"))
        assert len(generated_files) == 1
        report_file: Path = generated_files[0]

        with open(report_file, "r") as f:
            report_content: str = f.read()

        assert report_content == expected_csv_content


@pytest.fixture
def manager_class_with_folder_path(
    tmp_path: Path, monkeypatch
) -> Generator[Tuple[Type[BrokenLinksIntermediaryJSON], Path], None, None]:
    folder_path: Path = tmp_path / "broken_links"
    monkeypatch.setattr(BrokenLinksIntermediaryJSON, "_FOLDER_PATH", folder_path)
    yield BrokenLinksIntermediaryJSON, folder_path


class TestBrokenLinksIntermediaryJSON:
    @pytest.mark.parametrize("identifier", ["some-unique-id", None])
    def test_init_creates_folder_path(self, manager_class_with_folder_path, identifier):
        """Test if the manager's __init__ method correctly creates the designated folder."""
        # GIVEN a manager class and a non-existent folder path
        manager_class, folder_path = manager_class_with_folder_path
        assert not folder_path.exists()

        # WHEN the manager is instantiated with or without an identifier
        if identifier:
            manager_class(identifier)
        else:
            manager_class()

        # THEN the folder should be created
        assert folder_path.exists()

    def test_delete_old_json_file(self, manager_class_with_folder_path):
        """Test if delete_old_json_files removes only the target JSON files."""
        # GIVEN an instantiated manager and a set of files in its directory
        manager_class, folder_path = manager_class_with_folder_path
        identifier = "some-unique-id"
        manager: BrokenLinksIntermediaryJSON = manager_class(identifier)
        prefix: str = manager_class._FILE_PREFIX

        # GIVEN files that should be kept after cleanup
        csv_file: Path = folder_path.joinpath("file.csv")  # non-prefixed, different extension
        csv_file_with_prefix: Path = folder_path.joinpath(f"{prefix}_file.csv")  # prefixed, different extension
        csv_file_with_prefix_and_id: Path = folder_path.joinpath(
            f"{prefix}_{identifier}_file.csv"
        )  # prefixed with ID, different extension
        json_file_with_prefix_and_id: Path = folder_path.joinpath(
            f"{prefix}_{identifier}_file.json"
        )  # prefixed with current ID, correct extension
        files_to_keep: List[Path] = [csv_file, csv_file_with_prefix, csv_file_with_prefix_and_id, json_file_with_prefix_and_id]
        for file in files_to_keep:
            file.touch()

        # GIVEN a file that should be deleted
        # This is a JSON file with the prefix but a different (old) identifier
        json_file_to_delete: Path = folder_path.joinpath(f"{prefix}_other-unique-id.json")
        json_file_to_delete.touch()

        # WHEN the cleanup method is called
        manager.delete_old_json_files()

        # THEN only the old JSON file should be deleted
        for file in files_to_keep:
            assert file.exists()
        assert not json_file_to_delete.exists()

    def test_dump_and_load(self, manager_class_with_folder_path):
        """Test if data is correctly dumped to and loaded from a JSON file."""
        # GIVEN an empty directory and an instantiated manager
        manager_class, folder_path = manager_class_with_folder_path
        manager: BrokenLinksIntermediaryJSON = manager_class()
        assert not any(folder_path.iterdir())

        # GIVEN resources with and without broken links (assuming they are globally accessible or mocked)
        broken_links_resources: List[Resource] = BrokenLinksResourceFactory.create_batch(size=3)
        non_broken_links_resources: List[Resource] = ResourceFactory.create_batch(size=3)

        # WHEN data is dumped
        manager.dump()

        # THEN a single JSON file should be created in the target folder
        generated_files: List[Path] = list(folder_path.glob("*.json"))
        assert len(generated_files) == 1
        json_file: Path = generated_files[0]

        # AND the file content should be correct
        with open(json_file, "r") as f:
            content: str = f.read()
            dumped_data: Dict[str, Any] = json.loads(content)

        # THEN verify that only broken link resources are present in the dump
        for resource in broken_links_resources:
            assert resource.link in content
        for resource in non_broken_links_resources:
            assert resource.link not in content

        # WHEN data is loaded back
        loaded_data: List[Dict[str, Any]] = manager.load()

        # THEN the loaded data must match the data that was dumped
        assert loaded_data == dumped_data


class TestReportFolder:
    def test_report_folder_root_is_subdirectory_of_settings_path(self, reports_media_root: str):
        """
        Tests that the ReportFolder's _root path is correctly constructed
        as a subdirectory of the path defined in settings.REPORTS_MEDIA_ROOT.

        Note: This check is important due to security reasons.
         ReportFolder class makes delete operations on files in the subdirectory.
        """
        # 1. Setup: Create a temporary base path using mocked settings
        base_reports_path = Path(reports_media_root)

        # 2. Execute: Instantiate the class to trigger the path construction
        report_folder = ReportFolder()

        # 3. Assert: Verify the constructed path is correct
        # Reconstruct the expected full path for comparison
        expected_full_path = base_reports_path.joinpath("resources", "public")

        # Check if the generated path is exactly what we expect
        assert report_folder._root == expected_full_path

    @pytest.mark.parametrize(
        ("language", "extension"),
        [
            (None, None),
            (None, "csv"),
            (None, "xlsx"),
            ("en", None),
            ("pl", None),
            ("en", "csv"),
            ("en", "xlsx"),
            ("pl", "csv"),
            ("pl", "xlsx"),
        ],
    )
    def test_report_folder_files_search(
        self,
        sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
        language: Optional[str],
        extension: Optional[str],
    ):
        # GIVEN
        # Public Broken Links report files for all languages and extensions.
        pl_csv_file: Path = sample_public_broken_links_files[ReportLanguage.PL, ReportFormat.CSV]
        pl_xlsx_file: Path = sample_public_broken_links_files[ReportLanguage.PL, ReportFormat.XLSX]
        en_csv_file: Path = sample_public_broken_links_files[ReportLanguage.EN, ReportFormat.CSV]
        en_xlsx_file: Path = sample_public_broken_links_files[ReportLanguage.EN, ReportFormat.XLSX]

        # Prepare expected results for different scenarios
        expected_files_map: Dict[Tuple[Optional[str], Optional[str]], Set[Path]] = {
            # Root search (lang=None) - recursive search
            (None, None): {pl_csv_file, pl_xlsx_file, en_csv_file, en_xlsx_file},
            (None, "csv"): {pl_csv_file, en_csv_file},
            (None, "xlsx"): {pl_xlsx_file, en_xlsx_file},
            # 'en' directory search
            ("en", None): {en_csv_file, en_xlsx_file},
            ("en", "csv"): {en_csv_file},
            ("en", "xlsx"): {en_xlsx_file},
            # 'pl' directory search
            ("pl", None): {pl_csv_file, pl_xlsx_file},
            ("pl", "csv"): {pl_csv_file},
            ("pl", "xlsx"): {pl_xlsx_file},
        }

        # WHEN
        # Retrieve Public Broken Links reports files.
        report_folder = ReportFolder()
        files: List[Path] = report_folder.files(lang=language, format_=extension)

        expected_files: Set[Path] = expected_files_map[(language, extension)]
        assert set(files) == expected_files

    def test_report_folder_all_files_search(
        self,
        sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    ):
        all_files: Set[Path] = set(sample_public_broken_links_files.values())
        report_folder = ReportFolder()
        files: List[Path] = report_folder.files()
        assert all_files == set(files)

    def test_cleanup(
        self,
        sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    ):
        files: List[Path] = list(sample_public_broken_links_files.values())
        for file in sample_public_broken_links_files.values():
            assert file.exists() and file.is_file()

        report_folder = ReportFolder()
        report_folder.cleanup(files)

        for file in files:
            assert not file.exists()
            parent_folder: Path = file.parent
            assert parent_folder.exists()

    def test_cleanup_does_not_remove_folder(
        self,
        sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
    ):
        report_folder = ReportFolder()
        parent_folders: Set[Path] = set((file.parent for file in sample_public_broken_links_files.values()))
        with pytest.raises(IsADirectoryError):
            report_folder.cleanup(list(parent_folders))
        for folder in parent_folders:
            folder.exists()

    def test_cleanup_does_not_remove_files_outside_the_scope(
        self,
        sample_public_broken_links_files: Dict[Tuple[ReportLanguage, ReportFormat], Path],
        tmp_path: Path,
    ):
        # GIVEN file outside the reports directory
        all_files: List[Path] = list(sample_public_broken_links_files.values())
        outside_folder_file: Path = tmp_path.joinpath("outside.csv")
        outside_folder_file.touch()

        # WHEN
        # Try to delete files with any outside the folder
        report_folder = ReportFolder()
        with pytest.raises(ValueError):
            report_folder.cleanup([*all_files, outside_folder_file])

        # THEN
        # No file will be removed
        assert outside_folder_file.exists()
        for file in all_files:
            file.exists()


@pytest.mark.parametrize(
    "env_variable_value_broken_links_exclude_developers, expected_validations_count", ([True, 3], [False, 10])
)
def test_developers_resources_included_excluded_from_broken_links(
    mocker: MockerFixture, env_variable_value_broken_links_exclude_developers: bool, expected_validations_count: int
):
    # GIVEN - 10 all resoures (7 developers, 3 non-developers)
    dev_api_resource_ids: List[int] = [
        resource.id
        for resource in ApiResourceFactory.create_batch(
            4, dataset__organization__institution_type=Organization.INSTITUTION_TYPE_DEVELOPER
        )
    ]
    dev_web_resource_ids: List[int] = [
        resource.id
        for resource in WebResourceFactory.create_batch(
            3, dataset__organization__institution_type=Organization.INSTITUTION_TYPE_DEVELOPER
        )
    ]
    state_api_resource_ids: List[int] = [
        resource.id
        for resource in ApiResourceFactory.create_batch(
            2, dataset__organization__institution_type=Organization.INSTITUTION_TYPE_STATE
        )
    ]
    other_web_resource_id: List[int] = WebResourceFactory.create(
        dataset__organization__institution_type=Organization.INSTITUTION_TYPE_OTHER
    ).id

    non_developers_resource_ids: List[int] = sorted(state_api_resource_ids + [other_web_resource_id])
    all_resource_ids: List[int] = sorted(dev_api_resource_ids + dev_web_resource_ids + non_developers_resource_ids)

    mocked_chord: MagicMock = mocker.patch("mcod.reports.tasks.chord", return_value=MagicMock())
    mocked_validate_link: MagicMock = mocker.patch("mcod.reports.tasks.validate_link")

    with override_settings(BROKEN_LINKS_EXCLUDE_DEVELOPERS=env_variable_value_broken_links_exclude_developers):
        # WHEN
        validate_resources_links()
    # THEN
    mocked_chord.assert_called_once()
    args, kwargs = mocked_chord.call_args
    subtask = args[0]
    assert len(subtask) == expected_validations_count

    validated_resource_ids: List[int] = sorted([args[0] for args, kwargs in mocked_validate_link.s.call_args_list])

    if env_variable_value_broken_links_exclude_developers:
        assert validated_resource_ids == non_developers_resource_ids
    else:
        assert validated_resource_ids == all_resource_ids
