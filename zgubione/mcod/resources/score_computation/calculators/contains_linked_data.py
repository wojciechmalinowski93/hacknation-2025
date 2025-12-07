from typing import Set, Union
from urllib.parse import urlparse

from rdflib import ConjunctiveGraph, Graph, URIRef


def graph_contains_linked_data(graph: Union[ConjunctiveGraph, Graph]) -> bool:
    # TODO zastanowić się kiedy plik zawiera dane zlinkowane
    def add_graph_uri(triple_elem, predicate, graph_uris: Set):
        if isinstance(triple_elem, URIRef) and not str(predicate).startswith("http://www.w3.org/1999/02/22-rdf-syntax-ns#"):
            graph_uris.add(urlparse(str(triple_elem)).netloc)

    graph_uris = set()
    for g in graph.store.contexts():
        for subject, predicate, object_ in g:
            add_graph_uri(subject, predicate, graph_uris)
            add_graph_uri(object_, predicate, graph_uris)
            if len(graph_uris) > 1:
                return True
    return False
