from django.contrib import auth
from django.test import Client

from mcod.lib.rules import assigned_to_organization


class TestDatasetRules:

    def test_anonymous_user(self):
        client = Client()
        user = auth.get_user(client)
        assert not assigned_to_organization(user)

    def test_user_without_organization(self, admin):
        assert not assigned_to_organization(admin)

    def test_user_in_organization(self, active_editor):
        assert assigned_to_organization(active_editor)
