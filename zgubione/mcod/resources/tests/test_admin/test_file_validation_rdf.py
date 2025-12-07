import tempfile
from pathlib import Path
from typing import Generator

import pytest
from rdflib import Dataset as RDFDataset, Graph, URIRef
from rdflib.namespace import FOAF
from rdflib.term import Literal

from mcod.resources.file_validation import analyze_file
from mcod.resources.score_computation import OpennessScoreValue, get_score


@pytest.fixture
def empty_graph() -> Graph:
    dataset = RDFDataset()
    return dataset


@pytest.fixture
def empty_graph_with_namespace() -> Graph:
    dataset = RDFDataset()
    dataset.bind("ns1", "http://schema.dev.dane.gov.pl")
    return dataset


@pytest.fixture
def non_empty_graph_without_namespace() -> Graph:
    dataset = RDFDataset()
    dataset.add(
        (
            Literal("dataset"),  # subject
            Literal("zawiera"),  # predicate
            Literal("zasoby"),  # object
        )
    )
    return dataset


@pytest.fixture
def non_empty_graph_with_namespace() -> Graph:
    dataset = RDFDataset()
    dataset.add(
        (
            URIRef("http://schema.dev.dane.gov.pl/dataset"),  # subject
            URIRef("http://schema.dev.dane.gov.pl/zawiera"),  # predicate
            URIRef("http://schema.dev.dane.gov.pl/zasoby"),  # object
        )
    )
    return dataset


@pytest.fixture
def non_empty_graph_with_two_namespaces() -> Graph:
    dataset = RDFDataset()
    dataset.bind("foaf", FOAF)
    dataset.add(
        (
            URIRef("http://schema.dev.dane.gov.pl/dataset"),  # subject
            URIRef("http://schema.dev.dane.gov.pl/zawiera"),  # predicate
            FOAF.status,  # object
        )
    )
    return dataset


class MockFieldFile:
    def __init__(self, file_path: Path):
        self.path = str(file_path.absolute())


@pytest.fixture
def rdf_samples_dir() -> Generator[Path, None, None]:
    """Use a real directory to capture samples, for example Path(settings.TEST_SAMPLES_PATH) / "rdf-samples"""
    with tempfile.TemporaryDirectory() as p:
        yield Path(p)


@pytest.mark.parametrize(
    "graph_fixture, extension, mime_type, expected_analyzed_extension, "
    "expected_openness_score, expected_openness_score_forced_format",
    [
        # jsonld
        ("empty_graph", "jsonld", "application/ld+json", "json", 3, 4),
        ("empty_graph_with_namespace", "jsonld", "application/ld+json", "json", 3, 4),
        ("empty_file", "jsonld", "application/ld+json", "jsonld", 4, 4),
        ("non_empty_graph_without_namespace", "jsonld", "application/ld+json", "json", 3, 4),
        ("non_empty_graph_with_two_namespaces", "jsonld", "application/ld+json", "jsonld", 5, 5),
        ("non_empty_graph_with_namespace", "jsonld", "application/ld+json", "jsonld", 4, 4),
        # n3
        ("non_empty_graph_without_namespace", "n3", "text/n3", "n3", 4, 4),
        ("empty_file", "n3", "text/n3", "n3", 4, 4),
        ("empty_graph", "n3", "text/n3", "txt", 1, 4),
        ("empty_graph_with_namespace", "n3", "text/n3", "txt", 1, 4),
        ("non_empty_graph_with_namespace", "n3", "text/n3", "n3", 4, 4),
        ("non_empty_graph_with_two_namespaces", "n3", "text/n3", "n3", 5, 5),
        # nq
        ("empty_graph", "nq", "application/n-quads", "txt", 1, 4),
        ("empty_graph_with_namespace", "nq", "application/n-quads", "txt", 1, 4),
        ("empty_file", "nq", "application/n-quads", "nq", 4, 4),
        ("non_empty_graph_without_namespace", "nq", "application/n-quads", "txt", 1, 4),
        ("non_empty_graph_with_two_namespaces", "nq", "application/n-quads", "nq", 5, 5),
        ("non_empty_graph_with_namespace", "nq", "application/n-quads", "nq", 4, 4),
        # nquads
        ("empty_graph", "nquads", "application/n-quads", "txt", 1, 4),
        ("empty_file", "nquads", "application/n-quads", "nquads", 4, 4),
        ("empty_graph_with_namespace", "nquads", "application/n-quads", "txt", 1, 4),
        ("non_empty_graph_without_namespace", "nquads", "application/n-quads", "txt", 1, 4),
        ("non_empty_graph_with_two_namespaces", "nquads", "application/n-quads", "nq", 5, 5),
        ("non_empty_graph_with_namespace", "nquads", "application/n-quads", "nq", 4, 4),
        # nt
        ("empty_file", "nt", "application/n-triples", "nt", 4, 4),
        ("empty_graph", "nt", "application/n-triples", "nt", 4, 4),
        ("empty_graph_with_namespace", "nt", "application/n-triples", "nt", 4, 4),
        ("non_empty_graph_without_namespace", "nt", "application/n-triples", "n3", 4, 4),
        ("non_empty_graph_with_two_namespaces", "nt", "application/n-triples", "n3", 5, 5),
        ("non_empty_graph_with_namespace", "nt", "application/n-triples", "n3", 4, 4),
        # nt11
        ("empty_file", "nt11", "application/n-triples", "nt11", 4, 4),
        ("non_empty_graph_without_namespace", "nt11", "application/n-triples", "n3", 4, 4),
        ("empty_graph", "nt11", "application/n-triples", "nt11", 4, 4),
        ("non_empty_graph_with_namespace", "nt11", "application/n-triples", "n3", 4, 4),
        ("empty_graph_with_namespace", "nt11", "application/n-triples", "nt11", 4, 4),
        ("non_empty_graph_with_two_namespaces", "nt11", "application/n-triples", "n3", 5, 5),
        # ntriples
        ("empty_graph", "ntriples", "application/n-triples", "ntriples", 4, 4),
        ("empty_graph_with_namespace", "ntriples", "application/n-triples", "ntriples", 4, 4),
        ("non_empty_graph_without_namespace", "ntriples", "application/n-triples", "n3", 4, 4),
        ("non_empty_graph_with_namespace", "ntriples", "application/n-triples", "n3", 4, 4),
        ("non_empty_graph_with_two_namespaces", "ntriples", "application/n-triples", "n3", 5, 5),
        ("empty_file", "ntriples", "application/n-triples", "ntriples", 4, 4),
        # turtle (ttl)
        ("non_empty_graph_without_namespace", "ttl", "text/turtle", "n3", 4, 4),
        ("non_empty_graph_with_namespace", "ttl", "text/turtle", "n3", 4, 4),
        ("non_empty_graph_with_two_namespaces", "ttl", "text/turtle", "n3", 5, 5),
        ("empty_file", "ttl", "text/turtle", "ttl", 4, 4),
        ("empty_graph", "ttl", "text/turtle", "txt", 1, 4),
        ("empty_graph_with_namespace", "ttl", "text/turtle", "txt", 1, 4),
        # turtle
        ("empty_graph_with_namespace", "turtle", "text/turtle", "txt", 1, 4),
        ("non_empty_graph_without_namespace", "turtle", "text/turtle", "n3", 4, 4),
        ("non_empty_graph_with_namespace", "turtle", "text/turtle", "n3", 4, 4),
        ("non_empty_graph_with_two_namespaces", "turtle", "text/turtle", "n3", 5, 5),
        ("empty_file", "turtle", "text/turtle", "turtle", 4, 4),
        ("empty_graph", "turtle", "text/turtle", "txt", 1, 4),
        # rdfa
        ("empty_file", "rdfa", "application/rdfa+xml", "rdfa", 4, 4),
        ("non_empty_graph_without_namespace", "rdfa", "application/rdfa+xml", "rdfa", 4, 4),
        ("empty_graph_with_namespace", "rdfa", "application/rdfa+xml", "rdfa", 4, 4),
        ("non_empty_graph_with_namespace", "rdfa", "application/rdfa+xml", "rdfa", 4, 4),
        ("non_empty_graph_with_two_namespaces", "rdfa", "application/rdfa+xml", "rdfa", 4, 4),
        ("empty_graph", "rdfa", "application/rdfa+xml", "rdfa", 4, 4),
        # trig
        ("empty_file", "trig", "application/trig", "trig", 4, 4),
        ("empty_graph", "trig", "application/trig", "txt", 1, 4),
        ("empty_graph_with_namespace", "trig", "application/trig", "txt", 1, 4),
        ("non_empty_graph_without_namespace", "trig", "application/trig", "trig", 4, 4),
        ("non_empty_graph_with_two_namespaces", "trig", "application/trig", "trig", 5, 5),
        ("non_empty_graph_with_namespace", "trig", "application/trig", "trig", 4, 4),
        # trix
        ("empty_graph_with_namespace", "trix", "application/trix", "rdf", 4, 4),
        ("empty_file", "trix", "application/trix", "trix", 4, 4),
        ("empty_graph", "trix", "application/trix", "rdf", 4, 4),
        ("non_empty_graph_with_namespace", "trix", "application/trix", "trix", 4, 4),
        ("non_empty_graph_without_namespace", "trix", "application/trix", "trix", 4, 4),
        ("non_empty_graph_with_two_namespaces", "trix", "application/trix", "trix", 5, 5),
        # rdf+xml as rdf
        ("empty_file", "rdf", "application/rdf+xml", "rdf", 4, 4),
        ("empty_graph_with_namespace", "rdf", "application/rdf+xml", "xml", 3, 4),
        ("non_empty_graph_with_two_namespaces", "rdf", "application/rdf+xml", "rdf", 5, 5),
        ("empty_graph", "rdf", "application/rdf+xml", "xml", 3, 4),
        ("non_empty_graph_with_namespace", "rdf", "application/rdf+xml", "rdf", 4, 4),
        pytest.param(
            "non_empty_graph_without_namespace",
            "rdf",
            "application/rdf+xml",
            "xml",
            0,
            0,
            marks=pytest.mark.xfail(run=False, reason="can't create invalid xml"),
        ),
        # rdf+xml as xml
        ("empty_file", "xml", "application/rdf+xml", "xml", 3, 3),
        ("empty_graph_with_namespace", "xml", "application/rdf+xml", "xml", 3, 3),
        ("non_empty_graph_with_two_namespaces", "xml", "application/rdf+xml", "rdf", 5, 5),
        ("empty_graph", "xml", "application/rdf+xml", "xml", 3, 3),
        ("non_empty_graph_with_namespace", "xml", "application/rdf+xml", "rdf", 4, 4),
        pytest.param(
            "non_empty_graph_without_namespace",
            "xml",
            "application/rdf+xml",
            "xml",
            0,
            0,
            marks=pytest.mark.xfail(run=False, reason="can't create invalid xml"),
        ),
    ],
)
def test_analyze_and_score_graphs(
    graph_fixture: Graph,
    extension: str,
    expected_analyzed_extension: str,
    mime_type: str,
    expected_openness_score: OpennessScoreValue,
    expected_openness_score_forced_format: OpennessScoreValue,
    request,
    rdf_samples_dir: Path,
) -> None:
    # Given
    file_path = rdf_samples_dir / f"{graph_fixture}-expected-{expected_openness_score}.{extension}"
    if extension == "rdfa":
        with open(file_path, "w") as fd:
            fd.write("")
    elif graph_fixture == "empty_file":
        with open(file_path, "w") as fd:
            fd.write("")
    else:
        graph: Graph = request.getfixturevalue(graph_fixture)
        with open(file_path, "w") as fd:
            graph.print(format=mime_type, out=fd)
    # When
    analyzed_ext, *_ = analyze_file(file_path)
    file_field = MockFieldFile(file_path)
    openness_score_analyzed_format = get_score(file_field, analyzed_ext)
    openness_score_forced_format = get_score(file_field, extension)
    # Then
    assert analyzed_ext == expected_analyzed_extension
    assert openness_score_analyzed_format == expected_openness_score
    assert openness_score_forced_format == expected_openness_score_forced_format
