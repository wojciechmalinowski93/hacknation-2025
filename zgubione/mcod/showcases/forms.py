from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.postgres.forms.jsonb import JSONField
from django.templatetags.static import static
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from mcod.core.db.models import STATUS_CHOICES
from mcod.core.widgets import ExtendedSelect
from mcod.datasets.models import Dataset
from mcod.lib.forms.mixins import UnEscapeWidgetMixin
from mcod.lib.widgets import CKEditorUploadingWidget, ExternalDatasetsWidget
from mcod.showcases.models import Showcase, ShowcaseProposal
from mcod.tags.forms import ModelFormWithKeywords


def get_link_label(icon, name):
    icon = static(f"/showcases/icons/{icon}")
    text = _("link to the application")
    return mark_safe(f'<img src="{icon}" alt="logo" /> {name} - {text}')


class ShowcaseForm(ModelFormWithKeywords, UnEscapeWidgetMixin):
    title = forms.CharField(
        required=True,
        label=_("Title"),
        max_length=300,
        widget=forms.Textarea(attrs={"style": "width: 99%", "rows": 2}),
    )
    slug = forms.CharField(required=False)
    notes = forms.CharField(widget=CKEditorUploadingWidget, required=True, label=_("Notes"))
    notes_en = forms.CharField(widget=CKEditorUploadingWidget, required=False, label=_("Notes") + " (EN)")
    datasets = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(status=STATUS_CHOICES[0][0]),
        required=False,
        widget=FilteredSelectMultiple(_("datasets"), False),
        label=_("Dataset"),
    )
    external_datasets = JSONField(label=_("External datasets"), widget=ExternalDatasetsWidget(), required=False)

    class Meta:
        model = Showcase
        fields = [
            "category",
            "title",
            "slug",
            "is_mobile_app",
            "mobile_apple_url",
            "mobile_google_url",
            "is_desktop_app",
            "desktop_windows_url",
            "desktop_linux_url",
            "desktop_macos_url",
            "license_type",
            "notes",
            "author",
            "external_datasets",
            "url",
            "image",
            "illustrative_graphics",
            "illustrative_graphics_alt",
            "main_page_position",
            "status",
            "datasets",
            "tags",
        ]
        labels = {
            "desktop_linux_url": get_link_label("ic-linux.svg", "Linux"),
            "desktop_macos_url": get_link_label("ic-apple.svg", "MacOS"),
            "desktop_windows_url": get_link_label("ic-windows.svg", "Windows"),
            "mobile_apple_url": get_link_label("ic-apple.svg", "iOS"),
            "mobile_google_url": get_link_label("ic-android.svg", "Android"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._add_unescape_widget_for_fields_or_not()
        url_field_names = [
            "mobile_apple_url",
            "mobile_google_url",
            "desktop_windows_url",
            "desktop_linux_url",
            "desktop_macos_url",
        ]
        url_fields = [x for x in self.fields if x in url_field_names]
        for name in url_fields:
            css_class = self.fields[name].widget.attrs.get("class", "")
            css_class += " span12"
            self.fields[name].widget.attrs.update({"placeholder": "https://", "class": css_class})

    def clean(self):
        data = super().clean()
        category = data.get("category")
        is_mobile_app = data.get("is_mobile_app", False)
        is_desktop_app = data.get("is_desktop_app", False)
        license_type = data.get("license_type")
        mobile_apple_url = data.get("mobile_apple_url")
        mobile_google_url = data.get("mobile_google_url")
        desktop_linux_url = data.get("desktop_linux_url")
        desktop_macos_url = data.get("desktop_macos_url")
        desktop_windows_url = data.get("desktop_windows_url")

        if category in ("app", "www"):
            if not license_type:
                self.add_error("license_type", _("This field is required!"))
        else:
            data["license_type"] = ""
        if is_mobile_app and not any([mobile_apple_url, mobile_google_url]):
            self.add_error(None, _("At least one url for mobile app (iOS, Android) is required!"))

        if is_desktop_app and not any([desktop_linux_url, desktop_macos_url, desktop_windows_url]):
            self.add_error(
                None,
                _("At least one url for desktop app (Windows, Linux, MacOS) is required!"),
            )

        return data


class ShowcaseProposalForm(forms.ModelForm):

    class Meta:
        model = ShowcaseProposal
        fields = [
            "category",
            "title",
            "url",
            "notes",
            "applicant_email",
            "author",
            "keywords",
            "comment",
            "report_date",
            "decision",
            "decision_date",
        ]
        labels = {
            "decision": _("Decision made"),
            "title": _("Name"),
            "url": _("Application link / Application info page address"),
        }
        widgets = {
            "comment": forms.Textarea(attrs={"rows": "1", "class": "input-block-level"}),
            "decision": ExtendedSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["decision"].required = True
