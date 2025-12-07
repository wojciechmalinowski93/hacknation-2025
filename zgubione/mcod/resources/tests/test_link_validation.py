import re

import pytest
import requests_mock
from pytest_bdd import scenarios

from mcod.lib.file_format_from_response import get_extension_from_mime_type
from mcod.resources.link_validation import (
    InvalidContentType,
    InvalidResponseCode,
    InvalidSchema,
    InvalidUrl,
    MissingContentType,
    UnsupportedContentType,
    _filename_from_url,
    add_unique_suffix_to_filename,
    check_link_status,
    content_type_from_file_format,
    download_file,
)

scenarios(
    "features/resource_link_validation.feature",
)


class TestCheckLinkStatus:

    url = "http://mocker-test.com"

    def test_throw_invalid_url(self):
        try:
            check_link_status("www.brokenlink", "api")
            raise pytest.fail("No exception occurred. Expected: InvalidUrl")
        except InvalidUrl as err:
            assert err.args[0] == "Invalid url address: www.brokenlink"

    @requests_mock.Mocker(kw="mock_request")
    def test_throw_invalid_response_code(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "application/json"}
        mock_request.head(self.url, headers=headers, status_code=504)
        mock_request.get(self.url, headers=headers, status_code=504)

        with pytest.raises(InvalidResponseCode) as e:
            check_link_status(self.url, "api")
        assert e.match("Invalid response code: 504")

    @requests_mock.Mocker(kw="mock_request")
    def test_invalid_content_type(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "application/text/json"}
        mock_request.head(self.url, headers=headers)
        try:
            check_link_status(self.url, "api")
            raise pytest.fail("No exception occurred. Expected: InvalidContentType")
        except InvalidContentType as err:
            assert err.args[0] == "application/text/json"

    @requests_mock.Mocker(kw="mock_request")
    def test_unsupported_content_type(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "video/mp4"}
        mock_request.head(self.url, headers=headers)
        try:
            check_link_status(self.url, "api")
            raise pytest.fail("No exception occurred. Expected: UnsupportedContentType")
        except UnsupportedContentType as err:
            assert err.args[0] == "Unsupported type: video/mp4"

    @requests_mock.Mocker(kw="mock_request")
    def test_check_link_status_no_errors(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "application/json"}
        mock_request.head(self.url, headers=headers)
        check_link_status(self.url, "api")

    @requests_mock.Mocker(kw="mock_request")
    def test_check_link_status_use_get_method_without_errors(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "application/json"}
        mock_request.head(self.url, headers=headers, status_code=405)
        mock_request.get(self.url, headers=headers)
        check_link_status(self.url, "api")

    @requests_mock.Mocker(kw="mock_request")
    def test_check_link_status_resource_location_changed(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {
            "Content-Type": "text/html",
            "Location": "http://redirect-mocker.com",
        }
        mock_request.head(self.url, headers=headers, status_code=301)
        mock_request.head("http://redirect-mocker.com", headers={"Content-Type": "text/html"})
        try:
            check_link_status(self.url, "website")
            raise pytest.fail("No exception occurred. Expected: InvalidResponseCode")
        except InvalidResponseCode as err:
            assert err.args[0] == "Resource location has been moved!"


class TestDownloadFile:

    url = "https://mocker-test.com"

    def test_throw_invalid_url(self):
        try:
            download_file("www.brokenlink")
            raise pytest.fail("No exception occurred. Expected: InvalidUrl")
        except InvalidUrl as err:
            assert err.args[0] == "Invalid url address: www.brokenlink"

    @requests_mock.Mocker(kw="mock_request")
    def test_throw_invalid_url_scheme(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "application/json"}
        mock_request.get("http://mocker-test.com", headers=headers, status_code=504)
        try:
            download_file("http://mocker-test.com")
            raise pytest.fail("No exception occurred. Expected: InvalidScheme")
        except InvalidSchema as err:
            assert err.args[0] == "Invalid schema!"

    @requests_mock.Mocker(kw="mock_request")
    def test_throw_invalid_response_code(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "application/json"}
        mock_request.get(self.url, headers=headers, status_code=504)
        try:
            download_file(self.url)
            raise pytest.fail("No exception occurred. Expected: InvalidResponseCode")
        except InvalidResponseCode as err:
            assert err.args[0] == "Invalid response code: 504"

    @requests_mock.Mocker(kw="mock_request")
    def test_invalid_content_type(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "application/text/json"}
        mock_request.get(self.url, headers=headers)
        try:
            download_file(self.url)
            raise pytest.fail("No exception occurred. Expected: InvalidContentType")
        except InvalidContentType as err:
            assert err.args[0] == "application/text/json"

    @requests_mock.Mocker(kw="mock_request")
    def test_unsupported_content_type(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {"Content-Type": "video/mp4"}
        mock_request.get(self.url, headers=headers)
        try:
            download_file(self.url)
            raise pytest.fail("No exception occurred. Expected: UnsupportedContentType")
        except UnsupportedContentType as err:
            assert err.args[0] == "Unsupported type: video/mp4"

    @requests_mock.Mocker(kw="mock_request")
    def test_download_file_missing_content_type(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {}
        mock_request.get(self.url, headers=headers)
        try:
            download_file(self.url)
            raise pytest.fail("No exception occurred. Expected: MissingContentType")
        except MissingContentType as err:
            assert err.args[0] == "Missing content-type header"

    @requests_mock.Mocker(kw="mock_request")
    def test_download_file_filename_from_content_disposition(self, **kwargs):
        # Given
        mock_request = kwargs["mock_request"]
        headers = {
            "Content-Type": "text/html",
            "Content-Disposition": "attachment; filename=example_file.html",
        }
        mock_request.get(self.url, headers=headers, content=b"")
        # When
        res_type, res_details = download_file(self.url)
        # Then
        pattern = r"^example_file_[a-zA-Z0-9]+\.html$"
        assert re.match(pattern, res_details["filename"])

    @requests_mock.Mocker(kw="mock_request")
    def test_download_file_filename_from_content_disposition_with_additional_data(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {
            "Content-Type": "text/html",
            "Content-Disposition": "attachment; filename=example_file.html; size=1234",
        }
        mock_request.get(self.url, headers=headers, content=b"")
        res_type, res_details = download_file(self.url)
        pattern = r"^example_file_[a-zA-Z0-9]+\.html$"
        assert re.match(pattern, res_details["filename"])

    @pytest.mark.parametrize(
        "url, content_type, expected_pattern",
        [
            ("https://mocker-test.com/test-file", "text/csv", r"^test-file_[0-9a-f]{8}.csv$"),
            ("https://mocker-test.com/test-file", "text/html", r"^test-file_[0-9a-f]{8}.html$"),
            ("https://mocker-test.com/test-file.mp4", "text/csv", r"^test-file_[0-9a-f]{8}\.mp4$"),
            ("https://mocker-test.com/test-file.mp4", "text/html", r"^test-file_[0-9a-f]{8}\.mp4$"),
        ],
    )
    def test_download_file_filename_from_url(self, url, content_type, expected_pattern, requests_mock):
        # Given
        headers = {"Content-Type": content_type}
        requests_mock.get(url, headers=headers, content=b"")
        # When
        res_type, res_details = download_file(url)
        # Then
        assert re.fullmatch(expected_pattern, res_details["filename"])

    @requests_mock.Mocker(kw="mock_request")
    def test_download_file_is_octetstream(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {
            "Content-Type": "application/octetstream",
            "Content-Disposition": "attachment; filename=example_file.doc",
        }
        mock_request.get(self.url, headers=headers, content=b"")
        res_type, res_details = download_file(self.url)
        assert res_details["format"] == "doc"

    @requests_mock.Mocker(kw="mock_request")
    def test_download_file_is_octetstream_from_content_disposition_with_additional_data(self, **kwargs):
        mock_request = kwargs["mock_request"]
        headers = {
            "Content-Type": "application/octetstream",
            "Content-Disposition": 'attachment; filename="example_file.doc"; size=1234',
        }
        mock_request.get(self.url, headers=headers, content=b"")
        res_type, res_details = download_file(self.url)
        assert res_details["format"] == "doc"


def test_content_type_from_file_format_unsupported_format():
    family, content_type = content_type_from_file_format("mp4")
    assert family is None
    assert content_type is None


def test_content_type_from_zip_format():
    family, content_type = content_type_from_file_format("zip")
    assert family == "application"
    assert content_type == "zip"


def test_extension_from_content_type():
    extension = get_extension_from_mime_type("video/mp4")
    assert extension == "mp4"


@pytest.mark.parametrize(
    "url, expected_filename, expected_extension",
    [
        ("http://mocker-test.com/test-file", "test-file", ""),
        ("http://mocker-test.com/test-file.mp4", "test-file", "mp4"),
    ],
)
def test_filename_from_url(url: str, expected_filename: str, expected_extension: str):
    filename, extension = _filename_from_url(url)
    assert filename == expected_filename
    assert extension == expected_extension


@pytest.mark.parametrize(
    "filename, expected_pattern",
    [
        ("example.txt", r"example_[0-9a-f]{8}\.txt"),
        ("archive.tar.gz", r"archive\.tar_[0-9a-f]{8}\.gz"),
        ("noext", r"noext_[0-9a-f]{8}"),
        ("emptyext.", r"emptyext_[0-9a-f]{8}."),
        (".hiddenfile", r"\.hiddenfile_[0-9a-f]{8}"),
        ("", r"_[0-9a-f]{8}"),
        (".", r"\._[0-9a-f]{8}"),
    ],
)
def test_add_unique_suffix_to_filename(filename, expected_pattern):
    result = add_unique_suffix_to_filename(filename)
    assert isinstance(result, str)
    assert re.fullmatch(expected_pattern, result)


def test_add_unique_suffix_to_filename_uniqueness():
    results = {add_unique_suffix_to_filename("file.txt") for _ in range(10)}
    assert len(results) == 10
