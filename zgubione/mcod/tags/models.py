from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from modeltrans.fields import TranslationField

from mcod import settings
from mcod.core.api.rdf import signals as rdf_signals
from mcod.core.api.search import signals as search_signals
from mcod.core.db.models import BaseExtendedModel
from mcod.lib.model_sanitization import SanitizedCharField
from mcod.tags.signals import update_related_datasets, update_related_showcases

User = get_user_model()

STATUS_CHOICES = [
    ("published", _("Published")),
    ("draft", _("Draft")),
]


class Tag(BaseExtendedModel):
    SIGNALS_MAP = {
        "updated": (update_related_datasets, update_related_showcases),
        "published": (update_related_datasets, update_related_showcases),
        "restored": (update_related_datasets, update_related_showcases),
        "removed": (update_related_datasets, update_related_showcases),
    }
    name = SanitizedCharField(max_length=100, verbose_name=_("name"))
    language = models.CharField(
        max_length=2,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGES[0][0],
        verbose_name=_("language"),
        db_index=True,
    )

    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="tags_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="tags_modified",
    )

    def __str__(self):
        en_name = getattr(self, "name_en", "") or ""
        return self.name or en_name

    @classmethod
    def accusative_case(cls):
        return _("acc: Tag")

    i18n = TranslationField(fields=("name",), required_languages=("pl",))
    tracker = FieldTracker()
    slugify_field = "name"

    objects = models.Manager()

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        db_table = "tag"
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]
        unique_together = ("name", "language")

    @property
    def translations_dict(self):
        return {lang: getattr(self, f"name_{lang}", "") or "" for lang in settings.MODELTRANS_AVAILABLE_LANGUAGES}

    @property
    def to_dict(self):
        return {
            "name": self.name,
            "language": self.language,
        }

    @property
    def language_readonly(self):
        return self.language


@receiver(update_related_datasets, sender=Tag)
def update_tag_in_datasets(sender, instance, *args, **kwargs):
    sender.log_debug(instance, "Updating related datasets", "update_related_datasets")
    for dataset in instance.datasets.all():
        search_signals.update_document.send(dataset._meta.model, dataset)
        rdf_signals.update_graph.send(dataset._meta.model, dataset)


@receiver(update_related_showcases, sender=Tag)
def update_tag_in_showcases(sender, instance, *args, **kwargs):
    sender.log_debug(instance, "Updating related showcases", "update_related_showcases")
    for showcase in instance.showcases.all():
        search_signals.update_document.send(showcase._meta.model, showcase)
