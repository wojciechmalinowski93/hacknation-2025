from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class SpecialSignsConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.special_signs"
    verbose_name = _("Special Signs")

    def ready(self):
        from mcod.special_signs.models import SpecialSign

        self.connect_core_signals(SpecialSign)
        self.connect_history(SpecialSign)
