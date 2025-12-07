import tempfile
from pathlib import Path
from typing import Dict, List

import pytest
import requests
from django.conf import settings

from mcod.resources.archives import ArchiveReader, PasswordProtectedArchiveError

IS_READABLE = True
IS_ENCRYPTED = True
archive_samples = [
    ("encrypted_content.7z", IS_READABLE, IS_ENCRYPTED),
    ("empty_file.7z", IS_READABLE, not IS_ENCRYPTED),
    ("regular.7z", IS_READABLE, not IS_ENCRYPTED),
    ("encrypted_content_and_headers.7z", IS_READABLE, IS_ENCRYPTED),
    ("linked_rdf_packed.zip", IS_READABLE, not IS_ENCRYPTED),
    ("encrypted_content.zip", IS_READABLE, IS_ENCRYPTED),
    ("empty_file.zip", IS_READABLE, not IS_ENCRYPTED),
    ("single_csv.zip", IS_READABLE, not IS_ENCRYPTED),
    ("csv_in_folders.zip", IS_READABLE, not IS_ENCRYPTED),
    ("tiff_and_tfw.zip", IS_READABLE, not IS_ENCRYPTED),
    ("single_geotiff.zip", IS_READABLE, not IS_ENCRYPTED),
    ("multi_pdf_xlsx.zip", IS_READABLE, not IS_ENCRYPTED),
    ("xlsx_in_archive.zip", IS_READABLE, not IS_ENCRYPTED),
    ("Mexico_and_US_Border.zip", IS_READABLE, not IS_ENCRYPTED),
    ("regular.zip", IS_READABLE, not IS_ENCRYPTED),
    ("regular.rar", IS_READABLE, not IS_ENCRYPTED),
    ("encrypted_content_and_headers.rar", IS_READABLE, IS_ENCRYPTED),
    ("empty_file.rar", IS_READABLE, not IS_ENCRYPTED),
    ("empty_docx_packed.rar", IS_READABLE, not IS_ENCRYPTED),
    ("multi_file.rar", IS_READABLE, not IS_ENCRYPTED),
    ("encrypted_content.rar", IS_READABLE, IS_ENCRYPTED),
    ("single_file.tar.gz", IS_READABLE, not IS_ENCRYPTED),
    ("empty_file.tar.gz", IS_READABLE, not IS_ENCRYPTED),
    ("empty_file.tar.bz2", IS_READABLE, not IS_ENCRYPTED),
    ("state_variants.csv.bz2", IS_READABLE, not IS_ENCRYPTED),
]


@pytest.mark.otd_1152
@pytest.mark.parametrize("archive_file_name, is_readable, is_encrypted", archive_samples)
def test_archive_reader(archive_file_name: str, is_readable: bool, is_encrypted: bool) -> None:
    file_path = Path(settings.TEST_SAMPLES_PATH) / archive_file_name
    assert file_path.exists()
    assert file_path.is_file()
    if is_encrypted:
        with pytest.raises(PasswordProtectedArchiveError):
            ArchiveReader(file_path)
    else:
        with ArchiveReader(file_path) as archive:
            assert archive


@pytest.mark.otd_1152
@pytest.mark.parametrize(
    "file_name, expected_files_inside",
    (
        ("empty_file.zip", 1),
        ("empty_file.rar", 1),
        ("empty_file.7z", 1),
        ("empty_file.tar.gz", 1),
        ("empty_file.tar.bz2", 1),
        ("multi_file.rar", 2),
    ),
)
def test_unpacking_of_archive_files(file_name: str, expected_files_inside: int) -> None:
    file_path = Path(settings.TEST_SAMPLES_PATH) / file_name
    with ArchiveReader(file_path) as archive:
        assert len(archive) == int(expected_files_inside)


@pytest.mark.otd_1152
@pytest.mark.parametrize(
    "archive_file_name, expected_files, expected_files_by_extension",
    (
        (
            "csv_in_folders.zip",
            ["a/b/c/unique_simple copy.csv"],
            {"csv": 1},
        ),
        (
            "empty_file.rar",
            ["empty.csv"],
            {"csv": 1},
        ),
    ),
)
def test_archive_reader_extracts_files(
    archive_file_name: str, expected_files: List[str], expected_files_by_extension: Dict[str, int]
) -> None:
    file_path = Path(settings.TEST_SAMPLES_PATH) / archive_file_name
    with ArchiveReader(file_path) as archive:
        assert archive
        for expected_file in expected_files:
            assert expected_file in archive
            extracted = archive.extract(expected_file)
            assert extracted.exists()
            assert extracted.read_bytes()
    assert not extracted.exists()
    with ArchiveReader(file_path) as archive:
        for ext, cnt in expected_files_by_extension.items():
            extracted = list(archive.get_by_extension(ext))
            assert len(extracted) == cnt
            extracted_file = extracted[0]
            assert extracted_file.exists()
            assert extracted_file.read_bytes()
    assert not extracted_file.exists()


@pytest.mark.otd_1152
def test_archive_reader_doesnt_handle_single_compressed_file() -> None:
    """A bzip without a tar confuses libarchive, the list of "files" is basically a list of lines of
    the original CSV. As of now, this is MUST be handled by the caller.
    ➜ bzip2 state_variants.csv
    ➜ ls state_variants.csv.bz2
    """
    file_path = Path(settings.TEST_SAMPLES_PATH) / "state_variants.csv.bz2"
    with ArchiveReader(file_path) as archive:
        assert archive
        assert "prev_status,status,was_removed,is_removed,created,prev_published,state" in archive


@pytest.mark.otd_1152
@pytest.mark.skip("Uncomment this to run the test in lab conditions")
def test_archive_reader_works_with_zip_bomb() -> None:
    """This smoke test downloads a known zip bomb and tries to open it with ArchiveReader.
    I'm marking it with unconditional `skip` to minimise risks to our CI/CD.
    """
    response = requests.get("https://www.bamsoftware.com/hacks/zipbomb/zbsm.zip")
    with tempfile.NamedTemporaryFile(mode="wb") as tmpfd:
        tmpfd.write(response.content)
        file_path = Path(tmpfd.name)
        with ArchiveReader(file_path) as archive:
            assert archive
            assert "1" in archive
            assert "2" in archive
