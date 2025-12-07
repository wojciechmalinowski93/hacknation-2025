from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class LicensesConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.licenses"
    verbose_name = _("Licenses")

    def ready(self):
        from mcod.licenses.models import License

        self.connect_core_signals(License)
