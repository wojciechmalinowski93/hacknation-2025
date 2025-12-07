from django.conf import settings

from mcod.discourse.client import DiscourseClient
from mcod.discourse.tests.utils import discourse_response_mocker


class TestDiscourseClient:

    def get_client(self):
        return DiscourseClient(
            settings.DISCOURSE_SYNC_HOST,
            settings.DISCOURSE_API_USER,
            settings.DISCOURSE_API_KEY,
        )

    def test_list_api_keys(self, admin):
        with discourse_response_mocker(admin):
            resp = self.get_client().list_api_keys()
        assert resp == [{"username": "admin", "key": "1234567", "keyid": 2}]

    def test_revoke_api_key(self, admin):
        with discourse_response_mocker(admin):
            resp = self.get_client().revoke_api_key(2)
        assert resp == {"revoked": True}

    def test_undo_revoke_api_key(self, admin):
        with discourse_response_mocker(admin):
            resp = self.get_client().undo_revoke_api_key(2)
        assert resp == {"restored": True}

    def test_delete_api_key(self, admin):
        with discourse_response_mocker(admin):
            resp = self.get_client().delete_api_key(2)
        assert resp == {"deleted": True}
