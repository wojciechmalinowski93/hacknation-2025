from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker

from mcod.categories.signals import null_in_related_datasets, update_related_datasets
from mcod.core import storages
from mcod.core.api.rdf import signals as rdf_signals
from mcod.core.api.search import signals as search_signals
from mcod.core.api.search.tasks import null_field_in_related_task
from mcod.core.db.managers import TrashManager
from mcod.core.db.models import ExtendedModel, TrashModelBase
from mcod.core.managers import SoftDeletableManager
from mcod.lib.model_sanitization import (
    SanitizedCharField,
    SanitizedTextField,
    SanitizedTranslationField,
)

User = get_user_model()


class Category(ExtendedModel):
    SIGNALS_MAP = {
        "updated": (update_related_datasets,),
        "published": (update_related_datasets,),
        "restored": (update_related_datasets,),
        "removed": (null_in_related_datasets, rdf_signals.update_related_graph),
    }
    code = SanitizedCharField(max_length=100, verbose_name=_("Code"))
    title = SanitizedCharField(max_length=100, verbose_name=_("Title"))
    description = SanitizedTextField(null=True, verbose_name=_("Description"))
    color = models.CharField(max_length=20, default="#000000", null=True, verbose_name=_("Color"))
    image = models.ImageField(
        max_length=200,
        storage=storages.get_storage("common"),
        upload_to="",
        blank=True,
        null=True,
        verbose_name=_("Image URL"),
    )
    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Created by"),
        related_name="categories_created",
    )
    modified_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Modified by"),
        related_name="categories_modified",
    )

    @classmethod
    def accusative_case(cls):
        return _("acc: Category")

    def __str__(self):
        return self.title_i18n

    @property
    def image_url(self):
        if not self.image or not self.image.url:
            return None
        return "{}{}".format(settings.BASE_URL, self.image.url)

    i18n = SanitizedTranslationField(fields=("title", "description"))

    objects = SoftDeletableManager()
    trash = TrashManager()

    tracker = FieldTracker()
    slugify_field = "title"

    class Meta:
        db_table = "category"
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        default_manager_name = "objects"
        indexes = [
            GinIndex(fields=["i18n"]),
        ]


@receiver(null_in_related_datasets, sender=Category)
def null_category_in_datasets(sender, instance, *args, **kwargs):
    sender.log_debug(instance, "Setting null in datasets", "null_in_related_datasets")
    null_field_in_related_task.apply_async_on_commit(args=(instance._meta.app_label, instance._meta.object_name, instance.id))


@receiver(update_related_datasets, sender=Category)
def update_category_in_datasets(sender, instance, *args, **kwargs):
    sender.log_debug(instance, "Updating related datasets", "update_related_datasets")
    for dataset in instance.dataset_set.all():
        search_signals.update_document.send(dataset._meta.model, dataset)
        rdf_signals.update_graph.send(dataset._meta.model, dataset)


class CategoryTrash(Category, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash")
        verbose_name_plural = _("Trash")
