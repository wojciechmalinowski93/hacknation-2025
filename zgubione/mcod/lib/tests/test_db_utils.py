from contextlib import ExitStack
from typing import Set
from unittest.mock import Mock, call, patch

import pytest

from mcod.lib.db_utils import (
    IndexConsistency,
    get_all_document_ids_for_es_index,
    get_db_and_es_inconsistencies,
    get_django_model_with_es_documents,
)


class TestIndexConsistency:
    def test_empty_index_consistency_creation(self):
        ic = IndexConsistency("test_index", set(), set())
        assert ic.index_name == "test_index"
        assert ic.db_ids == set()
        assert ic.es_ids == set()
        assert ic.only_db_ids == set()
        assert ic.only_es_ids == set()

    def test_index_consistency_creation_with_ids(self):
        ic = IndexConsistency("test_index", {1, 2, 3, 4}, {0, 3, 4, 5, 6})
        assert ic.index_name == "test_index"
        assert ic.db_ids == {1, 2, 3, 4}
        assert ic.es_ids == {0, 3, 4, 5, 6}
        assert ic.only_db_ids == {1, 2}
        assert ic.only_es_ids == {0, 5, 6}

    @pytest.mark.parametrize(
        "db_ids, es_ids, expected_consistency_result",
        [
            (set(), set(), True),
            ({1}, {1}, True),
            ({1, 2, 3}, {3, 1, 2}, True),
            ({1, 2}, set(), False),
            (set(), {3, 4}, False),
            ({1, 2}, {3, 4}, False),
            ({1, 2, 3}, {1, 2}, False),
            ({1, 2}, {1, 2, 3}, False),
        ],
    )
    def test_index_consistency_check(
        self,
        db_ids: Set[int],
        es_ids: Set[int],
        expected_consistency_result: bool,
    ):
        ic = IndexConsistency("test_index", db_ids, es_ids)
        assert ic.is_consistent == expected_consistency_result


@pytest.fixture
def mock_registry(mocker):
    mock = mocker.patch("mcod.lib.db_utils.registry")
    return mock


@pytest.fixture
def mock_apps(mocker):
    mock = mocker.patch("mcod.lib.db_utils.apps")
    return mock


@pytest.mark.parametrize(
    "es_ids,expected_output",
    [
        ([1, 2, 3], {1, 2, 3}),
        ([10, 20, 30, 40], {10, 20, 30, 40}),
        ([], set()),
    ],
)
def test_get_all_document_ids_for_es_index(es_ids, expected_output):
    # GIVEN
    mock_es_client = Mock()
    mock_get_connection = Mock(return_value=mock_es_client)
    mock_scan = Mock(return_value=[{"_id": str(id)} for id in es_ids])

    with ExitStack() as stack:
        stack.enter_context(patch("mcod.lib.db_utils.connections.get_connection", mock_get_connection))
        stack.enter_context(patch("mcod.lib.db_utils.scan", mock_scan))

        # WHEN
        result = get_all_document_ids_for_es_index("test_index_name")

    # THEN
    assert result == expected_output
    mock_scan.assert_called_once_with(
        mock_es_client,
        index="test_index_name",
        _source=False,
        docvalue_fields=["_id"],
    )


def test_get_django_model_with_es_documents(mock_apps, mock_registry):
    # GIVEN
    mock_model = Mock()
    mock_apps.get_model.return_value = mock_model

    mock_documents = {Mock(), Mock(), Mock()}
    mock_registry.get_documents.return_value = mock_documents

    # WHEN
    model, documents = get_django_model_with_es_documents("app_label", "model_name")

    # THEN
    assert model == mock_model
    assert isinstance(documents, list)
    assert set(documents) == mock_documents

    mock_apps.get_model.assert_called_once_with("app_label", "model_name")
    mock_registry.get_documents.assert_called_once_with([mock_model])


def test_get_django_model_with_es_documents_index_error(mock_apps, mock_registry):
    # GIVEN
    mock_model = Mock()
    mock_apps.get_model.return_value = mock_model

    mock_registry.get_documents.side_effect = IndexError

    # WHEN
    model, documents = get_django_model_with_es_documents("app_label", "model_name")

    # THEN
    assert model == mock_model
    assert documents == []

    mock_apps.get_model.assert_called_once_with("app_label", "model_name")
    mock_registry.get_documents.assert_called_once_with([mock_model])


def test_get_inconsistent_db_and_es_model_ids():
    # GIVEN
    mock_model = Mock()

    # Create 3 mock documents with names
    mock_documents = []
    indexes = ["index-1", "index-2", "index-3"]
    for index_name in indexes:
        mock_doc = Mock()
        mock_doc.Index.name = index_name
        mock_documents.append(mock_doc)

    # Mark only the second document index as consistent
    consistency_results = [
        Mock(is_consistent=False),
        Mock(is_consistent=True),
        Mock(is_consistent=False),
    ]
    mock_index_consistency = Mock(side_effect=consistency_results)

    # Create mock objects for functions that are called in tested function
    mock_get_django_model_with_es_documents = Mock(return_value=(mock_model, mock_documents))
    mock_get_all_ids_of_published_objects = Mock()
    mock_get_all_document_ids_for_es_index = Mock()

    with ExitStack() as stack:
        # Mock functions thar are called in tested function
        stack.enter_context(
            patch(
                "mcod.lib.db_utils.get_django_model_with_es_documents",
                mock_get_django_model_with_es_documents,
            )
        )
        stack.enter_context(
            patch(
                "mcod.lib.db_utils.get_all_ids_of_published_objects",
                mock_get_all_ids_of_published_objects,
            )
        )
        stack.enter_context(
            patch(
                "mcod.lib.db_utils.get_all_document_ids_for_es_index",
                mock_get_all_document_ids_for_es_index,
            )
        )
        stack.enter_context(
            patch(
                "mcod.lib.db_utils.IndexConsistency",
                mock_index_consistency,
            )
        )

        # WHEN
        inconsistencies = get_db_and_es_inconsistencies("test_app_label", "test_model_name")

    # THEN
    assert len(inconsistencies) == 2
    mock_get_django_model_with_es_documents.assert_called_once_with("test_app_label", "test_model_name")
    mock_get_all_ids_of_published_objects.assert_called_once_with(mock_model)

    expected_calls = [call(index_name) for index_name in indexes]
    mock_get_all_document_ids_for_es_index.assert_has_calls(expected_calls)
