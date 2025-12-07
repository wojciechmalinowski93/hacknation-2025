from typing import Optional
from unittest.mock import MagicMock, Mock

import requests
from pytest_mock import MockerFixture

from mcod.lib.utils import get_file_content


def mocked_response(url: str, content: Optional[bytes], headers: Optional[dict]) -> requests.Response:
    mock_resp = Mock(spec=requests.Response)
    mock_resp.url = url
    mock_resp.content = content
    mock_resp.headers = headers
    return mock_resp


def prepare_mock_ckan_response(
    *,
    mocker: MockerFixture,
    harvester_ckan_data_with_no_resource_format: dict,
    remote_file_url: str,
    test_data_file_name: Optional[str],
    ckan_response_headers: Optional[dict],
    format_from_magic_mock: Optional[str],
    format_in_ckan_payload: Optional[str],
) -> None:
    """
    Prepares mocks for testing CKAN harvester.
    Args:
        mocker: Fixture
        harvester_ckan_data_with_no_resource_format: Fixture with CKAN response payload (dict), assumed ony one resource
        remote_file_url: The remote file (data) from CKAN
        test_data_file_name: Optional payload, loaded from test_samples by name
        ckan_response_headers:
        format_from_magic_mock: Optional *extension* from magic (magic returns content-type, but this mock works a level further)
        format_in_ckan_payload: CKAN sources can specify format (i.e. extension) in the JSON paylod.

    Returns:
        Nothing - this fixture only configures mocks.
    """
    _ckan_payload = harvester_ckan_data_with_no_resource_format.copy()
    if format_in_ckan_payload:
        _ckan_payload[0]["resources"][0]["format"] = format_in_ckan_payload
    mocker.patch("mcod.harvester.utils.fetch_data", return_value=_ckan_payload)
    mocker.patch("mcod.harvester.models.DataSource._validate_ckan_type", return_value=None)
    mocker.patch("mcod.lib.file_format_from_response._get_extension_from_magic", return_value=format_from_magic_mock)
    # Mock file response
    if test_data_file_name:
        file_content = get_file_content(test_data_file_name)
    else:
        file_content = b""
    if not ckan_response_headers:
        ckan_response_headers = {}
    response_object = mocked_response(url=remote_file_url, content=file_content, headers=ckan_response_headers)
    mocker.patch("mcod.harvester.schema_utils.download_file", return_value=(None, {"response": response_object}))
    # Mock file response for STO calculation etc.
    _requests = MagicMock()
    _requests.get.return_value = response_object
    mocker.patch("mcod.resources.score_computation.score_calculation.requests", _requests)
