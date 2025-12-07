import nested_admin
from django import forms
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _

from mcod.laboratory.models import LabEvent, LabEventTrash, LabReport
from mcod.lib.admin_mixins import HistoryMixin, ModelAdmin, TrashMixin
from mcod.resources.forms import LinkOrFileUploadForm


class AddReportForm(LinkOrFileUploadForm):
    pass


class ReportsFormset(BaseInlineFormSet):
    def clean(self):
        _forms = [form for form in self.forms if form.is_valid() and form not in self.deleted_forms]
        if len(_forms) == 0:
            return
        if self.data.get("event_type") == "analysis" and len(_forms) > 1:
            raise forms.ValidationError(_("Analysis can have only one report assigned"))


class AddReportStacked(nested_admin.NestedStackedInline):
    template = "admin/laboratory/report-inline-new.html"
    model = LabReport
    form = AddReportForm
    formset = ReportsFormset
    fields = ("switcher", "file", "link")

    extra = 0
    min_num = 0
    max_num = 2


class LabEventAdmin(HistoryMixin, ModelAdmin):
    actions_on_top = True
    is_history_other = True
    lang_fields = True
    list_display = ["title", "event_type", "execution_date"]
    search_fields = ["title", "notes"]
    soft_delete = True

    inlines = [AddReportStacked]

    @property
    def suit_form_tabs(self):
        return [
            ("general", _("General")),
        ]

    def save_model(self, request, obj, form, change):
        if not obj.id:
            obj.created_by = request.user
        obj.modified_by = request.user
        obj.save()

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": (
                        "title",
                        "event_type",
                        "notes",
                        "execution_date",
                        "status",
                    ),
                },
            )
        ]
        fieldsets += self.get_translations_fieldsets()
        fieldsets[1][1]["fields"].remove("slug_en")
        return fieldsets

    class Media:
        css = {"all": ("admin/css/laboratory.css",)}


class LabEventTrashAdmin(HistoryMixin, TrashMixin):
    readonly_fields = (
        "title",
        "notes",
        "event_type",
        "status",
    )
    fields = [field for field in readonly_fields] + ["is_removed"]
    is_history_other = True


admin.site.register(LabEvent, LabEventAdmin)
admin.site.register(LabEventTrash, LabEventTrashAdmin)
