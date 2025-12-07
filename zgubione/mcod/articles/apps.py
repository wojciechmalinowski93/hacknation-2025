from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class ArticlesConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.articles"
    verbose_name = _("Articles")
