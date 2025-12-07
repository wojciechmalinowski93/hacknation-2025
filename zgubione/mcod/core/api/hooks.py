import json
import uuid
from importlib import import_module

import falcon
from constance import config
from django.contrib.auth import get_user
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.utils.translation import gettext_lazy as _
from django_redis import get_redis_connection

from mcod import settings
from mcod.lib.jwt import decode_jwt_token

session_store = import_module(settings.SESSION_ENGINE).SessionStore

role_properties = {
    "admin": "is_superuser",
    "lod_admin": "is_labs_admin",
    "aod_admin": "is_academy_admin",
    "official": "is_official",
    "editor": "is_staff",
    "user": "is_active",
    "agent": "agent",
}


def check_roles(user, roles):
    if not any(getattr(user, role_properties[role]) for role in roles):
        raise falcon.HTTPForbidden(
            title="403 Forbidden",
            description=_("Additional permissions are required!"),
            code="additional_perms_required",
        )


def get_expired_token_description():
    return _(
        "<b>Your account activation link has expired.</b><br>If you want to receive a new activation link, please "
        'contact us: <a href="mailto:%(email)s">%(email)s</a>'
    ) % {"email": config.CONTACT_MAIL}


def get_user_pending_description():
    return _(
        "<b>Your account has not been activated.</b><br>We sent an email to the e-mail address you used during "
        "registration with a link to activate your account.<br>If you have not received an e-mail from us, or "
        'the activation link has expired, please contact us: <a href="mailto:%(email)s">%(email)s</a>'
    ) % {"email": config.CONTACT_MAIL}


def login_required(req, resp, resource, params, roles=("user",), save=False, restore_from=None):  # noqa: C901
    if restore_from:
        if restore_from not in params:
            raise falcon.HTTPUnauthorized(
                title="401 Unauthorized",
                description=_("Missing token"),
                code="token_missing",
            )
        redis_connection = get_redis_connection()
        _key = params[restore_from]
        if isinstance(_key, uuid.UUID):
            _key = _key.hex
        user_payload = redis_connection.get(_key)
        try:
            user_payload = json.loads(user_payload)
        except Exception:
            user_payload = {}
    else:
        auth_header = req.get_header("Authorization")

        if not auth_header:
            raise falcon.HTTPUnauthorized(
                title="401 Unauthorized",
                description=_("Missing authorization header"),
                code="token_missing",
            )
        user_payload = decode_jwt_token(auth_header)["user"]

    if not {"session_key", "email"} <= set(user_payload):
        raise falcon.HTTPUnauthorized(
            title="401 Unauthorized",
            description=(_("Invalid token") if restore_from else _("Invalid authorization header")),
            code="token_error",
        )
    req.session = session_store(user_payload["session_key"])
    user = get_user(req)
    if not user or (hasattr(user, "is_anonymous") and user.is_anonymous):
        raise falcon.HTTPUnauthorized(
            title="401 Unauthorized",
            description=_("Incorrect login data"),
            code="authentication_error",
        )
    if user.email != user_payload["email"]:
        raise falcon.HTTPUnauthorized(
            title="401 Unauthorized",
            description=_("Incorrect login data"),
            code="authentication_error",
        )
    if user.state != "active":
        if user.state not in settings.USER_STATE_LIST or user.state == "deleted":
            raise falcon.HTTPUnauthorized(
                title="401 Unauthorized",
                description=_("Cannot login"),
                code="account_unavailable",
            )

        if user.state in ("draft", "blocked"):
            raise falcon.HTTPUnauthorized(
                title="401 Unauthorized",
                description=_("Account is blocked"),
                code="account_unavailable",
            )

        if user.state == "pending":
            raise falcon.HTTPForbidden(
                title="403 Forbidden",
                description=get_user_pending_description(),
                code="account_inactive",
            )

    check_roles(user, roles)

    req.user = user
    connection.cursor().execute(f'SET myapp.userid = "{user.id}"')
    if save:
        redis_connection = get_redis_connection()
        _token = uuid.uuid4().hex
        user_payload = {
            "session_key": req.session.session_key,
            "email": req.user.email,
        }
        redis_connection.set(_token, json.dumps(user_payload), ex=60)
        resp._token = _token


def login_optional(req, resp, resource, *args, **kwargs):
    auth_header = req.get_header("Authorization")
    if not auth_header:
        req.user = AnonymousUser()
        return

    try:
        user_payload = ()
        user_payload = decode_jwt_token(auth_header)["user"]
    except Exception:
        pass

    if not {"session_key", "email"} <= set(user_payload):
        req.user = AnonymousUser()
        return

    req.session = session_store(user_payload["session_key"])
    user = get_user(req)
    if user != AnonymousUser() and any((not user, user.email != user_payload["email"], user.state != "active")):
        user = AnonymousUser()
    req.user = user
    if user.id:
        connection.cursor().execute(f'SET myapp.userid = "{user.id}"')
