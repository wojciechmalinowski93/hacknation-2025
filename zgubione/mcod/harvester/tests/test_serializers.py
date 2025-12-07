from typing import List, Optional

import pytest
from pytest_mock import MockerFixture

from mcod.harvester.serializers import DatasetSchema
from mcod.harvester.tests.utils import mocked_response
from mcod.lib.utils import get_file_content


@pytest.mark.parametrize(
    "url, sample_filename, content_type, expected_format, magic_mime",
    [
        ("https://mock-endpoint.local/some.xml", "csv2jsonld.csv", "application/pdf", "xml", "application/csv"),
        ("https://mock-endpoint.local/some", "csv2jsonld.csv", "application/pdf", "csv", "application/csv"),
        ("https://mock-endpoint.local/some", None, "application/pdf", "pdf", None),
    ],
)
def test_valid_format_extraction_from_ckan_url(
    mocker: MockerFixture,
    url: str,
    sample_filename: Optional[str],
    content_type: str,
    expected_format: str,
    magic_mime: Optional[str],
    harvester_ckan_data_with_no_resource_format: List[dict],
):
    """
    Test correct format extraction from CKAN-style harvested data using various URL, content
    and content-type combinations.
    """
    # GIVEN file content, headers and url
    file_content = get_file_content(filename=sample_filename)
    headers = {
        "Content-Type": content_type,
    }
    # THEN create mock response
    get_mocked_response = mocked_response(url, file_content, headers)
    return_value = {"response": get_mocked_response}
    mocker.patch("mcod.harvester.schema_utils.download_file", return_value=(None, return_value))
    mocker.patch("mcod.lib.file_format_from_response.get_file_mime_type_from_chunk", return_value=magic_mime)

    # WHEN creating XML schema instance

    schema = DatasetSchema(many=True)

    # WHEN load data to schema
    data = schema.load(harvester_ckan_data_with_no_resource_format)
    resource_format: str = data[0]["resources"][0]["format"]

    # THEN calculated resource format is as expected
    assert resource_format == expected_format
