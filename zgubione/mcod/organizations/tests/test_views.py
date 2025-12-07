from django.test import Client
from django.urls import reverse


def test_organization_autocomplete_view(institutions, admin):
    client = Client()
    client.force_login(admin)

    response = client.get(reverse("admin:organizations_organization_autocomplete"))

    assert len(response.json()["results"]) == 3


def test_organization_autocomplete_view_editor_without_organization(institution, active_editor_without_org):
    client = Client()
    client.force_login(active_editor_without_org)

    response = client.get(reverse("admin:organizations_organization_autocomplete"))

    assert response.json() == {"error": "403 Forbidden"}


def test_organization_autocomplete_view_editor_with_organization(institutions, active_editor):
    client = Client()
    client.force_login(active_editor)

    response = client.get(reverse("admin:organizations_organization_autocomplete"))

    assert len(response.json()["results"]) == 1
