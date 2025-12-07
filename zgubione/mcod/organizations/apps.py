import logging

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin
from mcod.core.metrics import ORGANIZATION_COUNT

logger = logging.getLogger("mcod")


class OrganizationsConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.organizations"
    verbose_name = _("Institutions")

    def ready(self):
        from mcod.organizations.models import Organization, OrganizationTrash

        self.connect_core_signals(Organization)
        self.connect_core_signals(OrganizationTrash)
        self.connect_history(Organization)

        try:
            ORGANIZATION_COUNT.labels(source="published").set(Organization.objects.all().count())
        except Exception as e:
            logger.error(f"Could get data from DB: {e}")
