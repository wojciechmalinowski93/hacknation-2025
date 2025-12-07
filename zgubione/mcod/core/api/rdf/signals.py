from mcod.core.api.rdf.registry import registry
from mcod.core.api.rdf.tasks import (
    create_graph_task,
    create_graph_with_related_update_task,
    delete_graph_task,
    delete_graph_with_related_update_task,
    delete_sub_graphs,
    update_graph_task,
    update_graph_with_related_task,
    update_related_graph_task,
)
from mcod.core.mixins.signals import SignalLoggerMixin
from mcod.core.signals import ExtendedSignal

create_graph = ExtendedSignal()
create_graph_with_related_update = ExtendedSignal()
update_graph = ExtendedSignal()
update_graph_with_related = ExtendedSignal()
update_graph_with_conditional_related = ExtendedSignal()
update_related_graph = ExtendedSignal()
delete_graph_with_related_update = ExtendedSignal()
delete_graph = ExtendedSignal()


class SparqlSignalProcessor(SignalLoggerMixin):

    def __init__(self):
        create_graph.connect(self.create_graph)
        update_graph.connect(self.update_graph)
        create_graph_with_related_update.connect(self.create_graph_with_related_update)
        update_graph_with_related.connect(self.update_graph_with_related)
        update_graph_with_conditional_related.connect(self.update_graph_with_conditional_related_update)
        delete_graph_with_related_update.connect(self.delete_graph_with_related_update)
        update_related_graph.connect(self.update_related_graph)
        delete_graph.connect(self.delete_graph)

    @staticmethod
    def get_task_kwargs(instance):
        return {
            "app_label": instance._meta.app_label,
            "object_name": instance._meta.concrete_model._meta.object_name,
            "instance_id": instance.id,
        }

    def update_graph(self, sender, instance, *args, **kwargs):
        self.debug("Updating graph in rdf db", sender, instance, "update_graph")
        update_graph_task.s(**self.get_task_kwargs(instance)).apply_async_on_commit()

    def update_related_graph(self, sender, instance, *args, **kwargs):
        self.debug("Updating related graph in rdf db", sender, instance, "update_related_graph")
        update_related_graph_task.s(**self.get_task_kwargs(instance)).apply_async_on_commit()

    def update_graph_with_conditional_related_update(self, sender, instance, *args, **kwargs):
        if registry.related_condition_changed(instance):
            self.update_graph_with_related(sender, instance, *args, **kwargs)
        else:
            self.update_graph(sender, instance, *args, **kwargs)

    def update_graph_with_related(self, sender, instance, *args, **kwargs):
        self.debug(
            "Updating graph with related in rdf db",
            sender,
            instance,
            "update_graph_with_related",
        )
        update_graph_with_related_task.s(**self.get_task_kwargs(instance)).apply_async_on_commit()

    def create_graph(self, sender, instance, *args, **kwargs):
        self.debug("Creating graph in rdf db", sender, instance, "create_graph")
        create_graph_task.s(**self.get_task_kwargs(instance)).apply_async_on_commit()

    def create_graph_with_related_update(self, sender, instance, *args, **kwargs):
        self.debug(
            "Creating graph with related update in rdf db",
            sender,
            instance,
            "create_graph_with_related_update",
        )
        create_graph_with_related_update_task.s(**self.get_task_kwargs(instance)).apply_async_on_commit()

    def delete_graph(self, sender, instance, *args, **kwargs):
        self.debug("Deleting graph in rdf db", sender, instance, "delete_graph")
        graphs_set = registry.get_graph(instance)
        parents_to_remove = [graph(named_graph=registry.graph_name).is_parent_removed(instance) for graph in graphs_set]
        task_kwargs = self.get_task_kwargs(instance)
        if registry.is_parent_model(instance):
            delete_sub_graphs.s(**task_kwargs).apply_async_on_commit()
        if not any(parents_to_remove):
            delete_graph_task.s(**task_kwargs).apply_async_on_commit()

    def delete_graph_with_related_update(self, sender, instance, *args, **kwargs):
        self.debug(
            "Deleting graph with related update in rdf db",
            sender,
            instance,
            "delete_graph_with_related_update",
        )
        graphs_set = registry.get_graph(instance)
        parents_to_remove = [graph(named_graph=registry.graph_name).is_parent_removed(instance) for graph in graphs_set]
        if not any(parents_to_remove):
            related_models = registry.get_related_models(instance)
            task_kwargs = self.get_task_kwargs(instance)
            task_kwargs["related_models"] = related_models
            delete_graph_with_related_update_task.s(**task_kwargs).apply_async_on_commit()
