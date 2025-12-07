import json

from django.db.models import Manager
from django.test import Client
from django.urls import NoReverseMatch, reverse
from pytest_bdd import given, parsers, then, when

from mcod.core.models import SoftDeletableModel
from mcod.core.registries import factories_registry
from mcod.users.forms import UserCreationForm


@given(
    parsers.parse("UserCreationForm with {posted_data}"),
    target_fixture="user_creation_form",
)
def user_create_form_with_posted_data(posted_data):
    form = UserCreationForm(data=json.loads(posted_data))
    return form


@then(parsers.parse("form validation equals {expected_validation}"))
def form_validation_euqals(user_creation_form, expected_validation):
    validation_value = expected_validation == "true"
    assert user_creation_form.is_valid() == validation_value


@when(parsers.parse("admin user runs restore action for selected {object_type} objects with ids {requested_object_ids}"))
def admin_user_runs_restore_action(admin_context, object_type, requested_object_ids):
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    client = Client()
    client.force_login(admin_context.admin.user)
    page_url = reverse(f"admin:{model._meta.app_label}_{model.__name__}trash_changelist".lower())
    data = {
        "action": "restore_objects",
        "_selected_action": requested_object_ids.split(","),
    }
    response = client.post(page_url, data=data, follow=True)
    admin_context.response = response


@then(parsers.parse("{object_type} objects with ids {restored_object_ids} are restored from trash"))
def objects_with_ids_are_restored_from_trash(object_type, restored_object_ids):
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    ids_list = restored_object_ids.split(",")
    assert model.objects.filter(pk__in=ids_list, is_removed=False).count() == len(ids_list)


@then(parsers.parse("{object_type} objects with ids {unrestored_object_ids} are still in trash"))
def objects_with_ids_are_still_in_trash(object_type, unrestored_object_ids):
    _factory = factories_registry.get_factory(object_type)
    ids_list = unrestored_object_ids.split(",")
    model = _factory._meta.model
    assert model.raw.filter(pk__in=ids_list, is_removed=True).count() == len(ids_list)


@when(parsers.parse("admin's path is changelist for {object_type}"))
@then(parsers.parse("admin's path is changelist for {object_type}"))
def admin_path_is_changelist(admin_context, object_type):
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    path = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
    admin_context.admin.path = path


@when(parsers.parse("admin's path is trash change for {object_type}"))
@then(parsers.parse("admin's path is trash change for {object_type}"))
def admin_path_is_trash_change(admin_context, object_type):
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    assert admin_context.obj
    path = reverse(
        f"admin:{model._meta.app_label}_{model._meta.model_name}trash_change",
        kwargs={"object_id": admin_context.obj.id},
    )
    admin_context.admin.path = path


@then(parsers.parse("{object_type} has trash if {has_trash}"))
def object_type_has_trash_if(admin_context, object_type, has_trash):
    has_trash = bool(int(has_trash))
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    client = Client()
    client.force_login(admin_context.admin.user)
    try:
        page_url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}trash_changelist")
        response = client.get(page_url, follow=True)
        assert has_trash
        assert response.status_code == 200
    except NoReverseMatch:
        assert not has_trash


@then(parsers.parse("object is deletable in admin panel if {can_delete}"))
def object_type_is_deletable_if(admin_context, can_delete):
    can_delete = bool(int(can_delete))
    instance = admin_context.obj
    client = Client()
    client.force_login(admin_context.admin.user)
    page_url = reverse(
        f"admin:{instance._meta.app_label}_{instance._meta.model_name}_delete",
        kwargs={"object_id": instance.id},
    )
    response = client.get(page_url, follow=True)
    if can_delete:
        assert response.status_code == 200
    else:
        assert response.status_code == 403


def make_proxy_model(model):
    class ProxyModel(model):
        class Meta:
            proxy = True
            app_label = model._meta.app_label

        objects = Manager()

    return ProxyModel


def factory_get_or_create(object_type, params, is_removed=False):
    kwargs = json.loads(params)
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    is_model_soft_deletable = issubclass(model, SoftDeletableModel)
    manager_name = "objects"
    if is_model_soft_deletable and is_removed:
        manager_name = "trash"
        kwargs["is_removed"] = True

    id_ = kwargs.get("id")
    proxy_model = make_proxy_model(model)
    qs = proxy_model.objects.filter(id=id_)
    if qs.exists():
        if is_model_soft_deletable:
            qs.update(is_removed=is_removed, is_permanently_removed=False)
        instance = getattr(model, manager_name).get(id=id_)
    else:
        instance = _factory(**kwargs)
        instance.save()
    return instance


@then(parsers.parse("object can be removed from database by button if {can_delete} and {can_remove_from_db}"))
def can_be_deleted_by_button(admin_context, can_delete, can_remove_from_db):
    can_delete = bool(int(can_delete))
    if not can_delete:
        return

    can_remove_from_db = bool(int(can_remove_from_db))
    instance = factory_get_or_create(admin_context.object_type, admin_context.params)
    assert getattr(instance, "is_removed", False) is False

    proxy_model = make_proxy_model(instance._meta.model)

    client = Client()
    client.force_login(admin_context.admin.user)

    delete_url = reverse(
        f"admin:{instance._meta.app_label}_{instance._meta.model_name}_delete",
        kwargs={"object_id": instance.id},
    )
    response = client.post(delete_url, data={"post": "yes"}, follow=True)
    assert response.status_code == 200

    try:
        obj = proxy_model.objects.get(id=instance.id)
        assert not can_remove_from_db
        assert obj.is_removed is True
    except proxy_model.DoesNotExist:
        assert can_remove_from_db


@then(parsers.parse("object can be removed from database by action if {can_delete} and {can_remove_from_db}"))
def can_be_deleted_by_action(admin_context, can_delete, can_remove_from_db):
    can_delete = bool(int(can_delete))
    if not can_delete:
        return

    can_remove_from_db = bool(int(can_remove_from_db))
    instance = factory_get_or_create(admin_context.object_type, admin_context.params)
    assert getattr(instance, "is_removed", False) is False

    proxy_model = make_proxy_model(instance._meta.model)

    client = Client()
    client.force_login(admin_context.admin.user)

    list_url = reverse(f"admin:{instance._meta.app_label}_{instance._meta.model_name}_changelist")
    response = client.get(list_url)
    if response.status_code == 302:
        list_url = response.url

    data = {"action": "delete_selected", "_selected_action": instance.id, "post": "yes"}
    response = client.post(list_url, data=data, follow=True)
    assert response.status_code == 200

    try:
        obj = proxy_model.objects.get(id=instance.id)
        assert not can_remove_from_db
        assert obj.is_removed is True
    except proxy_model.DoesNotExist:
        assert can_remove_from_db


@then(parsers.parse("object can be removed from database by model delete method if {can_delete} and {can_remove_from_db}"))
def can_be_deleted_by_model_delete_method(admin_context, can_delete, can_remove_from_db):
    can_delete = bool(int(can_delete))
    if not can_delete:
        return

    can_remove_from_db = bool(int(can_remove_from_db))
    instance = factory_get_or_create(admin_context.object_type, admin_context.params)
    assert getattr(instance, "is_removed", False) is False

    proxy_model = make_proxy_model(instance._meta.model)
    instance.delete()

    try:
        obj = proxy_model.objects.get(id=instance.id)
        assert not can_remove_from_db
        assert obj.is_removed is True
    except proxy_model.DoesNotExist:
        assert can_remove_from_db


@then(parsers.parse("object can be removed from database by queryset delete method if {can_delete} and {can_remove_from_db}"))
def can_be_deleted_by_queryset_delete_method(admin_context, can_delete, can_remove_from_db):
    can_delete = bool(int(can_delete))
    if not can_delete:
        return

    can_remove_from_db = bool(int(can_remove_from_db))
    instance = factory_get_or_create(admin_context.object_type, admin_context.params)
    assert getattr(instance, "is_removed", False) is False

    model = instance._meta.model
    proxy_model = make_proxy_model(model)

    qs = model.objects.filter(id=instance.id)
    assert qs.count() == 1
    qs.delete()

    try:
        obj = proxy_model.objects.get(id=instance.id)
        assert not can_remove_from_db
        assert obj.is_removed is True
    except proxy_model.DoesNotExist:
        assert can_remove_from_db


@then("removed object is flagged as permanently removed after deleted from trash by button")
def can_be_deleted_from_trash_by_button(admin_context):
    instance = factory_get_or_create(admin_context.object_type, admin_context.params, is_removed=True)
    assert instance.is_permanently_removed is False

    proxy_model = make_proxy_model(instance._meta.model)

    client = Client()
    client.force_login(admin_context.admin.user)

    delete_url = reverse(
        f"admin:{instance._meta.app_label}_{instance._meta.model_name}trash_delete",
        kwargs={"object_id": instance.id},
    )
    response = client.post(delete_url, data={"post": "yes"}, follow=True)
    assert response.status_code == 200
    assert proxy_model.objects.filter(id=instance.id, is_permanently_removed=True).exists()


@then("removed object is flagged as permanently removed after deleted from trash by action")
def can_be_deleted_from_trash_by_action(admin_context):
    instance = factory_get_or_create(admin_context.object_type, admin_context.params, is_removed=True)
    assert instance.is_permanently_removed is False

    proxy_model = make_proxy_model(instance._meta.model)

    client = Client()
    client.force_login(admin_context.admin.user)

    list_url = reverse(f"admin:{instance._meta.app_label}_{instance._meta.model_name}trash_changelist")
    response = client.get(list_url)
    if response.status_code == 302:
        list_url = response.url

    data = {"action": "delete_selected", "_selected_action": instance.id, "post": "yes"}
    response = client.post(list_url, data=data, follow=True)

    assert response.status_code == 200
    assert proxy_model.objects.filter(id=instance.id, is_permanently_removed=True).exists()


@then("removed object is flagged as permanently removed after deleted from trash by model delete method")
def can_be_deleted_from_trash_by_model_delete_method(admin_context):
    instance = factory_get_or_create(admin_context.object_type, admin_context.params, is_removed=True)
    assert instance.is_permanently_removed is False

    proxy_model = make_proxy_model(instance._meta.model)
    instance.delete()
    assert proxy_model.objects.filter(id=instance.id, is_permanently_removed=True).exists()


@then("removed object is flagged as permanently removed after deleted from trash by trash queryset delete method")
def can_be_deleted_by_trash_queryset_delete_method(admin_context):
    instance = factory_get_or_create(admin_context.object_type, admin_context.params, is_removed=True)
    assert instance.is_permanently_removed is False

    model = instance._meta.model
    proxy_model = make_proxy_model(model)

    qs = model.trash.filter(id=instance.id)
    assert qs.count() == 1
    qs.delete()
    assert proxy_model.objects.filter(id=instance.id, is_permanently_removed=True).exists()


@given(parsers.parse("factory {object_type} with params {params}"))
def factory_object_with_id(admin_context, object_type, params):
    admin_context.obj = factory_get_or_create(object_type, params)
    admin_context.object_type = object_type
    admin_context.params = params


@given(parsers.parse("removed factory {object_type} with params {params}"))
def removed_factory_object_with_id(admin_context, object_type, params):
    admin_context.obj = factory_get_or_create(object_type, params, is_removed=True)
    admin_context.object_type = object_type
    admin_context.params = params
