import logging
from io import BytesIO
from xml.etree import ElementTree

from django.conf import settings
from rdflib import ConjunctiveGraph, Graph

from mcod.resources.score_computation.calculators.contains_linked_data import (
    graph_contains_linked_data,
)
from mcod.resources.score_computation.common import OpennessScoreValue, SourceData

logger = logging.getLogger("mcod")


RDF_EXTENSIONS = {extension: mime_type for extension, mime_type in settings.RDF_FORMAT_TO_MIMETYPE.items()}


def _validate_score_4(source_data: SourceData) -> bool:
    try:
        namespaces = dict([node for _, node in ElementTree.iterparse(BytesIO(source_data.data), events=["start-ns"])])
        if not namespaces:
            return False
        tree = ElementTree.ElementTree(ElementTree.fromstring(source_data.data))
        root = tree.getroot()
        if not root:
            return False
    except Exception:
        logger.exception("Handled exception in calculate_score_for_xml._validate_score_4")
        return False

    items_tags = [item.tag for item in root.iter()]
    for item_tag in items_tags:
        if not any([ns in item_tag for ns in namespaces.values()]):
            return False

    return True


def _validate_score_5(source_data: SourceData) -> bool:
    graph = ConjunctiveGraph()
    extension = source_data.extension
    try:
        parse_format = RDF_EXTENSIONS[extension]
        graph: Graph = graph.parse(data=source_data.data, format=parse_format)
        if not len(graph) or not graph_contains_linked_data(graph):
            return False
    except Exception:
        logger.exception("Handled exception in calculate_score_for_xml._validate_score_5")
        return False
    return True


def calculate_score_for_xml(source_data: SourceData) -> OpennessScoreValue:
    score: OpennessScoreValue = 3  # default score
    if source_data.data is None:
        return score

    # validate score 4
    if not _validate_score_4(source_data):
        return score

    # increase score 3 -> 4
    score = 4

    # validate score 5
    if not _validate_score_5(source_data):
        return score

    return 5


def calculate_score_for_rdf(source_data: SourceData) -> OpennessScoreValue:
    default_score: OpennessScoreValue = 4
    extension = source_data.extension
    graph = ConjunctiveGraph()
    try:
        parse_format = RDF_EXTENSIONS[extension]
        graph: Graph = graph.parse(data=source_data.data, format=parse_format)
        # len(Graph()) returns the number of triples
        has_triples = any([len(g) for g in graph.store.contexts()])  # graph_contains_linked_data?
        if not has_triples or not graph_contains_linked_data(graph):
            return default_score
    except Exception as e:
        logger.exception(f"Handled exception in calculate_score_for_rdf {repr(e)}")
        return default_score
    return 5
