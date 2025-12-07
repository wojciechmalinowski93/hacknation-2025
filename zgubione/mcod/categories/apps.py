from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class CategoriesConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.categories"
    verbose_name = _("Categories")

    def ready(self):
        from mcod.categories.models import Category, CategoryTrash

        self.connect_core_signals(Category)
        self.connect_core_signals(CategoryTrash)
        self.connect_history(Category)
