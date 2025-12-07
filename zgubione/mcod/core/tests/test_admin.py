import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from mcod.users.factories import UserFactory

User = get_user_model()


class TestCommonAdmin:
    def test_manual_link(self, admin):
        client = Client()
        client.force_login(admin)
        response = client.get("/", follow=True, HTTP_ACCEPT_LANGUAGE="pl")
        assert response.status_code == 200

        pattern = re.compile(
            f"<a href=['\"]"
            f"{settings.CONSTANCE_CONFIG['MANUAL_URL'][0]}"
            f"['\"] target=['\"]_blank['\"] class=['\"]icon['\"]>"
        )
        assert len(pattern.findall(response.content.decode("utf-8"))) > 0

    def test_user_govpl_dropdown_list_empty(self, admin: User, active_user: User):
        """Test if active_user email is not visible in admin page.
        Admin user doesn't have connected WK accounts (by pesel),
        that's why active_user email shouldn't be visible in admin page."""
        client = Client()
        client.force_login(admin)
        response = client.get("/", follow=True, HTTP_ACCEPT_LANGUAGE="pl")
        content = response.content.decode("utf-8")
        assert active_user.email not in content

    def test_user_govpl_dropdown_one_element(self, admin: User, active_user: User, test_user_pesel: str):
        """Test if active_user email is displayed in admin page.
        Admin user and active_user have the same pesel.
        Expected active_user should be displayed in admin page"""
        admin.pesel = test_user_pesel
        admin.is_gov_auth = True
        active_user.pesel = test_user_pesel
        active_user.is_superuser = True
        active_user.save()
        admin.save()

        client = Client()
        client.force_login(admin)
        response = client.get("/", follow=True, HTTP_ACCEPT_LANGUAGE="pl")
        content = response.content.decode("utf-8")
        assert active_user.email in content

    def test_user_govpl_dropdown_more_elements(self, admin: User, test_user_pesel: str):
        """Test if different users emails are displayed in admin page.
        Admin user and other users have the same pesel.
        Expected users emails should be displayed in admin page"""
        admin.pesel = test_user_pesel
        admin.is_gov_auth = True
        other_users = UserFactory.create_batch(3, pesel=test_user_pesel, is_superuser=True)
        admin.save()

        client = Client()
        client.force_login(admin)
        response = client.get("/", follow=True, HTTP_ACCEPT_LANGUAGE="pl")
        content = response.content.decode("utf-8")

        for user in other_users:
            assert user.email in content

    def test_user_govpl_dropdown_no_elements_not_superuser(self, admin: User, test_user_pesel: str):
        """Test if different users emails are not displayed in admin page.
        Admin user and other users have the same pesel, but are not superusers.
        Expected users emails should not be displayed in admin page"""
        admin.pesel = test_user_pesel
        other_users = UserFactory.create_batch(3, pesel=test_user_pesel, is_superuser=False)
        admin.save()

        client = Client()
        client.force_login(admin)
        response = client.get("/", follow=True, HTTP_ACCEPT_LANGUAGE="pl")
        content = response.content.decode("utf-8")

        for user in other_users:
            assert user.email not in content

    def test_user_govpl_dropdown_no_elements_wrong_role(self, admin: User, test_user_pesel: str):
        """Test if different users emails are not displayed in admin page.
        Admin user and other users have the same pesel, but wrong role.
        Expected users emails should not be displayed in admin page"""
        admin.pesel = test_user_pesel
        other_users = UserFactory.create_batch(3, pesel=test_user_pesel, is_staff=False)
        admin.save()

        client = Client()
        client.force_login(admin)
        response = client.get("/", follow=True, HTTP_ACCEPT_LANGUAGE="pl")
        content = response.content.decode("utf-8")

        for user in other_users:
            assert user.email not in content
