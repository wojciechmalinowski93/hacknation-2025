from importlib import import_module
from typing import List, Optional

from bokeh.server.django.routing import Routing, RoutingConfiguration
from django.apps import AppConfig
from django.conf import settings

from mcod.lib.utils import is_django_ver_lt


class PnAppsConfig(AppConfig):
    if is_django_ver_lt(3, 2):
        label = "mcod.pn_apps"
    name = "mcod.pn_apps"
    verbose_name = "Panel Apps"

    _routes: Optional[RoutingConfiguration] = None

    @property
    def bokeh_apps(self) -> List[Routing]:
        module = settings.PN_APPS_URLCONF
        url_conf = import_module(module) if isinstance(module, str) else module
        return url_conf.bokeh_apps

    @property
    def routes(self) -> RoutingConfiguration:
        if self._routes is None:
            self._routes = RoutingConfiguration(self.bokeh_apps)
        return self._routes
