from collections import deque

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django_elasticsearch_dsl import Document as DESDocument
from django_elasticsearch_dsl.apps import DEDConfig
from elasticsearch.helpers import parallel_bulk

DEFAULT_CHUNK_SIZE = 500


class Document(DESDocument):

    def get_indexing_queryset(self, **kwargs):
        """
        Build queryset (iterator) for use by indexing.
        """
        qs = self.get_queryset()
        if "chunk_size" not in kwargs:
            kwargs["chunk_size"] = self.django.queryset_pagination or DEFAULT_CHUNK_SIZE
        return qs.iterator(**kwargs)

    def get_queryset_count(self):
        return self.get_queryset().count()

    def _get_actions(self, object_list, action):
        for object_instance in object_list:
            prepared_action = self._prepare_action(object_instance, action)
            yield prepared_action

    def parallel_bulk(self, actions, **kwargs):
        if "chunk_size" not in kwargs:
            kwargs["chunk_size"] = self.django.queryset_pagination or DEFAULT_CHUNK_SIZE

        bulk_actions = parallel_bulk(client=self._get_connection(), actions=actions, **kwargs)
        # As the `parallel_bulk` is lazy, we need to get it into `deque` to run it instantly
        # See https://discuss.elastic.co/t/helpers-parallel-bulk-in-python-not-working/39498/2
        deque(bulk_actions, maxlen=0)
        # Fake return value to emulate bulk() since we don't have a result yet,
        # the result is currently not used upstream anyway.
        return (1, [])

    def _bulk(self, *args, **kwargs):
        """Helper for switching between normal and parallel bulk operation"""
        parallel = kwargs.pop("parallel", False)
        if parallel:
            return self.parallel_bulk(*args, **kwargs)
        else:
            return self.bulk(*args, **kwargs)

    def update(self, thing, refresh=None, action="index", parallel=False, **kwargs):
        """
        Update each document in ES for a model, iterable of models or queryset
        """
        if refresh is True or (refresh is None and self.django.auto_refresh):
            kwargs["refresh"] = True

        if isinstance(thing, models.Model):
            object_list = [thing]
        else:
            object_list = thing

        return self._bulk(self._get_actions(object_list, action), parallel=parallel, **kwargs)

    def prepare_id(self, instance):
        return instance.pk

    def delete_by_id(self, _id, refresh=None, **kwargs):
        if refresh is True or (refresh is None and self.django.auto_refresh):
            kwargs["refresh"] = True

        actions = [
            {
                "_index": self._index._name,
                "_id": self.prepare_id(self.django.model(pk=_id)),
                "_type": "doc",
                "_op_type": "delete",
                "_source": None,
            }
        ]
        self._bulk(actions, **kwargs)

    def prepare(self, instance):
        data = {
            key: value
            for key, value in super().prepare(instance).items()
            if value is not NonIndexableValue and not isinstance(value, NonIndexableValue)
        }
        return data


class ProxyDocumentRegistry:
    def __init__(self, registry):
        self._registry = registry

    def __getattr__(self, item):
        return getattr(self._registry, item)

    def get_data_of_related_instances(self, instance):
        if not DEDConfig.autosync_enabled():
            return []

        related_instances = set()
        for doc in self._get_related_doc(instance):
            doc_instance = doc()
            try:
                related = doc_instance.get_instances_from_related(instance)
                if isinstance(related, models.Model):
                    related_instances.add(related)
                else:
                    related_instances.update(related)
            except ObjectDoesNotExist:
                pass

        data = []
        for obj in related_instances:
            if not obj.is_removed and not obj.is_permanently_removed:
                meta = obj._meta
                data.append(
                    {
                        "app_label": meta.app_label,
                        "object_name": meta.concrete_model._meta.object_name,
                        "instance_id": obj.id,
                    }
                )

        return data

    def delete_documents_by_model_and_id(self, model, _id, **kwargs):
        if not DEDConfig.autosync_enabled():
            return

        if model in self._models:
            for doc in self._models[model]:
                if not doc.django.ignore_signals:
                    doc().delete_by_id(_id, **kwargs)


class NonIndexableValue:
    pass
