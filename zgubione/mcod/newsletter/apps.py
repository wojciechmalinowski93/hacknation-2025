from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class NewsletterConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.newsletter"
    verbose_name = _("Newsletter")

    def ready(self):
        from mcod.newsletter.models import Newsletter, Submission, Subscription

        self.connect_history(Newsletter, Submission, Subscription)
