from collections import defaultdict

from django.db.models import Model

from mcod.core.api.search.tasks import _instance
from mcod.lib.rdf.store import get_sparql_store


class SparqlGraphRegistry:
    def __init__(self):
        self._models = defaultdict(set)
        self._related_models = defaultdict(set)
        self._parent_models = defaultdict(set)
        self._named_graph = None
        self.sparql_store = get_sparql_store()

    def process_graph(self, action, app_label, object_name, instance_id, *args, **kwargs):
        instance = _instance(app_label, object_name, instance_id)
        query, ns = getattr(self, action)(instance, *args, **kwargs)
        if not query:
            return
        try:
            self.sparql_store.update(query, initNs=ns)
        except Exception as e:
            self.sparql_store.rollback()
            raise e

    def register_graph(self, graph_cls):
        self._models[graph_cls.model].add(graph_cls)
        related_models = graph_cls.related_models or []
        parent_model = graph_cls.parent_model
        for related_model in related_models:
            self._related_models[related_model].add(graph_cls.model)
        if parent_model:
            self._parent_models[parent_model].add(graph_cls.model)

    def related_condition_changed(self, instance):
        condition_attr_changed = [
            graph(named_graph=self._named_graph).related_condition_changed(instance)
            for graph in self._models.get(instance.__class__, set())
        ]
        return any(condition_attr_changed)

    def update(self, instance):
        return self._process_action("update", instance)

    def create(self, instance):
        return self._process_action("create", instance)

    def update_related(self, instance):
        queries = []
        ns = {}
        for related_graph_cls in self._get_related_graphs(instance.__class__):
            related_graph = related_graph_cls(named_graph=self._named_graph)
            related_instances = related_graph.get_related_from_instance(instance)
            if related_instances:
                _q, _ns = related_graph.update(related_instances)
                queries.append(_q)
                ns.update(**_ns)
        full_query = "; ".join(queries)
        return full_query, ns

    def update_with_related(self, instance):
        update_q, update_ns = self.update(instance)
        related_q, related_ns = self.update_related(instance)
        update_ns.update(**related_ns)
        return f"{update_q} {related_q}", update_ns

    def create_with_related_update(self, instance):
        create_q, create_ns = self.create(instance)
        related_q, related_ns = self.update_related(instance)
        create_ns.update(**related_ns)
        return f"{create_q} {related_q}", create_ns

    def delete(self, instance):
        return self._process_action("delete", instance)

    def delete_sub_graphs(self, instance):
        queries = []
        ns = {}
        for related_graph_cls in self._get_sub_graphs(instance.__class__):
            sub_graph = related_graph_cls(named_graph=self._named_graph)
            related_instances = sub_graph.get_related_from_instance(instance)
            if related_instances:
                _q, _ns = sub_graph.delete(related_instances)
                queries.append(_q)
                ns.update(**_ns)
        full_query = "; ".join(queries)
        return full_query, ns

    def delete_with_related_update(self, instance, related_models):
        queries = []
        ns = {}
        for model in related_models:
            related_instance = _instance(model["app_label"], model["model_cls"], model["instance_id"])
            _q, _ns = self.update(related_instance)
            queries.append(_q)
            ns.update(**_ns)
        del_q, del_ns = self.delete(instance)
        queries.append(del_q)
        full_query = "; ".join(queries)
        ns.update(**del_ns)
        return full_query, ns

    def _process_action(self, action, instance, *args, **kwargs):
        model_cls = instance.__class__
        queries = []
        ns = {}
        if model_cls in self._models:
            for graph in self._models[model_cls]:
                _q, _ns = getattr(graph(named_graph=self._named_graph), action)(instance)
                queries.append(_q)
                ns.update(**_ns)
        full_query = "; ".join(queries)
        return full_query, ns

    def _get_related_graphs(self, model_cls):
        for model in self._related_models.get(model_cls, []):
            for graph in self._models[model]:
                if model_cls in graph.related_models:
                    yield graph

    def _get_sub_graphs(self, model_cls):
        for model in self._parent_models.get(model_cls, []):
            for graph in self._models[model]:
                if graph.parent_model and model_cls == graph.parent_model:
                    yield graph

    def get_related_models(self, instance):
        related_instances = set()
        model = instance.__class__
        for related_model in self._related_models[model]:
            for related_graph_cls in self._models[related_model]:
                if instance.__class__ in related_graph_cls.related_models:
                    related_graph = related_graph_cls(named_graph=self._named_graph)
                    related_instance = related_graph.get_related_from_instance(instance)
                    if isinstance(related_instance, Model):
                        related_instances.add(related_instance)
                    else:
                        related_instances.update(related_instance)
        related_instances_details = []
        for obj in related_instances:
            if not obj.is_removed:
                related_instances_details.append(
                    {
                        "app_label": obj._meta.app_label,
                        "model_cls": obj._meta.object_name,
                        "instance_id": obj.id,
                    }
                )
        return related_instances_details

    def get_graph(self, instance):
        return self._models[instance.__class__]

    def is_parent_model(self, instance):
        return instance.__class__ in self._parent_models

    def create_named_graph(self, graph_name):
        self._named_graph = graph_name
        self.sparql_store.update(f"CREATE GRAPH {self._named_graph}")

    def delete_named_graph(self):
        self.sparql_store.update(f"DROP GRAPH {self._named_graph}")

    @property
    def graph_name(self):
        return self._named_graph


registry = SparqlGraphRegistry()
