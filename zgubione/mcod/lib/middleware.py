import re

from django.contrib import messages
from django.db import connection
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _

from mcod import settings
from mcod.lib.jwt import get_auth_token


class PostgresConfMiddleware(MiddlewareMixin):
    def process_request(self, request, *args, **kwargs):
        if request.user.id:
            connection.cursor().execute(f'SET myapp.userid = "{request.user.id}"')


class APIAuthTokenMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        apiauthcookie = settings.API_TOKEN_COOKIE_NAME
        if apiauthcookie in request.COOKIES:
            if not request.user.is_authenticated:
                response.delete_cookie(
                    apiauthcookie,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    path=settings.SESSION_COOKIE_PATH,
                )
        else:
            if request.user.is_authenticated:
                token = get_auth_token(request.user, request.session.session_key)
                response.set_cookie(
                    apiauthcookie,
                    token,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    httponly=False,  # Make it readable for angular
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                    secure=settings.SESSION_COOKIE_SECURE,
                    path=settings.SESSION_COOKIE_PATH,
                    max_age=settings.JWT_EXPIRATION_DELTA,
                )

        return response


class ComplementUserDataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.COMPONENT == "admin" and request.user and not request.user.is_anonymous:
            if request.user.is_normal_staff and not request.user.has_complete_staff_data:
                allowed_paths = {
                    request.user.admin_change_url,
                    "/logout/",
                    "/pn-apps/stats/",
                    r"/pn-apps/charts/slot-\d+.png",
                }
                allowed_paths_pattern = "|".join(allowed_paths)
                if not re.match(allowed_paths_pattern, request.path):
                    messages.add_message(
                        request,
                        messages.ERROR,
                        _("Your account data is incomplete. Full name and phone number must be given"),
                    )
                    return redirect(request.user.admin_change_url)
        return self.get_response(request)
