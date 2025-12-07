from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote as urlquote

import nested_admin
from auditlog.admin import LogEntryAdmin as BaseLogEntryAdmin
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import quote, unquote
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.template.defaultfilters import truncatewords
from django.template.response import TemplateResponse
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.timezone import now
from django.utils.translation import gettext, gettext_lazy as _, pgettext_lazy
from modeltrans.translator import get_i18n_field
from modeltrans.utils import get_language
from rules.contrib.admin import (
    ObjectPermissionsModelAdmin as BaseObjectPermissionsModelAdmin,
    ObjectPermissionsStackedInline as BaseObjectPermissionsStackedInline,
)
from suit.admin import SortableStackedInline as BaseSortableStackedInline, SortableStackedInlineBase

from mcod import settings
from mcod.datasets.models import Dataset
from mcod.harvester.models import DataSourceImport
from mcod.histories.models import LogEntry
from mcod.reports.tasks import (
    generate_csv,
    generate_harvesters_imports_report,
    generate_harvesters_last_imports_report,
)
from mcod.tags.views import TagAutocompleteJsonView


class MCODChangeList(ChangeList):

    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        if hasattr(self.model, "accusative_case"):
            if self.is_popup:
                title = gettext("Select %s")
            elif self.model_admin.has_change_permission(request):
                title = gettext("Select %s to change")
            else:
                title = gettext("Select %s to view")
            self.title = title % self.model.accusative_case()


class MCODTrashChangeList(ChangeList):

    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.title = self.model._meta.verbose_name_plural.capitalize()


class TagAutocompleteMixin:
    def autocomplete_view(self, request):
        return TagAutocompleteJsonView.as_view(model_admin=self)(request)


class DecisionFilter(admin.SimpleListFilter):
    parameter_name = "decision"
    title = _("decision")
    template = "admin/decision_filter.html"

    def lookups(self, request, model_admin):
        return (
            ("taken", _("Decision taken")),
            ("not_taken", _("Decision not taken")),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == "taken":
            return queryset.with_decision()
        elif val == "not_taken":
            return queryset.without_decision()
        return queryset


def export_to_csv(self, request, queryset):
    generate_csv.s(
        tuple(obj.id for obj in queryset),
        self.model._meta.label,
        request.user.id,
        now().strftime("%Y%m%d%H%M%S.%s"),
    ).apply_async_on_commit()
    messages.add_message(request, messages.SUCCESS, _("Task for CSV generation queued"))


export_to_csv.short_description = _("Export selected to CSV")


class ExportCsvMixin:

    export_to_csv = False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.export_to_csv and request.user.is_superuser:
            actions.update(
                {
                    "export_to_csv": (
                        export_to_csv,
                        "export_to_csv",
                        _("Export selected to CSV"),
                    )
                }
            )
        return actions


class SoftDeleteMixin:
    """
    Overrides default queryset.delete() call from base class.
    """

    soft_delete = False

    def delete_queryset(self, request, queryset):
        if self.soft_delete:
            for instance in queryset:
                instance.delete(soft=True)
        else:
            super().delete_queryset(request, queryset)


class CRUDMessageMixin:
    """
    Overrides default messages displayed for user after successful saving of instance.
    """

    obj_gender = None  # options: f=feminine, n=neuter.

    add_msg_template = _('The {name} "{obj}" was added successfully.')
    add_msg_template_f = pgettext_lazy('The {name} "{obj}" was added successfully.', "feminine")
    add_msg_template_n = pgettext_lazy('The {name} "{obj}" was added successfully.', "neuter")

    add_continue_msg_template = _('The {name} "{obj}" was added successfully.')
    add_continue_msg_template_f = pgettext_lazy('The {name} "{obj}" was added successfully.', "feminine")
    add_continue_msg_template_n = pgettext_lazy('The {name} "{obj}" was added successfully.', "neuter")

    add_addanother_msg_template = _('The {name} "{obj}" was added successfully. You may add another {name} below.')
    add_addanother_msg_template_f = pgettext_lazy(
        'The {name} "{obj}" was added successfully. You may add another {name} below.',
        "feminine",
    )
    add_addanother_msg_template_n = pgettext_lazy(
        'The {name} "{obj}" was added successfully. You may add another {name} below.',
        "neuter",
    )

    change_msg_template = _('The {name} "{obj}" was changed successfully.')
    change_msg_template_f = pgettext_lazy('The {name} "{obj}" was changed successfully.', "feminine")
    change_msg_template_n = pgettext_lazy('The {name} "{obj}" was changed successfully.', "neuter")

    change_continue_msg_template = _('The {name} "{obj}" was changed successfully. You may edit it again below.')
    change_continue_msg_template_f = pgettext_lazy(
        'The {name} "{obj}" was changed successfully. You may edit it again below.',
        "feminine",
    )
    change_continue_msg_template_n = pgettext_lazy(
        'The {name} "{obj}" was changed successfully. You may edit it again below.',
        "neuter",
    )

    change_saveasnew_msg_template = _('The {name} "{obj}" was added successfully. You may edit it again below.')
    change_saveasnew_msg_template_f = pgettext_lazy(
        'The {name} "{obj}" was added successfully. You may edit it again below.',
        "feminine",
    )
    change_saveasnew_msg_template_n = pgettext_lazy(
        'The {name} "{obj}" was added successfully. You may edit it again below.',
        "neuter",
    )

    change_addanother_msg_template = _('The {name} "{obj}" was changed successfully. You may add another {name} below.')
    change_addanother_msg_template_f = pgettext_lazy(
        'The {name} "{obj}" was changed successfully. You may add another {name} below.',
        "feminine",
    )
    change_addanother_msg_template_n = pgettext_lazy(
        'The {name} "{obj}" was changed successfully. You may add another {name} below.',
        "neuter",
    )

    delete_msg_template = _('The %(name)s "%(obj)s" was deleted successfully.')
    delete_msg_template_f = pgettext_lazy('The %(name)s "%(obj)s" was deleted successfully.', "feminine")
    delete_msg_template_n = pgettext_lazy('The %(name)s "%(obj)s" was deleted successfully.', "neuter")

    def get_msg_template(self, template_name):
        if self.obj_gender in ["f", "n"]:
            template_name = f"{template_name}_{self.obj_gender}"
        return getattr(self, template_name)

    def response_add(self, request, obj, post_url_continue=None):
        if "_popup" in request.POST:
            return super().response_add(request, obj, post_url_continue=post_url_continue)

        opts = obj._meta
        preserved_filters = self.get_preserved_filters(request)
        obj_url = reverse(
            "admin:%s_%s_change" % (opts.app_label, opts.model_name),
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        # Add a link to the object's change form if the user can edit the obj.
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', urlquote(obj_url), obj)
        else:
            obj_repr = str(obj)
        msg_dict = {
            "name": opts.verbose_name.capitalize(),
            "obj": obj_repr,
        }
        if "_continue" in request.POST or (
            # Redirecting after "Save as new".
            "_saveasnew" in request.POST
            and self.save_as_continue
            and self.has_change_permission(request, obj)
        ):

            msg = self.get_msg_template("add_continue_msg_template")
            if self.has_change_permission(request, obj):
                msg += " " + gettext("You may edit it again below.")
            self.message_user(request, format_html(msg, **msg_dict), messages.SUCCESS)
            if post_url_continue is None:
                post_url_continue = obj_url
            post_url_continue = add_preserved_filters(
                {"preserved_filters": preserved_filters, "opts": opts},
                post_url_continue,
            )
            return HttpResponseRedirect(post_url_continue)

        elif "_addanother" in request.POST:
            msg = format_html(self.get_msg_template("add_addanother_msg_template"), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)
        else:
            msg = format_html(self.get_msg_template("add_msg_template"), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_add(request, obj)

    def _get_obj_url(self, request, obj):
        obj_url = getattr(obj, "admin_change_url", None) or urlquote(request.path)
        if self.model._meta.proxy and not obj.is_removed:
            opts = self.model._meta.concrete_model._meta
            obj_url = reverse(
                "admin:%s_%s_change" % (opts.app_label, opts.model_name),
                args=(obj.pk,),
                current_app=self.admin_site.name,
            )
        return obj_url

    def response_change(self, request, obj):
        if "_popup" in request.POST:
            return super().response_change(request, obj)

        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)

        obj_url = self._get_obj_url(request, obj)
        msg_dict = {
            "name": opts.verbose_name.capitalize(),
            "obj": format_html('<a href="{}">{}</a>', obj_url, truncatewords(obj, 18)),
        }
        if "_continue" in request.POST:
            msg = format_html(self.get_msg_template("change_continue_msg_template"), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_saveasnew" in request.POST:
            msg = format_html(self.get_msg_template("change_saveasnew_msg_template"), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse(
                "admin:%s_%s_change" % (opts.app_label, opts.model_name),
                args=(obj.pk,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_addanother" in request.POST:
            msg = format_html(self.get_msg_template("change_addanother_msg_template"), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse(
                "admin:%s_%s_add" % (opts.app_label, opts.model_name),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = format_html(self.get_msg_template("change_msg_template"), **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_change(request, obj)

    def response_delete(self, request, obj_display, obj_id):
        opts = self.model._meta

        if "_popup" in request.POST:
            popup_response_data = json.dumps(
                {
                    "action": "delete",
                    "value": str(obj_id),
                }
            )
            return TemplateResponse(
                request,
                self.popup_response_template
                or [
                    "admin/%s/%s/popup_response.html" % (opts.app_label, opts.model_name),
                    "admin/%s/popup_response.html" % opts.app_label,
                    "admin/popup_response.html",
                ],
                {
                    "popup_response_data": popup_response_data,
                },
            )

        self.message_user(
            request,
            self.get_msg_template("delete_msg_template")
            % {
                "name": opts.verbose_name.capitalize(),
                "obj": truncatewords(obj_display, 18),
            },
            messages.SUCCESS,
        )

        if self.has_change_permission(request, None):
            post_url = reverse(
                "admin:%s_%s_changelist" % (opts.app_label, opts.model_name),
                current_app=self.admin_site.name,
            )
            preserved_filters = self.get_preserved_filters(request)
            post_url = add_preserved_filters({"preserved_filters": preserved_filters, "opts": opts}, post_url)
        else:
            post_url = reverse("admin:index", current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)


class MCODAdminMixin:
    @property
    def admin_url(self):
        opts = self.model._meta
        changelist_url = "admin:%s_%s_changelist" % (opts.app_label, opts.model_name)
        return reverse(changelist_url)

    def get_changelist(self, request, **kwargs):
        return MCODChangeList

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        if hasattr(self.model, "accusative_case"):
            if add:
                title = _("Add %s")
            elif self.has_change_permission(request, obj):
                title = _("Change %s")
            else:
                title = _("View %s")
            context["title"] = title % self.model.accusative_case()
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)


class AdminListMixin:

    class Media:
        css = {"all": ("./fontawesome/css/all.min.css",)}

    task_status_to_css_class = {
        "SUCCESS": "fas fa-check text-success",
        "PENDING": "fas fa-question-circle text-warning",
        "FAILURE": "fas fa-times-circle text-error",
        None: "fas fa-minus-circle text-light",
        "": "fas fa-minus-circle text-light",
    }

    task_status_tooltip = {
        "SUCCESS": _("Correct Validation"),
        "PENDING": _("Validation in progress"),
        "FAILURE": _("Validation failed"),
        None: _("No validation"),
        "": _("No validation"),
    }

    def _format_list_status(self, val):
        return format_html(f'<i class="{self.task_status_to_css_class[val]}"' f' title="{self.task_status_tooltip[val]}"></i>')


class ListDisplayMixin:

    STATUS_CSS_CLASSES = {
        "accepted": "label label-success",
        "active": "label label-success",
        "awaits": "label label-warning",
        "blocked": "label label-important",
        "draft": "label label-warning",
        "error": "label label-important",
        "FAILURE": "label label-important",
        "inactive": "label",
        "pending": "label label-warning",
        "PENDING": "label label-warning",
        "publication_finished": "label label-info",
        "published": "label label-success",
        "rejected": "label label-important",
        "sent": "label label-success",
        "SUCCESS": "label label-success",
    }
    label_attributes = [
        "status",
        "created_by",
        "decision",
        "ordered_by",
        "state",
    ]

    def replace_attributes(self, items):
        for val in self.label_attributes:
            items = [item if item not in [val, f"_{val}"] else f"{val}_label" for item in items]
        return items

    def created_by_label(self, obj):
        return self._format_user_display(obj.created_by.email if obj.created_by else "")

    created_by_label.admin_order_field = "created_by"
    created_by_label.short_description = _("Created by")

    def get_status_label(self, obj):
        return obj.STATUS[obj.status]

    def get_status_value(self, obj):
        return obj.status

    def status_label(self, obj):
        return self._format_label(obj, "status")

    status_label.admin_order_field = "status"
    status_label.short_description = _("status")

    def _format_label(self, obj, labeled_attribute):
        self_get_label_fn = getattr(self, f"get_{labeled_attribute}_label")
        self_get_value_fn = getattr(self, f"get_{labeled_attribute}_value")
        return format_html(
            f'<span class="{self.STATUS_CSS_CLASSES.get(self_get_value_fn(obj), "label")}">' f"{self_get_label_fn(obj)}</span>"
        )

    @staticmethod
    def _format_user_display(val, default="Brak"):
        user, host = val.split("@") if val and "@" in val else (None, None)
        if user and host:
            return format_html(
                f'<span class="email-label-user" title="{val}">{user}</span>' f'<span class="email-label-host">{host}</span>'
            )
        return default


class AdminInlineLangMixin:

    use_translated_fields = False

    def get_lang_fields(self):
        i18n_field = get_i18n_field(self.model)
        fields = []
        for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES:
            if lang_code == settings.LANGUAGE_CODE:
                continue
            lang_fields = [f"{field.name}" for field in i18n_field.get_translated_fields() if field.name.endswith(lang_code)]
            fields.extend(lang_fields)
        return fields

    def extend_by_lang_fields(self, orig_fields):
        if self.use_translated_fields:
            extended_fields = []
            i18n_fields = self.get_lang_fields()
            fields_map = defaultdict(list)
            for field in i18n_fields:
                if field not in orig_fields:
                    fields_map[field.rsplit("_", 1)[0]].append(field)
            for field in orig_fields:
                extended_fields.append(field)
                if field in orig_fields:
                    extended_fields.extend(fields_map[field])
            return extended_fields
        return orig_fields


class NestedStackedInline(AdminInlineLangMixin, nested_admin.NestedStackedInline):
    pass


class SortableNestedStackedInline(SortableStackedInlineBase, NestedStackedInline):
    pass


class StackedInline(AdminInlineLangMixin, admin.StackedInline):
    pass


class TabularInline(ListDisplayMixin, AdminListMixin, admin.TabularInline):
    pass


class SortableStackedInline(BaseSortableStackedInline):

    template = "admin/edit_inline/_stacked.html"

    def get_formset(self, request, obj=None, **kwargs):
        # https://stackoverflow.com/questions/1206903/how-do-i-require-an-inline-in-the-django-admin/53868121#53868121
        formset = super().get_formset(request, obj=obj, **kwargs)
        formset.validate_min = True
        return formset


class LangFieldsOnlyMixin:

    lang_fields = False

    def get_form(self, request, obj=None, **kwargs):
        if self.lang_fields:
            i18n_field = get_i18n_field(self.model)
            language = get_language()

            for field in i18n_field.get_translated_fields():
                if field.language == language:
                    field.blank = field.original_field.blank

        return super().get_form(request, obj=obj, **kwargs)

    def get_translations_fieldsets(self):
        i18n_field = get_i18n_field(self.model)
        fieldsets = []
        for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES:
            if lang_code == settings.LANGUAGE_CODE:
                continue
            tab_name = "general" if lang_code == settings.LANGUAGE_CODE else f"lang-{lang_code}"
            fieldset = (
                None,
                {
                    "classes": (
                        "suit-tab",
                        f"suit-tab-{tab_name}",
                    ),
                    "fields": [f"{field.name}" for field in i18n_field.get_translated_fields() if field.name.endswith(lang_code)],
                },
            )
            fieldsets.append(fieldset)
        return fieldsets

    @staticmethod
    def get_translations_tabs():
        return tuple(
            (f"lang-{lang_code}", _(f"Translation ({lang_code.upper()})"))
            for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES
            if lang_code is not settings.LANGUAGE_CODE
        )


class ModelAdminMixin(
    ListDisplayMixin,
    LangFieldsOnlyMixin,
    AdminListMixin,
    ExportCsvMixin,
    SoftDeleteMixin,
    CRUDMessageMixin,
    MCODAdminMixin,
):

    check_imported_obj_perms = False
    delete_selected_msg = None

    def get_actions(self, request):
        """Override delete_selected action description."""
        actions = super().get_actions(request)
        if self.delete_selected_msg and "delete_selected" in actions:
            func, action, description = actions.get("delete_selected")
            actions["delete_selected"] = func, action, self.delete_selected_msg
        return actions

    def get_ordering(self, request):
        ordering = super().get_ordering(request)
        has_created_field = hasattr(self, "model") and getattr(self.model, "has_created_field", False)
        return ("-created",) if has_created_field else ordering

    def has_add_permission(self, request):
        if self.check_imported_obj_perms:
            object_id = request.resolver_match.kwargs.get("object_id")
            obj = None
            if object_id:
                try:
                    obj = self.model.raw.get(id=object_id)
                except self.model.DoesNotExist:
                    pass
                if obj and obj.is_imported:
                    return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if self.check_imported_obj_perms and obj and obj.is_imported:
            return False
        return super().has_change_permission(request, obj=obj)


class ModelAdmin(ModelAdminMixin, admin.ModelAdmin):
    def action_checkbox(self, obj):
        return super().action_checkbox(obj)

    action_checkbox.short_description = mark_safe(
        '<input type="checkbox" id="action-toggle" aria-label="zaznacza wszystkie elementy w tabeli">'
    )


class NestedModelAdmin(ModelAdminMixin, nested_admin.NestedModelAdmin):
    pass


class UserAdmin(ListDisplayMixin, ExportCsvMixin, SoftDeleteMixin, BaseUserAdmin):
    soft_delete = True


class ObjectPermissionsStackedInline(
    AdminInlineLangMixin,
    AdminListMixin,
    nested_admin.NestedStackedInline,
    BaseObjectPermissionsStackedInline,
):

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        return self.extend_by_lang_fields(fields)


class ObjectPermissionsModelAdmin(
    ListDisplayMixin,
    LangFieldsOnlyMixin,
    ExportCsvMixin,
    SoftDeleteMixin,
    MCODAdminMixin,
    nested_admin.NestedModelAdmin,
    BaseObjectPermissionsModelAdmin,
):
    pass


class LogEntryAdmin(MCODAdminMixin, BaseLogEntryAdmin):
    pass


class TrashMixin(ModelAdmin):
    delete_selected_msg = _("Delete selected objects")
    related_objects_query = None
    cant_restore_msg = _("Couldn't restore following objects," " because their related objects are still removed: {}")

    excluded_actions = ["export_to_csv"]

    actions = ["restore_objects"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        for action in self.excluded_actions:
            actions.pop(action, None)
        return actions

    def restore_objects(self, request, queryset):
        to_restore = queryset
        cant_restore = None
        if self.related_objects_query:
            query = {self.related_objects_query + "__is_removed": True}
            to_restore = to_restore.exclude(**query)
            cant_restore = queryset.filter(**query)
        for obj in to_restore:
            obj.is_removed = False
            obj.save()
        if cant_restore:
            self.message_user(
                request,
                self.cant_restore_msg.format(", ".join([str(obj) for obj in cant_restore])),
            )
        self.message_user(request, _("Successfully restored objects: {}").format(to_restore.count()))

    restore_objects.short_description = _("Restore selected objects")

    def get_changelist(self, request, **kwargs):
        return MCODTrashChangeList

    def get_queryset(self, request):
        return self.model.trash.all()

    def has_add_permission(self, request, obj=None):
        return False

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context["show_save_and_continue"] = False
        if hasattr(self.model, "accusative_case"):
            if add:
                title = _("Add %s - trash")
            elif self.has_change_permission(request, obj):
                title = _("Change %s - trash")
            else:
                title = _("View %s - trash")
            context["title"] = title % self.model.accusative_case()
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "is_removed":
            kwargs["label"] = _("Removed:")
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class HistoryMixin:

    is_history_other = False
    is_history_with_unknown_user_rows = False

    def render_change_form(
        self,
        request: HttpRequest,
        context: Dict[str],
        add: bool = False,
        change: bool = False,
        form_url: str = "",
        obj: models.Model | None = None,
    ) -> TemplateResponse:
        context["has_history_permission"] = bool(obj and self.has_history_permission(request, obj))
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    def get_history(self, obj: models.Model, request: HttpRequest | None = None):
        queryset = LogEntry.objects.get_for_object(obj)
        if not self.is_history_with_unknown_user_rows:
            queryset = queryset.exclude(actor_id=1)
        return queryset

    def has_history_permission(self, request, obj):
        return self.has_change_permission(request, obj)

    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""
        # First check if the user can see this history.
        model = self.model
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, model._meta, object_id)

        if not self.has_history_permission(request, obj):
            raise PermissionDenied

        # Then get the history for this object.
        opts = model._meta
        app_label = opts.app_label
        action_list = self.get_history(obj, request)
        context = dict(
            self.admin_site.each_context(request),
            title=_("Change history: %s") % obj,
            action_list=action_list,
            module_name=str(capfirst(opts.verbose_name_plural)),
            object=obj,
            opts=opts,
            preserved_filters=self.get_preserved_filters(request),
        )
        context.update(extra_context or {})

        request.current_app = self.admin_site.name

        return TemplateResponse(
            request,
            self.object_history_template
            or [
                f"admin/{app_label}/{opts.model_name}/object_history.html",
                f"admin/{app_label}/object_history.html",
                "admin/object_history.html",
            ],
            context,
        )

    def obj_history(self, obj):
        try:
            product_url = reverse(
                "admin:%s_%s_history" % (obj._meta.app_label, obj._meta.model_name),
                args=(obj.id,),
            )
        except NoReverseMatch:
            product_url = ""

        html = mark_safe('<a href="%s" target="_blank">%s</a>' % (product_url, _("History")))

        return html

    obj_history.short_description = _("History")


def export_imports_to_csv(modeladmin, request, queryset):

    data_from_str: Optional[str] = request.POST.getlist("date_from")[0] or None
    data_to_str: Optional[str] = request.POST.getlist("date_to")[0] or None

    date_from: Optional[datetime] = datetime.strptime(data_from_str, "%Y-%m-%d") if data_from_str else None
    date_to: Optional[datetime] = datetime.strptime(data_to_str, "%Y-%m-%d") if data_to_str else None

    datasource_pks: QuerySet = queryset.values_list("pk", flat=True)
    imports: QuerySet = DataSourceImport.objects.filter(datasource__in=datasource_pks).order_by("datasource_id")

    if date_from is not None:
        imports = imports.filter(start__gte=date_from)
    if date_to is not None:
        imports = imports.filter(start__lt=date_to + timedelta(days=1))

    imports_pks: QuerySet = imports.values_list("pk", flat=True)

    if imports_pks.count() > 0:
        imports_pks: List[int] = list(imports_pks)

        generate_harvesters_imports_report.s(
            imports_pks,
            "harvester.DataSourceImport",
            request.user.id,
            now().strftime("%Y%m%d%H%M%S.%s"),
        ).apply_async_on_commit()
        messages.add_message(request, messages.SUCCESS, _("Task for CSV generation queued"))
    else:
        messages.add_message(request, messages.WARNING, _("No data was found for the report according to the specified criteria"))


def export_last_import_to_csv(modeladmin, request, queryset):

    chosen_datasource_pks: List[int] = list(row.id for row in queryset)

    dataset_pks_for_choosen_datasources: QuerySet = Dataset.objects.filter(source__in=chosen_datasource_pks).values_list(
        "id", flat=True
    )

    if dataset_pks_for_choosen_datasources.count() > 0:
        generate_harvesters_last_imports_report.s(
            chosen_datasource_pks,
            "harvester.DataSourceImport",
            request.user.id,
            now().strftime("%Y%m%d%H%M%S.%s"),
        ).apply_async_on_commit()

        messages.add_message(request, messages.SUCCESS, _("Task for CSV generation queued"))
    else:
        messages.add_message(request, messages.WARNING, _("No data was found for the report according to the specified criteria"))


class ExportHarvestersCsvActionForm(ActionForm):
    date_from = forms.DateField(
        required=False,
        help_text="Od daty",
    )

    date_to = forms.DateField(
        required=False,
        help_text="Do daty",
    )


class ExportHarvestersCsvMixin(ExportCsvMixin):

    export_selected_to_csv = False
    export_last_import_to_csv = False

    action_form = ExportHarvestersCsvActionForm

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.export_selected_to_csv and request.user.is_superuser:
            actions.update(
                {
                    "export_imports_to_csv": (
                        export_imports_to_csv,
                        "export_imports_to_csv",
                        _("Export selected to CSV"),
                    )
                }
            )
        if self.export_last_import_to_csv and request.user.is_superuser:
            actions.update(
                {
                    "export_last_import_to_csv": (
                        export_last_import_to_csv,
                        "export_last_import_to_csv",
                        _("Export last import to CSV"),
                    )
                }
            )

        return actions
