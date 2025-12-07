from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class TagsConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.tags"
    verbose_name = _("Tags")

    def ready(self):
        from mcod.tags.models import Tag

        self.connect_core_signals(Tag)
        self.connect_history(Tag)
