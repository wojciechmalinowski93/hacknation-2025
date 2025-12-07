from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class GuidesConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.guides"
    verbose_name = _("Portal guide")

    def ready(self):
        from mcod.guides.models import Guide, GuideItem

        self.connect_history(Guide, GuideItem)
