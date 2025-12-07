from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class LaboratoryConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.laboratory"
    verbose_name = _("Laboratory")

    def ready(self):
        from mcod.laboratory.models import LabEvent, LabEventTrash

        self.connect_core_signals(LabEvent)
        self.connect_core_signals(LabEventTrash)
        self.connect_history(LabEvent)
