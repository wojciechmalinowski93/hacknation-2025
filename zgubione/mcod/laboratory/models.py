from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from modeltrans.fields import TranslationField

from mcod.core import storages
from mcod.core.db.managers import TrashManager
from mcod.core.db.models import ExtendedModel, TrashModelBase
from mcod.core.managers import SoftDeletableManager
from mcod.lib.model_sanitization import SanitizedCharField, SanitizedRichTextUploadingField

EVENT_TYPES = [("analysis", _("Analysis")), ("research", _("Research"))]


class LabEvent(ExtendedModel):
    title = SanitizedCharField(max_length=300, verbose_name=_("Title"))
    event_type = models.CharField(
        max_length=10,
        choices=EVENT_TYPES,
        default="analysis",
        editable=True,
        verbose_name=_("Event type"),
    )
    notes = SanitizedRichTextUploadingField(verbose_name=_("Notes"))
    execution_date = models.DateField(verbose_name=_("Execution date"))

    objects = SoftDeletableManager()
    trash = TrashManager()
    i18n = TranslationField(fields=("title", "notes"))
    tracker = FieldTracker()

    @classmethod
    def accusative_case(cls):
        return _("acc: Event")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        db_table = "lab_event"
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]


class LabEventTrash(LabEvent, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash")
        verbose_name_plural = _("Trash")


class LabReport(ExtendedModel):
    link = models.URLField(verbose_name=_("Report Link"), max_length=2000, blank=True, null=True)
    file = models.FileField(
        verbose_name=_("File"),
        storage=storages.get_storage("lab_reports"),
        max_length=2000,
        blank=True,
        null=True,
    )
    lab_event = models.ForeignKey(to=LabEvent, on_delete=models.DO_NOTHING, related_name="reports")

    objects = SoftDeletableManager()
    trash = TrashManager()
    i18n = TranslationField(fields=())
    tracker = FieldTracker()

    @property
    def report_type(self):
        return "link" if self.link else "file"

    @property
    def download_url(self):
        return self._get_absolute_url(self.file.url, use_lang=False) if self.file else None

    def __str__(self):
        if self.link:
            return self.link

        if self.file:
            return self.file.name

        return super().__str__()

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        db_table = "lab_report"
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]
