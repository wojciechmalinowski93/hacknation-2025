from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from modeltrans.fields import TranslationField

from mcod.core.db.models import ExtendedModel
from mcod.lib.model_sanitization import SanitizedCharField, SanitizedTextField
from mcod.special_signs.managers import SpecialSignManager, SpecialSignTrashManager


class SpecialSign(ExtendedModel):
    symbol = models.CharField(max_length=30, verbose_name=_("symbol"))
    name = SanitizedCharField(max_length=100, verbose_name=_("name"))
    description = SanitizedTextField(verbose_name=_("description"))
    created_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("created by"),
        related_name="special_signs_created",
    )
    modified_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("modified by"),
        related_name="special_signs_modified",
    )

    objects = SpecialSignManager()
    trash = SpecialSignTrashManager()
    i18n = TranslationField(fields=("name", "description"), required_languages=("pl",))
    tracker = FieldTracker()
    slugify_field = "name"

    def __str__(self):
        return self.name

    class Meta:
        default_manager_name = "objects"
        verbose_name = _("special sign")
        verbose_name_plural = _("special signs")
