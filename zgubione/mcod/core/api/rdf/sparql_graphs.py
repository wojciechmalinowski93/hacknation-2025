from django.db.models import Model
from rdflib.term import BNode

from mcod.core.api.rdf.registry import registry


class SparqlGraph:
    model = None
    related_models = None
    parent_model = None
    parent_fk = None
    related_condition_attr = None

    def __init__(self, named_graph=None, *args, **kwargs):
        self._named_graph = named_graph
        super().__init__(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        registry.register_graph(cls)
        super().__init_subclass__(**kwargs)

    def related_condition_changed(self, instance):
        return self.related_condition_attr and instance.tracker.has_changed(self.related_condition_attr)

    def update(self, instance):
        ns, instance_nodes = self._prepare_query_data(instance)
        delete_q = self._get_delete_query(instance_nodes)
        insert_q = self._get_create_query(instance_nodes)
        update_query = f"{delete_q}; {insert_q}"
        return update_query, ns

    def delete(self, instance):
        ns, instance_nodes = self._prepare_query_data(instance)
        return self._get_delete_query(instance_nodes), ns

    def _get_delete_query(self, graph_nodes):
        if self._named_graph:
            q = (
                "DELETE {{ GRAPH {graph_name} {{?s  ?p   ?o . ?o  ?p1  ?o1 .}} }}"
                " WHERE {{ GRAPH {graph_name} {{ ?s  ?p  ?o . FILTER (?s IN ({nodes})) ."
                " OPTIONAL {{?o  ?p1  ?o1  . FILTER (isBlank(?o)) }} }} }}".format(
                    graph_name=f"{self._named_graph} ",
                    nodes=", ".join(graph_nodes.keys()),
                )
            )
        else:
            q = (
                "DELETE {{?s  ?p   ?o . ?o  ?p1  ?o1 .}} WHERE {{ ?s  ?p  ?o . FILTER (?s IN ({})) ."
                " OPTIONAL {{?o  ?p1  ?o1  . FILTER (isBlank(?o)) }} }}".format(", ".join(graph_nodes.keys()))
            )
        return q

    def _get_create_query(self, graph_nodes):
        if self._named_graph:
            q = "INSERT DATA {{ GRAPH {} {{ {} }} }}".format(f"{self._named_graph} ", " ".join(list(graph_nodes.values())))
        else:
            q = "INSERT DATA {{ {} }}".format(" ".join(list(graph_nodes.values())))
        return q

    def _get_delete_triple_query(self, graph_nodes):
        if self._named_graph:
            q = "DELETE DATA {{ GRAPH {} {{ {} }} }}".format(f"{self._named_graph} ", " ".join(list(graph_nodes.values())))
        else:
            q = "DELETE DATA {{ {} }}".format(" ".join(list(graph_nodes.values())))
        return q

    def _get_delete_triple_filter_query(self, sub, pred):
        if self._named_graph:
            q = (
                "DELETE {{ GRAPH {graph_name} {{?s  ?p   ?o }} }}"
                " WHERE {{ GRAPH {graph_name} {{ ?s  ?p  ?o . FILTER"
                " (?s = {sub} && ?p = {pred}) }} }}".format(graph_name=f"{self._named_graph} ", sub=sub.n3(), pred=pred.n3())
            )
        else:
            q = "DELETE {{?s  ?p   ?o }} WHERE {{ ?s  ?p  ?o . FILTER (?s = {sub} && ?p = {pred}) }}".format(
                sub=sub.n3(), pred=pred.n3()
            )
        return q

    def create(self, instance):
        ns, instance_nodes = self._prepare_query_data(instance)
        return self._get_create_query(instance_nodes), ns

    def _prepare_query_data(self, instance):
        many = not isinstance(instance, Model)
        serialized_data = self.dump(instance, many=many)
        ns = {ns[0]: ns[1] for ns in serialized_data.namespaces()}
        all_nodes = {}
        b_nodes = {}
        for s, p, o in serialized_data.triples((None, None, None)):
            _s = s.n3()
            triple_str = all_nodes.get(_s, "")
            triple_str += f"{_s} {serialized_data.qname(p)} {o.n3()} . "
            all_nodes[_s] = triple_str
            if isinstance(o, BNode):
                b_nodes[o.n3()] = _s
        for b_node, b_node_subject in b_nodes.items():
            all_nodes[b_node_subject] += all_nodes.pop(b_node)
        return ns, all_nodes

    def is_parent_removed(self, instance):
        return self.parent_model and self.parent_fk and getattr(instance, self.parent_fk).is_removed
