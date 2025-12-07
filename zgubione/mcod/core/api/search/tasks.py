from celery.utils.log import get_task_logger
from django.apps import apps
from django_elasticsearch_dsl.registries import registry
from elasticsearch.exceptions import TransportError

from mcod.core.db.elastic import ProxyDocumentRegistry
from mcod.core.tasks import extended_shared_task

logger = get_task_logger("index_tasks")


def _instance(app_label, object_name, instance_id):
    model = apps.get_model(app_label, object_name)
    if hasattr(model, "raw"):
        instance = model.raw.get(pk=instance_id)
    else:
        instance = model.objects.get(pk=instance_id)

    return instance


def bulk_update_documents(app_label, object_name, ids_list, action="index"):
    model = apps.get_model(app_label, object_name)
    docs = registry.get_documents((model,))
    instances = model.objects.filter(pk__in=ids_list)
    for doc in docs:
        doc().update(instances, action=action)


@extended_shared_task
def update_document_task(app_label, object_name, instance_id):
    instance = _instance(app_label, object_name, instance_id)
    registry.update(instance)
    return {"app": app_label, "model": object_name, "instance_id": instance_id}


@extended_shared_task(max_retries=5, retry_on_errors=(TransportError,))
def update_with_related_task(app_label, object_name, instance_id):
    instance = _instance(app_label, object_name, instance_id)
    registry.update(instance)
    registry.update_related(instance)
    return {"app": app_label, "model": object_name, "instance_id": instance_id}


@extended_shared_task
def update_related_task(app_label, object_name, pk_set, **kwargs):
    model = apps.get_model(app_label, object_name)
    docs = registry.get_documents((model,))
    for doc in docs:
        qs = model.objects.filter(pk__in=pk_set)
        doc().update(qs.iterator(), **kwargs)
    return {
        "app": model._meta.app_label,
        "model": model._meta.object_name,
        "instance_id": pk_set,
    }


@extended_shared_task(max_retries=5, retry_on_errors=(TransportError,))
def delete_document_task(app_label, object_name, instance_id):
    model = apps.get_model(app_label, object_name)
    registry_proxy = ProxyDocumentRegistry(registry)
    registry_proxy.delete_documents_by_model_and_id(model, instance_id, raise_on_error=False)
    return {"app": app_label, "model": object_name, "instance_id": instance_id}


@extended_shared_task(max_retries=5, retry_on_errors=(TransportError,))
def delete_with_related_task(related_instances_data, app_label, object_name, instance_id):
    for data in related_instances_data:
        instance = _instance(**data)
        registry.update(instance)

    model = apps.get_model(app_label, object_name)
    registry_proxy = ProxyDocumentRegistry(registry)
    registry_proxy.delete_documents_by_model_and_id(model, instance_id, raise_on_error=False)
    return {
        "related_instances_data": related_instances_data,
        "app": app_label,
        "model": object_name,
        "instance_id": instance_id,
    }


@extended_shared_task
def delete_related_documents_task(app_label, object_name, instance_id):
    instance = _instance(app_label, object_name, instance_id)
    registry.update_related(instance)
    return {"app": app_label, "model": object_name, "instance_id": instance_id}


@extended_shared_task
def null_field_in_related_task(app_label, object_name, instance_id):
    instance = _instance(app_label, object_name, instance_id)
    for rel in instance._meta.related_objects:
        field_name = rel.field.name
        model = rel.field.model
        rel_instances = model.objects.filter(**{rel.field.name: instance})
        doc = list(
            registry.get_documents(
                models=[
                    model,
                ]
            )
        )[0]
        for rel_inst in rel_instances:
            setattr(rel_inst, field_name, None)
            doc_instance = doc(related_instance_to_ignore=instance)
            doc_instance.update(rel_inst)


@extended_shared_task
def bulk_delete_documents_task(app_label, object_name, ids_list):
    return update_related_task(app_label, object_name, ids_list, action="delete")
