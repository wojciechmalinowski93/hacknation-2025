from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class ShowcasesConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.showcases"
    verbose_name = _("PoCoTo")

    def ready(self):
        from mcod.showcases.models import Showcase, ShowcaseProposal, ShowcaseTrash

        self.connect_core_signals(Showcase)
        self.connect_core_signals(ShowcaseTrash)
        self.connect_m2m_signal(Showcase.datasets.through)
        self.connect_history(Showcase, ShowcaseProposal)
