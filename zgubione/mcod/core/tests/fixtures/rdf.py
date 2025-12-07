import pytest
from django.conf import settings
from rdflib.plugins.stores.sparqlstore import SPARQLStore

from mcod.core.api.rdf.registry import registry as rdf_registry


@pytest.fixture
def sparql_store():
    return SPARQLStore(endpoint=getattr(settings, "SPARQL_QUERY_ENDPOINT"))


@pytest.fixture
def sparql_registry():
    return rdf_registry
