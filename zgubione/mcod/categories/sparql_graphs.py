from mcod.categories.models import Category
from mcod.core.api.rdf.sparql_graphs import SparqlGraph
from mcod.datasets.serializers import CategoryRDFNestedSchema


class CategorySparqlGraph(CategoryRDFNestedSchema, SparqlGraph):
    model = Category
