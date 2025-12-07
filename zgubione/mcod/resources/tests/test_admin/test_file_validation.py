from pathlib import Path
from typing import Optional, Type

import pytest
from django.conf import settings
from pytest_bdd import scenarios

from mcod.resources.archives import PasswordProtectedArchiveError
from mcod.resources.file_validation import analyze_file

scenarios(
    "../features/file_validation.feature",
)


@pytest.mark.parametrize(
    "file_name, expected_extension, expected_file_mimetype, expected_extracted_extension, "
    "expected_extracted_mimetype, expected_analyze_exception",
    (
        ("test_samples/json_in_zip.zip", "zip", "application/zip", "geojson", "application/geo+json", None),
        # fmt: off
        pytest.param(
            "test_samples/plik_nq.nq", "nq", "text/plain", None, None, None,
            marks=pytest.mark.xfail(strict=True, run=True)
        ),
        pytest.param(
            "test_samples/html-disguised-as.txt", "html", "text/html", None, None, None,
            marks=pytest.mark.xfail(reason="This minimal html is also valid xml which is also a valid empty rdf/xml,"
                                           " but we skip the check for html")
        ),
        pytest.param(
            "test_samples/example.html", "html", "text/html", None, None, None,
        ),
        # fmt: on
        ("test_samples/plik_nq.nq", "nq", "application/n-quads", None, None, None),
        ("test_samples/linked_nt.nt", "n3", "text/n3", None, None, None),
        ("test_samples/rdf/example_turtle.ttl", "n3", "text/n3", None, None, None),
        pytest.param(
            "test_samples/rdf/example_turtle.ttl",
            "ttl",
            "text/turtle",
            None,
            None,
            None,
            marks=pytest.mark.xfail(reason="Turtle is a subset of N3 so we're unable to distinguish them by parsing"),
        ),
        ("test_samples/rdf/example_n3.n3", "n3", "text/n3", None, None, None),
        ("test_samples/linked_nt.nt.zip", "zip", "application/zip", "n3", "text/n3", None),
        ("test_samples/linked_rdf.rdf", "rdf", "application/rdf+xml", None, None, None),
        ("test_samples/linked_rdf_packed.zip", "zip", "application/zip", "rdf", "application/rdf+xml", None),
        ("test_samples/cms-json-disguised-as.txt", "json", "application/json", None, None, None),
        ("test_samples/Mexico_and_US_Border.zip", "shp", "application/shapefile", None, None, None),
        ("test_samples/tiff_and_tfw.zip", "geotiff", "image/tiff;application=geotiff", None, None, None),
        ("dbf_examples/dbase_f5.dbf", "dbf", "application/x-dbf", None, None, None),
        ("test_samples/empty_file.7z", "7z", "application/x-7z-compressed", "csv", "text/plain", None),
        ("test_samples/empty_file.rar", "rar", "application/x-rar", "csv", "text/plain", None),
        ("test_samples/encrypted_content_and_headers.rar", "rar", "application/x-rar", None, None, PasswordProtectedArchiveError),
        ("test_samples/encrypted_content.zip", "zip", "application/zip", None, None, PasswordProtectedArchiveError),
        ("test_samples/encrypted_content.7z", "7z", "application/x-7z-compressed", None, None, PasswordProtectedArchiveError),
        # fmt: off
        pytest.param(
            "test_samples/empty_file.rar", "rar", "application/x-rar", "csv", "text/plain", None,
            marks=pytest.mark.xfail(
                reason="Assignment of mime-type to CSV varies between Debian (our Docker) and Ubuntu (Gitlab)."
            ),
        ),
        pytest.param(
            "test_samples/regular.zip", "zip", "application/zip", "csv", "application/csv", None,
            marks=pytest.mark.xfail(
                reason="Assignment of mime-type to CSV varies between Debian (our Docker) and Ubuntu (Gitlab)."
            ),
        ),
        pytest.param(
            "test_samples/regular.rar", "rar", "application/x-rar", "csv", "application/csv", None,
            marks=pytest.mark.xfail(
                reason="Assignment of mime-type to CSV varies between Debian (our Docker) and Ubuntu (Gitlab)."
            ),
        ),
        # fmt: on
    ),
)
def test_analyze_file(
    file_name: str,
    expected_extension: str,
    expected_file_mimetype: str,
    expected_extracted_extension: Optional[str],
    expected_extracted_mimetype: Optional[str],
    expected_analyze_exception: Optional[Type[Exception]],
) -> None:
    file_path = Path(settings.DATA_DIR) / file_name
    (
        actual_extension,
        actual_file_info,
        actual_encoding,
        actual_path,
        actual_file_mimetype,
        actual_analyze_exc,
        actual_extracted_extension,
        actual_extracted_mimetype,
        actual_extracted_encoding,
    ) = analyze_file(file_path)
    assert (
        actual_extension,
        actual_file_mimetype,
        actual_extracted_extension,
        actual_extracted_mimetype,
    ) == (
        expected_extension,
        expected_file_mimetype,
        expected_extracted_extension,
        expected_extracted_mimetype,
    )
    if expected_analyze_exception:
        assert isinstance(actual_analyze_exc, expected_analyze_exception)
