from typing import Optional

import pytest
from pytest_mock import MockerFixture

from mcod.harvester.tests.utils import mocked_response
from mcod.lib.file_format_from_response import (
    FormatFromResponse,
    _filename_from_url,
    _get_mime_type_from_content_disposition,
    _get_mime_type_from_content_type,
    _get_resource_formats_from_response,
    file_format_from_content_type_extension_map,
    get_resource_format_from_response,
)
from mcod.lib.utils import get_file_content


@pytest.mark.parametrize(
    "url, headers, expected_url, expected_magic, expected_content_type, expected_content_disposition, mocked_mime_type",
    [
        ("https://mcod.local/some.csv?param=param", {}, "csv", None, None, None, None),
        ("https://mcod.local/some.csv", {}, "csv", None, None, None, None),
        ("https://mcod.local/some", {}, None, "csv", None, None, "text/csv"),
        ("https://mcod.local/some", {"Content-Type": "text/pdf"}, None, None, "pdf", None, None),
        (
            "https://mcod.local/some",
            {"Content-Disposition": "attachment; filename=some.jpeg"},
            None,
            None,
            None,
            "jpeg",
            None,
        ),
        (
            "https://mcod.local/some",
            {
                "Content-Disposition": "attachment; filename=some.csv",
                "Content-Type": "image/jpeg",
            },
            None,
            None,
            "jpeg",
            "csv",
            None,
        ),
    ],
)
def test_get_resource_formats_from_response(
    url: str,
    headers: dict,
    expected_url: str,
    expected_magic: str,
    expected_content_type: str,
    mocker: MockerFixture,
    mocked_mime_type: Optional[str],
    expected_content_disposition: Optional[str],
):
    """
    Test `get_resource_formats_from_response` with various combinations of URL and HTTP headers
    to ensure correct detection of file format metadata.

    The function should infer format information from the following sources:
    - URL (e.g., file extension),
    - Content-Type header,
    - Content-Disposition header,
    - MIME type from file content (mocked in this test).

    Each test case simulates a different edge case, such as:
    - Presence or absence of file extension in the URL,
    - Empty, missing, or conflicting HTTP headers,
    - MIME type detection based on mocked file content,
    - Inconsistencies between headers and inferred metadata.

    Note:
    Since MIME detection via `python-magic` can vary across platforms, we mock
    `get_file_mime_type_from_chunk` to ensure consistent test behavior regardless of the environment.
    """
    response_object = mocked_response(url=url, content=b"", headers=headers)
    mocker.patch("mcod.lib.file_format_from_response.get_file_mime_type_from_chunk", return_value=mocked_mime_type)
    res: FormatFromResponse = _get_resource_formats_from_response(response_object)
    assert isinstance(res, FormatFromResponse)
    assert res.url == expected_url
    assert res.magic == expected_magic
    assert res.content_type == expected_content_type
    assert res.content_disposition == expected_content_disposition


def test_get_resource_format_from_response_if_stages_works_as_expected_url():
    """
    Test that get_resource_format_from_response uses URL first to detect format
    when multiple hints are available.
    """
    url = "https://mcod.local/some.pdf"
    response_object = mocked_response(
        url=url,
        content=get_file_content("csv2jsonld.csv"),  # type CSV
        headers={
            "Content-Disposition": "attachment; filename=some.xml",
            "Content-Type": "text/pdf",
        },
    )
    res: Optional[str] = get_resource_format_from_response(response_object)
    assert isinstance(res, str)
    assert res == "pdf"


@pytest.mark.xfail(
    reason="Assignment of mime-type to CSV varies between Debian (our Docker) and Ubuntu (Gitlab).",
)
def test_get_resource_format_from_response_if_stages_works_as_expected_magic():
    """
    Test that get_resource_format_from_response falls back to magic detection
    when URL provides no format and content contradicts headers.
    """
    url = "https://mcod.local/some"
    response_object = mocked_response(
        url=url,
        content=get_file_content("csv2jsonld.csv"),  # type CSV
        headers={
            "Content-Disposition": "attachment; filename=some.csv",
            "Content-Type": "text/pdf",
        },
    )
    res: Optional[str] = get_resource_format_from_response(response_object)
    assert isinstance(res, str)
    assert res == "csv"


def test_get_resource_format_from_response_if_stages_works_as_expected_content_type():
    """
    Test that get_resource_format_from_response uses Content-Type as last resort
    when neither URL nor magic detection provides the format.
    """
    url = "https://mcod.local/some"
    response_object = mocked_response(
        url=url,
        content=b"",
        headers={
            "Content-Disposition": "attachment; filename=some.csv",
            "Content-Type": "text/pdf",
        },
    )
    res: Optional[str] = get_resource_format_from_response(response_object)
    assert isinstance(res, str)
    assert res == "pdf"


@pytest.mark.parametrize(
    "content_disposition_header, expected_file_extension",
    [
        ("filename=some.xml", "xml"),
        ("filename=some.csv", "csv"),
        ("filename=some.blabla", "blabla"),
        (None, None),
        ("attachment; filename*=UTF-8''file%20name.jpg", "jpg"),
        ("attachment; filename=zażółć.jpg", "jpg"),
    ],
)
def test__get_mime_type_from_content_disposition(content_disposition_header, expected_file_extension):
    res = _get_mime_type_from_content_disposition({"Content-Disposition": f"attachment; {content_disposition_header}"})
    assert res == expected_file_extension


@pytest.mark.parametrize(
    "content_type, expected_file_extension",
    [
        ("text/pdf", "pdf"),
        ("text/csv", "csv"),
        ("application/csv", "csv"),
        ("application/x-csv", "csv"),
        ("application/x-excel", "xls"),
        ("application/atom+xml", "xml"),
        ("application/zip", "zip"),
        ("application/xml", "xml"),
        ("text/xml", "xml"),
        (None, None),
        ("application/xml; boundary=ExampleBoundaryString", "xml"),
        ("multipart/form-data; boundary=ExampleBoundaryString", None),
        ("", None),
    ],
)
def test__get_mime_type_from_content_type(content_type: Optional[str], expected_file_extension: Optional[str]) -> None:
    actual = _get_mime_type_from_content_type({"Content-Type": content_type})
    assert actual == expected_file_extension


@pytest.mark.parametrize(
    "url, expected_result",
    [
        ("https://mcod.local/some.csv", ("some", "csv")),
        ("https://mcod.local/.csv", ("unknown", "")),
        ("https://mcod.local/some", ("some", "")),
    ],
)
def test__filename_from_url(url, expected_result):
    res = _filename_from_url(url)
    assert res == expected_result


@pytest.mark.parametrize(
    "mime_type, family, extension, expected_extension",
    [
        ("x-csv", None, None, "csv"),
        ("csv", "application", None, "csv"),
        ("csv", "application", "xml", "csv"),
        ("nt-triples", "application", "nt11", "nt11"),
        ("nt-triples", "application", None, "nt"),
        ("zip", None, None, "zip"),
        ("x-7z", None, None, None),
        ("x-7z-compressed", None, None, "7z"),
    ],
)
def test_file_format_from_content_type_extension_map(
    mime_type: Optional[str], family: Optional[str], extension: Optional[str], expected_extension: Optional[str]
):
    actual = file_format_from_content_type_extension_map(mime_type, family, extension)
    assert actual == expected_extension
