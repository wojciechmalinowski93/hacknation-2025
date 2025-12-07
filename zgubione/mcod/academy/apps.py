from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class AcademyConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.academy"
    verbose_name = _("Open Data Academy")

    def ready(self):
        from mcod.academy.models import Course, CourseTrash

        self.connect_core_signals(Course)
        self.connect_core_signals(CourseTrash)
        self.connect_history(Course)
