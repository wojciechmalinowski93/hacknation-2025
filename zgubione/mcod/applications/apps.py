from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class ApplicationsConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.applications"
    verbose_name = _("Applications")
