import logging
from collections import namedtuple
from typing import List, Optional

from django_elasticsearch_dsl.registries import registry
from elasticsearch import exceptions as es_exceptions
from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import get_connection
from elasticsearch_dsl.query import Q
from elasticsearch_dsl.response import Response
from typing_extensions import TypeAlias

from mcod.core.exceptions import ElasticsearchIndexError

logger = logging.getLogger("mcod")

MessageTemplate: TypeAlias = str


def _handle_es_error(exc: Exception, index: str) -> None:
    """
    Map Elasticsearch exceptions to application-level errors.

    Args:
        exc (Exception): The original exception instance.
        index (str): The Elasticsearch index associated with the failed operation.

    Raises:
        ElasticsearchIndexError: Always raised for known Elasticsearch exceptions.
            Any other exception is propagated unchanged.
    """
    if not isinstance(exc, es_exceptions.ElasticsearchException):
        raise exc

    exc_messages = {
        es_exceptions.ConnectionTimeout: "Timeout while querying index '{index}'.",
        es_exceptions.ConnectionError: "Failed to connect to Elasticsearch while accessing index '{index}'.",
        es_exceptions.AuthorizationException: "Not authorized to access index '{index}'.",
        es_exceptions.NotFoundError: "Elasticsearch index '{index}' not found.",
        es_exceptions.RequestError: "Invalid Elasticsearch query for index '{index}'.",
    }
    msg_template: MessageTemplate = exc_messages.get(type(exc), "Unexpected Elasticsearch error for index '{index}': {exc}")
    msg = msg_template.format(index=index, exc=exc)

    logger.error(msg)
    raise ElasticsearchIndexError(msg) from exc


def get_document_for_model(model):
    documents = registry.get_documents()
    for document in documents:
        if model == document._doc_type.model:
            return document


def get_index_total(index: str, query: Optional[Q] = None) -> int:
    """
    Get the number of documents from the given Elasticsearch index
    (filtered by the optional elasticsearch_dsl query).

    Args:
        index (str): Index name.
        query (Q, optional): Optional query Q from elasticsearch_dsl.
                             If None, returns all documents.

    Returns:
        int: Number of documents in index.

    Raises:
        ElasticsearchIndexError: If there is a connection error,
            the index does not exist, or the query fails.
    """
    try:
        es = get_connection()
        s = Search(using=es, index=index).extra(size=0)

        if query is not None:
            s = s.query(query)

        resp: Response = s.execute()
        total = resp.hits.total
        return getattr(total, "value", total)

    except es_exceptions.ElasticsearchException as exc:
        _handle_es_error(exc, index)


"""
Simplified representation of the one hit from the Elasticsearch search result
    ...
    "hits": [
        {
            "_index": "broken-links",
            "_type": "doc",
            "_id": "Txy-4ZkBm8QrB_EdG0pe",
            "_score": 1.0,
            "_source": {
                "institution": "Nexx",
                "dataset": "Ceny inwestycja Wzgórze Poetów Etap II w 2025 r.",
                "title": "Ceny - inwestycja Wzgórze Poetów Etap II 2025-09-26",
                "portal_data_link": "https://mcod.local/pl/dataset/4365/resource/49474",
                "link": "https://nexx.voxdeveloper.com/files/dane_gov_pl/Ceny-2025-09-26.csv"
            }
        },
    ...
"""
ElasticsearchHit = namedtuple("ElasticsearchHit", ["id", "source"])


def get_index_hits(
    index: str,
    size: int,
    from_: int = 0,
    query: Optional[Q] = None,
    sort: Optional[List[str]] = None,
    source_fields: Optional[List[str]] = None,
) -> List[ElasticsearchHit]:
    """
    Get hits from the Elasticsearch search result.

    Args:
        index (str): Index name.
        size (int): Number of documents to return.
        from_ (int): Offset for pagination.
        query (Q, optional): Optional elasticsearch_dsl query.
        sort (List[str], optional): Fields to sort by.
        source_fields (List[str], optional): Fields to return.

    Returns:
        List[ESDocument]: List of tuples with id and documents as a dicts.

    Raises:
        ElasticsearchIndexError: If any Elasticsearch-related error occurs, including:
            ConnectionTimeout,
            ConnectionError,
            RequestError,
            NotFoundError,
            AuthorizationException,
    """
    resp = None
    try:
        es = get_connection()
        s = Search(using=es, index=index).extra(from_=from_, size=size)

        if query is not None:
            s = s.query(query)
        if sort:
            s = s.sort(*sort)
        if source_fields:
            s = s.source(source_fields)

        logger.debug("Executing search on index '%s': %s", index, s.to_dict())
        resp: Response = s.execute()
    except es_exceptions.ElasticsearchException as exc:
        _handle_es_error(exc, index)

    if resp and not resp.success():
        raise ElasticsearchIndexError(f"Query to index '{index}' did not complete successfully")

    return [ElasticsearchHit(id=hit.meta.id, source=hit.to_dict()) for hit in resp.hits]
