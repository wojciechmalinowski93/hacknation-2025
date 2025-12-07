from typing import Type
from unittest.mock import MagicMock, patch

import pytest
from elasticsearch import ConnectionError as ESConnectionError, exceptions as es_exceptions
from namedlist import namedlist

from mcod.core.api.search.helpers import (
    ElasticsearchHit,
    _handle_es_error,
    get_index_hits,
    get_index_total,
)
from mcod.core.exceptions import ElasticsearchIndexError
from mcod.lib.helpers import change_namedlist, validate_update_data_for_beat_schedule


class TestChangeNamedlist:
    def test_correct_change(self):
        test_list = namedlist("test_list", ["x", "y"])
        test_list_instance = test_list(1, 2)
        assert test_list_instance.x == 1
        assert test_list_instance.y == 2

        test_list_instance2 = change_namedlist(test_list_instance, {"x": 3})
        assert test_list_instance2.x == 3
        assert test_list_instance2.y == 2

    def test_assert(self):
        test_list = namedlist("test_list", ["x", "y"])
        test_list_instance = test_list(1, 2)
        with pytest.raises(KeyError) as e:
            change_namedlist(test_list_instance, {"z": 3})
        assert "Field with name z is not in list test_list(x=1, y=2)" in str(e.value)


@pytest.mark.parametrize(
    ["data_to_validate", "expected_result"],
    [
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":21, "hour": 23, "minute": 20}}',
            True,
            id="OK - 1 task data for change",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":21, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}}',
            True,
            id="OK - 2 tasks data for change",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":21, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}, "catalog_xml_file_creation":{"hour": 8, "minute": 10}}',
            False,
            id="One task duplicated in data_to_validate",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":21, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation_xxxxxxxxx":{"hour": 7, "minute": 5}}',
            False,
            id="task name not in beat_schedule",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"month_of_year": 13, "day_of_month":21, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}}',
            False,
            id="bad month_of_year value",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_week":8, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}}',
            False,
            id="bad day_of_week value",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":32, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}}',
            False,
            id="bad day_of_month value",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":21, "hour": 26, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}}',
            False,
            id="bad hour value",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":21, "hour": 23, "minute": 10},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 85}}',
            False,
            id="bad minute value",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"doy_of_month":10, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5}}',
            False,
            id="bad parameter name (doy_of_month)",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":10, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"houur": 7, "minute": 5}}',
            False,
            id="bad parameter name (houur)",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":10, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "mminut": 5}}',
            False,
            id="bad parameter name (mminut)",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":10, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7, "minute": 5, "aaaa": 5}}',
            False,
            id="additional bad parameter name (aaaa)",
        ),
        pytest.param(
            '{"kronika_sparql_performance": {"day_of_month":10, "hour": 23, "minute": 20},'
            ' "catalog_xml_file_creation":{"hour": 7}}',
            True,
            id="time parameter without minute",
        ),
        pytest.param(
            "aaaabbbccc",
            False,
            id="not correct parameters structure - string",
        ),
        pytest.param(
            "{}",
            False,
            id="not correct parameters structure - empty dict",
        ),
        pytest.param(
            "[]",
            False,
            id="not correct parameters structure - empty list",
        ),
        pytest.param(
            "",
            False,
            id="not correct parameters structure - empty string",
        ),
    ],
)
def test_validate_update_data_for_beat_schedule(beat_schedule_fixture: dict, data_to_validate: str, expected_result: bool):
    assert validate_update_data_for_beat_schedule(beat_schedule_fixture, data_to_validate) == expected_result


def test_validate_update_data_for_beat_schedule_task_name_included_other_task_name(beat_schedule_fixture: dict):
    beat_schedule: dict = {**beat_schedule_fixture, "catalog_xml_file_creation_extended_name": {"hour": 8, "minute": 10}}
    data_to_validate: str = (
        '{"kronika_sparql_performance": {"day_of_month":21, "hour": 23, "minute": 20}, '
        '"catalog_xml_file_creation":{"hour": 7, "minute": 5}, '
        '"catalog_xml_file_creation_extended_name":{"hour": 12, "minute": 30}}'
    )
    assert validate_update_data_for_beat_schedule(beat_schedule, data_to_validate)


@pytest.mark.parametrize(
    "total_value",
    [
        pytest.param(MagicMock(value=111), id="total_as_object"),  # Elasticsearch 7+
        pytest.param(111, id="total_as_int"),  # Elasticsearch 6
    ],
)
def test_get_index_total_handles_total(total_value):
    """
    Test if `get_index_total()` correctly handles hits.total being either
    an int (ES 6.x) or an object with `.value` (ES 7.x+).
    """
    # Given
    total_hits = 111
    index_name = "test-index"
    mock_resp = MagicMock()
    mock_resp.hits.total = total_value

    with patch("mcod.core.api.search.helpers.get_connection") as es_conn, patch(
        "mcod.core.api.search.helpers.Search"
    ) as es_search:
        instance = es_search.return_value
        instance.extra.return_value = instance
        instance.execute.return_value = mock_resp
        # When
        result = get_index_total(index_name)
        # Then
        assert result == total_hits
        es_conn.assert_called_once()
        es_search.assert_called_once_with(using=es_conn(), index=index_name)


def test_get_index_total_with_query():
    """
    Test if a function `get_index_total()` returns the mocked total hits,
    where metadata hits.total is treated as an integer (Elasticsearch 6.x and earlier).
    """
    # Given
    total_hits = 111
    index_name = "test-index"
    mock_resp = MagicMock()
    mock_resp.hits.total = MagicMock(value=total_hits)

    with patch("mcod.core.api.search.helpers.get_connection") as es_conn, patch(
        "mcod.core.api.search.helpers.Search"
    ) as es_search:
        instance = es_search.return_value
        instance.extra.return_value = instance
        instance.query.return_value = instance
        instance.execute.return_value = mock_resp
        fake_query = MagicMock()
        # When
        result = get_index_total(index_name, query=fake_query)
        # Then
        assert result == total_hits
        es_conn.assert_called_once()
        es_search.assert_called_once_with(using=es_conn(), index=index_name)
        instance.query.assert_called_once_with(fake_query)


def _es_exception_factory(exc_type: Type[Exception]) -> Exception:
    """
    Create an Elasticsearch exception instance safely for testing.

    Args:
        exc_type: The exception class to instantiate.

    Returns:
        An instance of the given exception type.
    """
    exc_args_map = {
        es_exceptions.ConnectionTimeout: ("N/A", "timeout"),
        es_exceptions.ConnectionError: ("N/A", "connection failed"),
        es_exceptions.AuthorizationException: (403, "not authorized"),
        es_exceptions.NotFoundError: (404, "index not found"),
        es_exceptions.RequestError: (400, "bad_request", {"query": "test"}),
        es_exceptions.ElasticsearchException: (500, "generic ES error"),
    }
    exc_args = exc_args_map[exc_type]
    return exc_type(*exc_args)


@pytest.mark.parametrize(
    "exc_type, expected_msg_part",
    [
        (es_exceptions.ConnectionTimeout, "Timeout"),
        (es_exceptions.ConnectionError, "Failed to connect"),
        (es_exceptions.AuthorizationException, "Not authorized"),
        (es_exceptions.NotFoundError, "not found"),
        (es_exceptions.RequestError, "Invalid Elasticsearch query"),
        (es_exceptions.ElasticsearchException, "Unexpected Elasticsearch error"),
    ],
)
def test_handle_es_error_maps_known_exceptions(exc_type, expected_msg_part):
    """
    Test that `_handle_es_error()` maps known Elasticsearch exceptions correctly.
    """
    # Given
    exc = _es_exception_factory(exc_type)
    index_name = "test-index"

    with patch("mcod.core.api.search.helpers.logger") as mock_logger:
        with pytest.raises(ElasticsearchIndexError) as e:
            # When
            _handle_es_error(exc, index_name)

    # Then
    mock_logger.error.assert_called_once()
    assert expected_msg_part in str(e.value)


def test_handle_es_error_raises_original_for_unknown_exception():
    """Test that unknown exceptions are re-raised as-is."""

    # Given
    class CustomError(Exception):
        pass

    exc = CustomError("some error")
    index_name = "test-index"

    # When/Then
    with pytest.raises(CustomError):
        _handle_es_error(exc, index_name)


def test_get_index_hits_success(es_hits_response_factory):
    # Given
    index_name = "test-index"
    total_hits = 5
    fake_response = es_hits_response_factory(count=total_hits)

    with patch("mcod.core.api.search.helpers.Search.execute", return_value=fake_response):
        # When
        hits = get_index_hits(index=index_name, size=total_hits)

    # Then
    assert len(hits) == total_hits
    assert all(isinstance(hit, ElasticsearchHit) for hit in hits)
    assert all(hasattr(hit, "id") and hasattr(hit, "source") for hit in hits)


def test_get_index_hits_failure_connection_error():
    # Given
    index_name = "test-index"
    total_hits = 5

    with patch("mcod.core.api.search.helpers.get_connection", side_effect=ESConnectionError("ES error")):
        with pytest.raises(ElasticsearchIndexError) as exc_info:
            # When
            get_index_hits(index=index_name, size=total_hits)

    # Then
    assert isinstance(exc_info.value, ElasticsearchIndexError)
    assert index_name in str(exc_info.value)


def test_get_index_hits_unsuccessful_response(es_hits_response_factory):
    # Given
    index_name = "test-index"
    total_hits = 5
    fake_response = es_hits_response_factory(count=total_hits)
    fake_response.success = lambda: False
    with patch("mcod.core.api.search.helpers.get_connection"), patch(
        "mcod.core.api.search.helpers.Search.execute", return_value=fake_response
    ):
        # When
        with pytest.raises(ElasticsearchIndexError) as exc_info:
            get_index_hits(index=index_name, size=total_hits)
    # Then
    assert f"Query to index '{index_name}' did not complete successfully" in str(exc_info.value)
