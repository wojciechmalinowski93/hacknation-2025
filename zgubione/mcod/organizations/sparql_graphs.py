import marshmallow as ma
from rdflib import ConjunctiveGraph
from rdflib.term import URIRef

from mcod.core.api.rdf.schemas import ResponseSchema as RDFResponseSchema
from mcod.core.api.rdf.sparql_graphs import SparqlGraph
from mcod.datasets.serializers import OrganizationRDFMixin
from mcod.organizations.models import Organization


class OrganizationSparqlGraph(SparqlGraph, OrganizationRDFMixin, RDFResponseSchema):
    model = Organization
    include_nested_triples = True
    related_condition_attr = "slug"

    @ma.pre_dump(pass_many=True)
    def prepare_data(self, data, many, **kwargs):
        # If many, serialize data as catalog - from Elasticsearch
        return data

    @ma.post_dump(pass_many=False)
    def prepare_graph_triples(self, data, **kwargs):
        distribution = self.get_rdf_class_for_model(model=Organization)(subject=URIRef(data["access_url"]))
        return distribution.to_triples(data, self.include_nested_triples)

    @ma.post_dump(pass_many=True)
    def prepare_graph(self, data, many, **kwargs):
        graph = ConjunctiveGraph()
        self.add_bindings(graph=graph)
        if many:
            for triple_group in data:
                for triple in triple_group:
                    graph.add(triple)
        else:
            for triple in data:
                graph.add(triple)
        return graph
