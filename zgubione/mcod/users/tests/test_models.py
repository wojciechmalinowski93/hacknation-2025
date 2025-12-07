import django
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import ObjectDoesNotExist
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone, translation
from falcon.testing import TestClient
from rest_framework.test import APIRequestFactory

from mcod.core.caches import flush_sessions
from mcod.users.models import LoggingMethod, Token, get_token_expiration_date
from mcod.users.views import ACSView

User = get_user_model()


def test_user_create(inactive_user):
    usr = User.objects.get(email=inactive_user.email)
    assert usr.id == inactive_user.id
    assert usr.last_login is None
    assert usr.state == "pending"


def test_last_login(inactive_user):
    now = timezone.now()
    user_logged_in.send(User, request=None, user=inactive_user)
    usr = User.objects.get(email=inactive_user.email)
    assert now < usr.last_login


def test_email_unique():
    with pytest.raises(django.core.exceptions.ValidationError) as e:
        User.objects.create_user("aaa@example.com", "12345.Abcde")
        User.objects.create_user("aaa@example.com", "12345.Abcde")
    assert "email" in e.value.message_dict


def test_is_active(active_user):
    assert active_user.state == "active"
    assert active_user.is_active is True


def test_admin_panel_access_flag(active_user):
    assert active_user.system_role == "user"

    active_user.is_superuser = True
    assert active_user.system_role == "admin"

    active_user.is_superuser = False
    active_user.is_staff = True
    assert active_user.system_role == "editor"


def test_check_session_valid(mocker):
    usr = User.objects.create_user("aaa@example.com", "12345.Abcde")
    assert usr.check_session_valid(None) is False
    assert usr.check_session_valid("aaa") is False

    mocker.patch("mcod.users.models.decode_jwt_token", return_value={"user": {}})
    assert usr.check_session_valid("aaa") is False

    mocker.patch(
        "mcod.users.models.decode_jwt_token",
        return_value={"user": {"session_key": 1234}},
    )
    assert usr.check_session_valid("aaa") is False

    mocker.patch(
        "mcod.users.models.decode_jwt_token",
        return_value={"user": {"session_key": 1234}},
    )
    mocker.patch("mcod.users.models.session_cache.get", return_value={})
    assert usr.check_session_valid("aaa") is False

    mocker.patch(
        "mcod.users.models.decode_jwt_token",
        return_value={"user": {"session_key": 1234}},
    )
    mocker.patch("mcod.users.models.session_cache.get", return_value={"_auth_user_hash": "aaaaa"})
    assert usr.check_session_valid("aaa") is False

    mocker.patch(
        "mcod.users.models.decode_jwt_token",
        return_value={"user": {"session_key": 1234}},
    )
    mocker.patch(
        "mcod.users.models.session_cache.get",
        return_value={"_auth_user_hash": "aaaaa", "_auth_user_id": "0"},
    )
    assert usr.check_session_valid("aaa") is False

    mocker.patch(
        "mcod.users.models.decode_jwt_token",
        return_value={"user": {"session_key": 1234}},
    )
    mocker.patch(
        "mcod.users.models.session_cache.get",
        return_value={"_auth_user_hash": "aaaaaa", "_auth_user_id": str(usr.id)},
    )
    assert usr.check_session_valid("aaa") is False

    mocker.patch(
        "mcod.users.models.decode_jwt_token",
        return_value={"user": {"session_key": 1234}},
    )
    mocker.patch(
        "mcod.users.models.session_cache.get",
        return_value={
            "_auth_user_hash": usr.get_session_auth_hash(),
            "_auth_user_id": str(usr.id),
        },
    )
    mocker.patch("mcod.users.models.constant_time_compare", return_value=False)
    assert usr.check_session_valid("aaa") is False

    mocker.patch(
        "mcod.users.models.decode_jwt_token",
        return_value={"user": {"session_key": 1234}},
    )
    mocker.patch(
        "mcod.users.models.session_cache.get",
        return_value={
            "_auth_user_hash": usr.get_session_auth_hash(),
            "_auth_user_id": str(usr.id),
        },
    )
    mocker.patch("mcod.users.models.constant_time_compare", return_value=True)
    assert usr.check_session_valid("aaa") is True


def test_tokens(active_user):
    assert active_user.tokens.count() == 0

    email_token1 = active_user.email_validation_token
    password_reset_token1 = active_user.password_reset_token

    assert email_token1 != password_reset_token1
    assert active_user.tokens.count() == 2

    token_obj = Token.objects.get(token=email_token1)
    now = timezone.now()
    token_obj.expiration_date = now
    token_obj.save()
    assert token_obj.is_valid is False

    email_token2 = active_user.email_validation_token
    assert email_token1 != email_token2
    assert active_user.tokens.count() == 3

    email_token3 = active_user.email_validation_token
    assert email_token3 == email_token2
    assert active_user.tokens.count() == 3

    token = Token.objects.create(user=active_user, token_type=0)
    assert token.is_valid is True
    assert active_user.tokens.count() == 4

    email_token4 = active_user.email_validation_token
    assert token.token == email_token4
    assert email_token3 != email_token4

    exp_date = get_token_expiration_date().date()

    assert token.expiration_date.date() == exp_date


class TestLogin:

    def test_admin_can_login_to_admin_panel(self, admin):
        client = Client()
        response = client.get("/")
        assert response.status_code == 302
        assert response.url == "/login/?next=/"
        client.login(email=admin.email, password="12345.Abcde")
        response = client.get("/")
        assert response.status_code == 200

    def test_editor_can_login_to_admin_panel(self, active_editor):
        client = Client()
        response = client.get("/")
        assert response.status_code == 302
        assert response.url == "/login/?next=/"
        client.login(email=active_editor.email, password="12345.Abcde")
        response = client.get("/")
        assert response.status_code == 200

    def test_active_user_cant_login_to_admin_panel(self, active_user):
        client = Client()
        response = client.get("/")
        assert response.status_code == 302
        assert response.url == "/login/?next=/"
        client.login(email=active_user.email, password="12345.Abcde")
        response = client.get("/")
        assert response.status_code == 302


def test_user_manager_create_superuser():
    superuser = User.objects.create_superuser("superadmin@test.pl", "password")
    assert superuser.email == "superadmin@test.pl"
    assert superuser.is_staff
    assert superuser.is_superuser
    assert superuser.state == "active"
    assert str(superuser) == "superadmin@test.pl"


def test_user_soft_delete(active_user):
    u = active_user
    u.delete()
    assert u.is_removed is True
    assert User.objects.get(id=active_user.id)


def test_user_unsafe_delete(active_user):
    u = active_user
    u.delete(soft=False)
    with pytest.raises(ObjectDoesNotExist):
        User.objects.get(id=active_user.id)


def test__get_absolute_url_with_lang(active_user):
    test_url = "/test/path"
    with translation.override("pl"):
        assert active_user._get_absolute_url(test_url) == f"{settings.BASE_URL}/pl/test/path"


def test_last_logged_method_logging_by_form(client: TestClient, active_user: User):
    """Test if user has last_logged_method set to `formularz` when logged via form."""
    flush_sessions()
    client.simulate_post(
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
    active_user.refresh_from_db()
    assert active_user.last_logged_method == LoggingMethod.FORM.value


def test_last_logged_method_logging_by_wk(admin_user: User, test_user_pesel: str):
    """
    Test if user has last_logged_method attribute set to `WK` when logged via /idp endpoint.
    Simulate django admin WK login.
    """
    admin_user.pesel = test_user_pesel
    admin_user.save()
    with override_settings(USERS_TEST_LOGINGOVPL=True):
        login_gov_pl_data = dict(
            in_response_to=f"ID-3226742f-c93b-4647-b138-81b6ba8f631e-ADMIN-LOGIN-{admin_user.id}",
            first_name="Some",
            last_name="Name",
            dob="1234",
            pesel=test_user_pesel,
        )
        request = APIRequestFactory().post(reverse("idp"), data=login_gov_pl_data, format="json")

        acs_view = ACSView.as_view()
        acs_view(request)
        admin_user.refresh_from_db()
        assert admin_user.last_logged_method == LoggingMethod.WK.value


def test_last_logged_method_logging_by_wk_admin(admin_user: User, test_user_pesel: str):
    """
    Test if user has last_logged_method attribute set to `WK` when logged via /idp endpoint using portal type `ADMIN`.
    It's simulate a WK loging in django admin page.
    """
    admin_user.pesel = test_user_pesel
    admin_user.save()
    with override_settings(USERS_TEST_LOGINGOVPL=True):
        login_gov_pl_data = dict(
            in_response_to=f"ID-3226742f-c93b-4647-b138-81b6ba8f631e-ADMIN-LOGIN-{admin_user.id}",
            first_name="Some",
            last_name="Name",
            dob="1234",
            pesel=test_user_pesel,
        )
        url_reverse = reverse("logingovpl")
        url = f"{url_reverse}?portal=admin"
        request = APIRequestFactory().post(url, data=login_gov_pl_data, format="json")

        acs_view = ACSView.as_view()
        acs_view(request)

        admin_user.refresh_from_db()
        assert admin_user.last_logged_method == LoggingMethod.WK.value


def test_last_logged_method_logging_by_form_admin(admin_user: User, test_user_pesel: str):
    """
    Test if user has last_logged_method attribute set to `WK` when logged by form using portal type `ADMIN`.
    Simulates logging in django admin page by form.
    """
    client = Client()
    admin_user.pesel = test_user_pesel
    admin_user.save()

    password = "adminpassword123"
    admin_user.set_password(password)
    admin_user.save()

    # Prepare the login data as expected by the admin login form
    login_data = {
        "username": admin_user.email,  # Admin login uses 'username'
        "password": password,  # The known password
        "next": reverse("admin:index"),  # Redirect to admin dashboard after login
    }

    client.post(reverse("admin:login"), data=login_data)
    admin_user.refresh_from_db()

    assert admin_user.last_logged_method == LoggingMethod.FORM
