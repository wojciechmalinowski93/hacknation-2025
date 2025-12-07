from collections import namedtuple
from datetime import datetime, timedelta

import falcon
import jwt
from django.utils.translation import gettext_lazy as _

from mcod import settings
from mcod.lib.encoders import DateTimeToISOEncoder

ValidationResult = namedtuple("ValidationResult", "is_valid, data")


def is_token_valid(auth_header) -> ValidationResult:
    """
    Token validation with specified conditions. Returns true if token is valid and data
    which is an error response or a token itself.
    """
    if not auth_header:
        return ValidationResult(False, "Missing Authorization Header")

    parts = auth_header.split()

    if parts[0].lower() != settings.JWT_HEADER_PREFIX.lower():
        return ValidationResult(False, "Invalid Authorization Header")
    elif len(parts) == 1:
        return ValidationResult(False, "Invalid Authorization Header: Token Missing")
    elif len(parts) > 2:
        return ValidationResult(False, "Invalid Authorization Header: Contains extra content")

    return ValidationResult(True, parts[1])


def parse_auth_token(auth_header: str) -> str:
    """Validate token and return parsed token or Falcon HTTPUnauthorized exception."""
    token_validation = is_token_valid(auth_header)
    if not token_validation.is_valid:
        raise falcon.HTTPUnauthorized(
            title="401 Unauthorized",
            description=_(token_validation.data),
            code="token_error",
        )

    return token_validation.data


def decode_token(auth_header: str, parse=True) -> dict:
    """
    Decode a JWT token and return parsed token. Token can be validated directly from headers with the
    name of the token kind (for example Bearer), or directly from a string.
    """
    if parse:
        token = parse_auth_token(auth_header=auth_header)
    else:
        token = auth_header

    options = dict(("verify_" + claim, True) for claim in settings.JWT_VERIFY_CLAIMS)

    options.update(dict(("require_" + claim, True) for claim in settings.JWT_REQUIRED_CLAIMS))

    payload = jwt.decode(
        jwt=token,
        key=settings.JWT_SECRET_KEY,
        options=options,
        algorithms=settings.JWT_ALGORITHMS,
        leeway=settings.JWT_LEEWAY,
    )

    return payload


def decode_jwt_token(auth_header: str) -> dict:
    """JWT token decoding."""
    try:
        payload = decode_token(auth_header=auth_header)
    except jwt.InvalidTokenError as exc:
        raise falcon.HTTPUnauthorized(title="401 Unauthorized", description=str(exc), code="token_error")
    return payload


def get_auth_header(user, session_key, now=None, exp_delta=None):
    auth_token = get_auth_token(user, session_key, now=now, exp_delta=exp_delta)

    return f"{settings.JWT_HEADER_PREFIX} {auth_token}"


def get_auth_token(user, session_key, now=None, exp_delta=None):
    if not now:
        now = datetime.utcnow()

    discourse_api_key = user.discourse_api_key if user.has_access_to_forum else None
    discourse_user_name = user.discourse_user_name if user.has_access_to_forum else None

    payload = {
        "user": {
            "session_key": session_key,
            "email": user.email,
            "roles": user.system_roles,
            "discourse_user_name": discourse_user_name,
            "discourse_api_key": discourse_api_key,
        }
    }

    exp_delta = exp_delta if exp_delta else settings.JWT_EXPIRATION_DELTA

    if "iat" in settings.JWT_VERIFY_CLAIMS:
        payload["iat"] = now

    if "nbf" in settings.JWT_VERIFY_CLAIMS:
        payload["nbf"] = now + timedelta(seconds=settings.JWT_LEEWAY)

    if "exp" in settings.JWT_VERIFY_CLAIMS:
        payload["exp"] = now + timedelta(seconds=exp_delta)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, json_encoder=DateTimeToISOEncoder).decode("utf-8")
