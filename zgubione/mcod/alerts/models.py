from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils import Choices
from model_utils.models import StatusModel

from mcod.core.db.mixins import AdminMixin
from mcod.core.db.models import TimeStampedModel
from mcod.lib.model_sanitization import (
    SanitizedCharField,
    SanitizedTextField,
    SanitizedTranslationField,
)

User = get_user_model()

STATUS_CHOICES = [
    ("published", _("Active")),
    ("draft", _("Draft")),
]

DISPLAY_STATUS = {
    "ongoing": ("success", _("Ongoing")),
    "n/a": ("default", _("Not applicable")),
    "finished": ("info", _("Finished")),
    "waiting": ("default", _("Waiting")),
}


class Alert(AdminMixin, StatusModel, TimeStampedModel):
    STATUS = Choices(*STATUS_CHOICES)
    title = SanitizedCharField(
        max_length=300,
        verbose_name=_("Title"),
        null=False,
        blank=False,
        help_text=_("Title of the alert (300 characters max.)"),
    )
    description = SanitizedTextField(
        verbose_name=_("Description"),
        null=False,
        blank=False,
        help_text=_("Description of the alert"),
    )
    start_date = models.DateTimeField(
        null=False,
        blank=False,
        verbose_name=_("Start date"),
        help_text=_("Date and time from which the message should be displayed"),
    )
    finish_date = models.DateTimeField(
        null=False,
        blank=False,
        verbose_name=_("Finish date"),
        help_text=_("Date and time until which the message should be displayed"),
    )
    created_by = models.ForeignKey(
        User,
        models.SET_NULL,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="alerts_created",
    )

    modified_by = models.ForeignKey(
        User,
        models.SET_NULL,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="alerts_modified",
    )

    i18n = SanitizedTranslationField(fields=("title", "description"), required_languages=("pl",))

    @classmethod
    def accusative_case(cls):
        return _("acc: Alert")

    class Meta:
        verbose_name = _("Alert")
        verbose_name_plural = _("Alerts")
        db_table = "alert"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]

    def __str__(self):
        return self.title_i18n
