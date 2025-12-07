import logging
import os
from mimetypes import guess_extension
from typing import Any, Dict, Optional

import magic
from dal import autocomplete, forward
from dateutil.utils import today
from django import forms
from django.conf import settings as dj_settings
from django.contrib.admin.widgets import AdminDateWidget, FilteredSelectMultiple
from django.contrib.postgres.forms.jsonb import JSONField
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile, UploadedFile
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from mcod import settings
from mcod.datasets.models import Dataset
from mcod.lib.field_validators import ContainsLetterValidator
from mcod.lib.forms.mixins import HighValueDataFormValidatorMixin, UnEscapeWidgetMixin
from mcod.lib.metadata_validators import validate_high_value_data_from_ec_list_organization
from mcod.lib.utils import capitalize_first_character
from mcod.lib.widgets import (
    CheckboxSelect,
    CKEditorWidget,
    OpennessScoreStars,
    ResourceDataRulesWidget,
    ResourceDataSchemaWidget,
    ResourceMapsAndPlotsWidget,
)
from mcod.organizations.models import Organization
from mcod.regions.fields import RegionsMultipleChoiceField
from mcod.resources.archives import is_password_protected_archive_file
from mcod.resources.dga_constants import (
    ALLOWED_DGA_INSTITUTIONS,
    DGA_COLUMNS,
    DGA_RESOURCE_EXTENSIONS,
    SAVE_CONFIRMATION_FIELD,
)
from mcod.resources.dga_utils import (
    create_uploaded_file_from_path,
    get_dga_resource_for_institution,
    get_main_dga_resource,
    validate_dga_file_columns,
)
from mcod.resources.models import Resource, ResourceFile, Supplement
from mcod.special_signs.models import SpecialSign
from mcod.unleash import is_enabled

logger = logging.getLogger("mcod")


class ResourceSourceSwitcher(forms.widgets.HiddenInput):
    input_type = "hidden"
    template_name = "admin/forms/widgets/resources/switcher.html"


class ResourceSwitcherField(forms.Field):
    def validate(self, value):
        if value not in ("file", "link"):
            return ValidationError("No option choosed")


class ResourceFileWidget(forms.widgets.FileInput):
    template_name = "admin/forms/widgets/resources/file.html"


class ResourceLinkWidget(forms.widgets.URLInput):
    template_name = "admin/forms/widgets/resources/url.html"


class ResourceListForm(forms.ModelForm):
    link = forms.HiddenInput(attrs={"required": False})
    file = forms.HiddenInput(attrs={"required": False})


def names_repr(names):
    names = map(_, names)
    names = map(str, names)
    names = ", ".join(list(names))
    return names


class MapsJSONField(JSONField):
    def validate(self, value):
        super().validate(value)
        fields = value.get("fields")
        if fields:
            names = [x.get("geo") for x in fields if x.get("geo")]
            self.only_one_x_validator(names)
            self.from_different_sets(names)
            self.complete_group(names)
            self.coordinates_should_be_numeric(fields)

    def only_one_x_validator(self, names):
        ones = {
            "b": _("latitude"),
            "l": _("longitude"),
            "postal_code": _("postal code"),
            "place": _("place"),
            "house_number": _("house number"),
            "uaddress": _("universal address"),
            "label": _("label"),
        }
        for k, v in ones.items():
            if names.count(k) > 1:
                raise ValidationError(
                    f'{_("element")} {v} {_("occured more than once")}. '
                    f'{_("Redefine the map by selecting only once the required element of the map set.")}'
                )

    def from_different_sets(self, names):
        groups = {
            "coordinates": ["b", "l"],
            "uaddress": ["uaddress"],
            "address": ["house_number", "place", "postal_code", "street"],
        }
        membership = set()
        names = set(names)
        if "label" in names:
            names.remove("label")

        for p in names:
            for k, g in groups.items():
                if p in g:
                    membership.add(k)
        if len(membership) > 1:
            err_msg = _("Selected items {} come from different map data sets.").format(names_repr(names))
            err_msg += str(_(" Redefine the map by selecting items from only one map data set."))
            raise ValidationError(err_msg)

    def complete_group(self, names):
        groups = [
            ({"label", "b", "l"}, "geographical coordinates"),
            ({"label", "uaddress"}, "universal address"),
            ({"label", "place", "postal_code"}, "address"),
            ({"label", "house_number", "place", "postal_code"}, "address"),
            ({"label", "house_number", "place", "postal_code", "street"}, "address"),
        ]
        if names:
            names = set(names)

            for g in groups:
                if names == g[0]:
                    return

            if names == {"label"}:
                if self.widget.instance.format == "shp":
                    return
                raise ValidationError(_("The map data set is incomplete."))
            else:
                for g in groups:
                    if names.issubset(g[0]):
                        missing = names_repr(g[0] - names)
                        err_msg = _("Missing elements: {} for the map data set: {}.").format(missing, _(g[1]))
                        err_msg += str(_(" Redefine the map by selecting the selected items."))
                        raise ValidationError(err_msg)

                raise ValidationError(_("The map data set is incomplete."))

    @staticmethod
    def coordinates_should_be_numeric(fields):
        for f in fields:
            geo = f.get("geo")
            f_type = f.get("type")
            if geo == "l" and f_type not in ["integer", "number"]:
                raise ValidationError(_("Longitude should be a number"))
            if geo == "b" and f_type not in ["integer", "number"]:
                raise ValidationError(_("Latitude should be a number"))


class SpecialSignMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.symbol} ({obj.name}) - {obj.description}"


class ResourceForm(forms.ModelForm, HighValueDataFormValidatorMixin):
    title = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 99%", "rows": 2}),
        label=_("Title"),
    )
    title_en = forms.CharField(
        widget=forms.Textarea(attrs={"style": "width: 99%", "rows": 2}),
        label=_("Title") + " (EN)",
        required=False,
    )
    description = forms.CharField(
        widget=CKEditorWidget,
        label=_("Description"),
        min_length=settings.DESCRIPTION_FIELD_MIN_LENGTH,
        max_length=settings.DESCRIPTION_FIELD_MAX_LENGTH,
        validators=[ContainsLetterValidator()],
    )
    description_en = forms.CharField(
        widget=CKEditorWidget,
        label=_("Description") + " (EN)",
        required=False,
        min_length=settings.DESCRIPTION_FIELD_MIN_LENGTH,
        max_length=settings.DESCRIPTION_FIELD_MAX_LENGTH,
        validators=[ContainsLetterValidator()],
    )

    special_signs = SpecialSignMultipleChoiceField(
        queryset=SpecialSign.objects.published(),
        required=False,
        label=_("Special Signs"),
        widget=FilteredSelectMultiple(_("special signs"), False),
    )
    regions = RegionsMultipleChoiceField(required=False, label=_("Regions"))
    has_dynamic_data = forms.ChoiceField(
        label=_("dynamic data").capitalize(),
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Wskazanie TAK oznacza, że zasób jest traktowany jako dane dynamiczne.<br><br>Jeżeli chcesz się "
            'więcej dowiedzieć na temat danych dynamicznych <a href="%(url)s" target="_blank">przejdź do strony'
            "</a>"
        )
        % {"url": f"{settings.BASE_URL}{settings.DYNAMIC_DATA_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    has_high_value_data = forms.ChoiceField(
        label=_("has high value data").capitalize(),
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Wskazanie TAK oznacza, że zasób jest traktowany jako dane o wysokiej wartości.<br><br>Jeżeli chcesz "
            'się więcej dowiedzieć na temat danych o wysokiej wartości <a href="%(url)s" target="_blank">przejdź '
            "do strony</a>"
        )
        % {"url": f"{settings.BASE_URL}{settings.HIGH_VALUE_DATA_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    has_high_value_data_from_ec_list = forms.ChoiceField(
        label=capitalize_first_character(_("has high value data from the EC list")),  # `KE` / `EC` must be uppercase
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Wskazanie TAK oznacza, że zasób jest traktowany jako dane o wysokiej wartości z wykazu KE.<br><br>Jeżeli chcesz "
            'się więcej dowiedzieć na temat danych o wysokiej wartości z wykazu KE <a href="%(url)s" target="_blank">przejdź '
            "do strony</a>"
        )
        % {"url": f"{settings.BASE_URL}{settings.HIGH_VALUE_DATA_FROM_EC_LIST_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    has_research_data = forms.ChoiceField(
        label=_("has research data").capitalize(),
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            "Wskazanie TAK oznacza, że zasób jest traktowany jako dane badawcze.<br><br>Jeżeli chcesz "
            'się więcej dowiedzieć na temat danych badawczych <a href="%(url)s" target="_blank">przejdź '
            "do strony</a>"
        )
        % {"url": f"{settings.BASE_URL}{settings.RESEARCH_DATA_MANUAL_URL}"},
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    contains_protected_data = forms.ChoiceField(
        required=True,
        label=_("Contains protected data list").capitalize(),
        choices=[(True, _("Yes")), (False, _("No"))],
        help_text=(
            f"Wskazanie TAK dla opublikowanego zasobu oznacza, że "
            f"zasób jest traktowany jako aktualny wykaz chronionych "
            f"danych tej instytucji.<br><br> Jeżeli chcesz się "
            f"więcej dowiedzieć na temat chronionych danych "
            f'<a href="{settings.BASE_URL}{settings.PROTECTED_DATA_MANUAL_URL}" '
            f'target="_blank">przejdź do strony</a>'
        ),
        widget=CheckboxSelect(attrs={"class": "inline"}),
    )
    confirm_save = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "related_resource" in self.fields:
            self.fields["related_resource"].label_from_instance = lambda obj: obj.label_from_instance
            self.fields["related_resource"].widget = autocomplete.ModelSelect2(
                url="resource-autocomplete",
                attrs={"data-html": True},
                forward=["dataset", forward.Const(self.instance.id, "id")],
            )
            # https://stackoverflow.com/a/42629593/1845230
            self.fields["related_resource"].widget.choices = self.fields["related_resource"].choices

    def clean_confirm_save(self) -> bool:
        confirm_save_str: str = self.cleaned_data.get(SAVE_CONFIRMATION_FIELD, "false")
        confirm_save: bool = confirm_save_str.lower() == "true"
        return confirm_save

    def clean(self):
        # Create a copy of cleaned data as using `self.add_error` may remove fields from the original dictionary.
        data = super().clean().copy()

        instance_pk: Optional[int] = self.instance.pk
        creating_resource: bool = False if instance_pk else True
        contains_protected_data: bool = data.get("contains_protected_data") == "True"

        if contains_protected_data:
            if creating_resource:
                # get temporary saved file on resource creation
                self._replace_file_on_resource_creation()
            else:
                # use existing file on resource update
                self._replace_file_on_resource_update()

        self._validate_data_date(data)
        self._validate_resource_status(data)
        self._validate_related_resource(data)

        # Check if updating Main DGA Resource
        is_main_dga_resource: bool = self._is_main_dga_resource_updated(instance_pk)

        dataset: Optional[Dataset] = data.get("dataset")
        organization: Optional[Organization]
        # Retrieve organization from dataset object if exists.
        # There is a possibility to pass resource form with dataset with no organization.
        # This leads to an internal server error - see more OTD-1548
        try:
            organization = dataset.organization if dataset else None
        except ObjectDoesNotExist:
            organization = None

        if contains_protected_data:
            self._validate_data_flags_when_contains_protected_data(data)

            # Don't validate DGA file for Main DGA Resource due to specific
            # file structure.
            if not is_main_dga_resource:
                self._validate_dga_file(creating_resource=creating_resource)

            if organization:
                self._validate_institution_when_contains_protected_data(organization)

            # Don't remove DGA flag from other Resource when updating main
            # DGA Resource.
            if not is_main_dga_resource and organization:
                self._remove_dga_flag_from_current_dga_resource_if_needed(data, organization)

        self.validate_high_value_data_flags_conflict(data)
        if organization:
            self._validate_high_value_data_from_ec_list_organization(data, organization)
        return data

    def _validate_data_date(self, data: dict) -> None:
        data_date_err = Resource.get_auto_data_date_errors(data)
        if data_date_err:
            self.add_error(data_date_err.field_name, data_date_err.message)

    def _validate_resource_status(self, data: dict) -> None:
        s62_data_status = data.get("status")
        dataset = data.get("dataset")
        if s62_data_status == "published" and dataset and dataset.status == "draft":
            error_message = _(
                "You can't set status of this resource to published, because "
                "it's dataset is still a draft. "
                "You should first published that dataset: "
            )
            self.add_error("status", mark_safe(error_message + dataset.title_as_link))

    def _validate_related_resource(self, data: dict) -> None:
        related_resource = data.get("related_resource")
        dataset = data.get("dataset")

        if is_enabled("S64_fix_for_status_code_500_when_type_change.be"):
            if dataset and related_resource and related_resource not in Resource.raw.filter(dataset_id=dataset.id):
                self.add_error(
                    "related_resource",
                    _("Only resource from related dataset resources is valid!"),
                )
        else:
            if all(
                (
                    dataset,
                    related_resource,
                    related_resource not in Resource.raw.filter(dataset_id=dataset.id),
                )
            ):
                self.add_error(
                    "related_resource",
                    _("Only resource from related dataset resources is valid!"),
                )

    @staticmethod
    def _is_main_dga_resource_updated(pk):
        if pk is None:
            return False
        main_dga_resource: Optional[Resource] = get_main_dga_resource()
        return pk == main_dga_resource.pk if main_dga_resource else False

    def _validate_data_flags_when_contains_protected_data(self, data: dict) -> None:
        has_dynamic_data: bool = data.get("has_dynamic_data") == "True"
        has_high_value_data: bool = data.get("has_high_value_data") == "True"
        has_high_value_data_from_ec_list: bool = data.get("has_high_value_data_from_ec_list") == "True"
        has_research_data: bool = data.get("has_research_data") == "True"
        if any([has_dynamic_data, has_high_value_data, has_research_data, has_high_value_data_from_ec_list]):
            self.add_error(
                "contains_protected_data",
                _(
                    "To select YES here, select NO in the fields for "
                    "dynamic, high-value, high-value from the EC list and research data."
                ),
            )

    def _validate_institution_when_contains_protected_data(self, organization: Organization) -> None:
        if organization.institution_type not in ALLOWED_DGA_INSTITUTIONS:
            self.add_error(
                "dataset",
                _(
                    "Select the collection of a government institution or "
                    "local government if you mark the resource below as a "
                    "list of protected data."
                ),
            )
            self.add_error(
                "contains_protected_data",
                _("To select YES here, above select the dataset of a " "government or local government institution."),
            )

    def _validate_dga_file(self, creating_resource: bool) -> None:
        file: InMemoryUploadedFile = self.cleaned_data.get("file")
        if file is None:
            return

        extension: Optional[str] = guess_extension(file.content_type)
        if extension is None:
            logger.warning(f"Could not find extension for content type: " f"{file.content_type}")
            self.add_error(
                "file",
                _(
                    "Pick a file from disk in xls, xlsx or csv format if "
                    "you mark the resource below as a list of protected "
                    "data."
                ),
            )
            return
        extension = extension[1:]
        if extension not in DGA_RESOURCE_EXTENSIONS:
            if creating_resource:
                self.add_error(
                    "file",
                    _(
                        "Pick a file from disk in xls, xlsx or csv format if "
                        "you mark the resource below as a list of protected "
                        "data."
                    ),
                )
            # can't add err message to not existing field "file" while updating
            else:
                self.add_error(
                    "contains_protected_data",
                    _("The resource has a different type than csv, xls or " "xlsx format."),
                )
            return

        valid_dga_columns: bool = validate_dga_file_columns(file, extension)
        if not valid_dga_columns:
            if creating_resource:
                self.add_error(
                    "file",
                    _(
                        "The resource labeled below as a list of "
                        "protected data can only contain columns named "
                        "in this order: "
                    )
                    + ", ".join(DGA_COLUMNS)
                    + ".",
                )
            # can't add err message to not existing field "file" while updating
            else:
                self.add_error(
                    "contains_protected_data",
                    _("The saved file has a different structure than that " "required for the list of protected data."),
                )

    def _remove_dga_flag_from_current_dga_resource_if_needed(
        self,
        data: dict,
        organization: Organization,
    ) -> None:
        organization_id: int = organization.pk
        exclude_object_id: Optional[int] = self.instance.pk if self.instance else None
        try:
            current_dga_resource = get_dga_resource_for_institution(organization_id, exclude_object_id)
        except MultipleObjectsReturned:
            self.add_error(
                "contains_protected_data",
                _("There is more than one resource containing protected data"),
            )
            return

        save_not_confirmed: bool = not data.get("confirm_save")
        not_publish: bool = self.data.get("status") != "published"
        if any((self.errors, save_not_confirmed, not_publish)):
            return
        if current_dga_resource:
            current_dga_resource.contains_protected_data = False
            current_dga_resource.save()

    def _replace_file_on_resource_creation(self):
        """
        Updates cleaned_data with path to temporarily created file.
        """
        # link is not allowed for dga resource
        if self.cleaned_data.get("link"):
            self.add_error(
                "link",
                _(
                    "Pick a file from disk in xls, xlsx or csv format if "
                    "you mark the resource below as a list of protected "
                    "data."
                ),
            )
            return
        # after dga save confirmation we get file_ref instead of file
        file_ref: SimpleUploadedFile = self.cleaned_data.get("file_ref")
        if file_ref:
            self.cleaned_data["file"] = file_ref

    def _replace_file_on_resource_update(self):
        file = self.instance.main_file
        if not file:
            self.add_error(
                "contains_protected_data",
                _("The resource has a different type than csv, xls or xlsx " "format."),
            )
            return

        existing_file = create_uploaded_file_from_path(file.path)
        if existing_file:
            self.cleaned_data["file"] = existing_file
        else:
            self.add_error(
                "contains_protected_data",
                _("Cannot read existing file") + f": {file.name}.",
            )

    def _validate_high_value_data_from_ec_list_organization(
        self,
        data: Dict[str, Any],
        organization: Organization,
    ) -> None:
        has_high_value_data_from_ec_list: bool = data.get("has_high_value_data_from_ec_list") == "True"

        try:
            validate_high_value_data_from_ec_list_organization(has_high_value_data_from_ec_list, organization.institution_type)
        except ValidationError:
            self.add_error(
                "has_high_value_data_from_ec_list",
                _("Data of private or developer institutions are not high-value data from EC list."),
            )


class ChangeResourceForm(ResourceForm, UnEscapeWidgetMixin):
    openness_score = forms.IntegerField(
        widget=OpennessScoreStars(),
        label=_("Openness score"),
        disabled=True,
        required=False,
    )

    tabular_data_schema = JSONField(widget=ResourceDataSchemaWidget(), required=False)
    data_rules = JSONField(widget=ResourceDataRulesWidget(), required=False)
    maps_and_plots = MapsJSONField(widget=ResourceMapsAndPlotsWidget(), required=False)

    def __init__(self, *args, **kwargs):
        if "instance" in kwargs:
            _instance: Resource = kwargs["instance"]
            kwargs["initial"] = {
                "data_rules": _instance.tabular_data_schema,
                "maps_and_plots": _instance.tabular_data_schema,
            }

        super().__init__(*args, **kwargs)
        if hasattr(self, "instance"):
            self._add_unescape_widget_for_fields_or_not()
            if is_enabled("S64_fix_for_status_code_500_when_type_change.be"):
                if self.instance.is_imported_from_xml:
                    self._set_fields_required_attribute_to_false()

            self.instance: Resource
            self.fields["tabular_data_schema"].widget.instance = self.instance
            self.fields["data_rules"].widget.instance = self.instance
            self.fields["maps_and_plots"].widget.instance = self.instance
            if "regions" in self.fields:
                self.fields["regions"].choices = self.instance.regions.all().values_list("region_id", "hierarchy_label")

            if is_enabled("S64_fix_for_status_code_500_when_type_change.be"):
                if self.instance and self.instance.pk and self.instance.is_imported:
                    self.data = self.data.copy()  # Make self.data mutable
                    self.data = self._modify_data_for_imported(self.data, self.instance)

    def _set_fields_required_attribute_to_false(self) -> None:
        """
        Change fields behavior for resources imported from XML harvester. For example:
        If resource is imported from XML harvester with schema 1.0, some fields are not required,
        so we have to change form behavior -> change fields to be not required.
        Note: this is temporary solution, should be changed in the future -> https://jira.coi.gov.pl/browse/OTD-1259
        """
        if self.instance.has_dynamic_data is None:
            self.fields["has_dynamic_data"].required = False
        if self.instance.has_high_value_data is None:
            self.fields["has_high_value_data"].required = False
        if self.instance.has_high_value_data_from_ec_list is None:
            self.fields["has_high_value_data_from_ec_list"].required = False
        if self.instance.has_research_data is None:
            self.fields["has_research_data"].required = False

    @staticmethod
    def _modify_data_for_imported(data: Dict, instance: Resource) -> Dict:
        """
        Ensure required fields are included in the Django form.

        Imported (harvested) resource form fields are read-only, meaning their required values
        must be manually added from the instance data. When a new required field is added
        to this form, Django Admin does not pass it to the form instance automatically.
        Instead, we retrieve it directly from the associated Resource instance to ensure
        valid form submission.
        """
        data["has_dynamic_data"] = instance.has_dynamic_data
        data["has_high_value_data"] = instance.has_high_value_data
        data["has_research_data"] = instance.has_research_data
        data["contains_protected_data"] = instance.contains_protected_data
        data["has_high_value_data_from_ec_list"] = instance.has_high_value_data_from_ec_list
        return data

    def clean(self):
        data = super().clean()
        # `tabular_data_schema` field's widget modifies original `self.instance.tabular_data_schema`
        # then `maps_and_plots` field's widget makes use (and also modify) `self.instance.tabular_data_schema`.
        # Thanks to that `maps_and_plots` validators can make use of newest (if modified) column types.
        # In the result, the correct new value of `tabular_data_schema` is in both:
        # - `self.instance.tabular_data_schema` and `data['maps_and_plots']`.
        # TODO refactor
        data["tabular_data_schema"] = self.instance.tabular_data_schema
        return data

    class Meta:
        model = Resource
        exclude = [
            "old_resource_type",
        ]
        labels = {
            "created": _("Availability date"),
            "modified": _("Modification date"),
            "verified": _("Update date"),
            "is_chart_creation_blocked": _("Do not allow user charts to be created"),
            "main_file": _("File"),
            "csv_converted_file": _("File as CSV"),
            "jsonld_converted_file": _("File as JSON-LD"),
            "main_file_info": _("File info"),
            "main_file_encoding": _("File encoding"),
        }


class LinkOrFileUploadForm(forms.ModelForm):
    switcher = ResourceSwitcherField(label=_("Data source"), widget=ResourceSourceSwitcher)
    file = forms.FileField(label=_("File"), widget=ResourceFileWidget)
    link = forms.URLField(widget=ResourceLinkWidget(attrs={"style": "width: 99%"}))

    def clean_link(self):
        value = self.cleaned_data.get("link")
        if not value:
            return None
        return value

    def clean_switcher(self):
        switcher_field = self.fields["switcher"]
        selected_field = switcher_field.widget.value_from_datadict(self.data, self.files, self.add_prefix("switcher"))
        if self.instance and self.instance.id:
            self.fields["link"].required = self.fields["file"].required = False
            return selected_field

        if selected_field == "file":
            self.fields["link"].required = False
        elif selected_field == "link":
            self.fields["file"].required = False

        return selected_field


class AddResourceForm(ResourceForm, LinkOrFileUploadForm):
    data_date = forms.DateField(initial=today, widget=AdminDateWidget, label=_("Data date"))
    from_resource = forms.ModelChoiceField(queryset=Resource.objects.all(), widget=forms.HiddenInput(), required=False)
    link = forms.URLField(widget=ResourceLinkWidget(attrs={"style": "width: 99%", "placeholder": "https://"}))
    file_ref = forms.CharField(required=False)

    regions_ = RegionsMultipleChoiceField(required=False, label=_("Regions"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file_ref = self.data.get("file_ref")
        if file_ref:
            self.fields["file"].required = False

    def clean_file_ref(self):
        file_ref = self.cleaned_data.get("file_ref")
        if file_ref:
            file_path = f"{dj_settings.DGA_RESOURCE_CREATION_STAGING_ROOT}/{file_ref}"
            try:
                return create_uploaded_file_from_path(file_path)
            except IOError:
                self.add_error("file", _("Cannot read the file"))

    def clean_link(self):
        link = super().clean_link()
        if link and not link.startswith("https:"):
            self.add_error("link", _("Required scheme is https://"))
        return link

    def clean_switcher(self):
        selected_field = super().clean_switcher()
        if selected_field == "link":
            self.fields["data_date"].required = False

    def clean_data_date(self):
        data_date = self.cleaned_data.get("data_date")
        if not data_date:
            self.cleaned_data["data_date"] = today()
        return self.cleaned_data["data_date"]

    def clean_file(self):
        file: Optional[UploadedFile] = self.cleaned_data.get("file")
        if file:
            _name, ext = os.path.splitext(file.name)
            if ext.lower() not in settings.SUPPORTED_FILE_EXTENSIONS:
                self.add_error("file", _("Invalid file extension: %(ext)s.") % {"ext": ext or "-"})
            elif is_password_protected_archive_file(file.file):
                self.add_error("file", _("Password protected archives are not allowed."))
        return file


class AddResourceInlineForm(AddResourceForm):
    # Setting DGA flag is disallowed in the inline flow because validating
    # business rules (that only a single DGA resource exists in a Dataset)
    # would add too much technical complexity
    contains_protected_data = forms.CharField(initial="False", widget=forms.HiddenInput(), required=False)


class TrashResourceForm(forms.ModelForm):
    def clean_is_removed(self):
        dataset = self.instance.dataset

        if self.cleaned_data["is_removed"] is False and dataset.is_removed:
            error_message = _(
                "You can't restore this resource, because it's dataset is still removed. Please first restore dataset: "
            )

            error_message += "<a href='{}'>{}</a>".format(dataset.admin_trash_change_url, dataset.title)

            raise forms.ValidationError(mark_safe(error_message))

        return self.cleaned_data["is_removed"]


class ResourceInlineFormset(forms.models.BaseInlineFormSet):
    def save_new(self, form, commit=True):
        file = None
        if commit:
            file = form.cleaned_data.pop("file")
            form.instance.file = None
        instance = super().save_new(form, commit=commit)
        if file and instance.pk:
            ResourceFile.objects.create(resource=instance, is_main=True, file=file)
        # hack for dealing with bug described in https://code.djangoproject.com/ticket/12203 and
        # https://code.djangoproject.com/ticket/22852
        # It allows saving regions which are ManyToMany field with custom through model in InlineModelAdmin
        regions_data = form.cleaned_data.get("regions_")
        if regions_data and instance.id:
            for f in instance._meta.many_to_many:
                if f.name == "regions":
                    f.save_form_data(instance, regions_data)
        return instance


class SupplementForm(forms.ModelForm):
    class Meta:
        model = Supplement
        fields = "__all__"
        labels = {
            "file": _("Add file"),
            "name": _("Document name"),
            "name_en": _("Document name") + " (EN)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # hack to validate empty forms in formset, more:
        # https://stackoverflow.com/questions/4481366/django-and-empty-formset-are-valid
        self.empty_permitted = False

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            file_error = _("The wrong document format was selected!")
            mime = magic.from_buffer(file.read(2048), mime=True)
            if mime not in settings.ALLOWED_SUPPLEMENT_MIMETYPES:
                self.add_error("file", file_error)
            has_txt_extension = file.name.lower().endswith(".txt")
            if mime == "text/plain" and not has_txt_extension:
                self.add_error("file", file_error)
        return file
