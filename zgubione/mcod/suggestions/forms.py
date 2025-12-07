from django import forms
from django.utils.translation import gettext_lazy as _

from mcod.suggestions.models import (
    ACCEPTED_DATASET_SUBMISSION_STATUS_CHOICES_NO_PUBLISHED,
    AcceptedDatasetSubmission,
    DatasetComment,
    DatasetSubmission,
    ResourceComment,
)


class DatasetCommentForm(forms.ModelForm):

    class Meta:
        model = DatasetComment
        fields = [
            "decision",
            "decision_date",
            "editor_comment",
        ]
        labels = {
            "decision": _("Decision made"),
        }
        widgets = {
            "editor_comment": forms.Textarea(attrs={"rows": "1", "class": "input-block-level"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "decision" in self.fields:
            self.fields["decision"].required = True


class ResourceCommentForm(DatasetCommentForm):
    class Meta(DatasetCommentForm.Meta):
        model = ResourceComment


class DatasetSubmissionForm(forms.ModelForm):

    class Meta:
        model = DatasetSubmission
        fields = [
            "title",
            "notes",
            "organization_name",
            "data_link",
            "potential_possibilities",
            "comment",
            "submission_date",
            "decision",
            "decision_date",
        ]
        labels = {
            "organization_name": _("Name of data responsible institution"),
            "decision": _("Decision made"),
        }
        widgets = {
            "comment": forms.Textarea(attrs={"rows": "1", "class": "input-block-level"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "decision" in self.fields:
            self.fields["decision"].required = True


class AcceptedDatasetSubmissionForm(DatasetSubmissionForm):

    def __init__(self, data=None, *args, instance=None, **kwargs):
        super().__init__(data, *args, instance=instance, **kwargs)
        if "title" in self.fields:
            self.fields["title"].widget.attrs["rows"] = 2

        if "publication_finished_comment" in self.fields:
            if data is None or data.get("status") == AcceptedDatasetSubmission.STATUS.publication_finished:
                self.fields["publication_finished_comment"].required = True

        if (
            "status" in self.fields
            and instance
            and instance.status == "publication_finished"
            and not instance.tracker.has_changed("status")
        ):
            self.fields["status"].choices = ACCEPTED_DATASET_SUBMISSION_STATUS_CHOICES_NO_PUBLISHED

    def clean(self):
        cleaned_data = super().clean()
        if "is_published_for_all" in cleaned_data and "status" in cleaned_data:
            if cleaned_data["is_published_for_all"] and cleaned_data["status"] == "draft":
                raise forms.ValidationError(
                    _(
                        "If you wish to publish accepted dataset submission for all user,"
                        ' this submission must have "published" status'
                    )
                )
        return cleaned_data

    class Meta(DatasetSubmissionForm.Meta):
        model = AcceptedDatasetSubmission
        fields = [
            "title",
            "notes",
            "organization_name",
            "data_link",
            "potential_possibilities",
            "comment",
            "decision",
            "decision_date",
            "status",
            "publication_finished_comment",
            "is_published_for_all",
        ]
        widgets = {
            "title": forms.Textarea(attrs={"rows": "1", "class": "input-block-level"}),
            "notes": forms.Textarea(attrs={"rows": "2", "class": "input-block-level"}),
            "organization_name": forms.Textarea(attrs={"rows": "1", "class": "input-block-level"}),
            "data_link": forms.Textarea(attrs={"rows": "1", "class": "input-block-level"}),
            "potential_possibilities": forms.Textarea(attrs={"rows": "1", "class": "input-block-level"}),
            "publication_finished_comment": forms.Textarea(attrs={"rows": "5", "class": "input-block-level"}),
        }
