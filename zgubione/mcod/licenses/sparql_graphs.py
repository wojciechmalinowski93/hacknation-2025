from mcod.core.api.rdf.sparql_graphs import SparqlGraph
from mcod.licenses.models import License


class LicenseSparqlGraph(SparqlGraph):
    model = License
