from django.db import models
from django.utils import timezone
from django.utils.formats import localize
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker

from mcod.core.db.managers import TrashManager
from mcod.core.db.models import ExtendedModel, TrashModelBase
from mcod.core.managers import SoftDeletableManager
from mcod.guides.managers import GuideManager, GuideTrashManager
from mcod.lib.model_sanitization import (
    SanitizedCharField,
    SanitizedTextField,
    SanitizedTranslationField,
)


class Guide(ExtendedModel):
    title = SanitizedCharField(max_length=300, verbose_name=_("title"))
    created_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        editable=False,
        verbose_name=_("created by"),
        related_name="guides_created",
    )
    modified_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        blank=True,
        null=True,
        editable=False,
        verbose_name=_("modified by"),
        related_name="guides_modified",
    )

    objects = GuideManager()
    trash = GuideTrashManager()
    i18n = SanitizedTranslationField(fields=("title",))
    tracker = FieldTracker()

    def __str__(self):
        return self.title

    class Meta:
        default_manager_name = "objects"
        verbose_name = _("guide")
        verbose_name_plural = _("guides")

    @property
    def created_local(self):
        return timezone.localtime(self.created)

    @property
    def created_localized(self):
        return localize(self.created_local)

    @cached_property
    def items_included(self):
        return self.items.all()


class GuideTrash(Guide, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash (Guides)")
        verbose_name_plural = _("Trash (Guides)")


class GuideItem(ExtendedModel):
    POSITION_CHOICES = (
        ("top", _("top")),
        ("bottom", _("bottom")),
        ("left", _("left")),
        ("right", _("right")),
    )
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, verbose_name=_("guide"), related_name="items")
    title = SanitizedCharField(max_length=200, verbose_name=_("title"))
    content = SanitizedTextField(verbose_name=_("content"))
    route = SanitizedCharField(max_length=200, verbose_name=_("route"))
    css_selector = SanitizedCharField(max_length=300, verbose_name=_("css selector"))
    position = models.CharField(max_length=13, choices=POSITION_CHOICES, verbose_name=_("position"))
    order = models.PositiveIntegerField(verbose_name=_("order"))
    is_optional = models.BooleanField(verbose_name=_("optional communique"), default=False)
    is_clickable = models.BooleanField(verbose_name=_("clicking is required"), default=False)
    is_expandable = models.BooleanField(verbose_name=_("element is expandable"), default=False)

    objects = SoftDeletableManager()
    trash = TrashManager()
    i18n = SanitizedTranslationField(fields=("title", "content"))
    tracker = FieldTracker()

    def __str__(self):
        return self.title

    class Meta:
        default_manager_name = "objects"
        ordering = ("order",)
        verbose_name = _("guide item")
        verbose_name_plural = _("guide items")

    def delete(self, using=None, soft=True, *args, **kwargs):
        return super().delete(using=using, soft=False, *args, **kwargs)
