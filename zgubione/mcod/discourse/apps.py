from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_out
from django.utils.translation import gettext_lazy as _


class DiscourseConfig(AppConfig):
    name = "mcod.discourse"
    verbose_name = _("Discourse Integration")

    def ready(self):
        from mcod.discourse.signals import user_logout

        user_logged_out.connect(user_logout)
