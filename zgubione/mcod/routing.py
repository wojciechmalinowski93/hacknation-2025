import sentry_sdk
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.apps import apps
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from mcod import settings

bokeh_app_config = apps.get_app_config("mcod.pn_apps")

if settings.COMPONENT == "ws" and settings.ENABLE_SENTRY:

    sentry_sdk.init(**settings.SENTRY_SDK_KWARGS["ws"])

    application = ProtocolTypeRouter(
        {
            "websocket": SentryAsgiMiddleware(
                AuthMiddlewareStack(URLRouter(bokeh_app_config.routes.get_websocket_urlpatterns()))
            ),
            "http": SentryAsgiMiddleware(AuthMiddlewareStack(URLRouter(bokeh_app_config.routes.get_http_urlpatterns()))),
        }
    )
else:
    application = ProtocolTypeRouter(
        {
            "websocket": AuthMiddlewareStack(URLRouter(bokeh_app_config.routes.get_websocket_urlpatterns())),
            "http": AuthMiddlewareStack(URLRouter(bokeh_app_config.routes.get_http_urlpatterns())),
        }
    )
