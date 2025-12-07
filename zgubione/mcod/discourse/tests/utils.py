import contextlib

import requests_mock
from discourse_django_sso.utils import SSOClientUtils
from discourse_django_sso_test_project.urls import nonce_service
from django.conf import settings
from pydiscourse.sso import sso_payload


@contextlib.contextmanager
def discourse_response_mocker(user):
    mocked_urls = {}
    client_util = SSOClientUtils(settings.DISCOURSE_SSO_SECRET, settings.DISCOURSE_SSO_REDIRECT)
    nonce_val = nonce_service.generate_nonce()
    sso_url = client_util.generate_sso_url(nonce_val, False)
    forum_user_id = 1
    username = user.email.split("@")[0]
    user_details = {
        "external_id": user.pk,
        "email": user.email,
        "username": user.email.split("@")[0],
        "name": user.fullname if user.fullname else username,
        "admin": True if user.is_superuser else False,
        "moderator": True if user.is_superuser else False,
    }
    keyid = 2
    key = "1234567"
    sync_sso_payload = sso_payload(settings.DISCOURSE_SSO_SECRET, **user_details)
    mocked_urls["sync_sso_mock_url"] = settings.DISCOURSE_SYNC_HOST + f"/admin/users/sync_sso?{sync_sso_payload}"
    mocked_urls["api_keys_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/api/keys"
    mocked_urls["activate_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/users/{0}/activate.json".format(forum_user_id)
    mocked_urls["mock_sso_url"] = sso_url
    mocked_urls["external_id_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/users/by-external/{0}".format(user.pk)
    mocked_urls["deactivate_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/users/{0}/deactivate.json".format(forum_user_id)
    mocked_urls["list_api_keys_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/api/keys"
    mocked_urls["revoke_key_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/api/keys/{0}/revoke".format(keyid)
    mocked_urls["undo_revoke_key_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/api/keys/{0}/undo-revoke".format(keyid)
    mocked_urls["delete_api_key_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/api/keys/{0}".format(keyid)
    mocked_urls["log_out_mock_url"] = settings.DISCOURSE_SYNC_HOST + "/admin/users/{0}/log_out".format(forum_user_id)
    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            mocked_urls["external_id_mock_url"],
            json={"user": {"id": forum_user_id}},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        mock_request.post(
            mocked_urls["log_out_mock_url"],
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"success": "ok"},
        )
        mock_request.put(
            mocked_urls["deactivate_mock_url"],
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"deactivated": True},
        )
        mock_request.get(mocked_urls["mock_sso_url"])
        mock_request.post(
            mocked_urls["sync_sso_mock_url"],
            json={"username": username, "id": forum_user_id, "active": user.is_active},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        mock_request.post(
            mocked_urls["api_keys_mock_url"],
            json={"key": {"key": key}},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        mock_request.put(
            mocked_urls["activate_mock_url"],
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"activated": True},
        )
        mock_request.get(
            mocked_urls["list_api_keys_mock_url"],
            headers={"Content-Type": "application/json; charset=utf-8"},
            json=[{"username": username, "key": key, "keyid": keyid}],
        )
        mock_request.post(
            mocked_urls["revoke_key_mock_url"],
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"revoked": True},
        )
        mock_request.post(
            mocked_urls["undo_revoke_key_mock_url"],
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"restored": True},
        )
        mock_request.delete(
            mocked_urls["delete_api_key_mock_url"],
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={"deleted": True},
        )

        yield mocked_urls
