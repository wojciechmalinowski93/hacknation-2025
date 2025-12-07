from django.test import Client
from django.urls import reverse
from django.utils.encoding import smart_str
from pytest_bdd import scenarios

from mcod.organizations.models import Organization

scenarios(
    "features/organization_details_admin.feature",
    "features/organizations_list_admin.feature",
    "features/admin/autocomplete.feature",
)


def test_deleted_dataset_not_in_inlines(dataset, admin):
    client = Client()
    client.force_login(admin)
    response = client.get(reverse("admin:organizations_organization_change", args=[dataset.organization_id]))
    assert dataset.title in smart_str(response.content)
    dataset.delete()
    assert dataset.is_removed is True
    client = Client()
    client.force_login(admin)
    response = client.get(reverse("admin:organizations_organization_change", args=[dataset.organization_id]))
    assert dataset.slug not in smart_str(response.content)
    client = Client()
    client.force_login(admin)
    response = client.get("/datasets/dataset")
    assert dataset.slug not in smart_str(response.content)


def test_restore_organization_did_not_restore_his_datasets(db, institution_with_datasets, admin):
    client = Client()
    client.force_login(admin)
    institution = institution_with_datasets

    assert not institution.is_removed
    assert institution.datasets.all().count() == 2

    institution.delete()

    assert institution.is_removed
    assert institution.datasets.all().count() == 0

    client.post(
        f"/organizations/organizationtrash/{institution.id}/change/",
        data={"is_removed": False},
    )

    org = Organization.objects.get(id=institution.id)

    assert not org.is_removed
    assert org.datasets.all().count() == 0
