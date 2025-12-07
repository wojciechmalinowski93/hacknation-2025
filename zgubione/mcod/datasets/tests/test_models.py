from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import FileField
from django.test import Client
from django.utils.encoding import smart_str
from pytest_bdd import scenarios

from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.core.utils import clean_filename
from mcod.datasets.models import Dataset
from mcod.organizations.models import Organization
from mcod.resources.models import Resource
from mcod.users.models import User, UserFollowingDataset

scenarios("features/dataset_create_resources_files_zip.feature")


def create_organization(param):
    org = Organization()
    org.slug = param
    org.title = param
    org.postal_code = "00-001"
    org.city = "Warszwa"
    org.street = "Królewska"
    org.street_number = "27"
    org.flat_number = "1"
    org.street_type = "ul"
    org.email = "email@email.pl"
    org.fax = "123123123"
    org.tel = "123123123"
    org.epuap = "epuap"
    org.regon = "123123123"
    org.website = "www.www.www"
    org.save()
    return org


def create_dataset(param, org):
    dataset = Dataset()
    dataset.slug = param
    dataset.title = param
    dataset.organization = org
    dataset.save()
    return dataset


def create_editor(param, org):
    usr = User.objects.create_user(param, "123!@#qweQWE")
    usr.state = "active"
    usr.is_staff = True
    usr.phone = "+48123123123"
    usr.fullname = "Generated User"
    usr.organizations.set(
        [
            org,
        ]
    )
    usr.save()
    return usr


@pytest.fixture
def html_table():
    html = """<html>
<head></head>
<body>
<table>
<tr>1</tr>
<tr>2</tr>
</table>
</body>
</html>"""
    return html


def get_datasets_list(content):
    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")
    return rows


def test_get_datasets_lists(html_table):
    rows = get_datasets_list(html_table)
    assert len(rows) == 2


class TestDatasetModel:
    def test_cant_create_empty_dataset(self):
        with pytest.raises(ValidationError) as e:
            ds = Dataset()
            ds.full_clean()
        assert "'title'" in str(e.value)

    def test_dataset_fields(self, dataset):
        dataset_dict = dataset.__dict__
        fields = [
            "slug",
            "title",
            "url",
            "notes",
            "license_id",
            "organization_id",
            "customfields",
            "license_condition_db_or_copyrighted",
            "license_condition_personal_data",
            "license_condition_modification",
            "license_condition_original",
            "license_condition_responsibilities",
            "license_condition_cc40_responsibilities",
            "license_condition_source",
            "update_frequency",
            "category_id",
            "status",
            "image",
            "image_alt",
            "has_high_value_data",
            "has_high_value_data_from_ec_list",
            "has_research_data",
            "has_dynamic_data",
        ]

        for f in fields:
            assert f in dataset_dict

    def test_default_dataset_metadata_values(self, dataset):
        """
        Check if new instance of `Dataset` has default values of all metadata as None.
        """
        assert dataset.has_high_value_data is None
        assert dataset.has_high_value_data_from_ec_list is None
        assert dataset.has_research_data is None
        assert dataset.has_dynamic_data is None

    def test_delete_dataset(self, dataset):
        assert dataset.status == "published"
        dataset.delete()
        assert dataset.is_removed is True
        with pytest.raises(ObjectDoesNotExist):
            Dataset.objects.get(id=dataset.id)
        assert Dataset.raw.get(id=dataset.id)

    def test_safe_delete_dataset_also_delete_resource(self, dataset_with_resources):
        dataset = dataset_with_resources
        resource = dataset_with_resources.resources.first()
        assert "published" == dataset.status
        assert "published" == dataset.resources.first().status
        assert resource in dataset.resources.all()
        assert "published" == dataset.resources.first().status
        dataset.delete()
        assert dataset.is_removed is True
        resource = Resource.trash.get(id=resource.id)
        assert resource.is_removed is True

    def test_unsafe_delete_dataset_and_its_resources(self, dataset_with_resources):
        dataset = dataset_with_resources
        resource = dataset_with_resources.resources.first()
        ds_id = dataset.id
        r_id = resource.id
        assert resource in dataset.resources.all()
        dataset.delete(safe=False)
        with pytest.raises(ObjectDoesNotExist):
            Dataset.objects.get(id=ds_id)
        with pytest.raises(ObjectDoesNotExist):
            Resource.objects.get(id=r_id)

    @pytest.mark.parametrize(
        "dataset_to_delete, expected_dataset_is_permanently_removed",
        [("imported_xml_dataset", True), ("imported_ckan_dataset", True), ("dataset", False)],
    )
    def test_imported_and_not_imported_dataset_delete(
        self, request, dataset_to_delete: Dataset, expected_dataset_is_permanently_removed: bool
    ):
        """
        Checks if deleting only the harvested dataset results in permanent deletion dataset.
        """

        # GIVEN
        dataset: Dataset = request.getfixturevalue(dataset_to_delete)
        # WHEN
        dataset.delete()
        # THEN
        assert dataset.is_removed
        # AND THEN
        assert dataset.is_permanently_removed is expected_dataset_is_permanently_removed

    def test_restore_dataset_is_not_restoring_its_resources(self, dataset_with_resources):
        dataset = dataset_with_resources
        resource = dataset_with_resources.resources.first()
        assert resource in dataset.resources.all()
        dataset.delete()
        assert resource not in Resource.objects.all()
        assert resource in Resource.trash.all()

        dataset.is_removed = False
        dataset.save()

        assert resource not in Resource.objects.all()
        assert resource in Resource.trash.all()

    def test_set_draft_for_dataset_also_change_his_resources_to_draft(self, dataset_with_resources):
        dataset = dataset_with_resources
        resource = dataset_with_resources.resources.first()
        assert resource in dataset.resources.all()
        assert dataset.status == "published"
        assert dataset.resources.all().first().status == "published"

        dataset.status = "draft"
        dataset.save()

        assert dataset.status == "draft"
        assert dataset.resources.all().first().status == "draft"

    def test_dataset_has_unique_regions_from_resources(self, dataset_with_resources, additional_regions):
        for res in dataset_with_resources.resources.all():
            res.regions.set(additional_regions)
        assert dataset_with_resources.regions.count() == 4


class TestDatasetsUserRoles:
    def test_editor_can_see_datasets_in_admin_panel(self, active_editor, institution):
        client = Client()
        client.force_login(active_editor)
        active_editor.organizations.set([institution])
        response = client.get("/")
        assert response.status_code == 200
        assert "/datasets/" in smart_str(response.content)

    def test_editor_can_go_to_datasets_in_admin_panel(self, active_editor, institution):
        client = Client()
        client.force_login(active_editor)
        active_editor.organizations.set([institution])
        response = client.get("/datasets/")
        assert response.status_code == 200

    def test_admin_can_see_datasets_in_admin_panel(self, admin):
        client = Client()
        client.force_login(admin)
        response = client.get("/")
        assert response.status_code == 200
        assert "/datasets/" in smart_str(response.content)

    def test_admin_can_go_to_datasets_in_admin_panel(self, admin):
        client = Client()
        client.force_login(admin)
        response = client.get("/datasets/")
        assert response.status_code == 200

    def test_editor_should_see_only_datasets_from_his_organization_admin_see_all(self, admin):
        # create organization 1 and 2
        org_1 = create_organization("organization 1")
        org_2 = create_organization("organization 2")

        # create dataset 1 and 2
        dataset_1 = create_dataset("dataset 1", org_1)
        dataset_2 = create_dataset("dataset 2", org_2)

        # add dataset 1 to organization 1
        assert org_1 is dataset_1.organization
        # add dataset 2 to organization 2
        assert org_2 is dataset_2.organization

        editor_1 = create_editor("editor_1@test.pl", org_1)
        editor_2 = create_editor("editor_2@test.pl", org_2)

        # create editor 1 and 2
        # add editor 1 to organization 1
        # add editor 2 to organization 2
        assert org_1 in editor_1.organizations.all()
        assert org_1 not in editor_2.organizations.all()
        assert org_2 in editor_2.organizations.all()
        assert org_2 not in editor_1.organizations.all()

        # login as admin
        # assert dataset length = 2
        client = Client()
        client.force_login(admin)
        response = client.get("/datasets/dataset/")
        datasets = get_datasets_list(response.content)
        assert len(datasets) == 3

        # login as editor 1
        # assert datasets length = 2
        # assert editor 1 see dataset 1
        client = Client()
        client.force_login(editor_1)
        response = client.get("/datasets/dataset/")
        datasets = get_datasets_list(response.content)
        assert len(datasets) == 2
        nr = datasets[1].find("a").get("href").split("/")[3]
        ds = Dataset.objects.get(id=int(nr))
        assert dataset_1 == ds

        # login as editor 2
        # assert datasets length = 1
        # assert editor 2 see dataset 2
        client = Client()
        client.force_login(editor_2)
        response = client.get("/datasets/dataset/")
        datasets = get_datasets_list(response.content)
        assert len(datasets) == 2
        nr = datasets[1].find("a").get("href").split("/")[3]
        ds = Dataset.objects.get(id=int(nr))
        assert dataset_2 == ds

    def test_is_license_set(self):
        dataset = Dataset()
        assert not dataset.is_license_set
        dataset.license_condition_db_or_copyrighted = "MIT"
        assert dataset.is_license_set

    def test_followers_count(self, dataset, admin, active_editor):
        assert dataset.followers_count == 0
        UserFollowingDataset(follower=admin, dataset=dataset).save()
        assert dataset.followers_count == 1
        UserFollowingDataset(follower=active_editor, dataset=dataset).save()
        assert dataset.followers_count == 2


class TestDatasetArchiveFunctionality:
    def test_dataset_rename(self, dataset_with_resources: Dataset):
        """
        This method tests the renaming functionality for dataset archives.
        It begins by asserting the existence of the current symlink based on the
        dataset's title. Then, it changes the dataset's title to trigger the renaming
        operation. Upon saving and refreshing the dataset, it asserts the existence
        of the newly renamed symlink based on the updated title.
        """
        dataset: Dataset = dataset_with_resources
        title: str = clean_filename(dataset.title)
        abs_media_path: str = dataset.archived_resources_files.storage.location
        archive_field: FileField = dataset.archived_resources_files.field

        actual_symlink_name: str = archive_field.generate_filename(dataset, f"{title}.zip")
        abs_actual_symlink_path = Path(abs_media_path) / actual_symlink_name
        assert abs_actual_symlink_path.exists()

        # Changing dataset name will trigger task changing symlink name
        dataset.title = "New title"
        dataset.save()
        run_on_commit_events()
        dataset.refresh_from_db()

        new_title: str = clean_filename(dataset.title)
        new_symlink_name: str = archive_field.generate_filename(dataset, f"{new_title}.zip")
        new_abs_actual_symlink_path = Path(abs_media_path) / new_symlink_name

        assert new_abs_actual_symlink_path.exists()
        assert not abs_actual_symlink_path.exists()
