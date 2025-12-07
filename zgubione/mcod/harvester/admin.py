from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.urls import path, re_path, reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from mcod.core.decorators import prometheus_monitoring
from mcod.datasets.admin import PaginationInline
from mcod.datasets.models import Dataset
from mcod.harvester.forms import DataSourceAdminForm, DataSourceImportAdminForm
from mcod.harvester.models import DataSource, DataSourceImport, DataSourceTrash
from mcod.harvester.tasks import import_data_task
from mcod.harvester.views import ValidateXMLDataSourceView, get_progress
from mcod.lib.admin_mixins import ExportHarvestersCsvMixin, HistoryMixin, ModelAdmin, TrashMixin
from mcod.users.forms import FilteredSelectMultipleCustom


class CreatedListFilter(admin.filters.DateFieldListFilter):

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        now = timezone.now()
        this_year = now.replace(year=now.year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        self.links += (
            (
                _("More than year"),
                {
                    self.lookup_kwarg_until: str(this_year),
                },
            ),
        )


class DataSourceDatasets(PaginationInline):
    can_add = False
    can_change = False
    can_delete = False
    max_num = 0
    min_num = 0
    extra = 0
    suit_classes = "suit-tab suit-tab-datasets"
    model = Dataset
    fields = ["_title", "modified", "organization_title", "categories_titles"]
    page_param = "r"  # number of page for paginated results.
    verbose_name_plural = ""

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj=obj)

    def organization_title(self, obj):
        return obj.organization if obj.organization else "-"

    organization_title.short_description = _("Institution")

    def categories_titles(self, obj):
        return obj.categories_list_as_html

    categories_titles.short_description = _("Categories")

    def category_title(self, obj):
        return obj.category.title if obj.category else "-"

    category_title.short_description = _("Category")

    def _title(self, obj):
        return mark_safe(f'<a href="{obj.admin_change_url}">{obj.title}</a>')

    _title.short_description = _("Title")


class DataSourceImports(PaginationInline):
    can_add = False
    can_change = False
    can_delete = False
    form = DataSourceImportAdminForm
    template = "admin/harvester/datasourceimport-inline-list.html"
    fields = ("start", "end", "_status")
    max_num = 0
    min_num = 0
    extra = 0
    suit_classes = "suit-tab suit-tab-imports"

    model = DataSourceImport
    ordering = ("-id",)
    verbose_name_plural = ""

    def has_add_permission(self, request, obj=None):
        return False

    def _error_desc(self, obj):
        return mark_safe(obj.error_desc) or "-"

    _error_desc.short_description = _("Error description")

    def _start(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:harvester_datasourceimport_change", args=[obj.id]),
                obj.start_local_txt,
            )
        )

    _start.short_description = _("Start")

    def _status(self, obj):
        if not obj.end:
            return "-"
        template = '<span style="color:green;">{}</span>'
        if obj.is_failed:
            template = '<span style="color:red;">{}</span>'
        return mark_safe(template.format(obj.get_status_display()))

    _status.short_description = _("Result")

    def get_fields(self, request, obj=None):
        return (
            "_start",
            "end",
            "_status",
            "_error_desc",
        )

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj=obj)


@prometheus_monitoring
class DataSourceAdmin(ExportHarvestersCsvMixin, HistoryMixin, ModelAdmin):
    search_fields = ["name"]
    list_display = [
        "name",
        "type_col",
        "created_by_label",
        "created",
        "status_label",
        "last_import",
    ]
    list_filter = [
        ("created", CreatedListFilter),
        "status",
    ]
    form = DataSourceAdminForm
    add_form_template = "admin/harvester/datasource/change_form.html"
    autocomplete_fields = ["organization"]
    inlines = [DataSourceImports, DataSourceDatasets]
    readonly_fields = ["last_activation_date", "created_by", "modified_by"]
    actions_on_top = True
    add_msg_template = _('The data source "{obj}" was added successfully.')
    add_continue_msg_template = _('The data source "{obj}" was added successfully.')
    add_addanother_msg_template = _('The data source "{obj}" was added successfully. You may add another data source below.')

    change_msg_template = _('The data source "{obj}" was changed successfully.')
    change_continue_msg_template = _('The data source "{obj}" was changed successfully. You may edit it again below.')
    change_saveasnew_msg_template = _('The data source "{obj}" was added successfully. You may edit it again below.')
    change_addanother_msg_template = _('The data source "{obj}" was changed successfully. You may add another {name} below.')
    delete_selected_msg = _("Delete selected data sources")
    is_history_other = True
    obj_gender = "n"
    soft_delete = True
    suit_form_tabs = [
        ("general", _("General")),
        ("imports", _("Imports")),
    ]

    export_selected_to_csv = True
    export_last_import_to_csv = True

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj=obj)
        if obj:
            readonly_fields += ["created", "modified"]
        return readonly_fields

    def get_status_label(self, obj):
        choices_indexes = {status[0]: index for index, status in enumerate(obj.STATUS_CHOICES)}
        return obj.STATUS_CHOICES[choices_indexes[obj.status]][1].capitalize()

    def type_col(self, obj: DataSource) -> str:
        source_type = obj.get_source_type_display()
        if obj.source_type == "ckan":
            return f"{source_type} API"
        return source_type

    type_col.short_description = _("Type")
    type_col.admin_order_field = "source_type"

    def last_import(self, obj):
        if obj.last_import_status == "error":
            return mark_safe('<span style="color:red;">{}</span>'.format(obj.get_last_import_status_display()))
        return obj.get_last_import_status_display()

    last_import.short_description = _("Last import")
    last_import.admin_order_field = "last_import_status"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(Q(organization__in=request.user.organizations.iterator()) | Q(organization__isnull=True))
        return qs

    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [
            re_path(
                r"^validate_xml/(?P<task_id>[\w-]+)/$",
                staff_member_required(get_progress),
                name="validate-xml-task-status",
            ),
            path(
                "validate_xml/",
                staff_member_required(ValidateXMLDataSourceView.as_view()),
                name="validate-xml-view",
            ),
        ]
        return extra_urls + urls

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == "active":
            return False
        return super().has_delete_permission(request, obj=obj)

    def save_model(self, request, obj, form, change):
        if not obj.id:
            obj.created_by = request.user
        if change:
            obj.modified_by = request.user
        is_import_needed = obj.tracker.has_changed("status") and obj.is_active
        super().save_model(request, obj, form, change)
        if is_import_needed:
            import_data_task.s(obj.id, force=True).apply_async_on_commit()
            self.message_user(request, _("Import data task was launched!"), level=messages.SUCCESS)

    def get_fieldsets(self, request, obj=None):
        if obj:
            fields = (
                "name",
                "description",
                "created",
                "modified",
                "last_activation_date",
                "source_type",
                "source_hash",
                "xml_url",
                "portal_url",
                "api_url",
                "organization",
                "frequency_in_days",
                "created_by",
                "modified_by",
                "status",
                "license_condition_db_or_copyrighted",
                "categories",
                "institution_type",
                "emails",
                "sparql_query",
            )
        else:
            fields = (
                "name",
                "description",
                "last_activation_date",
                "source_type",
                "source_hash",
                "xml_url",
                "portal_url",
                "api_url",
                "organization",
                "frequency_in_days",
                "status",
                "license_condition_db_or_copyrighted",
                "categories",
                "institution_type",
                "emails",
                "sparql_query",
            )
        if obj:
            if obj.is_ckan:
                fields = (x for x in fields if x not in ["source_hash", "xml_url"])
            elif obj.is_xml:
                fields = (
                    x
                    for x in fields
                    if x
                    not in [
                        "portal_url",
                        "api_url",
                        "license_condition_db_or_copyrighted",
                        "categories",
                        "institution_type",
                    ]
                )
            elif obj.is_dcat:
                fields = (
                    x
                    for x in fields
                    if x
                    not in [
                        "source_hash",
                        "xml_url",
                        "portal_url",
                        "license_condition_db_or_copyrighted",
                        "categories",
                        "institution_type",
                    ]
                )
        return [
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": fields,
                },
            ),
        ]

    def get_suit_form_tabs(self, obj=None):
        suit_form_tabs = [x for x in self.suit_form_tabs]
        if obj:
            suit_form_tabs.append(("datasets", _("Datasets")))
        return suit_form_tabs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization" and not request.user.is_superuser:
            kwargs["queryset"] = request.user.organizations.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):

        def remove_jquery_urls(js_items):
            if isinstance(js_items, (list, tuple)):
                return [x for x in js_items if "vendor/jquery" not in str(x)]
            return js_items

        media = context.get("media")
        if media:
            media._js_lists = [remove_jquery_urls(x) for x in media._js_lists]
            context.update({"media": media})
        context.update({"suit_form_tabs": self.get_suit_form_tabs(obj)})
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)

        if db_field.name == "categories":
            attrs = {
                "data-from-box-label": _("Available categories"),
                "data-to-box-label": _("Selected categories"),
            }
            formfield.widget = admin.widgets.RelatedFieldWidgetWrapper(
                FilteredSelectMultipleCustom(formfield.label.lower(), False, attrs=attrs),
                db_field.remote_field,
                self.admin_site,
                can_add_related=False,
            )

        return formfield


@prometheus_monitoring
class DataSourceImportAdmin(ModelAdmin):

    exclude = ["is_report_email_sent"]  # email reports aren't implemented.

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _error_desc(self, obj):
        return mark_safe(obj.error_desc) or "-"

    _error_desc.short_description = _("Error description")

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=obj)
        fields[fields.index("error_desc")] = "_error_desc"
        return fields


class DataSourceTrashAdmin(HistoryMixin, TrashMixin):
    search_fields = ["name"]
    list_display = ("name", "created_by_label", "modified")
    readonly_fields = (
        "name",
        "description",
        "created",
        "modified",
        "last_activation_date",
        "portal_url",
        "api_url",
        "frequency_in_days",
        "created_by",
        "modified_by",
        "status",
        "license_condition_db_or_copyrighted",
        "categories_list",
        "institution_type",
        "emails",
    )
    fields = (
        "name",
        "description",
        "created",
        "modified",
        "last_activation_date",
        "portal_url",
        "api_url",
        "frequency_in_days",
        "created_by",
        "modified_by",
        "status",
        "license_condition_db_or_copyrighted",
        "categories_list",
        "institution_type",
        "emails",
        "is_removed",
    )
    is_history_other = True

    def categories_list(self, instance):
        return instance.categories_list_as_html

    categories_list.short_description = _("Categories")


admin.site.register(DataSource, DataSourceAdmin)
admin.site.register(DataSourceImport, DataSourceImportAdmin)
admin.site.register(DataSourceTrash, DataSourceTrashAdmin)
