import marshmallow as ma
from rdflib import ConjunctiveGraph

from mcod.core.api.rdf.graph_mixins import SparqlGraphCatalogModifiedMixin
from mcod.core.api.rdf.sparql_graphs import SparqlGraph
from mcod.datasets.models import Dataset
from mcod.licenses.models import License
from mcod.resources.models import Resource
from mcod.resources.serializers import ResourceRDFResponseSchema


class ResourceSparqlGraph(SparqlGraph, ResourceRDFResponseSchema, SparqlGraphCatalogModifiedMixin):
    model = Resource
    related_models = [Dataset, License]
    parent_model = Dataset
    include_nested_triples = False

    @ma.pre_dump(pass_many=True)
    def prepare_data(self, data, many, **kwargs):
        # If many, serialize data as catalog - from Elasticsearch
        return data

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

    def get_related_from_instance(self, related_instance):
        if isinstance(related_instance, Dataset):
            return related_instance.resources.filter(status="published")
        if isinstance(related_instance, License):
            return Resource.objects.filter(dataset__license__pk=related_instance.pk, status="published")

    def create(self, instance):
        create_q, ns = super().create(instance)
        catalog_modified_q, modified_ns = self.update_catalog_modified(instance)
        ns.update(**modified_ns)
        full_query = f"{create_q}; {catalog_modified_q}"
        return full_query, ns

    def delete(self, instance):
        delete_q, ns = super().delete(instance)
        catalog_modified_q, modified_ns = self.update_catalog_modified(instance)
        ns.update(**modified_ns)
        full_query = f"{delete_q}; {catalog_modified_q}"
        return full_query, ns
