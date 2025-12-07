from django.test import Client
from django.urls import reverse
from django.utils.encoding import smart_str
from pytest_bdd import scenarios

from mcod.datasets.models import User

scenarios("features/admin.feature")
scenarios("features/admin_forms.feature")
scenarios("features/meetings.feature")


class TestUserAdmin:
    def test_superuser_get_queryset(self, admin):
        client = Client()
        client.force_login(admin)
        response = client.get(reverse("admin:users_user_changelist"))
        assert response.content.count(b"field-email") == 1

    def test_admin_form_fields_rendered(self, admin):
        """Test if "Logowanie przez WK" text is displayed in response content."""
        client = Client()
        client.force_login(admin)
        url = reverse("admin:users_user_change", args=[admin.id])
        response = client.get(url)
        assert "Logowanie przez WK" in response.content.decode()

    def test_editor_with_organization_get_queryset(self, admin, active_editor):
        client = Client()
        client.force_login(active_editor)
        response = client.get(reverse("admin:users_user_changelist"))
        assert response.content.count(b"field-email") == 1

    def test_editor_without_organization_get_queryset(self, admin, active_editor):
        client = Client()
        client.force_login(active_editor)
        response = client.get(reverse("admin:users_user_changelist"))
        assert response.content.count(b"field-email") == 1

    def test_editor_cant_see_is_staff_is_superuser_state_fields_in_form(self, active_editor):
        client = Client()
        client.force_login(active_editor)
        response = client.get(active_editor.admin_change_url)
        assert 200 == response.status_code
        assert "id_email" in smart_str(response.content)
        assert '"id_is_staff"' not in smart_str(response.content)
        assert "id_is_superuser" not in smart_str(response.content)
        assert "id_state" not in smart_str(response.content)

    def test_editor_cant_change_himself_to_be_a_superuser_with_post_method(self, active_editor):
        client = Client()
        client.force_login(active_editor)
        response = client.post(
            active_editor.admin_change_url,
            data={
                "email": active_editor.email,
                "fullname": active_editor.fullname,
                "phone": active_editor.phone,
                "is_superuser": True,
            },
            follow=True,
        )
        assert 200 == response.status_code
        assert "To pole jest wymagane." not in smart_str(response.content)
        u = User.objects.get(id=active_editor.id)
        assert not u.is_superuser

    def test_login_email_is_case_insensitive(self, active_editor):
        client = Client()
        payloads = {"email": active_editor.email.upper(), "password": "12345.Abcde"}
        client.login(**payloads)
        response = client.get(reverse("admin:users_user_changelist"))
        assert 200 == response.status_code

    def test_admin_can_set_user_as_academy_admin_and_labs_admin(self, active_editor, admin):
        assert active_editor.is_academy_admin is False
        assert active_editor.is_labs_admin is False
        client = Client()
        client.force_login(admin)
        response = client.post(
            active_editor.admin_change_url,
            data={
                "email": active_editor.email,
                "is_superuser": False,
                "state": "active",
                "is_academy_admin": True,
                "is_labs_admin": True,
            },
            follow=True,
        )
        assert 200 == response.status_code
        u = User.objects.get(id=active_editor.id)
        assert u.is_academy_admin
        assert u.is_labs_admin

    def test_editor_change_form_doesnt_unsets_organizations(self, active_editor):
        client = Client()
        client.force_login(active_editor)
        response = client.post(
            active_editor.admin_change_url,
            data={
                "email": "new_mail@test.com",
                "fullname": active_editor.fullname,
                "phone": "111111111",
            },
            follow=True,
        )
        u = User.objects.get(id=active_editor.id)
        assert 200 == response.status_code
        assert u.organizations.exists()
