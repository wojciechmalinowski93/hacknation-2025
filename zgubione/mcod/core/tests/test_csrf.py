import json
from unittest import mock
from unittest.mock import Mock

import falcon
import pytest
from django.utils.translation import gettext as _
from falcon.util import http_cookies
from pytest_bdd import scenario

from mcod import settings
from mcod.core.api.middlewares import CsrfMiddleware
from mcod.core.csrf import (
    _sanitize_token,
    generate_csrf_token,
    get_new_csrf_string,
    unsalt_cipher_token,
)


@scenario("features/csrf.feature", "Test cipher salting identity.")
def test_cipher_salting_identity():
    pass


@scenario("features/csrf.feature", "Unsalting a token returns secret.")
def test_unsalting():
    pass


@pytest.mark.parametrize(
    "input_",
    [
        "N72jrQ4iMT5iBBaXxbwGT8n9Tplx9zJv",
        "6XYwZ7sqhgU6f7TRmCb7WvKmtXEUoL21N72jrQ4iMT5iBBaXxbwGT8n9Tplx9zJv",
        "abc",
        "",
        pytest.param(None, marks=pytest.mark.xfail),
    ],
)
def test_sanitized_token_length(input_):
    assert len(_sanitize_token(input_)) == 64


def test_generates_different_but_equivalent_tokens():
    secret = get_new_csrf_string()
    n = 10
    tokens = {generate_csrf_token(secret) for _ in range(n)}
    assert len(tokens) == n and len({unsalt_cipher_token(token) for token in tokens}) == 1


@mock.patch("mcod.settings.ENABLE_CSRF", True)
@mock.patch("mcod.settings.DEBUG", False)
@pytest.mark.parametrize(
    "cookie_value,header_value,should_return_error",
    [
        # Non-anonymous tests (use custom session secret)
        # happy path
        (
            "8N3I8Ki2ku8n4nwehWLriTcdx918xJ77MUsf7eF9s8FjZJc8ap5RIrqipEOhS8vv",
            "8N3I8Ki2ku8n4nwehWLriTcdx918xJ77MUsf7eF9s8FjZJc8ap5RIrqipEOhS8vv",
            False,
        ),
        # wrong cookie value
        (
            "k43DAZJaKsyQnnt0N3CuyNpYaLwXOWTw6u3uMp4ctwSALaLp7g6vcs6bMJ9fq6Sh",
            "q43DAZJaKsyQnnt0N3CuyNpYaLwXOWTw6u3uMp4ctwSALaLp7g6vcs6bMJ9fq6Sh",
            True,
        ),
        # invalid cookie value
        (
            "+++===%&*^(^$%7686754VGVUIJHVght",
            "k43DAZJaKsyQnnt0N3CuyNpYaLwXOWTw6u3uMp4ctwSALaLp7g6vcs6bMJ9fq6Sh",
            True,
        ),
        (
            "k43DAZJaKsyQnnt0N3CuyNpYaLwXOWTw6u3uMp4ctwSALaLp7g6vcs6bMJ9fq6Sh",
            "+++===%&*^(^$%7686754VGVUIJHVght",
            True,
        ),
        # empty cookie value
        (
            None,
            None,
            True,
        ),
        # empty cookie value - empty string version
        (
            "",
            "",
            True,
        ),
    ],
)
def test_csrf_middleware(cookie_value, header_value, should_return_error):
    default_session_secret = "Default0secretN6KnTyVlxyy9RudhRy"
    good_status = falcon.HTTP_200
    good_body = json.dumps(
        {
            "data": [
                {"type": "message", "id": 1, "attributes": {"title": "Hello, World!"}},
            ]
        }
    )
    bad_status = falcon.HTTP_403
    bad_body = json.dumps(
        {
            "errors": [
                {
                    "title": "CSRF error",
                    "detail": _("CSRF token missing or incorrect."),
                    "status": "Forbidden",
                    "code": falcon.HTTP_403,
                },
            ],
        }
    )

    req, resp, resource, params = Mock(), Mock(), Mock(), Mock()
    req.cookies = {
        settings.API_CSRF_COOKIE_NAME: cookie_value,
    }
    req.headers = {
        settings.API_CSRF_HEADER_NAME: header_value,
    }
    req.method = "POST"  # testing CSRF -- need to be unsafe method
    resp.cookies = {}
    resp.headers = {}
    resp.complete = False
    resp.status = good_status
    resp.text = good_body
    resource.csrf_exempt = False

    middleware = CsrfMiddleware()
    middleware.default_secret = default_session_secret
    middleware.process_resource(req, resp, resource, params)
    if should_return_error:
        assert resp.status == bad_status, "response status should be %s, is %s" % (
            bad_status,
            resp.status,
        )
        assert resp.text == bad_body, "response body should be a proper error message"
        assert resp.complete, "response should be complete in case of error"
    else:
        assert resp.status == good_status
        assert resp.text == good_body
        assert not resp.complete

    middleware.process_response(req, resp, None, None)

    resp.append_header.assert_called()
    cookie_domains = set()
    for call_args, call_kwargs in resp.append_header.call_args_list:
        assert call_args[0] == "Set-Cookie"

        cookies = http_cookies.SimpleCookie(call_args[1])
        assert cookies.get("mcod_csrf_token", None) is not None

        cookie = cookies["mcod_csrf_token"]
        new_cookie_value = cookie.value
        assert new_cookie_value != cookie_value, "server should assign a new CSRF token for every response"
        assert cookie["path"] == "/"
        assert (not settings.SESSION_COOKIE_SECURE and not cookie["secure"]) or (
            settings.SESSION_COOKIE_SECURE and cookie["secure"]
        )
        cookie_domain = cookie["domain"]
        assert cookie_domain in settings.API_CSRF_COOKIE_DOMAINS
        cookie_domains.add(cookie_domain)
        assert not cookie["httponly"]

    assert cookie_domains == set(settings.API_CSRF_COOKIE_DOMAINS)
