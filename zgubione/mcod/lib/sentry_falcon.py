"""
Sentry integration for Falcon 3.0.1 as current Sentry version only supports up to Falcon 2.0.
Based on https://github.com/getsentry/sentry-python/issues/643#issuecomment-1024045764
"""

from sentry_sdk._types import MYPY
from sentry_sdk.hub import Hub
from sentry_sdk.integrations import DidNotEnable, Integration
from sentry_sdk.integrations.falcon import FalconRequestExtractor
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware
from sentry_sdk.utils import capture_internal_exceptions, event_from_exception

if MYPY:
    from typing import Any, Dict  # noqa: F401

    from sentry_sdk._types import EventProcessor  # noqa: F401

try:
    import falcon  # type: ignore
    import falcon.app_helpers  # type: ignore
    from falcon import __version__ as FALCON_VERSION
except ImportError:
    raise DidNotEnable("Falcon not installed")


class SentryFalconMiddleware(object):
    """Captures exceptions in Falcon requests and send to Sentry"""

    def process_request(self, req, resp, *args, **kwargs):
        # type: (Any, Any, *Any, **Any) -> None
        hub = Hub.current
        integration = hub.get_integration(FalconIntegration)
        if integration is None:
            return

        with hub.configure_scope() as scope:
            scope._name = "falcon"
            scope.add_event_processor(_make_request_event_processor(req, integration))


TRANSACTION_STYLE_VALUES = ("uri_template", "path")


class FalconIntegration(Integration):
    identifier = "falcon"

    transaction_style = None

    def __init__(self, transaction_style="uri_template"):
        # type: (str) -> None
        if transaction_style not in TRANSACTION_STYLE_VALUES:
            raise ValueError(
                "Invalid value for transaction_style: %s (must be in %s)" % (transaction_style, TRANSACTION_STYLE_VALUES)
            )
        self.transaction_style = transaction_style

    @staticmethod
    def setup_once():
        # type: () -> None
        try:
            version = tuple(map(int, FALCON_VERSION.split(".")))
        except (ValueError, TypeError):
            raise DidNotEnable("Unparsable Falcon version: {}".format(FALCON_VERSION))

        if version < (1, 4):
            raise DidNotEnable("Falcon 1.4 or newer required.")

        _patch_wsgi_app()
        _patch_handle_exception()
        _patch_prepare_middleware()


def _patch_wsgi_app():
    # type: () -> None
    original_wsgi_app = falcon.App.__call__

    def sentry_patched_wsgi_app(self, env, start_response):
        # type: (falcon.App, Any, Any) -> Any
        hub = Hub.current
        integration = hub.get_integration(FalconIntegration)
        if integration is None:
            return original_wsgi_app(self, env, start_response)

        sentry_wrapped = SentryWsgiMiddleware(lambda envi, start_resp: original_wsgi_app(self, envi, start_resp))

        return sentry_wrapped(env, start_response)

    falcon.App.__call__ = sentry_patched_wsgi_app


def _patch_handle_exception():
    # type: () -> None
    original_handle_exception = falcon.App._handle_exception

    def sentry_patched_handle_exception(self, *args):
        # type: (falcon.App, *Any) -> Any
        # NOTE(jmagnusson): falcon 2.0 changed falcon.App._handle_exception
        # method signature from `(ex, req, resp, params)` to
        # `(req, resp, ex, params)`
        if isinstance(args[0], Exception):
            ex = args[0]
        else:
            ex = args[2]

        was_handled = original_handle_exception(self, *args)

        hub = Hub.current
        integration = hub.get_integration(FalconIntegration)

        if integration is not None and _exception_leads_to_http_5xx(ex):
            # If an integration is there, a client has to be there.
            client = hub.client  # type: Any

            event, hint = event_from_exception(
                ex,
                client_options=client.options,
                mechanism={"type": "falcon", "handled": False},
            )
            hub.capture_event(event, hint=hint)

        return was_handled

    falcon.App._handle_exception = sentry_patched_handle_exception


def _patch_prepare_middleware():
    # type: () -> None
    original_prepare_middleware = falcon.app_helpers.prepare_middleware

    def sentry_patched_prepare_middleware(middleware=None, independent_middleware=False):
        # type: (Any, Any) -> Any
        hub = Hub.current
        integration = hub.get_integration(FalconIntegration)
        if integration is not None:
            middleware = [SentryFalconMiddleware()] + (middleware or [])
        return original_prepare_middleware(middleware, independent_middleware)

    falcon.app_helpers.prepare_middleware = sentry_patched_prepare_middleware


def _exception_leads_to_http_5xx(ex):
    # type: (Exception) -> bool
    is_server_error = isinstance(ex, falcon.HTTPError) and (ex.status or "").startswith("5")
    is_unhandled_error = not isinstance(ex, (falcon.HTTPError, falcon.http_status.HTTPStatus))
    return is_server_error or is_unhandled_error


def _make_request_event_processor(req, integration):
    # type: (falcon.Request, FalconIntegration) -> EventProcessor

    def inner(event, hint):
        # type: (Dict[str, Any], Dict[str, Any]) -> Dict[str, Any]
        if integration.transaction_style == "uri_template":
            event["transaction"] = req.uri_template
        elif integration.transaction_style == "path":
            event["transaction"] = req.path

        with capture_internal_exceptions():
            FalconRequestExtractor(req).extract_into_event(event)

        return event

    return inner
