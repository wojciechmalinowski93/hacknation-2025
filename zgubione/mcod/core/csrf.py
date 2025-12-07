"""
Cross Site Request Forgery Middleware.

This module provides a middleware that implements protection
against request forgeries from other sites.
"""

import re
import secrets

from mcod import settings


def get_new_csrf_string():
    return "".join([secrets.choice(settings.CSRF_ALLOWED_CHARS) for _ in range(settings.CSRF_SECRET_LENGTH)])


def salt_cipher_secret(secret: str):
    """
    Given a secret (assumed to be a string of CSRF_ALLOWED_CHARS), generate a
    token by adding a salt and using it to encrypt the secret.

    Secret can only be of length from 1 to CSRF_SECRET_LENGTH characters long.
    """
    assert len(secret) == settings.CSRF_SECRET_LENGTH, len(secret)
    salt = get_new_csrf_string()
    chars = settings.CSRF_ALLOWED_CHARS
    pairs = zip((chars.index(x) for x in secret), (chars.index(x) for x in salt))
    cipher = "".join(chars[(x + y) % len(chars)] for x, y in pairs)
    return salt + cipher


def unsalt_cipher_token(token: str):
    """
    Given a token (assumed to be a string of CSRF_ALLOWED_CHARS, of length
    CSRF_TOKEN_LENGTH, and that its first half is a salt), use it to decrypt
    the second half to produce the original secret.
    """
    salt = token[: settings.CSRF_SECRET_LENGTH]
    token = token[settings.CSRF_SECRET_LENGTH :]
    chars = settings.CSRF_ALLOWED_CHARS
    pairs = zip((chars.index(x) for x in token), (chars.index(x) for x in salt))
    secret = "".join(chars[x - y] for x, y in pairs)  # Note negative values are ok
    return secret


def generate_csrf_token(session_secret: str = None):
    return salt_cipher_secret(session_secret or get_new_csrf_string())


def _sanitize_token(token):
    """
    You can pass either token or secret here and the whole token (with salt) will be returned.
    If passed invalid value of token (not alphanumeric), will generate new token.
    """
    # Allow only ASCII alphanumerics
    if re.search("[^a-zA-Z0-9]", token):
        return generate_csrf_token()
    elif len(token) == settings.CSRF_TOKEN_LENGTH:
        return token
    elif len(token) == settings.CSRF_SECRET_LENGTH:
        # Older Django versions set cookies to values of CSRF_SECRET_LENGTH
        # alphanumeric characters. For backwards compatibility, accept
        # such values as unsalted secrets.
        # It's easier to salt here and be consistent later, rather than add
        # different code paths in the checks, although that might be a tad more
        # efficient.
        return salt_cipher_secret(token)
    return generate_csrf_token()


def compare_salted_tokens(token1: str, token2: str):
    """
    Assume both arguments are sanitized -- that is, strings of
    length CSRF_TOKEN_LENGTH, all CSRF_ALLOWED_CHARS.
    """
    return secrets.compare_digest(
        unsalt_cipher_token(token1),
        unsalt_cipher_token(token2),
    )
