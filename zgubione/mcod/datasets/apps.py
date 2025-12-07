from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class DatasetsConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.datasets"
    verbose_name = _("Datasets")

    def ready(self):
        from mcod.core.registries import rdf_serializers_registry as rsr
        from mcod.datasets.models import Dataset, DatasetTrash, Supplement
        from mcod.datasets.serializers import DatasetRDFResponseSchema

        self.connect_core_signals(Dataset)
        self.connect_core_signals(DatasetTrash)
        self.connect_m2m_signal(Dataset.tags.through)
        self.connect_m2m_signal(Dataset.categories.through)
        rsr.register(DatasetRDFResponseSchema)
        self.connect_history(Dataset, Supplement)
