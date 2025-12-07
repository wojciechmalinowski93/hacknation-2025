import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import elasticapm
import elasticapm.instrumentation.control
import falcon
import sentry_sdk
from accept_types import get_best_match
from django.apps import apps
from django.db import OperationalError, ProgrammingError, close_old_connections, connection
from django.utils.http import is_same_domain
from django.utils.translation import activate, gettext_lazy as _
from django.utils.translation.trans_real import (
    get_supported_language_variant,
    language_code_re,
    parse_accept_lang_header,
)
from django_redis import get_redis_connection
from elasticapm.conf import constants
from elasticapm.utils.disttracing import TraceParent
from falcon import Request, Response
from falcon_caching.middleware import Middleware as BaseFalconCacheMiddleware
from falcon_caching.options import HttpMethods

from mcod import settings
from mcod.core.api.apm import get_data_from_request, get_data_from_response
from mcod.core.api.versions import VERSIONS
from mcod.core.csrf import _sanitize_token, compare_salted_tokens, generate_csrf_token
from mcod.core.db.managers import QueryLogger
from mcod.core.metrics import (
    API_DB_QUERY_TIME_HISTOGRAM,
    API_ERROR_COUNT,
    API_REQUEST_COUNT,
    API_REQUEST_LATENCY_HISTOGRAM,
)
from mcod.core.utils import falcon_set_cookie, jsonapi_validator, route_to_name
from mcod.counters.lib import Counter
from mcod.lib.encoders import DateTimeToISOEncoder
from mcod.unleash import is_enabled

logger = logging.getLogger("mcod-api")

_DECORABLE_METHOD_NAME = re.compile(r"^on_({})(_\w+)?$".format("|".join(method.lower() for method in falcon.COMBINED_METHODS)))


SAFE_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")
REASON_NO_REFERER = _("Referer checking failed - no Referer.")
REASON_BAD_REFERER = _("Referer checking failed - %s does not match any trusted origins.")
REASON_MALFORMED_REFERER = _("Referer checking failed - Referer is malformed.")
REASON_INSECURE_REFERER = _("Referer checking failed - Referer is insecure while host is secure.")


class DjangoDBConnectionMiddleware:
    def process_request(self, req: Request, resp: Response):
        close_old_connections()

    def process_response(self, req: Request, resp: Response, resource: Any, req_succeeded: bool):
        close_old_connections()


class PrometheusMiddleware:
    """
    Falcon middleware for collecting Prometheus metrics on request latency,
    request count, error count, and DB query time.
    """

    def process_request(self, req: Request, resp: Response) -> None:
        """Records the start time of the request to calculate latency later."""
        req.context["start_time"] = time.perf_counter()
        ql = QueryLogger()
        req.context["query_logger"] = ql
        connection.execute_wrapper(ql)

    def process_response(self, req: Request, resp: Response, resource: Any, req_succeeded: bool) -> None:
        """Records various Prometheus metrics after the request is processed."""
        method = req.method
        endpoint = req.path
        status_code = str(resp.status_code)

        # Record request latency
        try:
            end = time.perf_counter()
            start = req.context["start_time"]
            latency = end - start
            API_REQUEST_LATENCY_HISTOGRAM.labels(method, endpoint).observe(latency)
        except KeyError as err:
            logger.error(f"start_time couldn't be fetched from context {err}")
            sentry_sdk.api.capture_exception(err)

        # Record request count
        API_REQUEST_COUNT.labels(method, endpoint, status_code).inc()

        # Count 5xx errors or failed requests
        if not req_succeeded or resp.status_code >= 500:
            API_ERROR_COUNT.labels(method, endpoint, status_code).inc()

        ql: QueryLogger = req.context.get("query_logger")
        if ql is not None:
            try:
                duration = sum(float(q["duration"]) for q in ql.queries)
                API_DB_QUERY_TIME_HISTOGRAM.labels(path=endpoint or "unknown").observe(duration)
            except KeyError as err:
                logger.error(f"Couldn't get `duration` attribute from ql.queries. {err}")
                sentry_sdk.api.capture_exception(err)
            except (ProgrammingError, OperationalError, AttributeError) as err:
                logger.error(err)
                sentry_sdk.api.capture_exception(err)

            try:
                connection.execute_wrappers.remove(ql)
            except ValueError:
                logger.warning("QueryLogger was not found in execute_wrappers during cleanup.")


class SearchHistoryMiddleware:
    def process_response(self, req: Request, resp: Response, resource: Any, req_succeeded: bool):
        if hasattr(req, "user") and req.user.is_authenticated and req.path.endswith(settings.SEARCH_PATH) and req.params.get("q"):
            con = get_redis_connection()
            key = f"search_history_user_{req.user.id}"
            con.lpush(key, req.url)


class ApiVersionMiddleware:
    def process_request(self, req: Request, resp: Response):
        current_version = max(VERSIONS)
        version = req.headers.get("X-API-VERSION", str(current_version))
        try:
            if version not in VERSIONS:
                raise ValueError
        except ValueError:
            raise falcon.HTTPBadRequest(
                title="Unsupported version",
                description="Version provided in X-API-VERSION header is invalid.",
            )

        req.api_version = version

    def process_resource(self, req, resp, resource, params):
        # Version from path should override previous value
        version = params.get("api_version") or None
        if version:
            try:
                if version not in VERSIONS:
                    raise ValueError
            except ValueError:
                raise falcon.HTTPBadRequest(title="Unsupported version", description="Version provided in path is invalid.")

            req.api_version = version

    def process_response(self, req: Request, resp: Response, resource: Any, req_succeeded: bool):
        version = getattr(req, "api_version", max(VERSIONS))
        resp.append_header("x-api-version", version)


class FalconCacheMiddleware(BaseFalconCacheMiddleware):

    def process_resource(self, req, resp, resource, params):
        """Body of the method is almost all moved from parent class."""

        if not is_enabled("S66_falcon_caching_operate.be"):
            return

        # do not cache response for methods POST, PATCH, PUT and DELETE - regardless of set caching strategy
        if req.method.upper() in [
            HttpMethods.POST,
            HttpMethods.PATCH,
            HttpMethods.PUT,
            HttpMethods.DELETE,
        ]:
            return

        key = self.generate_cache_key(req)
        data = self.cache.get(key)

        if data:
            resp.media = self.deserialize(data)
            resp.status = falcon.HTTP_200
            req.context.cached = True
            resp.complete = True

    def deserialize(self, data):
        return data

    def serialize(self, req, resp, resource):
        return resp.media

    @staticmethod
    def generate_cache_key(req: falcon.request.Request, method: str = None) -> str:
        """Custom cache key method to take into account language from req.params (query string).
        Args:
            method: HTTP verb

        Returns: string to cache response under
        """
        default_key = BaseFalconCacheMiddleware.generate_cache_key(req, method)
        default_key = f"{default_key}:{req.query_string}"
        lang = req.params.get("lang", "pl")
        return f"{default_key}:{lang}"


class LocaleMiddleware:
    def get_language_from_header(self, header):
        for accept_lang, unused in parse_accept_lang_header(header):
            if accept_lang == "*":
                break

            if not language_code_re.search(accept_lang):
                continue

            try:
                return get_supported_language_variant(accept_lang)
            except LookupError:
                continue

        try:
            return get_supported_language_variant(settings.LANGUAGE_CODE)
        except LookupError:
            return settings.LANGUAGE_CODE

    def process_request(self, req: Request, resp: Response):
        lang = req.params.get("lang", None)
        if not lang:
            accept_header = req.headers.get("ACCEPT-LANGUAGE", "")
            lang = self.get_language_from_header(accept_header)
        req.language = lang.lower()
        activate(req.language)

    def process_response(self, req, resp, resource, params):
        resp.append_header("Content-Language", req.language)


class CounterMiddleware:

    def process_response(self, req: Request, resp: Response, resource: Any, req_succeeded: bool):
        try:
            view, ident = req.relative_uri.split("?")[0].split("/")[-2:]
            obj_id = int(str(ident).split(",", 1)[0])
        except (ValueError, IndexError):
            view, obj_id = None, None

        if resp.status == falcon.HTTP_200 and view:
            try:
                model = apps.get_model(view, view[:-1])
                label = model._meta.label
                if label in settings.COUNTED_MODELS:
                    Counter().incr_view_count(label, obj_id)
            except LookupError:
                pass


class DebugMiddleware:
    def process_request(self, request: Request, response: Response):

        response.context.debug = True if request.params.get("debug") == "yes" else False
        if response.context.debug:
            request.context.start_time = datetime.now()

    def process_response(self, request, response, resource, req_succeeded):
        if response.context.debug:
            duration = (datetime.now() - request.context.start_time).microseconds
            response_body = response.media
            valid, validated, errors = "n/a", None, None
            if response.status == falcon.HTTP_200:
                valid, validated, errors = jsonapi_validator(response_body)

            body = {
                "status": response.status,
                "valid": "ok" if valid else "error",
                "duration": "{} ms".format(duration / 1000),
                "query": getattr(response.context, "query", {}),
                "errors": errors or [],
                "body": response_body,
                "data": validated,
            }

            response.text = json.dumps(body, cls=DateTimeToISOEncoder)
            response.status = falcon.HTTP_200
            response.content_type = "application/json"


class ContentTypeMiddleware:
    def process_request(self, req: Request, resp: Response):
        allowed_mime_types = [
            "application/vnd.api+json",
            "application/vnd.api+json; ext=bulk",
        ] + list(set(settings.RDF_FORMAT_TO_MIMETYPE.values()))
        resp.content_type = get_best_match(req.accept, allowed_mime_types)


class TraceMiddleware:
    def __init__(self, apm_client):
        self.client = apm_client

    def process_request(self, req: Request, resp: Response):
        if self.client and req.user_agent not in ("mcod-heartbeat", "mcod-internal"):
            if constants.TRACEPARENT_HEADER_NAME in req.headers:
                trace_parent = TraceParent.from_string(req.headers[constants.TRACEPARENT_HEADER_NAME])
            else:
                trace_parent = None

            self.client.begin_transaction("request", trace_parent=trace_parent)

    def process_response(self, req: Request, resp: Response, resource: Any, req_succeeded: bool):
        if self.client and req.user_agent != "mcod-heartbeat":
            rule = route_to_name(req.uri_template, method=req.method)
            elasticapm.set_context(
                lambda: get_data_from_request(
                    req,
                    capture_body=self.client.config.capture_body in ("transactions", "all"),
                    capture_headers=self.client.config.capture_headers,
                ),
                "request",
            )
            elasticapm.set_context(
                lambda: get_data_from_response(resp, capture_headers=self.client.config.capture_headers),
                "response",
            )

            result = resp.status
            elasticapm.set_transaction_name(rule, override=False)
            if hasattr(req, "user") and req.user.is_authenticated:
                elasticapm.set_user_context(email=req.user.email, user_id=req.user.id)

            elasticapm.set_transaction_result(result, override=False)
            # Instead of calling end_transaction here, we defer the call until the response is closed.
            # This ensures that we capture things that happen until the WSGI server closes the response.
            self.client.end_transaction(rule, result)


class CsrfMiddleware:
    """
    Require a present and correct CSRF token for not safe
    requests that have a CSRF cookie, and set an outgoing CSRF cookie.
    """

    def process_resource(self, request, response, resource, params):
        if request.method not in SAFE_METHODS and not getattr(resource, "csrf_exempt", False):
            self.check_token(request, response)

    def process_response(self, request: Request, response: Response, resource: Any, req_succeeded: bool):
        new_token = generate_csrf_token()
        # Set the CSRF cookie even if it's already set, so we renew
        # the expiry timer.
        self.set_token(response, new_token)

    def check_token(self, request: Request, response: Response) -> None:
        """
        Check that token sent in cookies equals to one recorded in header.
        If the check fails, the response gets completed with a correct error.
        """
        header_csrf_token = self.get_token_from_header(request)
        cookie_csrf_token = self.get_token_from_cookie(request)

        referrer_reason = self.check_referrer(request)
        if referrer_reason:
            return self.reject(response, referrer_reason)

        if not compare_salted_tokens(cookie_csrf_token, header_csrf_token):
            return self.reject(response, _("CSRF token missing or incorrect."))

    @staticmethod
    def set_token(response: Response, salted_token: str) -> None:
        """We're setting multiple cookies to support debugging on localhost."""
        response.set_header(settings.API_CSRF_HEADER_NAME, salted_token)
        for cookie_domain in settings.API_CSRF_COOKIE_DOMAINS:
            falcon_set_cookie(
                response,
                settings.API_CSRF_COOKIE_NAME,
                salted_token,
                same_site=settings.SESSION_COOKIE_SAMESITE,
                path=settings.SESSION_COOKIE_PATH,
                secure=settings.SESSION_COOKIE_SECURE,
                http_only=False,
                domain=cookie_domain,
            )
        # Set the Vary header since content varies with the CSRF cookie.
        vary_val = response.headers.get("Vary")
        if not vary_val:
            vary_val = "Cookie"
        elif "Cookie" not in vary_val:
            vary_val = f"{vary_val}, Cookie"

        response.set_header("Vary", vary_val)

    @staticmethod
    def get_token_from_header(request: Request) -> str:
        return _sanitize_token(request.headers.get(settings.API_CSRF_HEADER_NAME) or "")

    @staticmethod
    def get_token_from_cookie(request: Request) -> str:
        cookie_token = request.cookies.get(settings.API_CSRF_COOKIE_NAME) or ""

        if cookie_token:
            cookie_token = cookie_token.split()[0]
        else:
            cookie_token = ""

        return _sanitize_token(cookie_token)

    @staticmethod
    def reject(response: Response, reason: str) -> None:
        """
        Complete request handling pipeline with an appropriate error.
        """
        http_status = falcon.HTTP_403
        response.text = json.dumps(
            {
                "errors": [
                    {
                        "title": "CSRF error",
                        "detail": str(reason),
                        "status": "Forbidden",
                        "code": http_status,
                    },
                ],
            }
        )
        response.status = http_status
        response.complete = True

    @staticmethod
    def check_referrer(request) -> Optional[str]:
        """
        Returns None if the check is successful, or a reason to reject the request.

        Suppose user visits http://example.com/
        An active network attacker (man-in-the-middle, MITM) sends a
        POST form that targets https://example.com/detonate-bomb/ and
        submits it via JavaScript.

        The attacker will need to provide a CSRF cookie and token, but
        that's no problem for a MITM and the session-independent
        secret we're using. So the MITM can circumvent the CSRF
        protection. This is true for any HTTP connection, but anyone
        using HTTPS expects better! For this reason, for
        https://example.com/ we need additional protection that treats
        http://example.com/ as completely untrusted. Under HTTPS,
        Barth et al. found that the Referer header is missing for
        same-domain requests in only about 0.2% of cases or less, so
        we can use strict Referer checking.
        """

        if request.scheme != "https":
            return

        referer = request.headers.get("Referrer")
        if referer is None:
            return REASON_NO_REFERER

        referer = urlparse(referer)

        # Make sure we have a valid URL for Referer.
        if "" in (referer.scheme, referer.netloc):
            return REASON_MALFORMED_REFERER

        # Ensure that our Referer is also secure. (if we ourselves use HTTPS)
        if referer.scheme != "https" and request.scheme == "https":
            return REASON_INSECURE_REFERER

        # If there isn't a CSRF_COOKIE_DOMAIN, require an exact match
        # match on host:port. If not, obey the cookie rules (or those
        # for the session cookie, if CSRF_USE_SESSIONS).
        good_referer = settings.SESSION_COOKIE_DOMAIN  # using django's var because it suits us
        if good_referer is not None:
            server_port = request.port
            if server_port not in ("443", "80"):
                good_referer = "%s:%s" % (good_referer, server_port)
        else:
            good_referer = request.host

        # Create a list of all acceptable HTTP referers, including the
        # current host if it's permitted by ALLOWED_HOSTS.
        good_hosts = list(settings.API_CSRF_TRUSTED_ORIGINS)
        if good_referer is not None:
            good_hosts.append(good_referer)

        if not any(is_same_domain(referer.netloc, host) for host in good_hosts):
            reason = REASON_BAD_REFERER % referer.geturl()
            return reason
