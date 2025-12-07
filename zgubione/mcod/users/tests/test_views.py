from collections import namedtuple
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import falcon
import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from logingovpl.objects import LoginGovPlUser
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from mcod import settings
from mcod.core.caches import flush_sessions
from mcod.core.tests.test_mixins import MethodsNotAllowedTestMixin
from mcod.lib.jwt import decode_jwt_token, get_auth_header
from mcod.lib.triggers import session_store
from mcod.users.constants import (
    LOGINGOVPL_PROCESS,
    LOGINGOVPL_PROCESS_RESULT,
    LOGINGOVPL_REQUEST_ID_SEPARATOR,
    LOGINGOVPL_UNKNOWN_USER_IDENTIFIER,
    PORTAL_TYPE,
)
from mcod.users.factories import AdminFactory, EditorFactory, UserFactory
from mcod.users.models import User as TypeUser
from mcod.users.services import LoginGovPlData, logingovpl_service
from mcod.users.views import ACSView

User = get_user_model()


@pytest.fixture()
def fake_user():
    return namedtuple("User", "email state fullname")


@pytest.fixture()
def fake_session():
    return namedtuple("Session", "session_key")


class TestLogout:

    def test_logout_by_not_logged_in(self, client):
        resp = client.simulate_post(path="/auth/logout")
        assert resp.status == falcon.HTTP_401
        assert resp.json["code"] == "token_missing"

    def test_logout(self, client, active_user):
        flush_sessions()
        resp = client.simulate_post(
            path="/auth/login",
            json={
                "data": {
                    "type": "user",
                    "attributes": {
                        "email": active_user.email,
                        "password": "12345.Abcde",
                    },
                }
            },
        )
        assert resp.status == falcon.HTTP_201

        active_usr_token = resp.json["data"]["attributes"]["token"]
        prefix = getattr(settings, "JWT_HEADER_PREFIX")

        assert active_user.check_session_valid(f"{prefix} {active_usr_token}") is True

        active_user2 = User.objects.create_user("test-active2@example.com", "12345.Abcde")
        active_user2.state = "active"
        active_user2.save()

        resp = client.simulate_post(
            path="/auth/login",
            json={
                "data": {
                    "type": "user",
                    "attributes": {
                        "email": active_user2.email,
                        "password": "12345.Abcde",
                    },
                }
            },
        )

        assert resp.status == falcon.HTTP_201

        active_usr2_token = resp.json["data"]["attributes"]["token"]
        assert active_user.check_session_valid(f"{prefix} {active_usr_token}") is True
        assert active_user2.check_session_valid(f"{prefix} {active_usr2_token}") is True

        resp = client.simulate_post(
            path="/auth/logout",
            headers={"Authorization": "Bearer %s" % active_usr_token},
        )

        assert resp.status == falcon.HTTP_200
        assert active_user.check_session_valid(f"{prefix} {active_usr_token}") is False
        assert active_user2.check_session_valid(f"{prefix} {active_usr2_token}") is True

        resp = client.simulate_post(
            path="/auth/logout",
            headers={"Authorization": "Bearer %s" % active_usr2_token},
        )

        assert resp.status == falcon.HTTP_200
        assert active_user.check_session_valid(f"{prefix} {active_usr_token}") is False
        assert active_user2.check_session_valid(f"{prefix} {active_usr2_token}") is False


class TestProfile:

    def test_get_profile_after_logout(self, client, active_user):
        resp = client.simulate_post(
            path="/auth/login",
            json={
                "data": {
                    "type": "user",
                    "attributes": {
                        "email": active_user.email,
                        "password": "12345.Abcde",
                    },
                }
            },
        )

        assert resp.status == falcon.HTTP_201
        token = resp.json["data"]["attributes"]["token"]

        resp = client.simulate_post(path="/auth/logout", headers={"Authorization": "Bearer %s" % token})

        assert resp.status == falcon.HTTP_200

        resp = client.simulate_get(path="/auth/user", headers={"Authorization": "Bearer %s" % token})
        assert resp.status == falcon.HTTP_401
        assert resp.json["code"] == "authentication_error"


class TestResetPasswordConfirm:

    def test_password_change(self, client, active_user):
        data = {
            "data": {
                "type": "user",
                "attributes": {
                    "new_password1": "123.4.bce",
                    "new_password2": "123.4.bce",
                },
            }
        }
        token = active_user.password_reset_token
        url = f"/auth/password/reset/{token}"

        resp = client.simulate_post(url, json=data)
        assert resp.status == falcon.HTTP_422
        assert resp.json["errors"]["data"]["attributes"]["new_password1"] == [
            "Hasło musi zawierać przynajmniej jedną dużą i jedną mała literę."
        ]

        data = {
            "data": {
                "type": "user",
                "attributes": {
                    "new_password1": "123.4.bCe",
                    "new_password2": "123.4.bCe!",
                },
            }
        }

        resp = client.simulate_post(url, json=data)
        assert resp.status == falcon.HTTP_422
        assert resp.json["errors"]["data"]["attributes"]["new_password1"] == ["Hasła nie pasują"]

        valid_password = "123.4.bCe"
        data = {
            "data": {
                "type": "user",
                "attributes": {
                    "new_password1": valid_password,
                    "new_password2": valid_password,
                },
            }
        }

        resp = client.simulate_post(url, json=data)
        assert resp.status == falcon.HTTP_201
        user = User.objects.get(pk=active_user.id)
        assert user.check_password(valid_password) is True
        token_obj = user.tokens.filter(token=token).first()
        assert token_obj is not None
        assert token_obj.is_valid is False

    def test_invalid_expired_token(self, client, active_user):
        data = {
            "data": {
                "type": "user",
                "attributes": {
                    "new_password1": "123.4.bcE",
                    "new_password2": "123.4.bcE",
                },
            }
        }

        token = active_user.password_reset_token

        token_obj = active_user.tokens.filter(token=token).first()

        assert token_obj.is_valid is True

        token_obj.invalidate()

        assert token_obj.is_valid is False
        resp = client.simulate_post(f"/auth/password/reset/{token}", json=data)
        assert resp.status == falcon.HTTP_400
        assert resp.json["code"] == "expired_token"


class TestVerifyEmail:

    def test_pending_user(self, client, inactive_user):
        token = inactive_user.email_validation_token
        resp = client.simulate_get(path="/auth/registration/verify-email/%s/" % token)
        assert resp.status == falcon.HTTP_200

        usr = User.objects.get(email=inactive_user)
        assert usr.state == "active"
        token_obj = usr.tokens.filter(token=token).first()
        assert token_obj.is_valid is False
        assert usr.email_confirmed.date() == timezone.now().date()

    def test_blocked_user(self, client, blocked_user):
        token = blocked_user.email_validation_token
        resp = client.simulate_get(path="/auth/registration/verify-email/%s/" % token)
        assert resp.status == falcon.HTTP_200

        usr = User.objects.get(email=blocked_user)
        assert usr.state == "blocked"
        token_obj = usr.tokens.filter(token=token).first()
        assert token_obj.is_valid is False
        assert usr.email_confirmed.date() == timezone.now().date()

    def test_errors(self, client, inactive_user):
        for token in ["abcdef", "8c37fd0c-5600-4277-a13a-67ced4a61e66"]:
            resp = client.simulate_get(path=f"/auth/registration/verify-email/{token}")
            assert resp.status == falcon.HTTP_404

        token = inactive_user.email_validation_token
        token_obj = inactive_user.tokens.filter(token=token).first()
        assert token_obj.is_valid is True

        token_obj.invalidate()

        resp = client.simulate_get(path=f"/auth/registration/verify-email/{token}")
        assert resp.status == falcon.HTTP_400
        assert resp.json["code"] == "expired_token"
        assert resp.json["title"] == "400 Bad Request"
        assert resp.json["description"] == (
            "<b>Twój link do aktywacji konta wygasł.</b><br>Jeżeli chcesz otrzymać nowy link aktywacyjny, "
            'skontaktuj się z nami: <a href="mailto:kontakt@dane.gov.pl">kontakt@dane.gov.pl</a>'
        )


class TestAdminPanelAccess:

    def test_extended_permissions(self, active_user):
        header = get_auth_header(active_user, "1")

        payload = decode_jwt_token(header)
        assert payload["user"]["roles"] == []

        active_user.is_staff = True

        header = get_auth_header(active_user, "1")

        payload = decode_jwt_token(header)
        assert payload["user"]["roles"] == ["editor"]

        active_user.is_staff = False
        active_user.is_superuser = True

        header = get_auth_header(active_user, "1")

        payload = decode_jwt_token(header)
        assert payload["user"]["roles"] == ["admin"]


def test_admin_autocomplete_view_for_superuser(admin: User):
    client = Client()
    client.force_login(admin)

    response = client.get(reverse("admin-autocomplete"))

    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["id"] == str(admin.id)
    assert response.json()["results"][0]["text"] == admin.email


@pytest.mark.parametrize("autocomplete_endpoint", ["admin-autocomplete", "staff-autocomplete"])
def test_autocomplete_view_returns_empty_for_not_superuser(
    active_editor: User,
    autocomplete_endpoint: str,
):
    """Checks if autocomplete user related views returns no results for not superuser."""
    client = Client()
    client.force_login(active_editor)

    response = client.get(reverse(autocomplete_endpoint))

    assert len(response.json()["results"]) == 0


AutocompleteResults = List[Tuple[str, str]]


def test_staff_autocomplete_view(admin: User):
    # GIVEN 17 users: 1 admin (also staff), 15 staff users, 1 not staff user
    UserFactory.create(is_staff=False)
    staff_users: List[User] = UserFactory.create_batch(15, is_staff=True)
    all_staff_users: List[User] = [*staff_users, admin]
    all_staff_users.sort(key=lambda user: user.email)  # sort staff users by email

    total_users_count: int = User.objects.count()
    assert total_users_count == 17, f"17 users should exist in DB, got {total_users_count}"

    # WHEN
    client = Client()
    client.force_login(admin)

    # 1st page request
    response_page1 = client.get(reverse("staff-autocomplete"))
    results_page1 = response_page1.json()["results"]
    # 2nd page request
    response_page2 = client.get(reverse("staff-autocomplete"), data={"page": 2})
    results_page2 = response_page2.json()["results"]
    # results for both pages
    results_page1_list: AutocompleteResults = [(result["id"], result["text"]) for result in results_page1]
    results_page2_list: AutocompleteResults = [(result["id"], result["text"]) for result in results_page2]

    # THEN
    # # Only admin and staff users should be returned (ORDERED by email)
    # Prepare expected data for paginated staff results (10 users per page).
    page1_expected_results: AutocompleteResults = [(str(user.id), user.email) for user in all_staff_users[:10]]
    page2_expected_results: AutocompleteResults = [(str(user.id), user.email) for user in all_staff_users[10:]]
    # Check expected results
    assert results_page1_list == page1_expected_results
    assert results_page2_list == page2_expected_results


def test_agent_autocomplete_view(admin: User):
    # GIVEN 17 users: 1 admin, 15 agent users, 1 not agent user
    UserFactory.create(is_agent=False)
    agents: List[User] = UserFactory.create_batch(15, is_agent=True)
    agents.sort(key=lambda user: user.email)  # sort created agents by email

    total_users_count: int = User.objects.count()
    assert total_users_count == 17, f"17 users should exist in DB, got {total_users_count}"

    # WHEN
    client = Client()
    client.force_login(admin)

    # 1st page request
    response_page1 = client.get(reverse("agent-autocomplete"))
    results_page1 = response_page1.json()["results"]
    # 2nd page request
    response_page2 = client.get(reverse("agent-autocomplete"), data={"page": 2})
    results_page2 = response_page2.json()["results"]
    # results for both pages
    results_page1_list: AutocompleteResults = [(result["id"], result["text"]) for result in results_page1]
    results_page2_list: AutocompleteResults = [(result["id"], result["text"]) for result in results_page2]

    # THEN
    # Only agent users should be returned (ORDERED by email)
    # Prepare expected data for paginated agent results (10 users per page).
    page1_expected_results: AutocompleteResults = [(str(user.id), user.email) for user in agents[:10]]
    page2_expected_results: AutocompleteResults = [(str(user.id), user.email) for user in agents[10:]]
    # Check expected results
    assert results_page1_list == page1_expected_results
    assert results_page2_list == page2_expected_results


class TestLogingovplSSOView(MethodsNotAllowedTestMixin):

    NOT_ALLOWED_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    client = Client()
    url = reverse("logingovpl")

    @override_settings(USERS_TEST_LOGINGOVPL=True)
    def test_mock_template_loads(self):
        """Test if template for test logingovpl is rendering properly when
        USERS_TEST_LOGINGOVPL flag is set to True.
        """
        res = self.client.get(self.url)

        assert res.status_code == 200
        assert "Testowa strona logowania login.gov.pl" in res.content.decode()

    @pytest.mark.parametrize("portal_type", ["MAIN", "ADMIN"])
    @override_settings(USERS_TEST_LOGINGOVPL=True)
    def test_in_response_to_template(self, portal_type, admin_user):
        """
        Test if the test logingovpl template renders with proper in_response_to identifier.
        """
        url = f"{self.url}?portal=admin" if portal_type == "ADMIN" else self.url
        res = self.client.get(url)
        content = res.content.decode()
        assert f"{portal_type}-LOGIN-{LOGINGOVPL_UNKNOWN_USER_IDENTIFIER}" in content

        self.client.force_login(admin_user)
        res2 = self.client.get(url)
        content = res2.content.decode()
        assert f"{portal_type}-LINK-{admin_user.pk}" in content

    @pytest.mark.parametrize("portal_type", ["MAIN", "ADMIN"])
    @override_settings(USERS_TEST_LOGINGOVPL=False)
    def test_envelope_is_prepared_for_linking_success(self, portal_type, active_user):
        """Test if for the logged user (linking process from the portal defined in `portal_type`),
        the correct envelope is prepared.
        """
        url = f"{self.url}?portal=admin" if portal_type == "ADMIN" else self.url
        with patch("logingovpl.views.add_sign", return_value="signed_xml"):
            with patch("django.contrib.auth.get_user", return_value=active_user):
                res = self.client.get(url)

        assert res.status_code == 200
        assert 'onload="document.forms[0].submit()"' in res.content.decode()
        assert "envelop" in res.context
        assert "relay_state" in res.context
        assert "sso_url" in res.context
        assert (
            f"{portal_type}{LOGINGOVPL_REQUEST_ID_SEPARATOR}LINK{LOGINGOVPL_REQUEST_ID_SEPARATOR}{active_user.id}"
            in res.context["authn_request_id"]
        )

    @pytest.mark.parametrize("portal_type", ["MAIN", "ADMIN"])
    @override_settings(USERS_TEST_LOGINGOVPL=False)
    def test_envelope_is_prepared_for_logging_success(self, portal_type):
        """Test if for the not logged user (logging process from the portal defined in `portal_type`),
        the correct envelope is prepared.
        """
        url = f"{self.url}?portal=admin" if portal_type == "ADMIN" else self.url
        with patch("logingovpl.views.add_sign", return_value="signed_xml"):
            res = self.client.get(url)

        assert res.status_code == 200
        assert 'onload="document.forms[0].submit()"' in res.content.decode()
        assert "envelop" in res.context
        assert "relay_state" in res.context
        assert "sso_url" in res.context
        assert (
            f"{portal_type}{LOGINGOVPL_REQUEST_ID_SEPARATOR}LOGIN{LOGINGOVPL_REQUEST_ID_SEPARATOR}UNKNOWN"
            in res.context["authn_request_id"]
        )


class TestLogingovplACSView(MethodsNotAllowedTestMixin):
    """Unit tests for ACSView class"""

    NOT_ALLOWED_METHODS = ["GET", "PUT", "PATCH", "DELETE"]
    client = Client()
    url = reverse("idp")

    def test_bad_structure_request_data(
        self,
        response_data_from_logingovpl: Dict[str, str],
    ):
        """
        Data received in first request has bad structure. E.g. lack of SAMLart part.
        """

        # Given
        # break correct response data
        del response_data_from_logingovpl["SAMLart"]
        request = APIRequestFactory().post(self.url, data=response_data_from_logingovpl, format="json")

        # When
        acs_view = ACSView.as_view()
        response = acs_view(request)

        # Then
        assert response.status_code == 302
        assert response.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.UNKNOWN, LOGINGOVPL_PROCESS.UNKNOWN, LOGINGOVPL_PROCESS_RESULT.UNKNOWN
        )

    @patch("mcod.users.services.ACSMixin.resolve_artifact")
    def test_saml_art_response_auth_failed(
        self,
        mocked_resolve_artifact,
        response_data_from_logingovpl: Dict[str, str],
        resolve_artifact_response_auth_failed: bytes,
    ):
        """
        WK returns other status than status:Success - e.g. status:AuthnFailed
        """

        # Given
        request = APIRequestFactory().post(self.url, data=response_data_from_logingovpl, format="json")
        resolve_artifact_response = MagicMock(content=resolve_artifact_response_auth_failed)
        mocked_resolve_artifact.return_value = resolve_artifact_response

        # When
        acs_view = ACSView.as_view()
        response = acs_view(request)

        # Then
        assert response.status_code == 302
        assert response.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.UNKNOWN, LOGINGOVPL_PROCESS.UNKNOWN, LOGINGOVPL_PROCESS_RESULT.UNKNOWN
        )

    @pytest.mark.parametrize(
        "user_exists, account_link_result, status_code, redirect_url",
        [
            (
                False,
                False,
                302,
                logingovpl_service.get_redirect_url(PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LINK, LOGINGOVPL_PROCESS_RESULT.ERROR),
            ),
            (
                True,
                True,
                302,
                logingovpl_service.get_redirect_url(PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LINK, LOGINGOVPL_PROCESS_RESULT.SUCCESS),
            ),
        ],
    )
    @patch("mcod.users.views.logingovpl_service.get_logingovpl_data_and_logout")
    @override_settings(USERS_TEST_LOGINGOVPL=False)
    def test_link_with_wk(
        self,
        mocked_get_logingovpl_data_and_logout,
        user_exists: bool,
        account_link_result: bool,
        status_code: int,
        redirect_url: str,
        logingovpl_user: LoginGovPlUser,
        active_user: TypeUser,
        response_data_from_logingovpl: Dict[str, str],
    ):
        """
        Test link OD account with WK account - two cases:
        1. field `in_response_to` regards to user which doesn't exist in OD user DB.
        2. field `in_response_to` regards to user which exists in OD user DB.
        """

        # Given
        if user_exists:
            user_id = active_user.id
        else:
            # id not existing user in DB
            user_id = active_user.id + 100

        login_gov_pl_data = LoginGovPlData(
            user=logingovpl_user,
            name_id="some_logingovpl_user",
            in_response_to=f"ID-3226742f-c93b-4647-b138-81b6ba8f631e-MAIN-LINK-{user_id}",
            session_id="61e435c2d509977d896b837c157da46e4fa52b7b6c82df0cd122ee3dc527ce49",
        )
        mocked_get_logingovpl_data_and_logout.return_value = login_gov_pl_data
        request = APIRequestFactory().post(self.url, data=response_data_from_logingovpl, format="json")
        if user_exists:
            request.session = session_store()
            request.session["_auth_user_id"] = str(active_user.id)
            request.session.save()
        assert active_user.is_gov_linked is False
        assert active_user.is_gov_auth is False

        # When
        acs_view = ACSView.as_view()
        response = acs_view(request)
        active_user.refresh_from_db()

        # Then
        assert active_user.is_gov_linked is account_link_result
        assert active_user.is_gov_auth is account_link_result
        assert response.status_code == status_code
        assert response.url == redirect_url

    @pytest.mark.parametrize(
        "portal_type, user, pesel, is_user_authenticated, redirect_url, is_gov_auth",
        [
            (
                PORTAL_TYPE.MAIN,
                "active_user",
                None,
                False,
                logingovpl_service.get_redirect_url(PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.ERROR),
                None,
            ),
            (
                PORTAL_TYPE.MAIN,
                "active_user",
                "other_pesel",
                False,
                logingovpl_service.get_redirect_url(PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.ERROR),
                None,
            ),
            (
                PORTAL_TYPE.MAIN,
                "active_user",
                "pesel",
                True,
                logingovpl_service.get_redirect_url(
                    PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.SUCCESS
                ),
                True,
            ),
            (
                PORTAL_TYPE.ADMIN,
                "active_editor",
                None,
                False,
                logingovpl_service.get_redirect_url(PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.ERROR),
                None,
            ),
            (
                PORTAL_TYPE.ADMIN,
                "active_editor",
                "other_pesel",
                False,
                logingovpl_service.get_redirect_url(PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.ERROR),
                None,
            ),
            (
                PORTAL_TYPE.ADMIN,
                "active_editor",
                "pesel",
                True,
                logingovpl_service.get_redirect_url(
                    PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.LOGIN, LOGINGOVPL_PROCESS_RESULT.SUCCESS
                ),
                True,
            ),
        ],
    )
    @patch("mcod.users.views.logingovpl_service.get_logingovpl_data_and_logout")
    @override_settings(USERS_TEST_LOGINGOVPL=False)
    def test_login_with_wk_pesel_match_user(
        self,
        mocked_get_logingovpl_data_and_logout,
        portal_type: PORTAL_TYPE,
        user: TypeUser,
        pesel: Optional[str],
        is_user_authenticated: bool,
        redirect_url: str,
        is_gov_auth: bool,
        logingovpl_user: LoginGovPlUser,
        response_data_from_logingovpl: Dict[str, str],
        request,
    ):
        """
        Login process using WK. 3 cases below for main portal (active user) and for admin panel (editor user):
        1. no user in DB has pesel info matching WK response (no user with any pesel in DB).
        2. no user in DB has pesel info matching WK response (only one user in DB, but without matching pesel).
        3. one user in DB has pesel info matching WK response.
        """

        # Given
        db_user = request.getfixturevalue(user)
        db_user.pesel = pesel
        db_user.save()
        login_gov_pl_data = LoginGovPlData(
            user=logingovpl_user,
            name_id="some_logingovpl_user",
            in_response_to=f"ID-3226742f-c93b-4647-b138-81b6ba8f631e-{portal_type.value}-LOGIN-{db_user.id}",
            session_id="61e435c2d509977d896b837c157da46e4fa52b7b6c82df0cd122ee3dc527ce49",
        )
        mocked_get_logingovpl_data_and_logout.return_value = login_gov_pl_data
        request = APIRequestFactory().post(self.url, data=response_data_from_logingovpl, format="json")
        acs_view = ACSView.as_view()
        assert not hasattr(request, "user")

        # When
        response = acs_view(request)

        # Then
        # check if active_user is logged
        assert request.user.is_authenticated is is_user_authenticated
        assert response.status_code == 302
        assert redirect_url == response.url
        if is_gov_auth is not None:
            assert request.user.is_gov_auth is is_gov_auth


class TestLogingovplUnlinkView(MethodsNotAllowedTestMixin):

    NOT_ALLOWED_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    client = APIClient()
    url = reverse("unlink")
    header_prefix = getattr(settings, "JWT_HEADER_PREFIX")

    def test_unlink_logged_user_success(self, active_user):
        """Test if the logged user linked to the login.gov.pl service can be unlinked
        with success (PESEL attribute is removed and redirect URL is `UNLINK_SUCCESS`).
        """

        active_user.pesel = "some pesel"
        active_user.save()

        with patch("django.contrib.auth.get_user", return_value=active_user):
            res = self.client.get(self.url)

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.UNLINK, LOGINGOVPL_PROCESS_RESULT.SUCCESS
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_linked is False

    def test_unlink_not_logged_user_failure(self, active_user):
        """Test if the not logged user, linked to the login.gov.pl service, can not
        be unlinked with success (PESEL attribute is not removed and redirect URL
        is `UNLINK_ERROR`).
        """

        active_user.pesel = "some pesel"
        active_user.save()

        res = self.client.get(self.url)

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.UNLINK, LOGINGOVPL_PROCESS_RESULT.ERROR
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_linked is True


class TestLogingovplSwitchView(MethodsNotAllowedTestMixin):

    NOT_ALLOWED_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    client = APIClient()
    url = reverse("switch")
    header_prefix = getattr(settings, "JWT_HEADER_PREFIX")
    common_pesel = "11111111111"

    def test_switch_logged_by_logingovpl_user_in_main_success(self):
        """Test if the user logged by the login.gov.pl service in the main panel can be switched
        to the other active account linked to the login.gov.pl service by the same PESEL.
        """

        active_user = UserFactory.create(email="active_user@dane.gov.pl", pesel=self.common_pesel, is_gov_auth=True)
        active_user2 = UserFactory.create(email="active_user2@dane.gov.pl", pesel=self.common_pesel)

        # try to switch from active_user to active_user2
        with patch("django.contrib.auth.get_user", return_value=active_user):
            res = self.client.get(self.url + f"?email={active_user2.email}")

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.SUCCESS
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_auth is False
        active_user2.refresh_from_db()
        assert active_user2.is_gov_auth is True

    def test_switch_logged_by_logingovpl_user_in_admin_success(self):
        """Test if the user logged by the login.gov.pl service in the admin panel can be switched
        to the other active account accepted by the admin panel and linked to the login.gov.pl service
        by the same PESEL.
        """

        active_user = AdminFactory.create(email="admin@dane.gov.pl", pesel=self.common_pesel, is_gov_auth=True)
        active_user2 = EditorFactory.create(email="editor_user@dane.gov.pl", pesel=self.common_pesel)

        # try to switch from active_user to active_user2
        with patch("django.contrib.auth.get_user", return_value=active_user):
            res = self.client.get(self.url + f"?email={active_user2.email}&portal=admin")

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.SUCCESS
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_auth is False
        active_user2.refresh_from_db()
        assert active_user2.is_gov_auth is True

    def test_switch_not_logged_by_logingovpl_user_in_main_failure(self):
        """Test if the not logged by the main panel user, linked to the login.gov.pl service,
        can not be switched to the other active account linked to the login.gov.pl service
        by the same PESEL.
        """

        active_user = UserFactory.create(email="active_user@dane.gov.pl", pesel=self.common_pesel)
        active_user2 = UserFactory.create(email="active_user2@dane.gov.pl", pesel=self.common_pesel)

        # try to switch from active_user to active_user2
        res = self.client.get(self.url + f"?email={active_user2.email}")

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_auth is False
        active_user2.refresh_from_db()
        assert active_user2.is_gov_auth is False

    def test_switch_not_logged_by_logingovpl_user_in_admin_failure(self):
        """Test if the not logged by the admin panel user linked to the login.gov.pl service
        can not be switched to the other active account accepted by the admin panel
        and linked to the login.gov.pl service by the same PESEL.
        """

        active_user = AdminFactory.create(email="admin@dane.gov.pl", pesel=self.common_pesel)
        active_user2 = EditorFactory.create(email="editor_user@dane.gov.pl", pesel=self.common_pesel)

        # try to switch from active_user to active_user2
        res = self.client.get(self.url + f"?email={active_user2.email}&portal=admin")

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_auth is False
        active_user2.refresh_from_db()
        assert active_user2.is_gov_auth is False

    def test_switch_logged_user_in_main_without_email_failure(self):
        """Test if the user logged by the login.gov.pl service in the main panel can not be switched
        to the other active account linked to the login.gov.pl service by the same PESEL,
        due to the lack of the email in the request URL.
        """

        active_user = UserFactory.create(email="active_user@dane.gov.pl", pesel=self.common_pesel, is_gov_auth=True)
        active_user2 = UserFactory.create(email="active_user2@dane.gov.pl", pesel=self.common_pesel)

        # try to switch from active_user to active_user2 without the email attribute
        with patch("django.contrib.auth.get_user", return_value=active_user):
            res = self.client.get(self.url)

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_auth is False
        active_user2.refresh_from_db()
        assert active_user2.is_gov_auth is False

    def test_switch_logged_user_in_main_with_not_validated_email_failure(self):
        """Test if the user logged by the login.gov.pl service in the main panel can not be switched
        to the other active account linked to the login.gov.pl service by the same PESEL,
        due to the not valid email in the request URL.
        """

        active_user = UserFactory.create(email="active_user@dane.gov.pl", pesel=self.common_pesel, is_gov_auth=True)
        not_valid_email = "wrong_letter_]@example.com"

        # try to switch from active_user to active_user2 without the email attribute
        with patch("django.contrib.auth.get_user", return_value=active_user):
            res = self.client.get(self.url + f"?email={not_valid_email}")

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.MAIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_auth is False

    def test_switch_logged_user_in_admin_without_email_failure(self):
        """Test if the user logged by the login.gov.pl service in the admin panel can not be switched
        to the other active account accepted by the admin panel and linked to the login.gov.pl service
        by the same PESEL, due to the lack of the email in the request URL.
        """

        active_user = AdminFactory.create(email="admin@dane.gov.pl", pesel=self.common_pesel, is_gov_auth=True)
        active_user2 = EditorFactory.create(email="editor_user@dane.gov.pl", pesel=self.common_pesel)

        # try to switch from active_user to active_user2 without the email attribute
        with patch("django.contrib.auth.get_user", return_value=active_user):
            res = self.client.get(self.url + "?portal=admin")

        assert res.status_code == status.HTTP_302_FOUND
        assert res.url == logingovpl_service.get_redirect_url(
            PORTAL_TYPE.ADMIN, LOGINGOVPL_PROCESS.SWITCH, LOGINGOVPL_PROCESS_RESULT.ERROR
        )
        active_user.refresh_from_db()
        assert active_user.is_gov_auth is False
        active_user2.refresh_from_db()
        assert active_user2.is_gov_auth is False
