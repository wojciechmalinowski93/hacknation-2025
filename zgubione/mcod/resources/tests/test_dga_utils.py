from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
import requests

from mcod.resources.dga_utils import (
    get_ckan_dga_resource_df,
    get_remote_extension_if_correct_dga_content_type,
    request_remote_dga,
)


def test_request_remote_dga_success(requests_mock):
    url = "https://example.com"
    requests_mock.get(url, content=b"mocked content", status_code=200)
    response = request_remote_dga(url)

    assert response.status_code == 200
    assert response.content == b"mocked content"


@pytest.mark.parametrize(
    "raised_exception",
    [
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.SSLError,
        requests.exceptions.ReadTimeout,
        requests.exceptions.HTTPError,
    ],
)
def test_request_remote_dga_raise_exception(requests_mock, raised_exception):
    url = "https://example.com"
    requests_mock.get(url, exc=raised_exception)

    with pytest.raises(requests.exceptions.RequestException):
        request_remote_dga(url)


@pytest.mark.parametrize(
    "content_type, expected_extension",
    [
        ("text/csv", "csv"),
        ("application/vnd.ms-excel", "xls"),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
        ("application/json", None),
        ("application/json", None),
        ("text/plain", None),
        ("text/html", None),
        ("application/msword", None),
        ("invalid/content-type", None),
        ("", None),
    ],
)
def test_get_remote_extension_if_correct_dga_content_type(content_type: str, expected_extension: Optional[str]):
    response = MagicMock()
    response.headers = {"Content-Type": content_type}
    result = get_remote_extension_if_correct_dga_content_type(response)

    assert result == expected_extension


@pytest.fixture
def mock_resource_with_link():
    resource = MagicMock()
    resource.link = "https://example.com"
    yield resource


@pytest.fixture
def mock_request_remote_dga():
    with patch("mcod.resources.dga_utils.request_remote_dga") as mock:
        yield mock


@pytest.fixture
def mock_request_remote_dga_status_200():
    with patch("mcod.resources.dga_utils.request_remote_dga") as mock:
        response = MagicMock()
        response.status_code = 200
        response.content = b"mocked content"

        mock.return_value = response
        yield mock


@pytest.fixture
def mock_get_remote_extension():
    with patch("mcod.resources.dga_utils.get_remote_extension_if_correct_dga_content_type") as mock:
        yield mock


@pytest.fixture
def mock_create_df_from_dga_file():
    with patch("mcod.resources.dga_utils.create_df_from_dga_file") as mock:
        yield mock


@pytest.fixture
def mock_validate_dga_df_columns():
    with patch("mcod.resources.dga_utils.validate_dga_df_columns") as mock:
        yield mock


@pytest.mark.feat_main_dga
def test_no_ckan_dga_df_when_resource_with_no_link():
    # GIVEN
    resource = MagicMock()
    resource.link = None
    # WHEN
    df = get_ckan_dga_resource_df(resource)
    # THEN
    assert df is None


def test_no_ckan_dga_df_when_site_not_responding(
    mock_resource_with_link,
    mock_request_remote_dga,
):
    # GIVEN
    mock_request_remote_dga.side_effect = requests.exceptions.RequestException
    # WHEN
    df = get_ckan_dga_resource_df(mock_resource_with_link)
    # THEN
    mock_request_remote_dga.assert_called_once_with(mock_resource_with_link.link)
    assert df is None


def test_no_ckan_dga_df_when_link_status_code_not_200(
    mock_resource_with_link,
    mock_request_remote_dga,
):
    # GIVEN
    response = MagicMock()
    response.status_code = 400
    mock_request_remote_dga.return_value = response
    # WHEN
    df = get_ckan_dga_resource_df(mock_resource_with_link)
    # THEN
    mock_request_remote_dga.assert_called_once_with(mock_resource_with_link.link)
    assert df is None


def test_no_ckan_dga_df_when_incorrect_file_extension(
    mock_resource_with_link,
    mock_request_remote_dga_status_200,
    mock_get_remote_extension,
):
    # GIVEN
    mock_get_remote_extension.return_value = None

    # WHEN
    df = get_ckan_dga_resource_df(mock_resource_with_link)

    # THEN
    mock_request_remote_dga_status_200.assert_called_once_with(mock_resource_with_link.link)
    mock_get_remote_extension.assert_called_once_with(mock_request_remote_dga_status_200())
    assert df is None


def test_no_ckan_dga_df_when_parse_data_error(
    mock_resource_with_link,
    mock_request_remote_dga_status_200,
    mock_get_remote_extension,
    mock_create_df_from_dga_file,
):
    # GIVEN
    mock_create_df_from_dga_file.return_value = None

    # WHEN
    df = get_ckan_dga_resource_df(mock_resource_with_link)

    # THEN
    mock_request_remote_dga_status_200.assert_called_once_with(mock_resource_with_link.link)
    mock_get_remote_extension.assert_called_once_with(mock_request_remote_dga_status_200())
    mock_create_df_from_dga_file.assert_called_once()
    assert df is None


@pytest.mark.parametrize("is_valid_file_structure", [False, True])
def test_ckan_dga_df_if_valid_file_structure(
    is_valid_file_structure: bool,
    mock_resource_with_link,
    mock_request_remote_dga_status_200,
    mock_get_remote_extension,
    mock_create_df_from_dga_file,
    mock_validate_dga_df_columns,
):
    # GIVEN
    mock_df = MagicMock()
    mock_create_df_from_dga_file.return_value = mock_df

    mock_validate_dga_df_columns.return_value = is_valid_file_structure

    # WHEN
    df = get_ckan_dga_resource_df(mock_resource_with_link)

    # THEN
    mock_request_remote_dga_status_200.assert_called_once_with(mock_resource_with_link.link)
    mock_get_remote_extension.assert_called_once_with(mock_request_remote_dga_status_200())
    mock_create_df_from_dga_file.assert_called_once()
    mock_validate_dga_df_columns.assert_called_once_with(mock_df)

    if is_valid_file_structure:
        assert df == mock_df
    else:
        assert df is None
