import json
import logging
from io import BytesIO
from urllib.parse import urlparse

from rdflib import ConjunctiveGraph

from mcod.resources.score_computation.calculators.contains_linked_data import (
    graph_contains_linked_data,
)
from mcod.resources.score_computation.common import OpennessScoreValue, SourceData

logger = logging.getLogger("mcod")


def _get_graph(source_data: SourceData) -> ConjunctiveGraph:
    """Loads source_data if there was a Link header - uses that as an @context,
    and presumably downloads the content of this link.
    Example Link values from https://jsonld.com/Book:
    link
        <https://jsonld.com/wp-json/>; rel="https://api.w.org/"
    link
        <https://jsonld.com/wp-json/wp/v2/pages/52>; rel="alternate"; title="JSON"; type="application/json"
    link
        <https://jsonld.com/?p=52>; rel=shortlink
    """
    json.loads(source_data.data)
    graph = ConjunctiveGraph()
    link_header = source_data.link_header
    if link_header and "application/ld+json" in link_header:
        json_ctx_uri = link_header.split(";")[0]
        json_ctx_path = json_ctx_uri.rstrip(">").lstrip("<")
        if not json_ctx_path.startswith("http"):
            url_details = urlparse(source_data.res_link)
            base_url = f"{url_details.scheme}://{url_details.netloc}"
            ctx_rel_has_slash = json_ctx_path.startswith("/")
            if ctx_rel_has_slash:
                full_ctx_url = base_url + json_ctx_path
            else:
                full_ctx_url = f"{base_url}/{json_ctx_path}"
        else:
            full_ctx_url = json_ctx_path
        json_data = json.loads(source_data.data)
        json_data["@context"] = full_ctx_url
        json_bts = BytesIO()
        json_bts.write(json.dumps(json_data).encode())
        json_bts.seek(0)
        json_str = json_bts.read()
    else:
        json_str = source_data.data
    graph.parse(data=json_str, format="json-ld")
    return graph


def calculate_score_for_json(source_data: SourceData) -> OpennessScoreValue:
    try:
        rdf_graph: ConjunctiveGraph = _get_graph(source_data)
    except Exception:
        logger.exception("Handled exception in calculate_score_for_json")
        return 3

    if not rdf_graph:
        return 3

    if not graph_contains_linked_data(rdf_graph):
        return 4

    return 5
