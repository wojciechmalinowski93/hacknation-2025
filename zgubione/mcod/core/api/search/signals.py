from django_elasticsearch_dsl.registries import registry
from django_elasticsearch_dsl.signals import BaseSignalProcessor

from mcod.core.api.search.tasks import (
    delete_document_task,
    delete_related_documents_task,
    delete_with_related_task,
    update_document_task,
    update_related_task,
    update_with_related_task,
)
from mcod.core.db.elastic import ProxyDocumentRegistry
from mcod.core.mixins.signals import SignalLoggerMixin
from mcod.core.signals import ExtendedSignal

update_document = ExtendedSignal()
update_document_with_related = ExtendedSignal()
update_document_related = ExtendedSignal()
remove_document = ExtendedSignal()
remove_document_with_related = ExtendedSignal()


class AsyncSignalProcessor(SignalLoggerMixin, BaseSignalProcessor):
    def _get_object_name(self, obj):
        return obj._meta.concrete_model._meta.object_name

    def setup(self):
        update_document.connect(self.update)
        update_document_with_related.connect(self.update_with_related)
        update_document_related.connect(self.update_related)
        remove_document.connect(self.remove)
        remove_document_with_related.connect(self.remove_with_related)

    def teardown(self):
        update_document.disconnect(self.update)
        update_document_with_related.disconnect(self.update_with_related)
        update_document_related.disconnect(self.update_related)
        remove_document.disconnect(self.remove)
        remove_document_with_related.disconnect(self.remove_with_related)

    def update(self, sender, instance, *args, **kwargs):
        self.debug("Updating document in elasticsearch", sender, instance, "update_document")
        obj_name = self._get_object_name(instance)
        update_document_task.s(instance._meta.app_label, obj_name, instance.id).apply_async_on_commit()

    def update_related(self, sender, instance, model, pk_set, **kwargs):
        self.debug(
            "Updating related documents in elasticsearch",
            sender,
            instance,
            "update_related",
        )
        update_related_task.s(model._meta.app_label, model._meta.object_name, list(pk_set)).apply_async_on_commit()

    def update_with_related(self, sender, instance, *args, **kwargs):
        self.debug(
            "Updating document and related documents in elasticsearch",
            sender,
            instance,
            "update_document_with_related",
        )
        obj_name = self._get_object_name(instance)
        update_with_related_task.s(instance._meta.app_label, obj_name, instance.id).apply_async_on_commit()

    def remove(self, sender, instance, *args, **kwargs):
        self.debug("Removing document from elasticsearch", sender, instance, "remove_document")
        obj_name = self._get_object_name(instance)
        delete_document_task.s(instance._meta.app_label, obj_name, instance.id).apply_async_on_commit()

    def remove_with_related(self, sender, instance, *args, **kwargs):
        self.debug(
            "Removing document and related documents from elasticsearch",
            sender,
            instance,
            "remove_document_with_related",
        )
        object_name = self._get_object_name(instance)
        registry_proxy = ProxyDocumentRegistry(registry)
        related_instances_data = registry_proxy.get_data_of_related_instances(instance)
        delete_with_related_task.s(
            related_instances_data, instance._meta.app_label, object_name, instance.id
        ).apply_async_on_commit()

    def handle_updated(self, sender, instance, **kwargs):
        is_indexable = getattr(instance, "is_indexable", False)
        if is_indexable:
            should_delete = (
                (hasattr(instance, "is_removed") and instance.is_removed)
                or (hasattr(instance, "status") and instance.status != "published")
                or kwargs.get("qs_delete", False)
            )

            object_name = self._get_object_name(instance)
            if should_delete:
                registry_proxy = ProxyDocumentRegistry(registry)
                related_instances_data = registry_proxy.get_data_of_related_instances(instance)
                delete_with_related_task.s(
                    related_instances_data,
                    instance._meta.app_label,
                    object_name,
                    instance.id,
                ).apply_async_on_commit()
            else:
                update_with_related_task.s(instance._meta.app_label, object_name, instance.id).apply_async_on_commit()

    def handle_pre_delete(self, sender, instance, **kwargs):
        is_indexable = getattr(instance, "is_indexable", False)
        if is_indexable:
            object_name = instance._meta.concrete_model._meta.object_name
            delete_related_documents_task.s(instance._meta.app_label, object_name, instance.id).apply_async_on_commit()

    def handle_delete(self, sender, instance, **kwargs):
        is_indexable = getattr(instance, "is_indexable", False)
        if is_indexable:
            object_name = instance._meta.concrete_model._meta.object_name
            delete_document_task.s(instance._meta.app_label, object_name, instance.id).apply_async_on_commit()

    def handle_m2m_changed(self, sender, instance, action, **kwargs):
        if action in ("post_add", "post_remove", "post_clear"):
            self.handle_save(sender, instance)
        elif action in ("pre_remove", "pre_clear"):
            self.handle_pre_delete(sender, instance)
