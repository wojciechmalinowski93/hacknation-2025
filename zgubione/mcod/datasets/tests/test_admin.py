from django.test import Client
from django.utils.encoding import smart_str
from pytest_bdd import scenarios

scenarios(
    "features/admin/dataset_details.feature",
    "features/admin/datasets_list.feature",
    "features/forms.feature",
    "features/admin/autocomplete.feature",
    "features/admin/custom_urls.feature",
    "features/admin/dataset_delete.feature",
)


def test_deleted_resource_are_not_shown_in_dataset_resource_inline(dataset_with_resources, admin):
    dataset = dataset_with_resources
    resource = dataset.resources.first()
    client = Client()
    client.force_login(admin)
    response = client.get(dataset.admin_change_url)
    assert resource.title in smart_str(response.content)
    resource.delete()
    assert resource.is_removed is True
    client = Client()
    client.force_login(admin)
    response = client.get(dataset.admin_change_url)
    assert resource.title not in smart_str(response.content)


def test_resources_are_also_deleted_after_dataset_delete(db, dataset_with_resources, admin):
    from mcod.resources.models import Resource

    dataset = dataset_with_resources
    resource = dataset.resources.first()
    client = Client()
    client.force_login(admin)
    response = client.get(dataset.admin_change_url)
    assert resource.title in smart_str(response.content)
    assert resource.status == "published"
    assert dataset.status == "published"
    dataset.delete()
    assert dataset.is_removed is True
    vr = Resource.trash.get(id=resource.id)
    assert vr.is_removed is True


def test_set_published_for_dataset_didnt_change_his_resources_to_publish(db, dataset_with_resources):
    dataset = dataset_with_resources
    assert dataset.status == "published"
    assert dataset.resources.all().first().status == "published"

    dataset.status = "draft"
    dataset.save()

    assert dataset.status == "draft"
    assert dataset.resources.first().status == "draft"
