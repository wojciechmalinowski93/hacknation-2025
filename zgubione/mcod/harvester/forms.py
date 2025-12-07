import logging

from django import forms
from django.contrib.admin.widgets import AdminURLFieldWidget
from django.utils.translation import gettext_lazy as _

from mcod.core.widgets import UnescapeTextInput
from mcod.harvester.models import DataSource, DataSourceImport
from mcod.lib.widgets import CKEditorWidget

logger = logging.getLogger("mcod")


class XMLUrlWidget(AdminURLFieldWidget):
    template_name = "admin/forms/widgets/harvester/url.html"


class XMLValidationForm(forms.Form):
    xml_url = forms.URLField(required=True)


class DataSourceAdminForm(forms.ModelForm):

    class Meta:
        model = DataSource
        exclude = ("last_import_status", "last_import_timestamp", "created_by")
        labels = {
            "description": _("Description (PL)"),
            "modified": _("Modification date"),
        }
        help_texts = {
            "emails": _("List of emails separated by a comma"),
        }
        widgets = {
            "api_url": forms.TextInput(attrs={"class": "span6"}),
            "description": CKEditorWidget(config_name="data_source_description"),
            "license_condition_db_or_copyrighted": forms.Textarea(attrs={"cols": "80", "class": "input-block-level"}),
            "name": UnescapeTextInput(attrs={"class": "span6"}),
            "portal_url": forms.TextInput(attrs={"class": "span6"}),
            "source_hash": forms.HiddenInput(),
            "xml_url": XMLUrlWidget(attrs={"class": "vURLField span6"}),
            "sparql_query": forms.Textarea(attrs={"rows": 12}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "category" in self.fields:
            self.fields["category"].widget.can_add_related = False
            self.fields["category"].widget.can_change_related = False
        if "categories" in self.fields:
            self.fields["categories"].widget.can_add_related = False
            self.fields["categories"].widget.can_change_related = False
            self.fields["categories"].widget.can_delete_related = False
        if "institution_type" in self.fields:
            choices = self.fields["institution_type"].choices
            self.fields["institution_type"].choices = [(k, v) for k, v in choices if k != ""]

        if self.instance and self.instance.id:
            self.fields["source_type"].disabled = True
            if self.instance.source_type and self.instance.source_type == "dcat":
                self.fields["sparql_query"].disabled = True
                self.fields["api_url"].disabled = True
            if "xml_url" in self.fields:
                self.fields["xml_url"].widget = forms.URLInput(attrs={"class": "span6"})
                self.fields["xml_url"].disabled = True
            if "organization" in self.fields and self.instance.organization:
                self.fields["organization"].widget.attrs.update({"class": "span6"})
                self.fields["organization"].disabled = True
            if "source_hash" in self.fields:
                self.fields["source_hash"].widget = forms.TextInput(attrs={"class": "span6"})
                self.fields["source_hash"].disabled = True

    def clean_sparql_query(self):
        try:
            query_val = self.cleaned_data["sparql_query"]
            source_type = self.cleaned_data.get("source_type")
            if source_type and source_type == "dcat" and not query_val:
                raise forms.ValidationError(_("This field is required."))
            return query_val
        except KeyError:
            return ""


class DataSourceImportAdminForm(forms.ModelForm):

    class Meta:
        model = DataSourceImport
        fields = (
            "datasource",
            "start",
            "end",
            "datasets_count",
            "datasets_created_count",
            "datasets_deleted_count",
            "resources_count",
            "resources_created_count",
            "resources_deleted_count",
            "status",
        )
