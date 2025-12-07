import logging
import re

from django.test import Client
from django.urls import reverse
from django.utils.encoding import smart_str

from mcod.datasets.documents import Resource

logger = logging.getLogger("mcod")


class TestEditorAccess:

    def test_editor_not_in_organization_cant_see_resource_from_organizaton(self, active_editor, resource):
        client = Client()
        client.force_login(active_editor)
        response = client.get(f"/resources/resource/{resource.id}", follow=False)
        assert response.status_code == 301

    def test_trash_for_editor(self, db, active_editor, resources):
        editor_resources = Resource.objects.filter(dataset__organization_id=active_editor.organizations.all()[0].pk)
        editor_res_ids = list(editor_resources.values_list("pk", flat=True))
        editor_resources.delete()
        for res in resources:
            res.delete()
        client = Client()
        client.force_login(active_editor)
        response = client.get(reverse("admin:resources_resourcetrash_changelist"))
        pattern = re.compile(r"/resources/resourcetrash/\d+/change")
        result = pattern.findall(smart_str(response.content))
        assert all([f"/resources/resourcetrash/{res_id}/change" in result for res_id in editor_res_ids])


class TestDuplicateResource:

    def test_editor_can_add_resource_based_on_other_resource(self, active_editor):
        resource = Resource.objects.filter(dataset__organization_id=active_editor.organizations.all()[0].pk)[0]
        id_ = resource.id
        client = Client()
        client.force_login(active_editor)
        response = client.get(f"/resources/resource/{id_}", follow=True)
        assert response.status_code == 200
        assert '<a href="/resources/resource/add/?from_id={}" class="btn btn-high"'.format(id_) in smart_str(response.content)
        response = client.get(f"/resources/resource/add/?from_id={id_}")
        assert response.status_code == 200
        content = response.content.decode()
        assert resource.title in content
        assert resource.description in content
        assert resource.status in content
        assert resource.dataset.title in content

    def test_admin_can_add_resource_based_on_other_resource(self, admin, dataset_with_resources):
        dataset = dataset_with_resources
        resource = dataset.resources.last()
        id_ = resource.id
        client = Client()
        client.force_login(admin)
        response = client.get(f"/resources/resource/{id_}", follow=True)
        assert response.status_code == 200
        assert '<a href="/resources/resource/add/?from_id={}" class="btn btn-high"'.format(id_) in smart_str(response.content)
        response = client.get(f"/resources/resource/add/?from_id={id_}")
        assert response.status_code == 200
        content = response.content.decode()

        # is form filled with proper data
        assert resource.title in content
        assert resource.description in content
        assert resource.status in content
        assert dataset.title in content
        assert f'value="{id_}"' in content

    def test_cant_duplicate_deleted_resource(self, admin, removed_resource):
        client = Client()
        client.force_login(admin)
        response = client.get(f"/resources/resource/add/?from_id={removed_resource.pk}")
        content = response.content.decode()
        assert removed_resource.title not in content
        assert removed_resource.description not in content

    def test_cant_duplicate_imported_resource(self, admin, imported_ckan_resource):
        client = Client()
        client.force_login(admin)
        response = client.get(f"/resources/resource/add/?from_id={imported_ckan_resource.pk}")
        content = response.content.decode()
        if f'value="{imported_ckan_resource.pk}"' in content:
            logger.error("CKAN RESOURCE ID:", imported_ckan_resource.pk)
        assert imported_ckan_resource.title not in content
        assert imported_ckan_resource.description not in content
