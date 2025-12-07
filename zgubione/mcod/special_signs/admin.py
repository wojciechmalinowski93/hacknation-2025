from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from mcod.lib.admin_mixins import HistoryMixin, ModelAdmin
from mcod.special_signs.forms import SpecialSignAdminForm
from mcod.special_signs.models import SpecialSign


class SpecialSignAdminMixin:
    is_history_other = True
    list_display = ("symbol", "name", "_description", "obj_history")

    def _description(self, obj):
        return obj.description

    _description.short_description = _("description")
    _description.admin_order_field = "description"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class SpecialSignAdmin(SpecialSignAdminMixin, HistoryMixin, ModelAdmin):

    actions_on_top = True
    delete_selected_msg = _("Delete selected special signs")
    form = SpecialSignAdminForm
    lang_fields = True
    soft_delete = True

    @property
    def suit_form_tabs(self):
        return (
            ("general", _("General")),
            *self.get_translations_tabs(),
        )

    def has_delete_permission(self, request, obj=None):
        has_delete_permission = super().has_delete_permission(request, obj=obj)
        if obj and obj.special_signs_resources.exists():
            return False
        return has_delete_permission

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
                        "symbol",
                        "name",
                        "description",
                    ),
                },
            ),
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": ("status",),
                },
            ),
        ]
        translations_fieldsets = self.get_translations_fieldsets()
        for title, fieldset in translations_fieldsets:
            fieldset["fields"] = [x for x in fieldset.get("fields", []) if x != "slug_en"]
        fieldsets += translations_fieldsets
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj=obj)
        if obj:
            readonly_fields += ("symbol",)
        return readonly_fields


admin.site.register(SpecialSign, SpecialSignAdmin)
