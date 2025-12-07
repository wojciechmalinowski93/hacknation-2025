import logging
from dataclasses import dataclass
from typing import List, Set, Tuple, Type

from django.apps import apps
from django.db.models import Model
from django_elasticsearch_dsl.registries import registry
from elasticsearch.helpers import scan
from elasticsearch_dsl import Document, connections

logger = logging.getLogger("mcod")

Resources_ids = List[int]


def get_all_document_ids_for_es_index(es_index_name: str) -> Set[int]:
    """
    Retrieve all document IDs from an ElasticSearch index.

    Args:
        es_index_name (str): ElasticSearch index name.

    Returns:
        Set[int]: A set of all document IDs in the ElasticSearch index.

    Raises:
        Exception: If scanning the ElasticSearch index fails.
    """
    es_client = connections.get_connection()

    try:
        results = scan(
            es_client,
            index=es_index_name,
            _source=False,
            docvalue_fields=["_id"],
        )
        es_doc_ids_list: Set[int] = {int(hit["_id"]) for hit in results}
    except Exception as e:
        logger.error(f"Scanning ElasticSearch index ({es_index_name}) failed. Reason: {e}")
        raise e

    return es_doc_ids_list


def get_all_ids_of_published_objects(model_class: Type[Model]) -> Set[int]:
    """
    Retrieve IDs of all published objects for a given Django model.

    Args:
        model_class (Type[Model]): The Django model class.

    Returns:
        Set[int]: A set of IDs for all published objects of the given model.

    Note:
        This method assumes that the provided Django model class has a 'status'
        attribute that can have values 'published' or 'draft'.
    """
    return set(model_class.objects.filter(status="published").values_list("id", flat=True))


def get_django_model_with_es_documents(app_label: str, model_name: str) -> Tuple[Type[Model], List[Type[Document]]]:
    """
    Get the Django model and corresponding ElasticSearch documents for a given
    app and model name.

    Args:
       app_label (str): The Django app label.
       model_name (str): The name of the Django model.

    Returns:
       Tuple[Type[Model], List[Type[Document]]]: A tuple containing the Django
           model class and the ElasticSearch documents classes.

    Raises:
       LookupError: if no application exists with this label, or no model
           exists with this name in the application.
    """
    django_model: Type[Model] = apps.get_model(app_label, model_name)

    try:
        documents: List[Type[Document]] = list(registry.get_documents([django_model]))
    except IndexError:
        documents = []

    return django_model, documents


def get_index_name(document_class: Type[Document]) -> str:
    return document_class.Index.name


@dataclass
class IndexConsistency:
    """
    Represents the consistency state between Database and ElasticSearch index IDs.

    This class holds information about IDs existing in the Database and ElasticSearch
    for a specific index. It provides methods to check data consistency
    between both systems.

    Attributes:
        index_name (str): The name of the ElasticSearch index being compared.
        db_ids (Set[int]): A set of IDs existing in the Database.
        es_ids (Set[int]): A set of IDs existing in ElasticSearch.
    """

    index_name: str
    db_ids: Set[int]
    es_ids: Set[int]

    def __post_init__(self):
        self._only_db_ids = self.db_ids - self.es_ids
        self._only_es_ids = self.es_ids - self.db_ids

    def __bool__(self) -> bool:
        """
        Returns False if there are any IDs present only in the Database
        or only in ElasticSearch, True otherwise.
        """
        return len(self._only_db_ids) == 0 and len(self._only_es_ids) == 0

    @property
    def is_consistent(self) -> bool:
        """
        Returns True if the data is consistent across both systems,
        False otherwise.
        """
        return bool(self)

    @property
    def only_db_ids(self) -> Set[int]:
        """
        Returns a set of IDs existing only in the Database.
        """
        return self._only_db_ids

    @property
    def only_es_ids(self) -> Set[int]:
        """
        Returns a set of IDs existing only in ElasticSearch.
        """
        return self._only_es_ids


def get_db_and_es_inconsistencies(app_label: str, model_name: str) -> List[IndexConsistency]:
    """
    Identify inconsistencies between database and ElasticSearch document IDs
    in all indexes for a given model.

    This function compares the IDs of published objects in the database with the document IDs
    in the corresponding ElasticSearch indices. It identifies two types of inconsistencies:
    1. IDs present in the database but not in ElasticSearch.
    2. IDs present in ElasticSearch but not in the database.

    Args:
        app_label (str): The Django app label.
        model_name (str): The name of the model.

    Returns:
        List[IndexConsistency]: A list of IndexInconsistency objects, each representing
        the inconsistencies found for a specific ElasticSearch index.
    """
    model_class, document_classes = get_django_model_with_es_documents(app_label, model_name)
    db_model_ids: Set[int] = get_all_ids_of_published_objects(model_class)

    inconsistencies: List[IndexConsistency] = []
    indexes: List[str] = [get_index_name(document_class) for document_class in document_classes]
    for index_name in indexes:
        es_model_ids: Set[int] = get_all_document_ids_for_es_index(index_name)

        idx_consistency = IndexConsistency(
            index_name=index_name,
            db_ids=db_model_ids,
            es_ids=es_model_ids,
        )
        if idx_consistency.is_consistent is False:
            inconsistencies.append(idx_consistency)

    return inconsistencies
