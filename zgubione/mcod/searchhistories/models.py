from django.db import models
from django.utils.translation import gettext_lazy as _

from mcod.core.api.search import signals as search_signals
from mcod.core.db.models import TimeStampedModel
from mcod.lib.model_sanitization import SanitizedCharField


class SearchHistory(TimeStampedModel):
    url = models.URLField(max_length=512)
    query_sentence = SanitizedCharField(max_length=256)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id} | user: {self.user} | {self.url}"

    class Meta:
        verbose_name = _("Search history")
        verbose_name_plural = _("Search Histories")


def index_document_after_save(sender, instance, created, raw, using, update_fields, **kwargs):
    search_signals.update_document.send(sender, instance)


def remove_document_after_delete(sender, instance, using, **kwargs):
    search_signals.remove_document.send(sender, instance)


models.signals.post_save.connect(index_document_after_save, sender=SearchHistory)
models.signals.post_delete.connect(remove_document_after_delete, sender=SearchHistory)
