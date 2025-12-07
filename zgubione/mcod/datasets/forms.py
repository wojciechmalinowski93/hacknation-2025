from typing import Any, Dict, Optional

from django import forms
from django.contrib.postgres.forms.jsonb import JSONField
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from mcod import settings
from mcod.core.db.models import STATUS_CHOICES
from mcod.core.widgets import UnescapeTextarea
from mcod.datasets.field_validators import validate_dataset_image_file_extension
from mcod.datasets.models import LICENSE_CONDITION_LABELS, UPDATE_FREQUENCY, Dataset, Supplement
from mcod.datasets.widgets import CheckboxInputWithLabel
from mcod.lib.field_validators import ContainsLetterValidator
from mcod.lib.forms.mixins import HighValueDataFormValidatorMixin
from mcod.lib.metadata_validators import validate_high_value_data_from_ec_list_organization
from mcod.lib.utils import capitalize_first_character
from mcod.lib.widgets import CheckboxSelect, CKEditorWidget, JsonPairDatasetInputs
from mcod.organizations.models import Organization
from mcod.resources.forms import SupplementForm as ResourceSupplementForm
from mcod.tags.forms import ModelFormWithKeywords

UPDATE_FREQUENCY_FOR_CREATE = ((None, ""),) + tuple(
    item for item in UPDATE_FREQUENCY if item != ("notApplicable", _("Not applicable"))
)
UPDATE_FREQUENCY_FOR_UPDATE = UPDATE_FREQUENCY


class DatasetForm(ModelFormWithKeywords, HighValueDataFormValidatorMixin):
    title = forms.CharField(
        widget=UnescapeTextarea(
            attrs={
                "placeholder": _("e.g. the name of the data set"),
                "style": "width: 99%",
                "rows": 2,
            }
        ),
        label=_("Title"),
        max_length=300,
    )
    slug = forms.SlugField(label="Slug", widget=forms.TextInput(attrs={"size": 85}), required=False)
    notes = forms.CharField(
        min_length=20,
        widget=CKEditorWidget(
            attrs={
                "placeholder": _("Some information about the data being added"),
                "cols": 80,
                "rows": 10,
            }
        ),
        required=True,
        label=_("Notes"),
        validators=[ContainsLetterValidator()],
    )
    notes_en = forms.CharField(
        min_length=20,
        widget=CKEditorWidget(
            attrs={
                "placeholder": _("Some information about the data being added"),
                "cols": 80,
                "rows": 10,
            }
        ),
        required=False,
        label=_("Notes") + " (EN)",
        validators=[ContainsLetterValidator()],
    )

    # choices for update_frequency are added in the form __init__ method,
    # depending on whether the form is used to add or edit an instance
    update_frequency = forms.ChoiceField(label=_("Update frequency"))
    url = forms.URLField(
        required=False,
        widget=forms.TextInput(attrs={"size": 85}),
        label=_("Source"),
        max_length=1000,
    )

    customfields = JSONField(
        label=_("Customfields"),
        widget=JsonPairDatasetInputs(val_attrs={"size": 35}, key_attrs={"class": "large"}),
        required=False,
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        help_text=_(
            "If you select a draft, the status of all published resources belonging to that set will be changed to a draft"
        ),
    )
    has_dynamic_data = forms.ChoiceField(
        required=True,
        label=_("dynamic data").capitalize(),
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Zaznaczenie TAK spowoduje oznaczenie wszystkich nowo dodanych danych w zbiorze jako dane dynamiczne."
            "<br><br>Jeżeli chcesz się więcej dowiedzieć na temat danych dynamicznych "
            '<a href="%(url)s" target="_blank">przejdź do strony</a>'
        )
        % {"url": f"{settings.BASE_URL}{settings.DYNAMIC_DATA_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    has_high_value_data = forms.ChoiceField(
        required=True,
        label=_("has high value data").capitalize(),
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Zaznaczenie TAK spowoduje oznaczenie wszystkich nowo dodanych danych w zbiorze jako dane o wysokiej "
            "wartości.<br><br>Jeżeli chcesz się więcej dowiedzieć na temat danych wysokiej wartości "
            '<a href="%(url)s" target="_blank">przejdź do strony</a>'
        )
        % {"url": f"{settings.BASE_URL}{settings.HIGH_VALUE_DATA_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    has_high_value_data_from_ec_list = forms.ChoiceField(
        required=True,
        label=capitalize_first_character(_("has high value data from the EC list")),  # `KE` / `EC` must be uppercase
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Zaznaczenie TAK spowoduje oznaczenie wszystkich nowo dodanych danych w zbiorze jako dane o wysokiej "
            "wartości z wykazu KE.<br><br>Jeżeli chcesz się więcej dowiedzieć na temat danych wysokiej wartości z wykazu KE "
            '<a href="%(url)s" target="_blank">przejdź do strony</a>'
        )
        % {"url": f"{settings.BASE_URL}{settings.HIGH_VALUE_DATA_FROM_EC_LIST_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    has_research_data = forms.ChoiceField(
        required=True,
        label=_("has research data").capitalize(),
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Zaznaczenie TAK spowoduje oznaczenie wszystkich nowo dodanych danych w zbiorze jako dane badawcze."
            "<br><br>Jeżeli chcesz się więcej dowiedzieć na temat danych badawczych "
            '<a href="%(url)s" target="_blank">przejdź do strony</a>'
        )
        % {"url": f"{settings.BASE_URL}{settings.RESEARCH_DATA_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )

    def __init__(self, *args, instance=None, **kwargs):  # noqa
        super().__init__(*args, instance=instance, **kwargs)
        instance_has_cc0_chosen = instance and instance.license_chosen == Dataset.LICENSE_CC0
        if "license_chosen" in self.fields and not instance_has_cc0_chosen:
            license_chosen_choices = list(self.fields["license_chosen"].choices)
            license_chosen_choices.remove(Dataset.LICENSE_CC0_TUPLE)
            self.fields["license_chosen"].choices = license_chosen_choices

        if "categories" in self.fields:
            self.fields["categories"].required = True
        try:
            self.fields["image"].validators.append(validate_dataset_image_file_extension)
            self.fields["image"].help_text = _(
                "Allowed file extensions: jpg, gif, png. For better readability,"
                " we recommend .png files with a transparent background"
            )
        except KeyError:
            pass

        if self.fields.get("tags_pl"):
            self.fields["tags_pl"].required = True

        if "update_notification_recipient_email" in self.fields:
            self.fields["update_notification_recipient_email"].required = True
            if instance and instance.modified_by and not instance.update_notification_recipient_email:
                self.initial["update_notification_recipient_email"] = instance.modified_by.email
        if instance:
            for label_name, label_value in instance.license_condition_labels.items():
                condition_field = self.fields.get(f"license_condition_{label_name}")
                if condition_field:
                    condition_field.label = label_value

        if self.instance and self.instance.pk:
            # Dataset edition
            self.fields["update_frequency"].choices = UPDATE_FREQUENCY_FOR_UPDATE
        else:
            # Dataset creation
            self.fields["update_frequency"].choices = UPDATE_FREQUENCY_FOR_CREATE

    class Meta:
        model = Dataset
        widgets = {
            "license_condition_source": CheckboxInputWithLabel(label="CC BY 4.0"),
            "license_condition_modification": CheckboxInputWithLabel(label="CC BY 4.0"),
            "license_condition_responsibilities": CKEditorWidget(config_name="licenses"),
            "license_condition_cc40_responsibilities": CheckboxInputWithLabel(label="CC BY 4.0"),
            "license_condition_db_or_copyrighted": CKEditorWidget(config_name="licenses"),
            "license_chosen": forms.RadioSelect,
            "license_condition_personal_data": CKEditorWidget(config_name="licenses"),
            "update_notification_frequency": forms.TextInput(attrs={"maxlength": 3}),
            "license_condition_default_cc40": CheckboxInputWithLabel(label="CC BY 4.0"),
            "license_condition_custom_description": CKEditorWidget(config_name="licenses"),
            "is_promoted": CheckboxInputWithLabel(
                label="Tak",
                style="margin-top:8px;vertical-align:middle;display:inline-block;margin-left:5px;",
            ),
        }
        fields = [
            "title",
            "slug",
            "category",
            "categories",
            "notes",
            "tags",
            "organization",
            "url",
            "image",
            "update_frequency",
            "customfields",
            "license_condition_source",
            "license_condition_modification",
            "license_condition_responsibilities",
            "license_condition_cc40_responsibilities",
            "license_condition_db_or_copyrighted",
            "license_chosen",
            "license_condition_personal_data",
            "status",
            "is_promoted",
        ]
        help_texts = {
            "is_promoted": _(
                "By checking the checkbox, the item will be promoted on the list of datasets. "
                "You can promote a maximum of %(limit)s datasets."
            )
            % {"limit": settings.DATASET_IS_PROMOTED_LIMIT},
            "update_notification_recipient_email": (
                "Uwaga! Adres email zostanie nadpisany adresem edytora, który będzie modyfikował metadane zbioru."
            ),
        }
        labels = {
            "created": _("Availability date"),
            "modified": _("Modification date"),
            "verified": _("Update date"),
            "archived_resources_files_media_url": _("Archived resources files"),
            "license_condition_source": LICENSE_CONDITION_LABELS["public"]["source"],
            "license_condition_modification": LICENSE_CONDITION_LABELS["public"]["modification"],
            "license_condition_responsibilities": LICENSE_CONDITION_LABELS["public"]["responsibilities"],
            "license_condition_db_or_copyrighted": LICENSE_CONDITION_LABELS["public"]["db_or_copyrighted"],
            "license_condition_personal_data": LICENSE_CONDITION_LABELS["public"]["personal_data"],
            "license_condition_custom_description": LICENSE_CONDITION_LABELS["public"]["custom_description"],
        }

    def clean(self):
        # Create a copy of cleaned data as using `self.add_error` may remove fields from the original dictionary.
        cleaned_data = super().clean().copy()
        self.validate_high_value_data_flags_conflict(cleaned_data)
        self._validate_high_value_data_from_ec_list_organization(cleaned_data)
        if cleaned_data.get("license_condition_db_or_copyrighted") and not cleaned_data.get("license_chosen"):
            self.add_error("license_chosen", _("Text area is filled, license must be selected"))
        if cleaned_data.get("license_condition_responsibilities") and cleaned_data.get("license_condition_cc40_responsibilities"):
            self.add_error(
                "license_condition_responsibilities",
                _(
                    "You can't enter custom license responsibilities and select"
                    " default CC BY 4.0 license responsibilities at the same time. Please choose one."
                ),
            )

        if cleaned_data.get("is_promoted"):
            limit = settings.DATASET_IS_PROMOTED_LIMIT
            msg = _(
                "Currently %(limit)s datasets have already been marked as promoted. "
                "If you want to select this dataset, you have to uncheck another one."
            ) % {"limit": limit}
            queryset = Dataset.objects.filter(status="published", is_promoted=True)
            promoted_datasets = queryset.exclude(id=self.instance.id) if self.instance else queryset
            if promoted_datasets.count() >= limit:
                self.add_error("is_promoted", msg)
            if cleaned_data.get("status") == "draft":
                self.add_error(
                    "is_promoted",
                    _("Only published dataset can be assigned as promoted!"),
                )
        return cleaned_data

    def clean_status(self):
        if self.instance.id:
            organization = self.instance.organization
        else:
            organization = self.cleaned_data.get("organization")

        if organization and organization.status == "draft":
            if self.cleaned_data["status"] == "published":
                error_message = _(
                    "You can't publish this dataset, because his organization has the status of a draft "
                    "Please set status to draft or set status to publish for organization: "
                )

                error_message += "<a href='{}'>{}</a>".format(organization.admin_change_url, organization.title)

                raise forms.ValidationError(mark_safe(error_message))

        return self.cleaned_data["status"]

    def clean_update_frequency(self):
        update_frequency = self.cleaned_data.get("update_frequency")

        if update_frequency == "notApplicable":
            # No longer supported value of update_frequency - OTD-1231
            raise forms.ValidationError(
                _("The 'Not Applicable' value is no longer supported by the portal. Change it to another one.")
            )
        return update_frequency

    def _validate_high_value_data_from_ec_list_organization(self, data: Dict[str, Any]):
        organization: Optional[Organization] = data.get("organization")
        if organization is None:
            return

        organization_type: str = organization.institution_type
        has_high_value_data_from_ec_list: bool = data.get("has_high_value_data_from_ec_list") == "True"

        try:
            validate_high_value_data_from_ec_list_organization(has_high_value_data_from_ec_list, organization_type)
        except ValidationError:
            self.add_error(
                "has_high_value_data_from_ec_list",
                _("Data of private or developer institutions are not high-value data from EC list."),
            )


class DatasetErrorList(forms.utils.ErrorList):

    def __init__(self, *args, **kwargs):
        kwargs["error_class"] = "alert alert-error"
        super().__init__(*args, **kwargs)


class DatasetFormSet(forms.BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        kwargs["error_class"] = DatasetErrorList
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        promoted_datasets_count = Dataset.objects.filter(status="published", is_promoted=True).count()
        limit = settings.DATASET_IS_PROMOTED_LIMIT
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            is_promoted = form.cleaned_data.get("is_promoted") and form.cleaned_data.get("status") == "published"
            if is_promoted:
                promoted_datasets_count += 1
        if promoted_datasets_count > limit:
            msg = _(
                "Currently %(limit)s datasets have already been marked as promoted. "
                "If you want to promote another one, you need to uncheck any of them."
            ) % {"limit": limit}
            raise forms.ValidationError(msg)


class DatasetStackedNoSaveForm(forms.ModelForm):
    title = forms.HiddenInput(attrs={"required": False})
    slug = forms.HiddenInput(attrs={"required": False})

    def save(self, commit=True):
        return super().save(commit=False)


class TrashDatasetForm(forms.ModelForm):

    def clean_is_removed(self):
        organization = self.instance.organization

        if self.cleaned_data["is_removed"] is False and organization.is_removed:
            error_message = _(
                "You can't restore this dataset, because it's organization is still removed. "
                "Please first restore organization: "
            )

            error_message += "<a href='{}'>{}</a>".format(organization.admin_trash_change_url, organization.title)

            raise forms.ValidationError(mark_safe(error_message))

        return self.cleaned_data["is_removed"]


class SupplementForm(ResourceSupplementForm):

    class Meta(ResourceSupplementForm.Meta):
        model = Supplement
