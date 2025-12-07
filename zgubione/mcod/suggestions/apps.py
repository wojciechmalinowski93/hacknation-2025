from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class SuggestionsConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.suggestions"
    verbose_name = _("Suggestions")

    def ready(self):
        from mcod.suggestions.models import (
            AcceptedDatasetSubmission,
            AcceptedDatasetSubmissionTrash,
            DatasetComment,
            DatasetSubmission,
            ResourceComment,
            SubmissionFeedback,
        )

        self.connect_core_signals(AcceptedDatasetSubmission)
        self.connect_core_signals(AcceptedDatasetSubmissionTrash)
        self.connect_core_signals(SubmissionFeedback)
        self.connect_history(
            AcceptedDatasetSubmission,
            DatasetComment,
            DatasetSubmission,
            ResourceComment,
        )
