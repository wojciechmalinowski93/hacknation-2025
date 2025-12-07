import json

from discourse_django_sso.utils import SSOClientUtils
from discourse_django_sso_test_project.urls import nonce_service
from django.conf import settings
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.http import limited_parse_qsl, urlquote_plus
from pytest_bdd import given, parsers, then, when

from mcod.discourse.tests.utils import discourse_response_mocker
from mcod.discourse.utils import ForumProducerUtils
from mcod.users.factories import AdminFactory


@when("User is logging in to forum")
@override_settings(DISCOURSE_FORUM_ENABLED=True)
def log_in_to_forum(context):
    client = Client()
    with discourse_response_mocker(context.user) as mocked_urls:
        sso_url = mocked_urls["mock_sso_url"]
        params = urlquote_plus(sso_url.split("?")[1])
        url_path = "{}?{}".format(reverse("discourse-login"), f"next=/discourse/connect/start?{params}")
        response = client.post(url_path, data=getattr(context, "obj", None), follow=True)
    context.response = response


@when(parsers.parse("forum request posted data is {req_post_data}"))
def forum_request_post_data(context, req_post_data):
    context.obj = json.loads(req_post_data)


@given(parsers.parse("admin with forum access and data{data_str}"))
def forum_admin_for_data(context, data_str):
    data = json.loads(data_str)
    data["state"] = "active"
    data["discourse_user_name"] = "activeAdmin"
    data["discourse_api_key"] = "123456"
    admin_user = AdminFactory(**data)
    context.user = admin_user


@given(parsers.parse("admin without forum access and data{data_str}"))
def forum_admin_without_access_for_data(context, data_str):
    data = json.loads(data_str)
    data["state"] = "active"
    admin_user = AdminFactory(**data)
    context.user = admin_user


@given(parsers.parse("inactive forum admin with data {data_str}"))
def inactive_admin_with_data(context, data_str):
    data = json.loads(data_str)
    data["is_active"] = False
    data["discourse_user_name"] = "activeAdmin"
    data["discourse_api_key"] = "123456"
    admin_user = AdminFactory(**data)
    context.user = admin_user


@given(parsers.parse("forum admin with status {user_status}"))
def admin_with_status_and_data(context, user_status):
    data = {
        "state": user_status,
        "discourse_user_name": "activeAdmin",
        "discourse_api_key": "123456",
        "email": "activeAdmin@dane.gov.pl",
        "password": "12345.Abcde",
    }
    admin_user = AdminFactory(**data)
    context.user = admin_user


@then("user is redirected to external forum url with sso login")
def sso_service_successful_login(context):
    response = context.response
    user = context.user
    client_util = SSOClientUtils(settings.DISCOURSE_SSO_SECRET, settings.DISCOURSE_SSO_REDIRECT)
    nonce_val = nonce_service.generate_nonce()
    sso_url = client_util.generate_sso_url(nonce_val, False)
    parsed_qsl = limited_parse_qsl(sso_url.split("?")[1])
    gen = ForumProducerUtils(
        sso_key=settings.DISCOURSE_SSO_SECRET,
        consumer_url=settings.DISCOURSE_SSO_REDIRECT,
        user=user,
        sso=parsed_qsl[0][1],
        sig=parsed_qsl[1][1],
    )
    final_session_payload = gen.get_signed_payload()
    sso_login_url = gen.get_sso_redirect(final_session_payload)
    assert len(response.redirect_chain) == 2
    assert response.redirect_chain[1][0] == sso_login_url


@then("login form error about no access is displayed")
def logged_in_user_has_no_access_to_forum(context):
    assert "Tylko administratorzy i pełnomocnicy mają dostęp do forum" in context.response.content.decode("utf-8")


@then("login form error about inactive account is displayed")
def logged_in_user_has_inactive_account(context):
    assert "Brak uprawnień do panelu administratora" in context.response.content.decode("utf-8")


@then(parsers.parse("login form error {status_error} is displayed"))
def status_error_is_displayed(context, status_error):
    assert status_error in context.response.content.decode("utf-8")
