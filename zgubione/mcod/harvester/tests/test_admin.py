import os.path
from typing import Dict, Literal, Optional

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from pytest_mock import MockerFixture

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.harvester.models import STATUS_ERROR, STATUS_OK, DataSource
from mcod.harvester.tests.utils import prepare_mock_ckan_response
from mcod.resources.models import Resource

User = get_user_model()


POST_CREATE_CKAN_DATASOURCE = {
    "name": "some_name",
    "description": "some description",
    "source_type": "ckan",
    "portal_url": "https://mcod.local",
    "api_url": "https://mcod.local",
    "frequency_in_days": 7,
    "status": "active",
    "institution_type": "other",
    "emails": "email@email.com",
    # Management form fields for `imports`
    "imports-TOTAL_FORMS": 0,
    "imports-INITIAL_FORMS": 0,
    "imports-MIN_NUM_FORMS": 0,
    "imports-MAX_NUM_FORMS": 1000,
    # Management form fields for `datasource_datasets`
    "datasource_datasets-TOTAL_FORMS": 0,
    "datasource_datasets-INITIAL_FORMS": 0,
    "datasource_datasets-MIN_NUM_FORMS": 0,
    "datasource_datasets-MAX_NUM_FORMS": 1000,
}
client = Client()
data_source_admin_url = reverse("admin:harvester_datasource_add")


class TestHarvesterImportsCkanStoCalculation:
    """
    Integration tests for verifying the automatic calculation of openness scores (STO)
    for datasets imported via a CKAN source in the Django admin interface.

    This class simulates the full flow of adding a new `DataSource` of type `ckan` through the
    admin panel, mocking external HTTP responses and file contents to control the format
    of returned resources and verify that the openness score is correctly calculated.
    """

    @pytest.mark.parametrize(
        "expected_openness_score, test_data_file_name, format_in_ckan_payload",
        [
            (3, "csv2jsonld.csv", "csv"),
            (1, "example.pdf", "pdf"),
        ],
    )
    def test_sto_calculates_for_ckan(
        self,
        mocker: "MockerFixture",
        admin: User,
        harvester_ckan_data_with_no_resource_format: dict,
        test_data_file_name: str,
        expected_openness_score: int,
        format_in_ckan_payload: str,
    ):
        """
        Parametrized test to verify correct calculation of the openness score (STO)
        for resources harvested from a CKAN source, based on file format.
        """
        # WHEN admin logins
        client.force_login(admin)
        # GIVEN CKAN example data
        prepare_mock_ckan_response(
            mocker=mocker,
            harvester_ckan_data_with_no_resource_format=harvester_ckan_data_with_no_resource_format,
            format_in_ckan_payload=format_in_ckan_payload,
            remote_file_url="https://mcod.local/test_sto_calculates_for_ckan/",
            test_data_file_name=test_data_file_name,
            format_from_magic_mock=None,
            ckan_response_headers={"Content-Type": "application/csv"},
        )
        # WHEN request post sends to django admin page
        post_data: dict = POST_CREATE_CKAN_DATASOURCE
        client.post(data_source_admin_url, data=post_data, follow=True)

        run_on_commit_events()
        resource: Resource = Resource.objects.first()

        # THEN resource is created with calculated openness score value.
        assert resource.openness_score == expected_openness_score
        # AND resource format is driven by CKAN
        assert resource.format == format_in_ckan_payload

    @pytest.mark.parametrize(
        "test_data_file_name, "
        "format_in_ckan_payload, "
        "remote_file_url,"
        "format_from_magic, "
        "mime_type_in_content_type, "
        "format_in_content_disposition, "
        "expected_format, expected_openness_score",
        [
            pytest.param(
                "csv2jsonld.csv",
                None,
                "https://mcod.local/test_ckan_resource_format_precedence/csv2jsonld.csv",
                "txt",
                "application/xml",
                "json",
                # exp
                "csv",
                3,
                id="URL > Magic",
            ),
            pytest.param(
                "csv2jsonld.csv",
                None,
                "https://mcod.local/test_ckan_resource_format_precedence/csv2jsonld-no-ext",
                "txt",
                "application/xml",
                "json",
                # exp
                "txt",
                1,
                id="Magic > Content-Type",
            ),
            pytest.param(
                "csv2jsonld.csv",
                None,
                "https://mcod.local/test_ckan_resource_format_precedence/csv2jsonld-no-ext",
                None,
                "application/xml",
                "json",
                # exp
                "xml",
                3,
                id="Content-Type > Content-Disposition",
            ),
            pytest.param(
                "csv2jsonld.csv",
                None,
                "https://mcod.local/test_ckan_resource_format_precedence/csv2jsonld-no-ext",
                None,
                None,
                "json",
                # exp
                "json",
                3,
                id="Content-Disposition if nothing else",
            ),
            pytest.param(
                "csv2jsonld.csv",
                "pdf",
                "https://mcod.local/test_ckan_resource_format_precedence/csv2jsonld.txt",
                "txt",
                "application/xml",
                "json",
                # exp
                "pdf",
                1,
                id="resources[0].format > everything else",
            ),
            pytest.param(
                "csv2jsonld.csv",
                "pdf",
                "https://mcod.local/test_ckan_resource_format_precedence/csv2jsonld.txt",
                None,
                None,
                None,
                # exp
                "pdf",
                1,
                id="resources[0].format > everything else",
            ),
        ],
    )
    def test_ckan_resource_format_precedence(
        self,
        mocker: "MockerFixture",
        admin: User,
        harvester_ckan_data_with_no_resource_format: dict,
        #
        test_data_file_name: str,
        format_in_ckan_payload: Optional[str],
        remote_file_url: str,
        format_from_magic: Optional[str],
        mime_type_in_content_type: Optional[str],
        format_in_content_disposition: Optional[str],
        expected_format: str,
        expected_openness_score: int,
    ):
        """
        Parametrized test to verify correct calculation of the openness score (STO)
        for resources harvested from a CKAN source, based on file format.
        """
        # WHEN admin logins
        client.force_login(admin)
        # GIVEN CKAN example data
        headers: Dict[str, str] = {}
        if mime_type_in_content_type:
            headers["Content-Type"] = mime_type_in_content_type
        if format_in_content_disposition:
            _filename, _ = os.path.splitext(test_data_file_name)
            headers["Content-Disposition"] = f"attachment; filename={_filename}.{format_in_content_disposition}"
        prepare_mock_ckan_response(
            mocker=mocker,
            harvester_ckan_data_with_no_resource_format=harvester_ckan_data_with_no_resource_format,
            format_in_ckan_payload=format_in_ckan_payload,
            remote_file_url=remote_file_url,
            test_data_file_name=test_data_file_name,
            format_from_magic_mock=format_from_magic,
            ckan_response_headers=headers,
        )
        # WHEN request post sends to django admin page
        post_data: dict = POST_CREATE_CKAN_DATASOURCE
        client.post(data_source_admin_url, data=post_data, follow=True)
        # And
        run_on_commit_events()
        # Then resource exists
        resource: Resource = Resource.objects.first()
        assert resource
        # THEN resource is created with calculated openness score value.
        assert resource.openness_score == expected_openness_score
        # AND resource format is driven by CKAN
        assert resource.format == expected_format


@pytest.mark.parametrize(
    "url, file_name, headers, format_from_magic_mock, format_in_payload, expected_status, expected_format",
    [
        ("https://mcod.local", "csv2jsonld.csv", {}, "csv", None, STATUS_OK, "csv"),
        ("https://mcod.local/csv2jsonld.csv.txt", None, {}, None, "csv", STATUS_OK, "csv"),
        ("https://mcod.local", None, {}, None, None, STATUS_OK, None),
        ("https://mcod.local", "example_dga_xls_file.xls", {}, "xls", None, STATUS_OK, "xls"),
        ("https://mcod.local", "example_geojson.geojson", {}, "json", None, STATUS_OK, "json"),
        pytest.param(
            "https://mcod.local",
            "geo.csv",
            {},
            "txt",
            None,
            STATUS_OK,
            "txt",
            id="Python magic will interpret geo.csv as plain/text. We want to allow harvester to go on.",
        ),
        (
            "https://mcod.local",
            None,
            {
                "Content-Disposition": "attachment; filename=some.xml",
                "Content-Type": "text/pdf",
            },
            "pdf",
            None,
            STATUS_OK,
            "pdf",
        ),
        (
            "https://mcod.local",
            None,
            {
                "Content-Disposition": "attachment; filename=some.xml",
            },
            "xml",
            None,
            STATUS_OK,
            "xml",
        ),
        (
            "https://mcod.local",
            None,
            {
                "Content-Type": "text/pdf",
            },
            "pdf",
            None,
            STATUS_OK,
            "pdf",
        ),
        ("https://mcod.local", None, {}, None, None, STATUS_OK, None),
        (
            "https://mcod.local",
            None,
            {},
            None,
            None,
            STATUS_OK,
            None,
        ),
        pytest.param(
            "https://mcod.local",
            None,
            {"Content-Disposition": "attachment; filename='" "file name.jpg" "'; filename*=UTF-8''file%20name.jpg"},
            None,
            None,
            STATUS_ERROR,
            None,
            id="Invalid header value structure. Should be double quote.",
        ),
        ("https://mcod.local/some.bat", None, {}, None, None, STATUS_ERROR, None),
        ("https://mcod.local/some.asp", None, {}, None, None, STATUS_ERROR, None),
        ("https://mcod.local/some.cgi", None, {}, None, None, STATUS_ERROR, None),
        ("https://mcod.local/some.exe", None, {}, None, None, STATUS_ERROR, None),
        pytest.param(
            "https://mcod.local/some.txt",
            None,
            {},
            "exe",  # magic
            "txt",  # ckan
            STATUS_OK,
            "txt",
            id="Magic recognised an exe so we should block the harvester, but CKAN source overrode format - so we don't",
        ),
        pytest.param(
            "https://mcod.local/some.txt",
            None,
            {},
            "txt",  # magic
            "exe",  # ckan
            STATUS_ERROR,
            "exe",
            id="Payload specified format as an exe, so should we block the harvester",
            marks=pytest.mark.xfail(reason="To fail change the location of format check to take payload['format'] into account."),
        ),
        (
            "https://mcod.local",
            None,
            {
                "Content-Disposition": "attachment; filename=some.bat",
            },
            None,
            None,
            STATUS_ERROR,
            None,
        ),
        (
            "https://mcod.local",
            None,
            {
                "Content-Disposition": "attachment; filename=some.asp",
            },
            None,
            None,
            STATUS_ERROR,
            None,
        ),
        (
            "https://mcod.local",
            None,
            {
                "Content-Disposition": "attachment; filename=some.exe",
            },
            None,
            None,
            STATUS_ERROR,
            None,
        ),
        (
            "https://mcod.local",
            None,
            {
                "Content-Disposition": "attachment; filename=some_no_known.blabla",
            },
            None,
            None,
            STATUS_ERROR,
            None,
        ),
        pytest.param(
            "https://mcod.local",
            "sample.bat",
            {},
            None,
            None,
            STATUS_OK,
            None,
            id="Python magic would interpret sample.bat as x-msdos-batch, "
            "but function get_mime_type_from_magic will return None (unknown mime-type). "
            "We want to allow harvester to go on.",
        ),
        ("https://mcod.local", None, {"Content-Disposition": "attachment; filename=some.bat"}, None, None, STATUS_ERROR, None),
        pytest.param(
            "https://mcod.local/case-when/",
            None,
            {"Content-Type": "attachment; filename=some.bat"},
            None,
            None,
            STATUS_OK,
            "txt",  # todo: why txt?
            id="Case when content-type returned unrecognized extension. Means we are not stopping harvester.",
        ),
        pytest.param(
            "https://mcod.local",
            None,
            {"Content-Type": "text/bat"},
            None,
            None,
            STATUS_ERROR,
            None,
            marks=pytest.mark.xfail(reason="Test will not fail, because mimetypes library wont recognize this mimetype"),
        ),
    ],
)
def test_harvester_resource_format_validation(
    mocker: MockerFixture,
    url: str,
    file_name: Optional[str],
    headers: dict,
    format_from_magic_mock: Optional[str],
    format_in_payload: Optional[str],
    expected_status: Literal["ok", "error"],
    expected_format: Optional[str],
    admin: User,
    harvester_ckan_data_with_no_resource_format: dict,
):
    """
    Test `POST` behavior of CKAN data sources based on file content, headers, and filenames. See get_resource_format.

    This test validates the harvester's behavior when attempting to determine the file format of a resource
    based on various combinations of:
    - the file name (when available),
    - HTTP response headers (Content-Type, Content-Disposition),
    - and Python's file magic detection (e.g., via `mimetypes` or similar tools).

    It ensures that:
    - Files with recognized extensions or headers are assigned correct formats.
    - Files with ambiguous or unsafe formats (e.g., .bat) are either rejected or passed through based on logic.
    - No format leads to `None`, while disallowed types raise an error and mark the import as failed.

    Each test case provides:
    - `url`: The URL the resource would have been downloaded from.
    - `file_name`: Example file name if available (used for format inference).
    - `headers`: Simulated HTTP headers from the server's response.
    - `format_in_payload`: CKAN datasource can set format in the payload.
    - `format_from_magic_mock`: In lieu of using magic (aka file) to determine file type from bytes we mock it here.
    - `expected_status`: Expected status of the import process (DataSourceImport).
    - `expected_format`: The expected value stored in the `Resource.format` field, or `None` if not applicable.

    This test uses mocking to simulate downloading a file and skips actual HTTP request, the actual
    file content comes from data/test_samples
    """
    # GIVEN
    client.force_login(admin)
    # GIVEN CKAN example data
    prepare_mock_ckan_response(
        mocker=mocker,
        harvester_ckan_data_with_no_resource_format=harvester_ckan_data_with_no_resource_format,
        format_in_ckan_payload=format_in_payload,
        remote_file_url=url,
        test_data_file_name=file_name,
        format_from_magic_mock=format_from_magic_mock,
        ckan_response_headers=headers,
    )
    #  WHEN
    client.post(data_source_admin_url, data=POST_CREATE_CKAN_DATASOURCE, follow=True)
    run_on_commit_events()
    # THEN
    datasource: DataSource = DataSource.objects.first()
    assert datasource.imports.first().status == expected_status
    # AND
    if expected_status == STATUS_OK:
        assert datasource.datasource_datasets.exists()
        assert datasource.datasource_datasets.first().resources.first().format == expected_format
    elif expected_status == STATUS_ERROR:
        assert not datasource.datasource_datasets.exists()
