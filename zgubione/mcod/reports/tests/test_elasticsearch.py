from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

import pandas as pd
import pytest
from elasticsearch import Elasticsearch
from pytest_mock import MockerFixture

from mcod.reports.broken_links.constants import public_bl_report_elasticsearch_fields_types
from mcod.reports.broken_links.elasticsearch import (
    create_mapping,
    generate_index_from_pandas_df,
    rebuild_brokenlinks_es_index,
)
from mcod.reports.broken_links.public import _HEADERS_MAP


@pytest.fixture
def mock_bulk_write(mocker) -> MagicMock:
    return mocker.patch("mcod.reports.broken_links.elasticsearch.bulk", MagicMock())


@pytest.fixture
def example_pandas_df_brokelinks_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Dostawca": ["Org 1", "Org 4", "Org 3"],
            "Zbiór danych": ["dataset1", "dataset2", "dataset3"],
            "Dane": ["resource1", "resource2", "resource3"],
            "Link do danych na portalu": ["https://innerlink1", "https://innerlink2", "https://innerlink3"],
            "Uszkodzony link do danych dostawcy": ["https://outerlink1", "https://outerlink2", "https://outerlink3"],
        }
    )


@pytest.mark.parametrize(
    "elastic_search_fields_info, expected_mapping",
    [
        (
            {
                "some_int_field_1": "integer",
                "some_text_field_1": "text",
                "some_int_field_2": "integer",
                "some_text_field_2": "text",
                "some_float_field": "float",
                "some_date_field": "date",
                "some_boolean_field": "boolean",
            },
            {
                "mappings": {
                    "doc": {
                        "properties": {
                            "some_int_field_1": {"type": "integer"},
                            "some_text_field_1": {"fields": {"keyword": {"type": "keyword"}}, "type": "text"},
                            "some_int_field_2": {"type": "integer"},
                            "some_text_field_2": {"fields": {"keyword": {"type": "keyword"}}, "type": "text"},
                            "some_float_field": {"type": "float"},
                            "some_date_field": {"type": "date"},
                            "some_boolean_field": {"type": "boolean"},
                        }
                    }
                }
            },
        ),
        (dict(), {"mappings": {"doc": {"properties": {}}}}),
    ],
)
def test_create_mapping(elastic_search_fields_info: Dict[str, str], expected_mapping: Dict):
    """
    Tests `create_mapping` function for different data types and empty input data.
    """
    result_mapping: Dict = create_mapping(elastic_search_fields_info)
    assert result_mapping == expected_mapping


def test_generate_index_from_pandas_df(mock_bulk_write: MagicMock):
    mock_es_handler: Elasticsearch = MagicMock(spec=Elasticsearch)

    # GIVEN
    data: Dict[str, List[Any]] = {"col1": [1, 2, 3], "col2": [10, 20, 30], "col3": ["a", "aa", "aaa"], "col4": ["b", "bb", "bbb"]}
    df = pd.DataFrame(data)
    mock_bulk_write.return_value = (df.shape[1], 0)

    # WHEN
    result_stats: Tuple[int, int] = generate_index_from_pandas_df(mock_es_handler, "broken_links", df)

    # THEN
    mock_bulk_write.assert_called_once()
    assert result_stats == (df.shape[1], 0)
    args, kwargs = mock_bulk_write.call_args
    assert args[0] == mock_es_handler
    assert kwargs == {"stats_only": True}

    generator = args[1]
    arguments = list(generator)
    assert len(arguments) == 3


@pytest.mark.parametrize("index_exists", (True, False))
def test_brokenlinks_es_index_is_conditionally_deleted_and_always_created(
    mocker: MockerFixture, mock_bulk_write: MagicMock, example_pandas_df_brokelinks_data: pd.DataFrame, index_exists: bool
):
    # GIVEN
    mock_connections: MagicMock = mocker.patch("mcod.reports.broken_links.elasticsearch.Connections", MagicMock())
    mock_connections.return_value.get_connection.return_value.indices.exists.return_value = index_exists
    mock_bulk_write.return_value = (10, 0)
    change_cols_name_data = {str(v): str(k.value) for k, v in _HEADERS_MAP.items()}
    mapping: Dict = create_mapping(public_bl_report_elasticsearch_fields_types)
    # WHEN
    rebuild_brokenlinks_es_index(
        "aaa",
        public_bl_report_elasticsearch_fields_types,
        example_pandas_df_brokelinks_data,
        change_cols_name_data,
    )
    # THEN
    if index_exists:  # delete and create new index
        mock_connections.return_value.get_connection.return_value.indices.delete.assert_called_once_with(index="aaa")
        mock_connections.return_value.get_connection.return_value.indices.create.assert_called_once_with(
            index="aaa", body=mapping
        )
    else:  # only create new index
        mock_connections.return_value.get_connection.return_value.indices.delete.assert_not_called()
        mock_connections.return_value.get_connection.return_value.indices.create.assert_called_once_with(
            index="aaa", body=mapping
        )
