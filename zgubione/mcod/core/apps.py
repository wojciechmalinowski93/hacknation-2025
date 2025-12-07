from django.apps import AppConfig


class ExtendedAppMixin:
    def connect_core_signals(self, sender):
        from django.db import models

        from mcod.core.db.models import BaseExtendedModel

        if issubclass(sender, BaseExtendedModel):
            models.signals.pre_init.connect(BaseExtendedModel.on_pre_init, sender=sender)
            models.signals.post_init.connect(BaseExtendedModel.on_post_init, sender=sender)
            models.signals.pre_save.connect(BaseExtendedModel.on_pre_save, sender=sender)
            models.signals.post_save.connect(BaseExtendedModel.on_post_save, sender=sender)
            models.signals.pre_delete.connect(BaseExtendedModel.on_pre_delete, sender=sender)
            models.signals.post_delete.connect(BaseExtendedModel.on_post_delete, sender=sender)

    def connect_m2m_signal(self, sender):
        from django.db import models

        from mcod.core.db.models import BaseExtendedModel

        models.signals.m2m_changed.connect(BaseExtendedModel.on_m2m_changed, sender=sender)

    def connect_history(self, *senders):
        from mcod.core.auditlog import auditlog
        from mcod.core.registries import history_registry

        for sender in senders:
            history_registry.register(sender)
            auditlog.register(sender)
            exclude_fields_mapping = {"User": ["pesel", "_pesel"]}
            exclude_fields = exclude_fields_mapping.get(sender.__name__, [])
            auditlog.register(sender, exclude_fields=exclude_fields)
            if hasattr(sender, "trash_class"):
                auditlog.register(sender.trash_class)


class CoreConfig(AppConfig):
    name = "mcod.core"
    signal_processor = None

    def ready(self):
        self.module.autodiscover()
        if not self.signal_processor:
            self.register_rdf_signal_processor()

    def register_rdf_signal_processor(self):
        from mcod.core.api.rdf.signals import SparqlSignalProcessor

        self.signal_processor = SparqlSignalProcessor()
