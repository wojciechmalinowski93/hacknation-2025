from admin_confirm import AdminConfirmMixin
from dal_select2.widgets import ModelSelect2Multiple
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.options import TO_FIELD_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import AdminPasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.translation import gettext_lazy as _
from django_admin_multiple_choice_list_filter.list_filters import MultipleChoiceListFilter

from mcod.discourse.tasks import user_sync_task
from mcod.lib.admin_mixins import HistoryMixin, MCODChangeList, ModelAdmin, TrashMixin, UserAdmin
from mcod.organizations.models import Organization
from mcod.users.forms import (
    FilteredSelectMultipleCustom,
    MeetingForm,
    UserChangeForm,
    UserCreationForm,
)
from mcod.users.models import (
    ACADEMY_PERMS_CODENAMES,
    LABS_PERMS_CODENAMES,
    Meeting,
    MeetingFile,
    MeetingTrash,
    User,
)
from mcod.users.tasks import send_registration_email_task


class UserChangeList(MCODChangeList):
    def __init__(self, request, *args, **kwargs):
        self.role_query_string = ""
        user_roles = request.GET.getlist("role")
        for item in user_roles:
            self.role_query_string += f"&role={item}"
        super().__init__(request, *args, **kwargs)
        if self.role_query_string and "role" in self.params:
            del self.params["role"]

    def get_query_string(self, new_params=None, remove=None):
        query_string = super().get_query_string(new_params=new_params, remove=remove)
        if self.role_query_string:
            query_string += self.role_query_string
        return query_string


class UserRoleListFilter(MultipleChoiceListFilter):
    template = "admin/users/user/roles_filter.html"
    title = _("choose roles")
    parameter_name = "role"

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        self.used_parameters[self.parameter_name] = list(set(request.GET.getlist(self.parameter_name, [])))

    def lookups(self, request, model_admin):
        return (
            ("staff", _("Editor")),
            ("official", _("Official")),
            ("agent", _("Agent")),
            ("superuser", _("Admin")),
            ("aod_admin", _("AOD admin")),
            ("lod_admin", _("LOD admin")),
        )

    def value(self):
        return ",".join(self.used_parameters.get(self.parameter_name))

    def queryset(self, request, queryset):
        roles = list(set(request.GET.getlist(self.parameter_name)))
        query = Q()
        if "staff" in roles:
            query |= Q(is_staff=True)
        if "official" in roles:
            query |= Q(is_official=True)
        if "agent" in roles:
            query |= Q(is_agent=True)
        if "superuser" in roles:
            query |= Q(is_superuser=True)

        if "aod_admin" in roles:
            aod_admin_ids = queryset.filter(user_permissions__codename=ACADEMY_PERMS_CODENAMES[0]).values_list("id", flat=True)
            query |= Q(id__in=aod_admin_ids)
        if "lod_admin" in roles:
            lod_admin_ids = queryset.filter(user_permissions__codename=LABS_PERMS_CODENAMES[0]).values_list("id", flat=True)
            query |= Q(id__in=lod_admin_ids)
        return queryset.filter(query) if query else queryset


@admin.register(User)
class UserAdmin(HistoryMixin, AdminConfirmMixin, UserAdmin):
    add_form_template = "admin/users/user/add_form.html"
    actions_on_top = True
    autocomplete_fields = ["agent_organization_main"]
    export_to_csv = True
    list_display = [
        "email",
        "fullname",
        "state_label",
        "last_login",
        "is_staff",
        "is_official",
        "is_agent",
        "_is_superuser",
        "_is_academy_admin",
        "_is_labs_admin",
    ]

    ordering = ("email",)
    readonly_fields = ("extra_agents_list",)
    search_fields = ["email", "fullname"]

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    confirm_change = True
    confirmation_fields = ["is_agent"]

    def _change_confirmation_view(self, request, object_id, form_url, extra_context):  # noqa: C901
        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        if to_field and not self.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField("The field %s cannot be referenced." % to_field)

        model = self.model
        opts = model._meta

        add = object_id is None
        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied

            obj = None
        else:
            obj = self.get_object(request, unquote(object_id), to_field)
            if obj is None:
                return self._get_obj_does_not_exist_redirect(request, opts, object_id)

            if not self.has_view_or_change_permission(request, obj):
                raise PermissionDenied

        ModelForm = self.get_form(request, obj=obj, change=not add)
        is_agent_initial = obj.is_agent

        form = ModelForm(request.POST, request.FILES, instance=obj)
        form_validated = form.is_valid()
        new_object = self.save_form(request, form, change=not add) if form_validated else form.instance

        is_agent_disabled = False
        if form_validated:
            is_agent_changed = (
                form.fields["is_agent"].has_changed(is_agent_initial, new_object.is_agent) if "is_agent" in form.fields else False
            )
            is_agent_disabled = is_agent_changed and not new_object.is_agent

        is_confirm_required = bool(is_agent_disabled and new_object.user_schedules.exists())

        if not is_confirm_required:
            return super()._changeform_view(request, object_id, form_url, extra_context)

        # Parse raw form data from POST
        form_data = {}
        # Parse the original save action from request
        save_action = None
        for key in request.POST:
            if key in ["_save", "_saveasnew", "_addanother", "_continue"]:
                save_action = key

            if key.startswith("_") or key == "csrfmiddlewaretoken":
                continue
            form_data[key] = request.POST.get(key)
        context = {
            **self.admin_site.each_context(request),
            "preserved_filters": self.get_preserved_filters(request),
            "title": _("Confirm user change"),
            "subtitle": str(obj),
            "object_name": str(obj),
            "object_id": object_id,
            "app_label": opts.app_label,
            "model_name": opts.model_name,
            "opts": opts,
            "form_data": form_data,
            "add": add,
            "submit_name": save_action,
            **(extra_context or {}),
        }
        return self.render_change_confirmation(request, context)

    def get_changelist(self, request, **kwargs):
        return UserChangeList  # overriden to fix pagination links for multi user role filtering.

    def get_list_filter(self, request):
        return ["state", UserRoleListFilter]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "agent_organization_main":
            formfield.widget.attrs["class"] = "ignore-changes"  # prevents showing of confirmExitIfModified popup.
        return formfield

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return (
                "is_academy_admin",
                "is_labs_admin",
            )
        return super().get_readonly_fields(request, obj=obj)

    def get_form(self, request, obj=None, **kwargs):
        self._request = request
        form = super().get_form(request, obj=obj, **kwargs)
        form.declared_fields["phone"].required = form.base_fields["fullname"].required = request.user.is_normal_staff

        request_user = request.user
        form._request_user = request_user

        # attach `agent_organizations` and `organizations` fields to form only for superuser
        # this is related to `admin/users/user/extra.html` template which attach extra JS scripts
        #     when those fields exist in the form
        if request_user.is_superuser:
            form.base_fields["agent_organizations"] = forms.ModelMultipleChoiceField(
                queryset=Organization.objects.all(),
                widget=ModelSelect2Multiple(url="organization-autocomplete"),
                required=False,
                label="",
                help_text="",
            )
            form.base_fields["organizations"] = forms.ModelMultipleChoiceField(
                queryset=Organization.objects.all(),
                widget=ModelSelect2Multiple(url="organization-autocomplete"),
                required=False,
                label="",
                help_text="",
            )

        return form

    def send_registration_email_view(self, request, object_id, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        user = get_object_or_404(User, id=object_id, state="pending")
        send_registration_email_task.s(object_id).apply_async()
        messages.info(
            request,
            "Zadanie wysyłki wiadomości email z linkiem do aktywacji konta zostało zlecone.",
        )
        return HttpResponseRedirect(user.admin_change_url)

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                "<path:object_id>/send_registration_email/",
                self.send_registration_email_view,
                name="send-registration-email",
            ),
        ] + urls

    def extra_agents_list(self, obj):
        return obj.extra_agents_list or "-"

    extra_agents_list.allow_tags = True
    extra_agents_list.short_description = _("extra agents")

    def _is_superuser(self, obj):
        return obj.is_superuser

    _is_superuser.admin_order_field = "is_superuser"
    _is_superuser.boolean = True
    _is_superuser.short_description = _("Admin")

    def _is_academy_admin(self, obj):
        return getattr(obj, "is_academy_admin", False)

    _is_academy_admin.boolean = True
    _is_academy_admin.short_description = _("Admin AOD")

    def _is_labs_admin(self, obj):
        return getattr(obj, "is_labs_admin", False)

    _is_labs_admin.boolean = True
    _is_labs_admin.short_description = _("Admin LOD")

    suit_form_tabs = (("general", _("General")),)

    def get_state_value(self, obj):
        return obj.state

    def get_state_label(self, obj):
        return obj.get_state_display()

    def state_label(self, obj):
        return self._format_label(obj, "state")

    state_label.admin_order_field = "state"
    state_label.short_description = _("State")

    def get_fieldsets(self, request, obj=None):
        _agent_organizations_fields = [
            "agent_organization_main",
            "agent_organizations",
            "extra_agent_of",
        ]
        show_copy_agent_fields = obj is None or (
            not obj.from_agent and not obj.agent_organization_main and not obj.extra_agent_of
        )
        _copy_agent_fields = ["is_agent_opts", "from_agent"] if show_copy_agent_fields else []
        permissions_fields = [
            "is_staff",
            "organizations",
            "is_official",
            "is_superuser",
            "is_academy_admin",
            "is_labs_admin",
            "is_agent",
            *_copy_agent_fields,
            *_agent_organizations_fields,
            "extra_agents_list",
            "state",
        ]
        if not request.user.is_superuser:
            permissions_fields = [
                x
                for x in permissions_fields
                if x
                not in [
                    "agent_organizations",
                    "agent_organization_main",
                    "extra_agent_of",
                ]
            ]

        general_tab = (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": (["email", "password"] if obj else ["email", "password1", "password2"]),
            },
        )
        personal_info_tab = (
            _("Personal info"),
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": ["fullname", ("phone", "phone_internal"), "is_gov_linked"],
            },
        )
        permissions_tab = (
            (
                _("Permissions"),
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": permissions_fields,
                },
            )
            if request.user.is_superuser
            else (None, {"fields": []})
        )

        return [
            general_tab,
            personal_info_tab,
            permissions_tab,
        ]

    def get_queryset(self, request):
        qs = super().get_queryset(request).exclude(is_removed=True).exclude(is_permanently_removed=True)
        return qs if request.user.is_superuser else qs.filter(id=request.user.id)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        data = form.cleaned_data
        if "is_academy_admin" in data:
            obj.set_academy_perms(data["is_academy_admin"])
        if "is_labs_admin" in data:
            obj.set_labs_perms(data["is_labs_admin"])
        if settings.DISCOURSE_FORUM_ENABLED:
            user_sync_task.s(obj.pk).apply_async_on_commit()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        if settings.DISCOURSE_FORUM_ENABLED:
            user_sync_task.s(obj.pk).apply_async_on_commit()


class MeetingFilesInline(admin.StackedInline):
    model = MeetingFile
    fields = ["file"]
    extra = 0
    verbose_name_plural = _("Add files")
    ordering = ("created",)


class MeetingAdminMixin(HistoryMixin):
    delete_selected_msg = _("Delete selected meetings")
    filter_horizontal = ("members",)
    form = MeetingForm
    inlines = [
        MeetingFilesInline,
    ]
    is_history_other = True
    list_display = ["_title", "_venue", "start_date", "_duration_hours"]
    obj_gender = "n"
    search_fields = ["title"]

    def _title(self, obj):
        return obj.title

    _title.short_description = _("meeting name")
    _title.admin_order_field = "title"

    def _venue(self, obj):
        return obj.venue

    _venue.short_description = _("meeting venue")
    _venue.admin_order_field = "venue"

    def _duration_hours(self, obj):
        return obj.duration_hours

    _duration_hours.short_description = _("duration hours")
    _duration_hours.admin_order_field = "start_time"

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "members":
            kwargs["queryset"] = User.objects.agents()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "members":
            formfield.label = _("Add meeting members")
            formfield.widget = admin.widgets.RelatedFieldWidgetWrapper(
                FilteredSelectMultipleCustom(
                    _("members"),
                    False,
                    attrs={
                        "data-from-box-label": _("Agents list"),
                        "data-to-box-label": _("Agents added to meeting"),
                    },
                ),
                db_field.remote_field,
                self.admin_site,
                can_add_related=False,
            )
        return formfield


class MeetingAdmin(MeetingAdminMixin, ModelAdmin):

    actions_on_top = True
    fieldsets = [
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": ("title",),
            },
        ),
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": ("venue",),
            },
        ),
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": ("description",),
            },
        ),
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": ("start_date",),
            },
        ),
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": (
                    "start_time",
                    "end_time",
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
                "fields": ("members",),
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
    suit_form_tabs = (("general", _("General")),)


class MeetingTrashAdmin(MeetingAdminMixin, TrashMixin):

    readonly_fields = (
        "title",
        "venue",
        "description",
        "start_date",
        "start_time",
        "end_time",
        "members",
        "status",
    )
    fields = [field for field in readonly_fields] + ["is_removed"]


admin.site.register(Meeting, MeetingAdmin)
admin.site.register(MeetingTrash, MeetingTrashAdmin)


admin.site.site_header = "Otwarte Dane"
admin.site.site_title = "Otwarte Dane"
admin.site.index_title = "Otwarte Dane"
