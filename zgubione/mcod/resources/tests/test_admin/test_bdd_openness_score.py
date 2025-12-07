from pathlib import Path

import pytest
from django.conf import settings
from pytest_bdd import scenarios

from mcod.resources.score_computation import get_score

scenarios(
    "../features/resource_openness.feature",
)


class MockFieldFile:
    def __init__(self, file_path: Path):
        self.path = str(file_path.absolute())


@pytest.mark.parametrize(
    "file_name, extension, expected_openness_score",
    (
        ("test_samples/json_in_zip.zip", "geojson", 3),
        ("test_samples/json_in_zip.zip", "zip", 3),
        ("test_samples/tiff_and_tfw.zip", "geotiff", 3),
        ("test_samples/linked_rdf_packed.zip", "rdf", 5),
        ("test_samples/linked_rdf_packed.zip", "zip", 5),
        ("test_samples/multi_file.rar", "rar", 1),
    ),
)
def test_get_score_archives(
    file_name: str,
    extension: str,
    expected_openness_score: int,
) -> None:

    file_path = Path(settings.DATA_DIR) / file_name
    file_field = MockFieldFile(file_path)
    openness_score = get_score(file_field, extension)
    assert openness_score == expected_openness_score


@pytest.mark.parametrize(
    "file_name, extension, expected_openness_score",
    (
        ("test_samples/unique_simple.csv", "csv", 3),
        ("test_samples/plik_nq.nq", "nq", 4),
        ("test_samples/plik_nq.nq", "none", 1),
        ("test_samples/linked_rdf.rdf", "xml", 5),
        ("test_samples/linked_rdf.rdf", "rdf", 5),
    ),
)
def test_get_score_plain_files(
    file_name: str,
    extension: str,
    expected_openness_score: int,
) -> None:
    file_path = Path(settings.DATA_DIR) / file_name
    file_field = MockFieldFile(file_path)
    openness_score = get_score(file_field, extension)
    assert openness_score == expected_openness_score
