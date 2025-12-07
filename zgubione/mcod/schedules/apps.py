from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class SchedulesConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.schedules"
    verbose_name = _("Schedules")
