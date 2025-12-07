from elasticsearch_dsl.faceted_search import Facet
from elasticsearch_dsl.query import Q


class NestedFacet(Facet):
    agg_type = "nested"

    def __init__(self, path, nested_facet):
        self._path = path
        self._inner = nested_facet
        super().__init__(path=path, aggs={"inner": nested_facet.get_aggregation()})

    def get_values(self, data, filter_values):
        return self._inner.get_values(data.inner, filter_values)

    def add_filter(self, filter_values):
        inner_q = self._inner.add_filter(filter_values)
        if inner_q:
            return Q("nested", path=self._path, query=inner_q)


class FilterFacet(Facet):
    agg_type = "filter"
